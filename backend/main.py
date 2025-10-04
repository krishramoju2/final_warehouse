from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta
import datetime, csv, io, zipfile, os, secrets
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np

from .database import get_db, Base, engine
from . import models, schemas

# Prometheus Instrumentation
from prometheus_fastapi_instrumentator import Instrumentator

# Create tables
Base.metadata.create_all(bind=engine)

# JWT & Auth
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Dependency functions
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Could not validate credentials", 
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

# FastAPI app setup
app = FastAPI(
    title="Warehouse & Trucker Management API (Canada-Based)",
    description="Manage employee data, trucker profiles, and critical logistics documents efficiently. This API is designed for a Canada-based registry, focusing on compliance and quick search functionalities. Now includes Prometheus metrics, a manual archiving trigger, robust internal JWT-based Authentication/Authorization, Data Export capabilities, and a dedicated Frontend! Added Growth Analysis, Predictive Analysis, and Business Impact.",
    version="1.1.0"
)

# -------------------- PROMETHEUS METRICS --------------------
metrics = Instrumentator()
metrics.instrument(app).expose(app)

# Mount static frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# -------------------- AUTH ROUTES --------------------
@app.post("/token", response_model=schemas.Token, summary="Login and get an access token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# -------------------- USER ROUTES --------------------
@app.post("/users/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, summary="Create a new internal user (Admin only)", dependencies=[Depends(get_current_admin_user)])
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter((models.User.username == user.username) | (models.User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_admin=user.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me/", response_model=schemas.UserOut, summary="Get current authenticated user's details", dependencies=[Depends(get_current_active_user)])
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

# -------------------- EMPLOYEE ROUTES --------------------
@app.post("/employees/", response_model=schemas.EmployeeOut, status_code=status.HTTP_201_CREATED, summary="Register a new employee/warehouse worker (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def register_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    db_employee = db.query(models.Employee).filter(models.Employee.email == employee.email).first()
    if db_employee:
        raise HTTPException(status_code=400, detail="Employee with this email already registered")
    db_employee = models.Employee(**employee.model_dump())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@app.get("/employees/", response_model=List[schemas.EmployeeOut], summary="Get all registered employees (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_employees(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Employee).offset(skip).limit(limit).all()

@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOutWithDocuments, summary="Get an employee by ID, including their documents (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee

@app.put("/employees/{employee_id}", response_model=schemas.EmployeeOut, summary="Update an employee's details (Requires Auth)", dependencies=[Depends(get_current_active_user)])
async def update_employee(employee_id: int, employee: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if db_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    for key, value in employee.model_dump(exclude_unset=True).items():
        setattr(db_employee, key, value)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@app.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate or delete an employee (Requires Admin Auth)", dependencies=[Depends(get_current_admin_user)])
async def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    db_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if db_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
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
    db.add(archived_employee)
    db.query(models.Document).filter(models.Document.employee_id == employee_id).delete()
    db.delete(db_employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# -------------------- TRUCKER ROUTES --------------------
@app.post("/truckers/", response_model=schemas.TruckerOut, status_code=status.HTTP_201_CREATED, summary="Register a new trucker (Public, no auth)")
async def register_trucker(trucker: schemas.TruckerCreate, db: Session = Depends(get_db)):
    if db.query(models.Trucker).filter(models.Trucker.license_number == trucker.license_number).first():
        raise HTTPException(status_code=400, detail="Trucker with this license already exists")
    db_trucker = models.Trucker(**trucker.model_dump())
    db.add(db_trucker)
    db.commit()
    db.refresh(db_trucker)
    return db_trucker

@app.get("/truckers/", response_model=List[schemas.TruckerOut], summary="Get all truckers (Public, no auth)")
async def get_truckers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Trucker).offset(skip).limit(limit).all()

@app.get("/truckers/{trucker_id}", response_model=schemas.TruckerOutWithDocuments, summary="Get a trucker by ID (Public, no auth)")
async def get_trucker(trucker_id: int, db: Session = Depends(get_db)):
    trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if not trucker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker not found")
    return trucker

@app.put("/truckers/{trucker_id}", response_model=schemas.TruckerOut, summary="Update a trucker's details (Public, no auth)")
async def update_trucker(trucker_id: int, trucker: schemas.TruckerUpdate, db: Session = Depends(get_db)):
    db_trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if not db_trucker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker not found")
    for key, value in trucker.model_dump(exclude_unset=True).items():
        setattr(db_trucker, key, value)
    db.add(db_trucker)
    db.commit()
    db.refresh(db_trucker)
    return db_trucker

@app.delete("/truckers/{trucker_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a trucker (Requires Admin Auth)", dependencies=[Depends(get_current_admin_user)])
async def delete_trucker(trucker_id: int, db: Session = Depends(get_db)):
    db_trucker = db.query(models.Trucker).filter(models.Trucker.id == trucker_id).first()
    if not db_trucker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trucker not found")
    db.query(models.Document).filter(models.Document.trucker_id == trucker_id).delete()
    db.delete(db_trucker)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



from .database import SessionLocal
from . import models

db = SessionLocal()
truckers = db.query(models.Trucker).all()
for t in truckers:
    print(t.id, t.first_name, t.last_name, t.driver_license_number)
db.close()