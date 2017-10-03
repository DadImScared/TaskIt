from rest_framework import serializers, status
from rest_framework.reverse import reverse
from rest_framework.response import Response
from collections import OrderedDict
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from guardian.shortcuts import get_perms_for_model, assign_perm
from .models import TaskList, TaskItem, User, TaskReminder
from .tasks import create_random_user_accounts, send_delayed_mail


class TaskListsSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='tasklist-detail')

    class Meta:
        model = TaskList
        fields = ('id', 'name', 'url')


class ListMembersSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username')


class ItemHyperLinkMixin:
    """
    Mixin to link to an item with multiple parameters.
    Used in ItemRelatedHyperLink and ItemHyperLink
    """

    view_name = 'taskitem-detail'

    def get_url(self, obj, view_name, request, format):
        url_kwargs = {
            'list_pk': obj.task_list.id,
            'pk': obj.pk
        }
        return reverse(view_name, kwargs=url_kwargs, request=request, format=format)

    def get_object(self, view_name, view_args, view_kwargs):
        lookup_kwargs = {
            'task_list_id': view_kwargs['list_pk'],
            'pk': view_kwargs['pk']
        }
        return self.get_queryset().get(**lookup_kwargs)


class ItemRelatedHyperLink(ItemHyperLinkMixin, serializers.HyperlinkedRelatedField):
    """Custom hyperlink field that links to item in a list. Example /lists/1/items/23/"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TaskListSerializer(serializers.ModelSerializer):
    tasks = ItemRelatedHyperLink(many=True, read_only=True)

    class Meta:
        model = TaskList
        fields = ('id', 'name', 'tasks')


class ItemHyperLink(ItemHyperLinkMixin, serializers.HyperlinkedIdentityField):
    """Custom hyperlink field that links to item in a list. Example /lists/1/items/23/"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CreateTaskSerializer(serializers.HyperlinkedModelSerializer):
    url = ItemHyperLink(view_name='taskitem-detail')

    class Meta:
        model = TaskItem
        fields = ('id', 'name', 'url')


class ScheduleSerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False)
    hours = serializers.IntegerField(required=False)
    minutes = serializers.IntegerField(required=False)


def make_duration(**kwargs):
    return timezone.now() + timezone.timedelta(**kwargs)


class CreateTaskRemindersSerializer(serializers.Serializer):
    schedule = ScheduleSerializer(required=True)
    recipients = serializers.ListField(child=serializers.IntegerField(), required=False)

    def create(self, validated_data):
        schedule = validated_data.pop('schedule', {'hours': 24})
        creator = validated_data.get('creator')
        item = validated_data.get('item')
        members = validated_data.get('recipients', [creator.id])
        member_list = [user.email for user in item.task_list.members.filter(pk__in=members)]
        member_list.append(item.task_list.owner.email)

        if hasattr(item, 'taskreminder'):
            # return TaskReminder.objects.get(item=item)
            raise serializers.ValidationError("Task has reminder")
        duration = make_duration(**schedule)
        celery_task = send_delayed_mail.apply_async(eta=duration, kwargs={
            "subject": "Reminder for todo list",
            "recipients": member_list,
            "message": "Reminder for item {}".format(item.name)
        })
        # celery_task = create_random_user_accounts.apply_async(eta=duration)
        return TaskReminder.objects.create(creator=creator, item=item, task_id=celery_task.id)


class TaskSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(source='creator.username')
    task_reminder = serializers.BooleanField(source='taskreminder')

    class Meta:
        model = TaskItem
        fields = ('id', 'name', 'creator', 'done', 'task_reminder')
        read_only_fields = ('id', 'creator', 'task_reminder')

    def to_representation(self, instance):
        """Remove null fields from serializer"""
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


class ItemPermissionSerializer(serializers.Serializer):
    permission = serializers.ChoiceField(choices=[(perm.codename, perm.name) for perm in get_perms_for_model(TaskItem)])
    list_member = serializers.IntegerField(required=True)

    def validate_list_member(self, value):
        task_list = self.context['task_list']
        try:
            return task_list.members.get(pk=value)
        except ObjectDoesNotExist:
            raise serializers.ValidationError("User not a member of list")

    def create(self, validated_data):
        item = validated_data.get('item')
        list_member = validated_data.get('list_member')
        added_permission = validated_data.get('permission')
        assigned_perm = assign_perm(perm=added_permission, user_or_group=list_member, obj=item)
        return assigned_perm
