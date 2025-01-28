from django.urls import path
from .views import register, groups, join_group, manage_expenses, group_summary, fetch_users, group_members
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('groups/', groups, name='groups'),
    path('groups/<int:group_id>/join/', join_group, name='join_group'),
    path('groups/<int:group_id>/expenses/', manage_expenses, name='add_expense'),
    path('groups/<int:group_id>/summary/', group_summary, name='group_summary'),
    path('users/', fetch_users, name='fetch_users'),
    path('groups/<int:group_id>/members/', group_members, name='group_members'),

]
