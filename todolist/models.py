from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class TaskList(models.Model):
    owner = models.ForeignKey(User, related_name='todo_list')
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(User, related_name='todo_list_members')

    class Meta:
        permissions = (
            ('add_task', 'Add task'),
        )

    def __str__(self):
        return self.name


class TaskItem(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    creator = models.ForeignKey(User, related_name='item_created')
    task_list = models.ForeignKey(TaskList, related_name='tasks')
    done = models.BooleanField(default=False)
    name = models.CharField(max_length=200)

    class Meta:
        permissions = (
            ('add_reminder', 'Add reminder'),
            ('delete_reminder', 'Delete reminder'),
        )

    def __str__(self):
        return "Item: {}. From list {}".format(self.name, self.task_list)


class TaskReminder(models.Model):
    item = models.OneToOneField(TaskItem)
    #: celery task_id
    task_id = models.TextField()
    creator = models.ForeignKey(User, related_name='reminders')
