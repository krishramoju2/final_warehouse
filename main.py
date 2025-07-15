# Import necessary modules from FastAPI for building the API.
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Response
# Import security components for OAuth2 authentication.
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# Import Session from SQLAlchemy for database interaction.
from sqlalchemy.orm import Session
# Import typing for type hints (List, Optional, Union).
from typing import List, Optional, Union
# Import date and timedelta for date and time calculations.
from datetime import date, timedelta
# Import datetime module for handling dates and times.
import datetime, csv, io, zipfile, os, secrets
# Import StaticFiles for serving static frontend files.
from fastapi.staticfiles import StaticFiles
# Import HTMLResponse and RedirectResponse for serving HTML and redirecting.
from fastapi.responses import HTMLResponse, RedirectResponse
# Import CryptContext from passlib for password hashing.
from passlib.context import CryptContext
# Import JWTError and jwt from jose for JSON Web Token operations.
from jose import JWTError, jwt
# Import get_db, Base, and engine from database.py for database setup.
from database import get_db, Base, engine
# Import models for SQLAlchemy ORM models.
import models, schemas
# Import metrics and FastAPIMetrics for Prometheus integration.
from fastapi_prometheus import metrics, FastAPIMetrics
# For predictive analysis (in-memory for this example)
# Import pandas for data manipulation.
import pandas as pd
# Import LinearRegression from scikit-learn for basic predictive modeling.
from sklearn.linear_model import LinearRegression
# Import numpy for numerical operations, especially with arrays.
import numpy as np

# Create all database tables defined in models.py based on the Base metadata.
# This will create tables if they don't already exist in the 'inmemory.db' file.
Base.metadata.create_all(bind=engine)

# Retrieve the secret key from environment variables for JWT signing.
SECRET_KEY = os.getenv("SECRET_KEY")
# If SECRET_KEY is not found in environment variables, generate a temporary one.
# This is crucial for security: temporary keys will change on every restart, invalidating existing tokens.
# A warning is printed to alert the developer.
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    print("\n" + "="*80)
    print("WARNING: SECRET_KEY environment variable not found. A temporary key has been generated.")
    print("         This key WILL NOT persist across restarts.")
    print(f"         For production, set the SECRET_KEY environment variable to a strong, random value.")
    print("="*80 + "\n")

# Define the algorithm for JWT signing. HS256 is a symmetric algorithm.
ALGORITHM = "HS256"
# Define the expiration time for access tokens in minutes.
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Initialize the password hashing context using bcrypt.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Initialize OAuth2PasswordBearer for handling token authentication.
# tokenUrl specifies the endpoint where clients can request an access token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Function to verify a plain password against a hashed password.
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Function to hash a plain password.
def get_password_hash(password):
    return pwd_context.hash(password)

# Function to create a JWT access token.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    # Make a copy of the input data to avoid modifying the original.
    to_encode = data.copy()
    # Calculate the expiration time for the token.
    # If expires_delta is not provided, defaults to 15 minutes.
    expire = datetime.datetime.now(datetime.timezone.utc) + (expires_delta or timedelta(minutes=15))
    # Add the expiration timestamp to the token data.
    to_encode.update({"exp": expire})
    # Encode the token using the secret key and algorithm.
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Dependency function to get the current authenticated user.
# It decodes the JWT token from the Authorization header.
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Define an HTTPException for invalid credentials.
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        # Decode the JWT token.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Extract the username (subject) from the token payload.
        username: str = payload.get("sub")
        # If username is missing, raise credentials exception.
        if username is None:
            raise credentials_exception
        # Create a TokenData schema instance from the username.
        token_data = schemas.TokenData(username=username)
    except JWTError:
        # If JWT decoding fails, raise credentials exception.
        raise credentials_exception
    # Query the database to find the user by username.
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    # If user not found, raise credentials exception.
    if user is None:
        raise credentials_exception
    # Return the found user object.
    return user

# Dependency function to get the current active authenticated user.
# It relies on get_current_user and then checks if the user is active.
async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    # If the user is not active, raise an HTTPException.
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    # Return the active user.
    return current_user

# Dependency function to get the current active admin user.
# It relies on get_current_active_user and then checks if the user is an admin.
async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    # If the user is not an admin, raise a forbidden HTTPException.
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    # Return the admin user.
    return current_user

# Initialize the FastAPI application.
# Set title, description, and version for API documentation (Swagger UI).
app = FastAPI(title="Warehouse & Trucker Management API (Canada-Based)", description="Manage employee data, trucker profiles, and critical logistics documents efficiently. This API is designed for a Canada-based registry, focusing on compliance and quick search functionalities. Now includes Prometheus metrics, a manual archiving trigger, robust internal JWT-based Authentication/Authorization, Data Export capabilities, and a dedicated Frontend! Added Growth Analysis, Predictive Analysis, and Business Impact.", version="1.1.0")

# Initialize Prometheus metrics for the FastAPI application.
metrics.init_app(app)
# Add FastAPIMetrics middleware to expose default metrics.
app.add_middleware(FastAPIMetrics)

# Mount static files from the "frontend" directory.
# This makes files like index.html, style.css, script.js accessible at /static/.
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Define the login endpoint to get an access token.
@app.post("/token", response_model=schemas.Token, summary="Login and get an access token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Query the database to find the user by username.
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    # Check if user exists and if the provided password verifies against the stored hash.
    if not user or not verify_password(form_data.password, user.hashed_password):
        # If authentication fails, raise unauthorized HTTPException.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    # Define the access token expiration time.
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Create the access token.
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    # Return the access token and token type.
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint to create a new internal user (admin only).
@app.post("/users/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, summary="Create a new internal user (Admin only)", dependencies=[Depends(get_current_admin_user)])
## IMPORTANT INITIAL SETUP INSTRUCTION:
# For the very first time you run this application and need to create an initial admin user:
# 1. Temporarily comment out the line above: `dependencies=[Depends(get_current_admin_user)]`
# 2. Save main.py (server will reload).
# 3. Access the frontend in your browser and use the "Create Admin User" form to register your first admin.
# 4. IMMEDIATELY UNCOMMENT THE LINE ABOVE AND SAVE main.py again to re-enable security.
#    Failure to do so leaves your user creation endpoint vulnerable!
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if a user with the same username or email already exists.
    db_user = db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first()
    if db_user:
        # If user exists, raise a bad request HTTPException.
        raise HTTPException(status_code=400, detail="Username or Email already registered")
    # Hash the provided password.
    hashed_password = get_password_hash(user.password)
    # Create a new User model instance.
    db_user = models.User(username=user.username, email=user.email, full_name=user.full_name, hashed_password=hashed_password, is_admin=user.is_admin)
    # Add the new user to the database session.
    db.add(db_user)
    # Commit the transaction to save changes to the database.
    db.commit()
    # Refresh the db_user object to load any database-generated fields (like ID).
    db.refresh(db_user)
    # Return the newly created user.
    return db_user

# Endpoint to get details of the current authenticated user.
@app.get("/users/me/", response_model=schemas.UserOut, summary="Get current authenticated user's details", dependencies=[Depends(get_current_active_user)])
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    # Returns the user object obtained from the dependency.
    return current_user

# Root endpoint of the API, redirects to the static frontend index.html.
@app.get("/", summary="API Root / Frontend Home", response_class=HTMLResponse)
async def read_root():
    return RedirectResponse(url="/static/index.html")

# Endpoint to register a new employee.
@app.post("/employees/", response_model=schemas.EmployeeOut, status_code=status.HTTP_201_CREATED, summary="Register a new employee/warehouse worker (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def register_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    # Check if an employee with the same email already exists.
    db_employee = db.query(models.Employee).filter(models.Employee.email == employee.email).first()
    if db_employee:
        # If employee exists, raise a bad request HTTPException.
        raise HTTPException(status_code=400, detail="Employee with this email already registered")
    # Create a new Employee model instance from the schema data.
    db_employee = models.Employee(**employee.model_dump())
    # Add the new employee to the database session.
    db.add(db_employee)
    # Commit changes.
    db.commit()
    # Refresh the db_employee object.
    db.refresh(db_employee)
    # Return the newly created employee.
    return db_employee

# Endpoint to get a list of all registered employees.
@app.get("/employees/", response_model=List[schemas.EmployeeOut], summary="Get all registered employees (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Query all employees with pagination (skip and limit).
    return db.query(models.Employee).offset(skip).limit(limit).all()

# Endpoint to get a single employee by their ID, including their documents.
@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOutWithDocuments, summary="Get an employee by ID, including their documents (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_employee(employee_id: int, db: Session = Depends(get_db)):
    # Query the employee by ID. The `relationship` in models.py handles loading documents.
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if employee is None:
        # If employee not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    # Return the found employee with documents.
    return employee

# Endpoint to update an existing employee's details.
@app.put("/employees/{employee_id}", response_model=schemas.EmployeeOut, summary="Update an employee's details (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def update_employee(employee_id: int, employee: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    # Get the employee to update.
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if db_employee is None:
        # If employee not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    # Iterate through the provided update fields and update the employee object.
    # exclude_unset=True ensures only provided fields are updated.
    for key, value in employee.model_dump(exclude_unset=True).items():
        setattr(db_employee, key, value)
    # Add the modified employee to the session (for tracking changes).
    db.add(db_employee)
    # Commit changes.
    db.commit()
    # Refresh the object.
    db.refresh(db_employee)
    # Return the updated employee.
    return db_employee

# Endpoint to deactivate or delete an employee (soft delete to archive).
@app.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate or delete an employee (Requires Admin Auth)", dependencies=[Depends(get_current_admin_user)])
async def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    # Get the employee to delete.
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if db_employee is None:
        # If employee not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    # Soft delete: Move to archive table.
    # Create an ArchivedEmployee instance with details from the employee.
    archived_employee = models.ArchivedEmployee(
        original_id=db_employee.id,
        first_name=db_employee.first_name,
        last_name=db_employee.last_name,
        email=db_employee.email,
        phone_number=db_employee.phone_number,
        position=db_employee.position,
        is_active=db_employee.is_active,
        registration_date=db_employee.registration_date,
        archived_reason="Manual deletion from active records."
    )
    # Add the archived record.
    db.add(archived_employee)
    # Delete associated documents from the active documents table.
    db.query(models.Document).filter(models.Document.employee_id == employee_id).delete()
    # Delete the employee from the active employees table.
    db.delete(db_employee)
    # Commit the transaction.
    db.commit()
    # Return a 204 No Content response, indicating successful deletion.
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Endpoint to register a new trucker.
@app.post("/truckers/", response_model=schemas.TruckerOut, status_code=status.HTTP_201_CREATED, summary="Register a new trucker (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def register_trucker(trucker: schemas.TruckerCreate, db: Session = Depends(get_db)):
    # Check if a trucker with the same driver's license number already exists.
    if db.query(models.Trucker).filter(models.Trucker.driver_license_number == trucker.driver_license_number).first():
        raise HTTPException(status_code=400, detail="Trucker with this license number already registered")
    # If truck_id_number is provided, check if a trucker with the same truck ID already exists.
    if trucker.truck_id_number and db.query(models.Trucker).filter(models.Trucker.truck_id_number == trucker.truck_id_number).first():
        raise HTTPException(status_code=400, detail="Trucker with this truck ID number already registered")
    # Create a new Trucker model instance.
    db_trucker = models.Trucker(**trucker.model_dump())
    # Add the new trucker to the session.
    db.add(db_trucker)
    # Commit changes.
    db.commit()
    # Refresh the object.
    db.refresh(db_trucker)
    # Return the newly created trucker.
    return db_trucker

# Endpoint to get a list of all registered truckers.
@app.get("/truckers/", response_model=List[schemas.TruckerOut], summary="Get all registered truckers (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_truckers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Query all truckers with pagination.
    return db.query(models.Trucker).offset(skip).limit(limit).all()

# Endpoint to get a single trucker by their ID, including their documents.
@app.get("/truckers/{trucker_id}", response_model=schemas.TruckerOutWithDocuments, summary="Get a trucker by ID, including their documents (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_trucker(trucker_id: int, db: Session = Depends(get_db)):
    # Query the trucker by ID.
    trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if trucker is None:
        # If trucker not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker not found")
    # Return the found trucker with documents.
    return trucker

# Endpoint to update an existing trucker's details.
@app.put("/truckers/{trucker_id}", response_model=schemas.TruckerOut, summary="Update a trucker's details (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def update_trucker(trucker_id: int, trucker: schemas.TruckerUpdate, db: Session = Depends(get_db)):
    # Get the trucker to update.
    db_trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if db_trucker is None:
        # If trucker not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker not found")
    # Update fields.
    for key, value in trucker.model_dump(exclude_unset=True).items():
        setattr(db_trucker, key, value)
    # Add to session.
    db.add(db_trucker)
    # Commit changes.
    db.commit()
    # Refresh object.
    db.refresh(db_trucker)
    # Return updated trucker.
    return db_trucker

# Endpoint to deactivate or delete a trucker (soft delete to archive).
@app.delete("/truckers/{trucker_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate or delete a trucker (Requires Admin Auth)", dependencies=[Depends(get_current_admin_user)])
async def delete_trucker(trucker_id: int, db: Session = Depends(get_db)):
    # Get the trucker to delete.
    db_trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if db_trucker is None:
        # If trucker not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker not found")
    # Soft delete: Move to archive table.
    archived_trucker = models.ArchivedTrucker(
        original_id=db_trucker.id,
        first_name=db_trucker.first_name,
        last_name=db_trucker.last_name,
        email=db_trucker.email,
        phone_number=db_trucker.phone_number,
        driver_license_number=db_trucker.driver_license_number,
        province_of_issue=db_trucker.province_of_issue,
        truck_id_number=db_trucker.truck_id_number,
        company_name=db_trucker.company_name,
        is_active=db_trucker.is_active,
        registration_date=db_trucker.registration_date,
        archived_reason="Manual deletion from active records."
    )
    db.add(archived_trucker)
    # Delete associated documents.
    db.query(models.Document).filter(models.Document.trucker_id == trucker_id).delete()
    # Delete the trucker.
    db.delete(db_trucker)
    # Commit transaction.
    db.commit()
    # Return 204 No Content.
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Endpoint to upload a new document for an employee or trucker.
@app.post("/documents/", response_model=schemas.DocumentOut, status_code=status.HTTP_201_CREATED, summary="Upload a new document (for employee or trucker) (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def upload_document(document: schemas.DocumentCreate, db: Session = Depends(get_db)):
    # Determine if the document belongs to an employee or a trucker and retrieve the associated person.
    person = db.query(models.Employee).filter(models.Employee.id == document.employee_id).first() if document.employee_id else \
             (db.query(models.Trucker).filter(models.Trucker.id == document.trucker_id).first() if document.trucker_id else None)
    if not person:
        # If no associated person is found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated person not found.")
    # Create a new Document model instance.
    db_document = models.Document(**document.model_dump())
    # Add the new document.
    db.add(db_document)
    # Commit changes.
    db.commit()
    # Refresh object.
    db.refresh(db_document)
    # Return the newly created document.
    return db_document

# Endpoint to get a list of all uploaded documents.
@app.get("/documents/", response_model=List[schemas.DocumentOut], summary="Get all uploaded documents (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Query all documents with pagination.
    return db.query(models.Document).offset(skip).limit(limit).all()

# Endpoint to get a single document by its ID.
@app.get("/documents/{document_id}", response_model=schemas.DocumentOut, summary="Get a document by ID (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_document(document_id: int, db: Session = Depends(get_db)):
    # Query the document by ID.
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if document is None:
        # If document not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Return the found document.
    return document

# Endpoint to update a document's details (e.g., verification status).
@app.put("/documents/{document_id}", response_model=schemas.DocumentOut, summary="Update a document's details (e.g., verification status) (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def update_document(document_id: int, document: schemas.DocumentUpdate, db: Session = Depends(get_db)):
    # Get the document to update.
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_document is None:
        # If document not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Update fields.
    for key, value in document.model_dump(exclude_unset=True).items():
        # If 'is_verified' is being set to True and was previously False,
        # set the verification_date to today.
        if key == "is_verified" and value is True and db_document.is_verified is False:
            setattr(db_document, "verification_date", datetime.date.today())
        setattr(db_document, key, value)
    # Add to session.
    db.add(db_document)
    # Commit changes.
    db.commit()
    # Refresh object.
    db.refresh(db_document)
    # Return updated document.
    return db_document

# Endpoint to delete a document (soft delete to archive).
@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a document (Requires Admin Auth)", dependencies=[Depends(get_current_admin_user)])
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    # Get the document to delete.
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_document is None:
        # If document not found, raise not found HTTPException.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Soft delete: Move to archive table.
    archived_document = models.ArchivedDocument(
        original_id=db_document.id,
        document_type=db_document.document_type,
        file_path=db_document.file_path,
        upload_date=db_document.upload_date,
        is_verified=db_document.is_verified,
        verification_date=db_document.verification_date,
        verified_by=db_document.verified_by,
        employee_id=db_document.employee_id,
        trucker_id=db_document.trucker_id,
        archived_reason="Manual deletion from active records."
    )
    db.add(archived_document)
    # Delete the document from the active table.
    db.delete(db_document)
    # Commit transaction.
    db.commit()
    # Return 204 No Content.
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Endpoint for live search of employees or truckers.
@app.get("/search/", response_model=List[schemas.LiveSearchResult], summary="Quickly find truckers or employees by ID, license, or email (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def live_search(query: str, db: Session = Depends(get_db)):
    results = []
    # Try searching by ID directly first if the query is numeric.
    try:
        query_int = int(query)
        # Search employees by ID.
        employee = db.query(models.Employee).filter(models.Employee.id == query_int).first()
        if employee:
            results.append(schemas.LiveSearchResult(
                type="employee",
                id=employee.id,
                name=f"{employee.first_name} {employee.last_name}",
                identifier=employee.email,
                is_active=employee.is_active,
                details=schemas.EmployeeOut.model_validate(employee)
            ))
        # Search truckers by ID.
        trucker = db.query(models.Trucker).filter(models.Trucker.id == query_int).first()
        if trucker:
            results.append(schemas.LiveSearchResult(
                type="trucker",
                id=trucker.id,
                name=f"{trucker.first_name} {trucker.last_name}",
                identifier=trucker.driver_license_number,
                is_active=trucker.is_active,
                details=schemas.TruckerOut.model_validate(trucker)
            ))
    except ValueError:
        # If query is not an integer, search by string fields.
        pass # Not a number, continue to string searches

    # Search employees by first name, last name, or email (case-insensitive).
    employees_by_string = db.query(models.Employee).filter(
        (models.Employee.first_name.ilike(f"%{query}%")) |
        (models.Employee.last_name.ilike(f"%{query}%")) |
        (models.Employee.email.ilike(f"%{query}%"))
    ).all()
    for employee in employees_by_string:
        # Only add if not already found by ID to avoid duplicates.
        if not any(r.id == employee.id and r.type == "employee" for r in results):
            results.append(schemas.LiveSearchResult(
                type="employee",
                id=employee.id,
                name=f"{employee.first_name} {employee.last_name}",
                identifier=employee.email,
                is_active=employee.is_active,
                details=schemas.EmployeeOut.model_validate(employee)
            ))

    # Search truckers by first name, last name, email, driver license, truck ID, or company name (case-insensitive).
    truckers_by_string = db.query(models.Trucker).filter(
        (models.Trucker.first_name.ilike(f"%{query}%")) |
        (models.Trucker.last_name.ilike(f"%{query}%")) |
        (models.Trucker.email.ilike(f"%{query}%")) |
        (models.Trucker.driver_license_number.ilike(f"%{query}%")) |
        (models.Trucker.truck_id_number.ilike(f"%{query}%")) |
        (models.Trucker.company_name.ilike(f"%{query}%"))
    ).all()
    for trucker in truckers_by_string:
        # Only add if not already found by ID to avoid duplicates.
        if not any(r.id == trucker.id and r.type == "trucker" for r in results):
            results.append(schemas.LiveSearchResult(
                type="trucker",
                id=trucker.id,
                name=f"{trucker.first_name} {trucker.last_name}",
                identifier=trucker.driver_license_number,
                is_active=trucker.is_active,
                details=schemas.TruckerOut.model_validate(trucker)
            ))
    return results

# Endpoint to get overall compliance data for the dashboard.
@app.get("/dashboard/compliance", response_model=schemas.ComplianceData, summary="Get overall compliance data for dashboard (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_compliance_data(db: Session = Depends(get_db)):
    # Count total and active employees.
    total_employees = db.query(models.Employee).count()
    active_employees = db.query(models.Employee).filter(models.Employee.is_active == True).count()
    # Count total and active truckers.
    total_truckers = db.query(models.Trucker).count()
    active_truckers = db.query(models.Trucker).filter(models.Trucker.is_active == True).count()
    # Count total and verified documents.
    documents_uploaded = db.query(models.Document).count()
    documents_verified = db.query(models.Document).filter(models.Document.is_verified == True).count()
    unverified_documents = documents_uploaded - documents_verified

    # Return compliance data as a schema.
    return schemas.ComplianceData(
        total_employees=total_employees,
        active_employees=active_employees,
        total_truckers=total_truckers,
        active_truckers=active_truckers,
        documents_uploaded=documents_uploaded,
        documents_verified=documents_verified,
        unverified_documents=unverified_documents
    )

# Endpoint to trigger a manual archiving process for old records.
@app.post("/archive/manual_trigger", response_model=schemas.ArchiveSummary, summary="Manually trigger archiving of old records (Admin only)", dependencies=[Depends(get_current_admin_user)])
async def manual_archive_trigger(days_old: int = 365, db: Session = Depends(get_db)):
    # Calculate the cutoff date for archiving.
    cutoff_date = datetime.date.today() - timedelta(days=days_old)

    archived_emp_count = 0
    archived_truck_count = 0
    archived_doc_count = 0

    # Archive inactive employees older than cutoff_date.
    inactive_employees = db.query(models.Employee).filter(
        (models.Employee.is_active == False) | (models.Employee.registration_date < cutoff_date)
    ).all()
    for emp in inactive_employees:
        # Only archive if not already archived (by checking original_id in archived_employees).
        if not db.query(models.ArchivedEmployee).filter_by(original_id=emp.id).first():
            archived_employee = models.ArchivedEmployee(
                original_id=emp.id,
                first_name=emp.first_name,
                last_name=emp.last_name,
                email=emp.email,
                phone_number=emp.phone_number,
                position=emp.position,
                is_active=emp.is_active,
                registration_date=emp.registration_date,
                archived_reason=f"Automated archive: inactive or older than {days_old} days."
            )
            db.add(archived_employee)
            db.delete(emp) # Delete from active table
            archived_emp_count += 1

    # Archive inactive truckers older than cutoff_date.
    inactive_truckers = db.query(models.Trucker).filter(
        (models.Trucker.is_active == False) | (models.Trucker.registration_date < cutoff_date)
    ).all()
    for truck in inactive_truckers:
        if not db.query(models.ArchivedTrucker).filter_by(original_id=truck.id).first():
            archived_trucker = models.ArchivedTrucker(
                original_id=truck.id,
                first_name=truck.first_name,
                last_name=truck.last_name,
                email=truck.email,
                phone_number=truck.phone_number,
                driver_license_number=truck.driver_license_number,
                province_of_issue=truck.province_of_issue,
                truck_id_number=truck.truck_id_number,
                company_name=truck.company_name,
                is_active=truck.is_active,
                registration_date=truck.registration_date,
                archived_reason=f"Automated archive: inactive or older than {days_old} days."
            )
            db.add(archived_trucker)
            db.delete(truck) # Delete from active table
            archived_truck_count += 1

    # Archive documents that are very old or associated with archived persons.
    # For simplicity, let's archive all documents older than the cutoff regardless of verification status.
    old_documents = db.query(models.Document).filter(
        models.Document.upload_date < cutoff_date
    ).all()
    for doc in old_documents:
        if not db.query(models.ArchivedDocument).filter_by(original_id=doc.id).first():
            archived_document = models.ArchivedDocument(
                original_id=doc.id,
                document_type=doc.document_type,
                file_path=doc.file_path,
                upload_date=doc.upload_date,
                is_verified=doc.is_verified,
                verification_date=doc.verification_date,
                verified_by=doc.verified_by,
                employee_id=doc.employee_id,
                trucker_id=doc.trucker_id,
                archived_reason=f"Automated archive: uploaded more than {days_old} days ago."
            )
            db.add(archived_document)
            db.delete(doc) # Delete from active table
            archived_doc_count += 1

    db.commit()

    return schemas.ArchiveSummary(
        archived_employees=archived_emp_count,
        archived_truckers=archived_truck_count,
        archived_documents=archived_doc_count,
        message=f"Archiving process completed. Archived {archived_emp_count} employees, {archived_truck_count} truckers, and {archived_doc_count} documents."
    )

# Endpoint to export all data to CSV (employees, truckers, documents).
@app.get("/export/csv", summary="Export all data (employees, truckers, documents) to CSV (Admin only)", dependencies=[Depends(get_current_admin_user)])
async def export_all_data_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    csv_writer = csv.writer(output)

    # Export Employees
    csv_writer.writerow(["Employees"])
    csv_writer.writerow([
        "ID", "First Name", "Last Name", "Email", "Phone Number",
        "Position", "Is Active", "Registration Date"
    ])
    employees = db.query(models.Employee).all()
    for emp in employees:
        csv_writer.writerow([
            emp.id, emp.first_name, emp.last_name, emp.email, emp.phone_number,
            emp.position, emp.is_active, emp.registration_date
        ])
    csv_writer.writerow([]) # Blank line for separation

    # Export Truckers
    csv_writer.writerow(["Truckers"])
    csv_writer.writerow([
        "ID", "First Name", "Last Name", "Email", "Phone Number",
        "Driver License Number", "Province of Issue", "Truck ID Number",
        "Company Name", "Is Active", "Registration Date"
    ])
    truckers = db.query(models.Trucker).all()
    for truck in truckers:
        csv_writer.writerow([
            truck.id, truck.first_name, truck.last_name, truck.email, truck.phone_number,
            truck.driver_license_number, truck.province_of_issue, truck.truck_id_number,
            truck.company_name, truck.is_active, truck.registration_date
        ])
    csv_writer.writerow([]) # Blank line for separation

    # Export Documents
    csv_writer.writerow(["Documents"])
    csv_writer.writerow([
        "ID", "Document Type", "File Path", "Upload Date", "Is Verified",
        "Verification Date", "Verified By", "Employee ID", "Trucker ID"
    ])
    documents = db.query(models.Document).all()
    for doc in documents:
        csv_writer.writerow([
            doc.id, doc.document_type, doc.file_path, doc.upload_date, doc.is_verified,
            doc.verification_date, doc.verified_by, doc.employee_id, doc.trucker_id
        ])
    csv_writer.writerow([]) # Blank line for separation

    # Export Archived Employees
    csv_writer.writerow(["Archived Employees"])
    csv_writer.writerow([
        "ID", "Original ID", "First Name", "Last Name", "Email", "Phone Number",
        "Position", "Is Active", "Registration Date", "Archive Date", "Archived Reason"
    ])
    archived_employees = db.query(models.ArchivedEmployee).all()
    for emp in archived_employees:
        csv_writer.writerow([
            emp.id, emp.original_id, emp.first_name, emp.last_name, emp.email, emp.phone_number,
            emp.position, emp.is_active, emp.registration_date, emp.archive_date, emp.archived_reason
        ])
    csv_writer.writerow([]) # Blank line for separation

    # Export Archived Truckers
    csv_writer.writerow(["Archived Truckers"])
    csv_writer.writerow([
        "ID", "Original ID", "First Name", "Last Name", "Email", "Phone Number",
        "Driver License Number", "Province of Issue", "Truck ID Number",
        "Company Name", "Is Active", "Registration Date", "Archive Date", "Archived Reason"
    ])
    archived_truckers = db.query(models.ArchivedTrucker).all()
    for truck in archived_truckers:
        csv_writer.writerow([
            truck.id, truck.original_id, truck.first_name, truck.last_name, truck.email, truck.phone_number,
            truck.driver_license_number, truck.province_of_issue, truck.truck_id_number,
            truck.company_name, truck.is_active, truck.registration_date, truck.archive_date, truck.archived_reason
        ])
    csv_writer.writerow([]) # Blank line for separation

    # Export Archived Documents
    csv_writer.writerow(["Archived Documents"])
    csv_writer.writerow([
        "ID", "Original ID", "Document Type", "File Path", "Upload Date", "Is Verified",
        "Verification Date", "Verified By", "Employee ID", "Trucker ID", "Archive Date", "Archived Reason"
    ])
    archived_documents = db.query(models.ArchivedDocument).all()
    for doc in archived_documents:
        csv_writer.writerow([
            doc.id, doc.original_id, doc.document_type, doc.file_path, doc.upload_date, doc.is_verified,
            doc.verification_date, doc.verified_by, doc.employee_id, doc.trucker_id, doc.archive_date, doc.archived_reason
        ])
    csv_writer.writerow([]) # Blank line for separation

    # Create a Response object with CSV content type and attachment header.
    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=eArbor_export.csv"
    return response

# Endpoint to export all data to a ZIP file containing multiple CSVs.
@app.get("/export/zip", summary="Export all data (employees, truckers, documents, archived) to a ZIP file of CSVs (Admin only)", dependencies=[Depends(get_current_admin_user)])
async def export_all_data_zip(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
        # Helper to write CSV to zip
        def write_csv_to_zip(filename, headers, data_rows):
            csv_output = io.StringIO()
            csv_writer = csv.writer(csv_output)
            csv_writer.writerow(headers)
            csv_writer.writerows(data_rows)
            zf.writestr(filename, csv_output.getvalue())

        # Employees
        employees = db.query(models.Employee).all()
        employee_headers = ["ID", "First Name", "Last Name", "Email", "Phone Number", "Position", "Is Active", "Registration Date"]
        employee_rows = [[emp.id, emp.first_name, emp.last_name, emp.email, emp.phone_number, emp.position, emp.is_active, emp.registration_date] for emp in employees]
        write_csv_to_zip("employees.csv", employee_headers, employee_rows)

        # Truckers
        truckers = db.query(models.Trucker).all()
        trucker_headers = ["ID", "First Name", "Last Name", "Email", "Phone Number", "Driver License Number", "Province of Issue", "Truck ID Number", "Company Name", "Is Active", "Registration Date"]
        trucker_rows = [[truck.id, truck.first_name, truck.last_name, truck.email, truck.phone_number, truck.driver_license_number, truck.province_of_issue, truck.truck_id_number, truck.company_name, truck.is_active, truck.registration_date] for truck in truckers]
        write_csv_to_zip("truckers.csv", trucker_headers, trucker_rows)

        # Documents
        documents = db.query(models.Document).all()
        document_headers = ["ID", "Document Type", "File Path", "Upload Date", "Is Verified", "Verification Date", "Verified By", "Employee ID", "Trucker ID"]
        document_rows = [[doc.id, doc.document_type, doc.file_path, doc.upload_date, doc.is_verified, doc.verification_date, doc.verified_by, doc.employee_id, doc.trucker_id] for doc in documents]
        write_csv_to_zip("documents.csv", document_headers, document_rows)

        # Archived Employees
        archived_employees = db.query(models.ArchivedEmployee).all()
        archived_employee_headers = ["ID", "Original ID", "First Name", "Last Name", "Email", "Phone Number", "Position", "Is Active", "Registration Date", "Archive Date", "Archived Reason"]
        archived_employee_rows = [[emp.id, emp.original_id, emp.first_name, emp.last_name, emp.email, emp.phone_number, emp.position, emp.is_active, emp.registration_date, emp.archive_date, emp.archived_reason] for emp in archived_employees]
        write_csv_to_zip("archived_employees.csv", archived_employee_headers, archived_employee_rows)

        # Archived Truckers
        archived_truckers = db.query(models.ArchivedTrucker).all()
        archived_trucker_headers = ["ID", "Original ID", "First Name", "Last Name", "Email", "Phone Number", "Driver License Number", "Province of Issue", "Truck ID Number", "Company Name", "Is Active", "Registration Date", "Archive Date", "Archived Reason"]
        archived_trucker_rows = [[truck.id, truck.original_id, truck.first_name, truck.last_name, truck.email, truck.phone_number, truck.driver_license_number, truck.province_of_issue, truck.truck_id_number, truck.company_name, truck.is_active, truck.registration_date, truck.archive_date, truck.archived_reason] for truck in archived_truckers]
        write_csv_to_zip("archived_truckers.csv", archived_trucker_headers, archived_trucker_rows)

        # Archived Documents
        archived_documents = db.query(models.ArchivedDocument).all()
        archived_document_headers = ["ID", "Original ID", "Document Type", "File Path", "Upload Date", "Is Verified", "Verification Date", "Verified By", "Employee ID", "Trucker ID", "Archive Date", "Archived Reason"]
        archived_document_rows = [[doc.id, doc.original_id, doc.document_type, doc.file_path, doc.upload_date, doc.is_verified, doc.verification_date, doc.verified_by, doc.employee_id, doc.trucker_id, doc.archive_date, doc.archived_reason] for doc in archived_documents]
        write_csv_to_zip("archived_documents.csv", archived_document_headers, archived_document_rows)

    zip_buffer.seek(0) # Rewind the buffer to the beginning.
    # Return a StreamingResponse for the ZIP file.
    return Response(content=zip_buffer.getvalue(), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=eArbor_all_data.zip"})

# NEW ANALYTICS ENDPOINTS

# Endpoint for employee growth analysis.
@app.get("/analytics/employee-growth", response_model=schemas.EmployeeGrowthAnalysis, summary="Get employee registration growth analysis (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_employee_growth(db: Session = Depends(get_db)):
    # Query all employees and their registration dates.
    employees = db.query(models.Employee.registration_date).all()
    # Create a pandas DataFrame for easier date manipulation.
    df = pd.DataFrame(employees, columns=['registration_date'])
    # Convert 'registration_date' to datetime objects.
    df['registration_date'] = pd.to_datetime(df['registration_date'])
    # Set 'registration_date' as the DataFrame index.
    df.set_index('registration_date', inplace=True)

    # Resample registrations by month to get monthly counts.
    # .resample('M'): Resample to month end.
    # .size(): Count number of entries in each month.
    # .fillna(0): Fill months with no registrations with 0.
    monthly_counts = df.resample('M').size().fillna(0)

    # Prepare data for growth analysis.
    monthly_growth_data = []
    # Iterate through monthly counts, creating RegistrationGrowth schema objects.
    for month_end, count in monthly_counts.items():
        monthly_growth_data.append(schemas.RegistrationGrowth(date=month_end.date(), count=int(count)))

    # Calculate total employees.
    total_employees = db.query(models.Employee).count()

    # Calculate average monthly growth.
    average_monthly_growth = monthly_counts.mean() if len(monthly_counts) > 0 else 0

    # --- Predictive Analysis for Employee Growth (Simple Linear Regression) ---
    projected_next_month = None
    if len(monthly_counts) >= 2: # Need at least 2 data points for linear regression
        # Create a series of numerical indices for months (e.g., 0, 1, 2...).
        X = np.arange(len(monthly_counts)).reshape(-1, 1)
        # Use monthly counts as the target variable.
        y = monthly_counts.values
        # Initialize and train a Linear Regression model.
        model = LinearRegression()
        model.fit(X, y)
        # Predict the next month (index = last_month_index + 1).
        next_month_index = len(monthly_counts)
        projected_next_month = int(max(0, model.predict([[next_month_index]])[0])) # Ensure non-negative count

    # Return the aggregated growth analysis data.
    return schemas.EmployeeGrowthAnalysis(
        monthly_growth=monthly_growth_data,
        total_employees=total_employees,
        average_monthly_growth=average_monthly_growth,
        projected_next_month=projected_next_month
    )

# Endpoint for trucker type analysis and predictive analysis.
@app.get("/analytics/trucker-analysis", response_model=schemas.TruckerAnalysis, summary="Get trucker type distribution and predictive analysis (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_trucker_analysis(db: Session = Depends(get_db)):
    # Query all truckers.
    truckers = db.query(models.Trucker).all()
    # Create a DataFrame from trucker data.
    df = pd.DataFrame([t.__dict__ for t in truckers])

    province_distribution = {}
    company_distribution_list = []
    most_common_type = None
    predictive_trend = "Stable" # Default trend

    if not df.empty:
        # Province Distribution
        # Count occurrences of each province of issue.
        province_counts = df['province_of_issue'].value_counts().to_dict()
        province_distribution = province_counts

        # Company Distribution
        # Count occurrences of each company name.
        company_counts = df['company_name'].fillna('Independent').value_counts()
        total_truckers_count = len(df)
        for company, count in company_counts.items():
            # Calculate percentage for each company.
            percentage = (count / total_truckers_count) * 100 if total_truckers_count > 0 else 0
            company_distribution_list.append(schemas.TruckerTypeDistribution(
                company_name=company,
                count=int(count),
                percentage=round(percentage, 2)
            ))

        # Most Common Trucker Type (by company name)
        if not company_counts.empty:
            most_common_type = company_counts.idxmax()

        # --- Predictive Analysis for Trucker Types (Simplified Logic) ---
        # This is a simplified predictive trend based on recent changes or heuristics.
        # For a real ML model, you'd train on historical 'company_name' changes over time.
        # Example: if 'Independent' truckers have grown significantly in the last few months.
        df['registration_date'] = pd.to_datetime(df['registration_date'])
        recent_cutoff = datetime.date.today() - timedelta(days=90) # Last 3 months
        recent_truckers_df = df[df['registration_date'].dt.date >= recent_cutoff]

        if not recent_truckers_df.empty:
            recent_company_counts = recent_truckers_df['company_name'].fillna('Independent').value_counts(normalize=True)
            overall_company_counts = df['company_name'].fillna('Independent').value_counts(normalize=True)

            # Heuristic: If 'Independent' truckers' share has increased significantly recently
            if 'Independent' in recent_company_counts and 'Independent' in overall_company_counts:
                if recent_company_counts['Independent'] > overall_company_counts['Independent'] * 1.1: # 10% increase
                    predictive_trend = "Increasing trend towards independent truckers."
                elif recent_company_counts['Independent'] < overall_company_counts['Independent'] * 0.9: # 10% decrease
                    predictive_trend = "Decreasing trend in independent truckers; growth in company-affiliated."

    # Return the trucker analysis data.
    return schemas.TruckerAnalysis(
        province_distribution=province_distribution,
        company_distribution=company_distribution_list,
        most_common_type=most_common_type,
        predictive_trend=predictive_trend
    )

# Endpoint for business impact analysis.
@app.get("/analytics/business-impact", response_model=schemas.BusinessImpactAnalysis, summary="Get business impact analysis (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_business_impact(db: Session = Depends(get_db)):
    # Calculate total and active/inactive counts for churn rate.
    total_employees = db.query(models.Employee).count() + db.query(models.ArchivedEmployee).count()
    active_employees = db.query(models.Employee).filter(models.Employee.is_active == True).count()
    deactivated_employees = db.query(models.ArchivedEmployee).count()

    total_truckers = db.query(models.Trucker).count() + db.query(models.ArchivedTrucker).count()
    active_truckers = db.query(models.Trucker).filter(models.Trucker.is_active == True).count()
    deactivated_truckers = db.query(models.ArchivedTrucker).count()

    # Calculate churn rates.
    employee_churn_rate = (deactivated_employees / total_employees * 100) if total_employees > 0 else 0
    trucker_churn_rate = (deactivated_truckers / total_truckers * 100) if total_truckers > 0 else 0

    # Document compliance rate.
    total_documents = db.query(models.Document).count()
    verified_documents = db.query(models.Document).filter(models.Document.is_verified == True).count()
    document_compliance_rate = (verified_documents / total_documents * 100) if total_documents > 0 else 0

    # Qualitative impact assessments and recommendations based on simple heuristics.
    potential_revenue_impact = "Neutral"
    operational_efficiency_impact = "Good"
    strategic_recommendations = []

    if employee_churn_rate > 10: # Example threshold
        potential_revenue_impact = "Potential negative impact due to high employee turnover."
        operational_efficiency_impact = "Reduced due to constant retraining."
        strategic_recommendations.append("Implement employee retention programs (e.g., improved benefits, career development).")

    if trucker_churn_rate > 15: # Example threshold
        potential_revenue_impact = "Significant negative impact on logistics capacity and delivery consistency."
        operational_efficiency_impact = "Highly impacted, leading to delays and increased operational costs."
        strategic_recommendations.append("Analyze trucker satisfaction, improve payment terms, or offer loyalty incentives.")
        strategic_recommendations.append("Explore partnerships with more trucking companies.")

    if document_compliance_rate < 80: # Example threshold
        operational_efficiency_impact = "Suboptimal, increased risk of non-compliance and legal issues."
        potential_revenue_impact = "Potential fines and operational disruptions from regulatory non-compliance."
        strategic_recommendations.append("Enhance document verification processes and training for staff.")
        strategic_recommendations.append("Automate document reminders for employees and truckers.")

    if not strategic_recommendations:
        strategic_recommendations.append("Maintain current operational standards; consider proactive measures for future growth.")

    # Return business impact analysis.
    return schemas.BusinessImpactAnalysis(
        employee_churn_rate=round(employee_churn_rate, 2),
        trucker_churn_rate=round(trucker_churn_rate, 2),
        document_compliance_rate=round(document_compliance_rate, 2),
        potential_revenue_impact=potential_revenue_impact,
        operational_efficiency_impact=operational_efficiency_impact,
        strategic_recommendations=strategic_recommendations
    )
