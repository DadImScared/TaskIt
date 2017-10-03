import requests
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework import status, permissions, generics, serializers
from celery.result import AsyncResult

from .serializers import (TaskListsSerializer,
                          TaskListSerializer,
                          CreateTaskSerializer,
                          ListMembersSerializer,
                          TaskSerializer,
                          CreateTaskRemindersSerializer,
                          ItemPermissionSerializer
                          )
from .models import TaskList, TaskItem, User, TaskReminder
from .permissions import IsListOwnerOrItemCreator

# Create your views here.


class AccountConfirm(APIView):
    """View to verify email address"""

    def get(self, request, key, *args, **kwargs):
        """Make post request to verify_email endpoint"""
        r = requests.post('http://127.0.0.1:8000/rest-auth/registration/verify-email/', data={'key': key})
        return Response()


class TaskListsView(generics.ListCreateAPIView):
    serializer_class = TaskListsSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.todo_list.all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TaskListView(generics.RetrieveAPIView):
    queryset = TaskList.objects.all()
    serializer_class = TaskListSerializer


class TaskItemView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = (IsListOwnerOrItemCreator,)

    def get_object(self):
        item = get_object_or_404(TaskItem, task_list_id=self.kwargs['list_pk'], pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, item)
        return item


class CreateReminderView(APIView):
    lookup_field = 'pk'
    serializer_class = CreateTaskRemindersSerializer
    parser_classes = (JSONParser,)

    def post(self, request, list_pk, pk, *args, **kwargs):
        item = get_object_or_404(TaskItem, pk=self.kwargs['pk'])
        serializer = CreateTaskRemindersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(creator=request.user, item=item)
        return Response({"message": "Reminder created"}, status=status.HTTP_201_CREATED)

    def delete(self, request, list_pk, pk, *args, **kwargs):
        item = get_object_or_404(TaskItem, pk=self.kwargs['pk'])
        reminder = get_object_or_404(TaskReminder, item=item)
        AsyncResult(reminder.task_id).revoke()
        reminder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreateListItem(generics.ListCreateAPIView):
    queryset = TaskItem.objects.all()
    serializer_class = CreateTaskSerializer
    permission_classes = (permissions.IsAuthenticated, IsListOwnerOrItemCreator)

    def get_queryset(self):
        return TaskItem.objects.filter(task_list_id=self.kwargs['list_pk'])

    def perform_create(self, serializer):
        task_list = get_object_or_404(TaskList, pk=self.kwargs['list_pk'])
        serializer.save(creator=self.request.user, task_list=task_list)


class ListMembersView(APIView):

    def get(self, request, list_pk=None):
        """Return list of users that are members of task list"""
        list_id = list_pk
        my_list = TaskList.objects.get(pk=list_id)
        all_members = my_list.members.all()
        members = ListMembersSerializer(all_members, many=True, read_only=True)
        return Response(members.data)

    def post(self, request, list_pk=None):
        """Add user to task list"""
        try:
            email = request.data['email']
        except KeyError:
            return Response({"message": "Email of user to add required."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            add_user = get_object_or_404(User, email=email)
            task_list = get_object_or_404(TaskList, pk=list_pk)
            task_list.members.add(add_user)
            return Response({"message": "User added"}, status=status.HTTP_201_CREATED)


class ItemPermissionsView(generics.GenericAPIView):
    """View to remove or add permissions to an item on a list"""
    permission_classes = (IsListOwnerOrItemCreator, )

    def get_object(self):
        item = get_object_or_404(TaskItem, pk=self.kwargs['pk'], task_list=self.kwargs['list_pk'])
        self.check_object_permissions(self.request, item)
        return item

    def post(self, request, list_pk=None, pk=None):
        """Add permission to item"""
        task_list = get_object_or_404(TaskList, pk=list_pk)
        list_item = self.get_object()
        # if request.user != list_item.creator or request.user != task_list.owner:
        #     return Response({"message": "User doesn't have permission to grant permission"},
        #                     status=status.HTTP_401_UNAUTHORIZED)
        serializer = ItemPermissionSerializer(data=request.data, context={'task_list': task_list})
        serializer.is_valid(raise_exception=True)
        serializer.save(creator=request.user, item=list_item)
        return Response({"message": "Permission added"}, status=status.HTTP_201_CREATED)
