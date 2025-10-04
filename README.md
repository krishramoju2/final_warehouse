database.py

This file sets up SQLAlchemy for use in apps like FastAPI by:

creating a database engine (connection manager),

preparing a SessionLocal factory for request-scoped sessions,

defining a Base class for ORM models,

and exposing a get_db() dependency that gives each request its own DB session and ensures it closes after use.


create_engine → builds the connection engine.

connect_args={"check_same_thread": False} is only for SQLite to allow multi-threaded access.

declarative_base → creates a base class (Base) that all ORM models inherit from.

sessionmaker → factory to generate Session objects:

autocommit=False → must call db.commit() manually.

autoflush=False → no automatic flush before queries.

bind=engine → sessions tied to the engine.

Database URL → "sqlite:///./inmemory.db" creates a file inmemory.db in current directory (not true in-memory; that’s sqlite:///:memory:).

Base = declarative_base() → needed for defining ORM models and creating tables with Base.metadata.create_all(bind=engine).

get_db() → FastAPI dependency that:

yields a fresh session per request,

closes it after use (prevents connection leaks).

Can be extended to rollback on errors.


schemas.py 

1. User Schemas

UserBase, UserCreate, UserOut → define input & output formats for user registration, login, and profile data.

Includes validation rules like email format, password length, etc.

UserOut uses from_attributes=True so you can return SQLAlchemy ORM models directly.

2. Authentication Schemas

Token → response schema for JWT login tokens.

TokenData → schema for data stored inside a JWT (e.g., username).

3. Employee Schemas

EmployeeCreate, EmployeeUpdate, EmployeeOut → define rules for adding, updating, and returning employee data.

Example: position, phone number, active status, registration date.

EmployeeOutWithDocuments → extends employee output with associated documents list.

4. Trucker Schemas

TruckerCreate, TruckerUpdate, TruckerOut → similar to employee schemas, but specific to truckers.

Includes trucker-specific fields like driver_license_number, province_of_issue, truck_id_number.

TruckerOutWithDocuments → returns trucker plus their documents.

5. Document Schemas

DocumentCreate, DocumentUpdate, DocumentOut → defines how documents (licenses, insurance, etc.) are created, updated, and returned.

Custom validation in DocumentCreate ensures exactly one of employee_id or trucker_id is set.

Example: can’t create a document without linking it to either an employee or trucker.

6. Search & Dashboard Schemas

LiveSearchResult → defines the format for a single search result (employee/trucker + details).

ComplianceData → schema for compliance dashboards (counts of employees, truckers, documents, verified/unverified).

ArchiveSummary → summarises archived records with a message.

7. Analytics Schemas

These schemas allow reporting/analytics features:

EmployeeGrowthAnalysis → shows monthly employee growth, totals, and projections.

TruckerAnalysis → shows trucker distribution by province/company, and predictive trends.

BusinessImpactAnalysis → high-level metrics like churn rate, compliance rate, revenue/efficiency impacts, and recommendations.
