from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
# Create your models here.

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(User, related_name="expense_groups")

    def __str__(self):
        return self.name

class Expense(models.Model):
    SPLIT_TYPE_CHOICES = [
        ("equal", "Equal"),
        ("custom", "Custom"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Expense amount must be greater than zero.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Contribution(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="contributions")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.user.username}: {self.amount}"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Contribution amount must be greater than zero.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)