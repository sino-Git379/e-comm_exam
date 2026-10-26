from decimal import Decimal
from django.db.models import F, Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from .pagination import CatalogPagination
from .permissions import AdminOrReadOnly
from .models import Category, Product, CartItem, Order, OrderItem
from .serializers import RegisterSerializer, CategorySerializer, ProductSerializer, CartItemSerializer, OrderSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD),
            },
            example={"username": "", "email": "", "password": ""},
        )
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProfileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"id": request.user.id, "username": request.user.username, "email": request.user.email})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ValidationError({"refresh": "This field is required."})
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            raise ValidationError({"refresh": "Invalid or expired refresh token."})
        return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)


class AdminWriteMixin:
    permission_classes = [AdminOrReadOnly]


class CategoryViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    pagination_class = CatalogPagination


class ProductViewSet(AdminWriteMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category").all().order_by("id")
    pagination_class = CatalogPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        search = params.get("search")
        category = params.get("category")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if category:
            queryset = queryset.filter(category_id=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        return queryset


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related("product")

    def perform_create(self, serializer):
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data.get("quantity", 1)
        item, created = CartItem.objects.get_or_create(
            user=self.request.user,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity += quantity
            if item.quantity > product.stock:
                raise ValidationError({"quantity": "Quantity exceeds available stock."})
            item.save(update_fields=["quantity"])


class CartSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = CartItem.objects.filter(user=request.user).select_related("product")
        total = sum((item.product.price * item.quantity for item in items), Decimal("0.00"))
        return Response({"items": CartItemSerializer(items, many=True).data, "total": total})


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product").order_by("-created_at")


class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = list(CartItem.objects.filter(user=request.user).select_related("product"))
        if not cart:
            raise ValidationError({"cart": "Cart is empty."})
        for item in cart:
            product = Product.objects.get(pk=item.product_id)
            if item.quantity > product.stock:
                raise ValidationError({"stock": f"Not enough stock for {product.name}."})

        order = Order.objects.create(user=request.user)
        total = Decimal("0.00")
        for item in cart:
            product = Product.objects.get(pk=item.product_id)
            OrderItem.objects.create(order=order, product=product, quantity=item.quantity, price=product.price)
            total += product.price * item.quantity
            Product.objects.filter(pk=product.pk).update(stock=F("stock") - item.quantity)
        order.total = total
        order.save(update_fields=["total"])
        CartItem.objects.filter(user=request.user).delete()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class CancelOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order.objects.filter(user=request.user), pk=pk)
        if order.status != Order.Status.PENDING:
            raise ValidationError({"status": "Only pending orders can be cancelled."})
        for item in order.items.all():
            Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order).data)


class SetOrderStatusView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        order = get_object_or_404(Order.objects.filter(user=request.user), pk=pk)
        new_status = request.data.get("status")
        if new_status not in Order.Status.values:
            raise ValidationError({"status": "Unknown order status."})
        order.status = new_status
        order.save(update_fields=["status"])
        return Response(OrderSerializer(order).data)
