from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated , AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import ExpenseGroup, Expense, Contribution
from .serializers import UserSerializer, ExpenseGroupSerializer, ExpenseSerializer
from decimal import Decimal


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
        group = ExpenseGroup.objects.get(id=group_id)
        group.members.add(request.user)
        return Response({'message': 'Joined group successfully'}, status=status.HTTP_200_OK)
    except ExpenseGroup.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def add_expense(request, group_id):
#     group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
#     if not group:
#         return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

#     description = request.data.get('description')
#     amount = request.data.get('amount')
#     split_type = request.data.get('split_type')
#     contributions = request.data.get('contributions', [])

#     if not description or not amount or not split_type:
#         return Response({'error': 'Description, amount, and split type are required'}, status=status.HTTP_400_BAD_REQUEST)

#     if split_type not in ['equal', 'custom']:
#         return Response({'error': 'Invalid split type'}, status=status.HTTP_400_BAD_REQUEST)

#     expense = Expense.objects.create(group=group, description=description, amount=amount, split_type=split_type)

#     if split_type == 'equal':
#         per_member_amount = float(amount) / group.members.count()
#         for member in group.members.all():
#             Contribution.objects.create(expense=expense, user=member, amount=per_member_amount)
#     elif split_type == 'custom':
#         total_contribution = sum(c['amount'] for c in contributions)
#         if total_contribution != float(amount):
#             return Response({'error': 'Contributions do not match the total amount'}, status=status.HTTP_400_BAD_REQUEST)
#         for c in contributions:
#             try:
#                 user = User.objects.get(id=c['user_id'])
#                 Contribution.objects.create(expense=expense, user=user, amount=c['amount'])
#             except User.DoesNotExist:
#                 return Response({'error': f"User with ID {c['user_id']} not found"}, status=status.HTTP_404_NOT_FOUND)

#     return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def group_summary(request, group_id):
#     group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
#     if not group:
#         return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

#     balances = {}
#     total_expense = sum(exp.amount for exp in group.expenses.all())
#     equal_share = total_expense / group.members.count()

#     for member in group.members.all():
#         paid = sum(contribution.amount for contribution in Contribution.objects.filter(expense__group=group, user=member))
#         owed = equal_share
#         balances[member.username] = round(paid - owed, 2)

#     return Response({'balances': balances}, status=status.HTTP_200_OK)


from django.db.models import Sum

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_expense(request, group_id):
    """Add an expense to a group"""
    group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
    if not group:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

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
        # Calculate per member amount
        # per_member_amount = amount / Decimal(group.members.count())
        
        # Store only positive contributions for each member
        for member in group.members.all():
            if member == request.user:
                # The requester contributes the full amount they spent
                Contribution.objects.create(expense=expense, user=member, amount=amount)
            else:
                # Other members contribute their equal share
                Contribution.objects.create(expense=expense, user=member, amount=0)

    elif split_type == 'custom':
        # Contributions are mandatory for custom splits
        if not contributions:
            return Response({'error': 'Contributions are required for custom split'}, status=status.HTTP_400_BAD_REQUEST)

        total_contribution = sum(Decimal(c['amount']) for c in contributions)
        if total_contribution != amount:
            return Response({'error': 'Contributions do not match the total amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Store only positive contributions
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