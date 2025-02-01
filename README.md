# Expense Splitter Backend

This is a Django REST Framework (DRF) project for managing expense groups, tracking expenses, and settling balances among group members. It provides endpoints for user registration, group management, expense tracking, and balance calculations.

## Features  
- User authentication using JWT  
- Expense group creation and management  
- Expense addition and tracking  
- Automatic expense splitting (equal/custom)  
- Balance calculations and settlement suggestions  
- User and group member management  

---

## Installation  

### Prerequisites  
- Python 3.8+  
- Django 5.1.3  
- Virtual environment (recommended)  

### Steps  

1. **Clone the repository**  
   ```bash
   git clone <repo-url>
   cd expense_splitter
   ```

2. **Create and activate a virtual environment**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**  
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (optional)**  
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**  
   ```bash
   python manage.py runserver 7777
   ```

---

## API Endpoints  

### Authentication  
- `POST /api/register/` – Register a new user  
- `POST /api/token/` – Get JWT access and refresh tokens  
- `POST /api/token/refresh/` – Refresh access token  

### Groups  
- `GET /api/groups/` – List user’s groups  
- `POST /api/groups/` – Create a new group  
- `POST  /api/groups/<group_id>/join/` – Add members to a group  
- `PATCH  /api/groups/<group_id>/edit/` – Rename a group  
- `DELETE  /api/groups/<group_id>/edit/` – Delete a group  
- `GET  /api/groups/<group_id>/members/` – Get members of a group  

### Expenses  
- `GET  /api/groups/<group_id>/expenses/` – List expenses in a group  
- `POST  /api/groups/<group_id>/expenses/` – Add an expense  
- `PATCH  /api/groups/<group_id>/expenses/<expense_id>/` – Edit an expense  
- `DELETE  /api/groups/<group_id>/expenses/<expense_id>/` – Delete an expense  

### Summary  
- `GET  /api/groups/<group_id>/summary/` – Get balance details of a group  

### Users  
- `GET  /api/users/` – Fetch all registered users  

---

## Running Tests  

To run the test suite:  
```bash
pytest
```

Ensure the database is set up correctly before running tests.  

---

## Tech Stack  
- **Backend**: Django, Django REST Framework  
- **Database**: SQLite3  
- **Authentication**: JWT (SimpleJWT)  
- **Testing**: Pytest, pytest-django  

---

