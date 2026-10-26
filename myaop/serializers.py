from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Category, Product, CartItem, Order, OrderItem

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "product", "product_name", "price", "quantity", "subtotal")
        read_only_fields = ("id", "product_name", "price", "subtotal")

    def get_subtotal(self, item):
        return item.product.price * item.quantity

    def validate(self, data):
        product = data.get("product", getattr(self.instance, "product", None))
        quantity = data.get("quantity", getattr(self.instance, "quantity", 1))
        if product and quantity > product.stock:
            raise serializers.ValidationError({"quantity": "Количество превышает остаток на складе."})
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("product", "product_name", "quantity", "price")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "status", "total", "created_at", "items")
