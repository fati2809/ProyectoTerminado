# 🔐 Microservices Application with Flask and JWT

This project is a microservices-based web application developed using Flask and JSON Web Tokens (JWT) for secure authentication and authorization. It follows a modular architecture with separate services for API gateway, authentication, user management, and task management, adhering to OWASP best practices for secure route protection and data handling.

---

## Features

- Microservices Architecture: Comprises API Gateway, Authentication Service, User Service, and Task Service.
- JWT-based Authentication: Secure user login and token-based route protection with 5-minute token expiration.
- Password Hashing: Uses Werkzeug's `generate_password_hash` for secure password storage.
- User Management: CRUD operations for users (register, list, get by ID, enable/disable, edit).
- Task Management: CRUD operations for tasks (register, list, get by ID, enable/disable, edit).
- SQLite Database: Persistent storage for users and tasks with secure schema initialization.
- Input Validation: Validates usernames, passwords, and date formats to ensure data integrity.
- Secure Route Protection: Uses JWT decorators to protect sensitive endpoints.
- Logging and Monitoring: Service logs are stored for debugging and monitoring.

--

## Version python
3.10 (Required for compatibility with `python3.10-venv` in Ubuntu)

## Dependences to install
See requirements.txt

--

## Project Structure

- api_gateway: Routes requests to appropriate microservices (runs on port 5000).
- auth_service: Handles user registration and login with JWT generation (runs on port 5001).
- user_service: Manages user CRUD operations (runs on port 5002).
- task_service: Manages task CRUD operations (runs on port 5003).
- shared_db: Shared database utilities for user and task services.
- logs: Directory for storing service logs.
- start_services.sh: Script to start all microservices.

-- 

## Steps to run

## 1. Create and Activate Virtual Environment (Ubuntu)
- Navigate to project directory
cd /path/to/project
- Install python3.10-venv
sudo apt install python3.10-venv
- Create virtual environment
python3 -m venv venv
- Activate virtual environment
source venv/bin/activate

## 2. Install Dependencies
pip install -r requirements.txt

## 3. Initialize Database
The database is automatically initialized when services start via the `init_db()` function in `shared_db/db.py`. Ensure the `database.db` file is writable in the project directory.

## 4. Start Microservices
- Make the script executable
chmod +x start_services.sh
- Run the script to start all services
./start_services.sh
- This starts:
   - API Gateway on http://localhost:5000
   - Authentication Service on http://localhost:5001
   - User Service on http://localhost:5002
   - Task Service on http://localhost:5003

   Logs are stored in the `logs/` directory for each service.

## 5. Stopping Services
To stop all services, use:
./stop_services.sh

## Testing the Application

- Register a user via POST /auth/register_user
- Log in via POST /auth/login to obtain a JWT token
- Use the token in the Authorization header (Bearer <token>) to access protected routes like /user/users, /task/tasks
- Test task operations (e.g., POST /task/register_task, PUT /task/tasks/<id>/enable)
- Check logs in the `logs/` directory for debugging
