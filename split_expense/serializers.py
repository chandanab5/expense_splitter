from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ExpenseGroup, Expense, Contribution

# Serializes the User model for registration and authentication
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username','email']

# Serializes the Group model including the members of the group
class ExpenseGroupSerializer(serializers.ModelSerializer):
    members = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username', many=True)

    class Meta:
        model = ExpenseGroup
        fields = ['id', 'name', 'members']

# Serializes the Contribution model, which links users to their contributions to an expense
class ContributionSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username')

    class Meta:
        model = Contribution
        fields = ['id', 'expense', 'user', 'amount']
        
# Serializes the Expense model to include the group, description, amount, and split type
class ExpenseSerializer(serializers.ModelSerializer):
    group = ExpenseGroupSerializer()  # Include the group details
    contributions = ContributionSerializer(many=True,read_only=True)

    class Meta:
        model = Expense
        fields = ['id', 'group', 'description', 'amount', 'split_type', 'contributions', 'created_at']

