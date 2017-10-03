
from __future__ import absolute_import, unicode_literals
import string

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.core import mail

from celery import shared_task

import config


@shared_task
def create_random_user_accounts(total=10):
    for i in range(total):
        username = 'user_{}'.format(get_random_string(10, string.ascii_letters))
        email = '{}@example.com'.format(username)
        password = get_random_string(50)
        User.objects.create_user(username=username, email=email, password=password)
    return '{} random users created with success!'.format(total)


@shared_task
def send_delayed_mail(subject, recipients, message):
    mail.send_mail(
        subject=subject,
        recipient_list=recipients,
        message=message,
        from_email=config.EMAIL_USER
    )
