from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    CartViewSet,
    CartSummaryView,
    CancelOrderView,
    CategoryViewSet,
    CheckoutView,
    LogoutView,
    OrderViewSet,
    ProductViewSet,
    ProfileView,
    RegisterView,
    SetOrderStatusView,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("products", ProductViewSet)
router.register("cart", CartViewSet, basename="cart")
router.register("orders", OrderViewSet, basename="orders")

auth_urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
]

urlpatterns = [
    path("auth/", include((auth_urlpatterns, "auth"))),
    path("cart/summary/", CartSummaryView.as_view(), name="cart-summary"),
    path("orders/checkout/", CheckoutView.as_view(), name="order-checkout"),
    path("orders/<int:pk>/cancel/", CancelOrderView.as_view(), name="order-cancel"),
    path("orders/<int:pk>/set_status/", SetOrderStatusView.as_view(), name="order-set-status"),
    path("", include(router.urls)),
]
