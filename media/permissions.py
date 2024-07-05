from rest_framework import permissions


class IsQADevPermission(permissions.BasePermission):
    """
    Custom permission to check if the user belongs to the 'qa_dev' group.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return False

        # Check if the user is an admin
        if request.user.is_staff:
            return True  # Admin users have permission automatically

        # Check if the user belongs to the 'qa_dev' group
        return request.user.groups.filter(name__in=['qa_dev']).exists()


class IsPmPermission(permissions.BasePermission):
    """
    Custom permission to check if the user belongs to the 'qa_dev' group.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return False

        # Check if the user is an admin
        if request.user.is_staff:
            return True  # Admin users have permission automatically

        # Check if the user belongs to the 'qa_dev' group
        return request.user.groups.filter(name__in=['ba_pm']).exists()