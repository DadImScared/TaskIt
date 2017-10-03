from rest_framework import permissions
from django.shortcuts import get_object_or_404
from .models import TaskList


class IsListOwnerOrItemCreator(permissions.BasePermission):
    """Custom permission to only allow owners of a TaskList to add items to it"""

    def has_object_permission(self, request, view, obj):
        if obj.task_list.owner == request.user or obj.creator == request.user:
            return True
        else:
            if request.method == "GET" or request.method == "POST":
                return request.user in obj.task_list.members.all()
            elif request.method == "PATCH":
                return request.user.has_perm('change_taskitem', obj)
            elif request.method == "DELETE":
                return request.user.has_perm('delete_taskitem', obj)

    def has_permission(self, request, view):
        todo_list = get_object_or_404(TaskList, pk=view.kwargs['list_pk'])
        return request.user == todo_list.owner or request.user in todo_list.members.all()
