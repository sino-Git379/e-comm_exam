from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAdminUser


class AdminOrReadOnly(BasePermission):
    """Allow public reads and reserve catalog changes for staff users."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or IsAdminUser().has_permission(request, view)
