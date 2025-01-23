from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated , AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import ExpenseGroup, Expense, Contribution
from .serializers import UserSerializer, ExpenseGroupSerializer, ExpenseSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username, password=password)
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_expense(request, group_id):
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

    expense = Expense.objects.create(group=group, description=description, amount=amount, split_type=split_type)

    if split_type == 'equal':
        per_member_amount = float(amount) / group.members.count()
        for member in group.members.all():
            Contribution.objects.create(expense=expense, user=member, amount=per_member_amount)
    elif split_type == 'custom':
        total_contribution = sum(c['amount'] for c in contributions)
        if total_contribution != float(amount):
            return Response({'error': 'Contributions do not match the total amount'}, status=status.HTTP_400_BAD_REQUEST)
        for c in contributions:
            try:
                user = User.objects.get(id=c['user_id'])
                Contribution.objects.create(expense=expense, user=user, amount=c['amount'])
            except User.DoesNotExist:
                return Response({'error': f"User with ID {c['user_id']} not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_summary(request, group_id):
    group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
    if not group:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    balances = {}
    total_expense = sum(exp.amount for exp in group.expenses.all())
    equal_share = total_expense / group.members.count()

    for member in group.members.all():
        paid = sum(contribution.amount for contribution in Contribution.objects.filter(expense__group=group, user=member))
        owed = equal_share
        balances[member.username] = round(paid - owed, 2)

    return Response({'balances': balances}, status=status.HTTP_200_OK)