from django.urls import path
from .views import register, groups, join_group, add_expense, group_summary
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('groups/', groups, name='groups'),
    path('groups/<int:group_id>/join/', join_group, name='join_group'),
    path('groups/<int:group_id>/expenses/', add_expense, name='add_expense'),
    path('groups/<int:group_id>/summary/', group_summary, name='group_summary'),
]
