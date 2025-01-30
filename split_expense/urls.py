from django.urls import path
from .views import register, groups, join_group, manage_expenses, group_summary, fetch_users, group_members,edit_group_members,edit_or_delete_group,edit_or_delete_expense
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('groups/', groups, name='groups'),
    path('groups/<int:group_id>/join/', join_group, name='join_group'),
    path('groups/<int:group_id>/expenses/', manage_expenses, name='manage_expenses'),
    path('groups/<int:group_id>/summary/', group_summary, name='group_summary'),
    path('users/', fetch_users, name='fetch_users'),
    path('groups/<int:group_id>/members/', group_members, name='group_members'),
    path('groups/<int:group_id>/update/', edit_group_members, name='edit_group_members'),
    path('groups/<int:group_id>/edit/', edit_or_delete_group, name='edit_or_delete_group'),
    path('groups/<int:group_id>/expenses/<int:expense_id>/', edit_or_delete_expense, name='edit_or_delete_expense'),


]
