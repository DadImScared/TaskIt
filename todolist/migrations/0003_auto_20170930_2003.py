# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-01 00:03
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('todolist', '0002_auto_20170930_1800'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='taskitem',
            options={'permissions': (('add_reminder', 'Add reminder'), ('delete_reminder', 'Delete reminder'))},
        ),
    ]
