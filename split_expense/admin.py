from django.contrib import admin
from .models import ExpenseGroup, Expense, Contribution
# Register your models here.

admin.site.register(ExpenseGroup)
admin.site.register(Expense)
admin.site.register(Contribution)