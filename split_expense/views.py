from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated , AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import ExpenseGroup, Expense, Contribution
from .serializers import UserSerializer, ExpenseGroupSerializer, ExpenseSerializer
from decimal import Decimal
from django.db.models import Sum


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    if not username or not email or not password:
        return Response({'error': 'Username, email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username, password=password, email=email)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def groups(request):
    if request.method == 'GET':
        user_groups = request.user.expense_groups.all()
        serializer = ExpenseGroupSerializer(user_groups, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        name = request.data.get('name')
        if not name:
            return Response({'error': 'Group name is required'}, status=status.HTTP_400_BAD_REQUEST)
        group = ExpenseGroup.objects.create(name=name)
        group.members.add(request.user)
        return Response(ExpenseGroupSerializer(group).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request, group_id):
    try:
        # Fetch the group by its ID
        group = ExpenseGroup.objects.get(id=group_id)
        
        # Check if the current user is authorized to add members to the group
        if request.user not in group.members.all():
            return Response({'error': 'You are not authorized to add members to this group'}, status=status.HTTP_403_FORBIDDEN)

        # Get the username of the member to add
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the user to add by username
        try:
            user_to_add = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user is already a member of the group
        if user_to_add in group.members.all():
            return Response({'error': f'{user_to_add.username} is already a member of the group'}, status=status.HTTP_400_BAD_REQUEST)

        # Add the user to the group's members
        group.members.add(user_to_add)

        return Response({'message': f'{user_to_add.username} has been added to the group successfully'}, status=status.HTTP_200_OK)
    except ExpenseGroup.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_expenses(request, group_id):
    """Handle GET and POST for expenses in a group"""
    group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
    if not group:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Fetch all expenses for the group
        expenses = Expense.objects.filter(group=group)
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == 'POST':
        # Handle adding an expense
        description = request.data.get('description')
        amount = request.data.get('amount')
        split_type = request.data.get('split_type')
        contributions = request.data.get('contributions', [])

        if not description or not amount or not split_type:
            return Response({'error': 'Description, amount, and split type are required'}, status=status.HTTP_400_BAD_REQUEST)

        if split_type not in ['equal', 'custom']:
            return Response({'error': 'Invalid split type'}, status=status.HTTP_400_BAD_REQUEST)

        # Convert amount to Decimal
        try:
            amount = Decimal(amount)
        except Exception:
            return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the expense
        expense = Expense.objects.create(group=group, description=description, amount=amount, split_type=split_type)

        # Logic for splitting
        if split_type == 'equal':
            # Distribute the expense equally among members
            for member in group.members.all():
                if member == request.user:
                    Contribution.objects.create(expense=expense, user=member, amount=amount)
                else:
                    Contribution.objects.create(expense=expense, user=member, amount=0)

        elif split_type == 'custom':
            # Contributions are mandatory for custom splits
            if not contributions:
                return Response({'error': 'Contributions are required for custom split'}, status=status.HTTP_400_BAD_REQUEST)

            total_contribution = sum(Decimal(c['amount']) for c in contributions)
            if total_contribution != amount:
                return Response({'error': 'Contributions do not match the total amount'}, status=status.HTTP_400_BAD_REQUEST)

            # Store the contributions
            for c in contributions:
                try:
                    user = User.objects.get(id=c['user_id'])
                    Contribution.objects.create(expense=expense, user=user, amount=Decimal(c['amount']))
                except User.DoesNotExist:
                    return Response({'error': f"User with ID {c['user_id']} not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_summary(request, group_id):
    """Get a summary of balances for a group"""
    group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
    if not group:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    # Calculate total contributions and balances
    contributions = Contribution.objects.filter(expense__group=group)
    total_expense = contributions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
    equal_share = total_expense / group.members.count()

    balances = {}
    for member in group.members.all():
        paid = contributions.filter(user=member).aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        balances[member.username] = round(paid - equal_share, 2)

    # Convert balances into "who owes whom" format
    owes = []
    for user, balance in balances.items():
        if balance > 0:
            owes.append({'owed_to': user, 'amount': balance})
        elif balance < 0:
            owes.append({'owed_by': user, 'amount': abs(balance)})

    return Response({'balances': owes}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_users(request):
    """Fetch all registered users"""
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=200)