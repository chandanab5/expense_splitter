# Generated by Django 5.1.3 on 2025-01-23 08:39

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('split_expense', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Group',
            new_name='ExpenseGroup',
        ),
    ]
