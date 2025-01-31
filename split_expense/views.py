from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated , AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import ExpenseGroup, Expense, Contribution
from .serializers import UserSerializer, ExpenseGroupSerializer, ExpenseSerializer
from decimal import Decimal
from django.db.models import Sum

#User Registration
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    #Ensure required fields are provided
    if not username or not email or not password:
        return Response({'error': 'Username, email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    #Create and return the new user
    user = User.objects.create_user(username=username, password=password, email=email)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

#Expense Groups Management
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def groups(request):
    if request.method == 'GET':
        #Get all groups the user belongs to
        user_groups = request.user.expense_groups.all()
        serializer = ExpenseGroupSerializer(user_groups, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        #Create a new expense group
        name = request.data.get('name')
        if not name:
            return Response({'error': 'Group name is required'}, status=status.HTTP_400_BAD_REQUEST)
        group = ExpenseGroup.objects.create(name=name)
        group.members.add(request.user)
        return Response(ExpenseGroupSerializer(group).data, status=status.HTTP_201_CREATED)

#Joining an expense group
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request, group_id):
    try:
        # Fetch the group by its ID
        group = ExpenseGroup.objects.get(id=group_id)
        
        # Check if the current user is authorized to add members to the group
        if request.user not in group.members.all():
            return Response({'error': 'You are not authorized to add members to this group'}, status=status.HTTP_403_FORBIDDEN)

        # Get the list of usernames to add
        usernames = request.data.get('usernames', [])
        if not usernames:
            return Response({'error': 'At least one username is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate and fetch users
        users_to_add = []
        errors = []
        for username in usernames:
            try:
                user = User.objects.get(username=username)
                if user in group.members.all():
                    errors.append(f'{username} is already a member of the group')
                else:
                    users_to_add.append(user)
            except User.DoesNotExist:
                errors.append(f'User {username} not found')

        # If there are errors, return them
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # Add the users to the group's members
        group.members.add(*users_to_add)

        # Prepare success message
        added_users = [user.username for user in users_to_add]
        return Response({
            'message': f'Successfully added {len(added_users)} user(s) to the group',
            'added_users': added_users
        }, status=status.HTTP_200_OK)

    except ExpenseGroup.DoesNotExist:
        return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)

#Managing expenses in a group
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
            #Check if contributions sum up to total expense
            total_contribution = sum(Decimal(c['amount']) for c in contributions)
            if total_contribution != amount:
                return Response({'error': 'Contributions do not match the total amount'}, status=status.HTTP_400_BAD_REQUEST)

            # Store the contributions
            errors = []
            for c in contributions:
                username = c.get('username')
                amount = Decimal(c.get('amount'))
                if not username or amount is None:
                    errors.append(f"Invalid contribution data: {c}")
                    continue

                try:
                    user = User.objects.get(username=username)
                    if user not in group.members.all():
                        errors.append(f"User {username} is not a member of the group")
                        continue
                    Contribution.objects.create(expense=expense, user=user, amount=amount)
                except User.DoesNotExist:
                    errors.append(f"User {username} not found")

            # If there are errors, delete the expense and return the errors
            if errors:
                expense.delete()
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)

#Fetching group summary
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_members(request, group_id):
    """Fetch members of a group"""
    group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
    if not group:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    members = group.members.all()
    serializer = UserSerializer(members, many=True)
    return Response({'members': serializer.data}, status=status.HTTP_200_OK)

@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def edit_or_delete_group(request, group_id):
    """Edit or delete a group"""
    try:
        group = ExpenseGroup.objects.get(id=group_id, members__in=[request.user])
    except ExpenseGroup.DoesNotExist:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PATCH':
        # Edit group name
        new_name = request.data.get('name')
        if not new_name:
            return Response({'error': 'Group name is required'}, status=status.HTTP_400_BAD_REQUEST)
        group.name = new_name
        group.save()
        return Response(ExpenseGroupSerializer(group).data, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        # Delete the group
        group.delete()
        return Response({'message': 'Group deleted successfully'}, status=status.HTTP_200_OK)

@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def edit_or_delete_expense(request, group_id, expense_id):
    """Edit or delete an expense in a group"""
    group = ExpenseGroup.objects.filter(id=group_id, members__in=[request.user]).first()
    if not group:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    try:
        expense = Expense.objects.get(id=expense_id, group=group)
    except Expense.DoesNotExist:
        return Response({'error': 'Expense not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PATCH':
        # Edit expense details
        description = request.data.get('description', expense.description)
        amount = request.data.get('amount', expense.amount)
        split_type = request.data.get('split_type', expense.split_type)

        if not description or not amount or not split_type:
            return Response({'error': 'Description, amount, and split type are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate split type
        if split_type not in ['equal', 'custom']:
            return Response({'error': 'Invalid split type'}, status=status.HTTP_400_BAD_REQUEST)

        # Convert amount to Decimal
        try:
            amount = Decimal(amount)
        except Exception:
            return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

        expense.description = description
        expense.amount = amount
        expense.split_type = split_type
        expense.save()

        # Update contributions if necessary
        if split_type == 'equal':
            Contribution.objects.filter(expense=expense).delete()
            for member in group.members.all():
                if member == request.user:
                    Contribution.objects.create(expense=expense, user=member, amount=amount)
                else:
                    Contribution.objects.create(expense=expense, user=member, amount=0)

        elif split_type == 'custom':
            contributions = request.data.get('contributions', [])
            if not contributions:
                return Response({'error': 'Contributions are required for custom split'}, status=status.HTTP_400_BAD_REQUEST)

            total_contribution = sum(Decimal(c['amount']) for c in contributions)
            if total_contribution != amount:
                return Response({'error': 'Contributions do not match the total amount'}, status=status.HTTP_400_BAD_REQUEST)

            Contribution.objects.filter(expense=expense).delete()
            for c in contributions:
                username = c.get('username')
                user_amount = Decimal(c.get('amount'))
                try:
                    user = User.objects.get(username=username)
                    if user in group.members.all():
                        Contribution.objects.create(expense=expense, user=user, amount=user_amount)
                except User.DoesNotExist:
                    return Response({'error': f'User {username} not found'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ExpenseSerializer(expense).data, status=status.HTTP_200_OK)

    elif request.method == 'DELETE':
        # Delete the expense and associated contributions
        expense.delete()
        return Response({'message': 'Expense deleted successfully'}, status=status.HTTP_200_OK)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_group_members(request, group_id):
    """Edit group members (add or remove users)"""
    try:
        group = ExpenseGroup.objects.get(id=group_id, members__in=[request.user])
    except ExpenseGroup.DoesNotExist:
        return Response({'error': 'Group not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get('action')
    usernames = request.data.get('usernames', [])
    
    #Ensure valid actions are provided
    if action not in ['add', 'remove']:
        return Response({'error': 'Invalid action. Use "add" or "remove"'}, status=status.HTTP_400_BAD_REQUEST)

    if not usernames:
        return Response({'error': 'At least one username is required'}, status=status.HTTP_400_BAD_REQUEST)

    errors = []
    users_to_modify = []
    
    for username in usernames:
        try:
            user = User.objects.get(username=username)
            if action == 'add' and user in group.members.all():
                errors.append(f'{username} is already a member of the group') #adds user
            elif action == 'remove' and user not in group.members.all():
                errors.append(f'{username} is not a member of the group') #removes user
            else:
                users_to_modify.append(user)
        except User.DoesNotExist:
            errors.append(f'User {username} not found')

    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'add':
        group.members.add(*users_to_modify)
        message = f'Successfully added {len(users_to_modify)} user(s) to the group'
    else:  # action == 'remove'
        group.members.remove(*users_to_modify)
        message = f'Successfully removed {len(users_to_modify)} user(s) from the group'

    return Response({'message': message, 'modified_users': [user.username for user in users_to_modify]}, status=status.HTTP_200_OK)