from rest_framework import permissions


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow only superusers to create, update, or delete,
    but allow all users to view.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True  # Allow any user to view (GET, HEAD, OPTIONS)
        return request.user and request.user.is_superuser


class IsAccountOwner(permissions.BasePermission):
    """
    Custom permission to allow only the current user to create objects.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request

        # Write permissions are only allowed to the owner of the object
        return obj.id == request.user.id


class IsBookOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Write permissions are only allowed to the owner of the object
        return obj.author == request.user


class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request

        # Write permissions are only allowed to the owner of the object
        return obj.user == request.user


class IsAuthor(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request

        # Write permissions are only allowed to the owner of the object
        return obj.author == request.user.id