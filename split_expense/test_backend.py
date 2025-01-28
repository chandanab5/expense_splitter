import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import ExpenseGroup, Expense, Contribution
from decimal import Decimal

@pytest.mark.django_db
def test_register_user(client):
    url = reverse('register')
    data = {
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'testpassword'
    }
    response = client.post(url, data, content_type='application/json')
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.count() == 1
    assert User.objects.first().username == 'testuser'


@pytest.mark.django_db
def test_create_group(client, authenticated_user):
    url = reverse('groups')
    data = {'name': 'Test Group'}
    token = get_jwt_token(authenticated_user)
    response = client.post(url, data, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code == status.HTTP_201_CREATED
    assert ExpenseGroup.objects.count() == 1
    assert ExpenseGroup.objects.first().name == 'Test Group'


@pytest.mark.django_db
def test_get_groups(client, authenticated_user):
    group = ExpenseGroup.objects.create(name='Test Group')
    group.members.add(authenticated_user)
    url = reverse('groups')
    token = get_jwt_token(authenticated_user)
    response = client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


@pytest.mark.django_db
def test_join_group(client, authenticated_user):
    # Create another user to add to the group
    new_user = User.objects.create_user(username='testuser2', password='testpassword2')
    # Create a group and add the authenticated_user to the group
    group = ExpenseGroup.objects.create(name='Test Group')
    group.members.add(authenticated_user)
    # Define the URL for joining the group
    url = reverse('join_group', kwargs={'group_id': group.id})
    # Data to add a new user to the group
    data = {'usernames': ['testuser2']}  # Properly formatted list of usernames
    # Get the JWT token for the authenticated user
    token = get_jwt_token(authenticated_user)
    # Send POST request to join the group
    response = client.post(url, data, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    # Assert that the response status is OK (200)
    assert response.status_code == status.HTTP_200_OK

    assert isinstance(response.data,dict)
    assert 'added_users' in response.data

    added_users = response.data['added_users']
    assert 'testuser2' in added_users
    
@pytest.mark.django_db
def test_manage_expenses(client, authenticated_user):
    # Create a group and add the authenticated_user to the group
    group = ExpenseGroup.objects.create(name='Test Group')
    group.members.add(authenticated_user)

    # Test case for equal split
    url = reverse('manage_expenses', kwargs={'group_id': group.id})
    data_equal_split = {
        'description': 'Test Expense Equal Split',
        'amount': '100.00',
        'split_type': 'equal'
    }
    token = get_jwt_token(authenticated_user)
    response_equal = client.post(url, data_equal_split, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response_equal.status_code == status.HTTP_201_CREATED
    assert Expense.objects.count() == 1
    assert Expense.objects.first().description == 'Test Expense Equal Split'

    # Test case for custom split
    data_custom_split = {
        'description': 'Test Expense Custom Split',
        'amount': '100.00',
        'split_type': 'custom',
        'contributions': [
            {'username': authenticated_user.username, 'amount': '60.00'},
            {'username': 'testuser2', 'amount': '40.00'}
        ]
    }
    
    # Create another user to add to the group
    new_user = User.objects.create_user(username='testuser2', password='testpassword2')
    group.members.add(new_user)

    # Send request for custom split
    response_custom = client.post(url, data_custom_split, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
    
    # Check if the expense is created and response status is 201 Created
    assert response_custom.status_code == status.HTTP_201_CREATED
    assert Expense.objects.count() == 2
    assert Expense.objects.last().description == 'Test Expense Custom Split'
    
    # Check if the contributions are correctly created
    contributions = Contribution.objects.filter(expense=Expense.objects.last())
    assert contributions.count() == 2
    assert contributions.filter(user=authenticated_user, amount=Decimal('60.00')).exists()
    assert contributions.filter(user=new_user, amount=Decimal('40.00')).exists()


@pytest.mark.django_db
def test_get_expenses(client, authenticated_user):
    group = ExpenseGroup.objects.create(name='Test Group')
    group.members.add(authenticated_user)
    expense = Expense.objects.create(group=group, description='Test Expense', amount=100.00, split_type='equal')
    url = reverse('manage_expenses', kwargs={'group_id': group.id})
    token = get_jwt_token(authenticated_user)
    response = client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['description'] == expense.description

@pytest.mark.django_db
def test_group_summary(client, authenticated_user):
    group = ExpenseGroup.objects.create(name='Test Group')
    group.members.add(authenticated_user)
    url = reverse('group_summary', kwargs={'group_id': group.id})
    token = get_jwt_token(authenticated_user)
    response = client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code == status.HTTP_200_OK
    assert 'balances' in response.data

@pytest.mark.django_db
def test_fetch_users(client, authenticated_user):
    url = reverse('fetch_users')
    token = get_jwt_token(authenticated_user)
    response = client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) > 0

@pytest.mark.django_db
def test_group_members(client, authenticated_user):
    group = ExpenseGroup.objects.create(name='Test Group')
    group.members.add(authenticated_user)
    url = reverse('group_members', kwargs={'group_id': group.id})
    token = get_jwt_token(authenticated_user)
    response = client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['members']) == 1

@pytest.fixture
def authenticated_user():
    user = User.objects.create_user(username='testuser', password='testpassword')
    return user

# Helper function to get JWT token
def get_jwt_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)
