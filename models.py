# Import necessary components from SQLAlchemy for defining database table columns and relationships.
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Text
# Import relationship for defining relationships between models.
from sqlalchemy.orm import relationship
# Import Base from our database configuration.
from database import Base
# Import datetime module for handling dates.
import datetime

# Define the User model, representing the 'users' table in the database.
class User(Base):
    # Specify the table name for this model.
    __tablename__ = "users"

    # Define columns for the 'users' table.
    # id: Primary key, auto-incrementing integer.
    id = Column(Integer, primary_key=True, index=True)
    # username: String, unique, indexed, and cannot be null.
    username = Column(String, unique=True, index=True, nullable=False)
    # hashed_password: String, stores the hashed password, cannot be null.
    hashed_password = Column(String, nullable=False)
    # email: String, unique, indexed, and cannot be null.
    email = Column(String, unique=True, index=True, nullable=False)
    # full_name: Optional string for the user's full name.
    full_name = Column(String, nullable=True)
    # is_active: Boolean, indicates if the user account is active, defaults to True.
    is_active = Column(Boolean, default=True)
    # is_admin: Boolean, indicates if the user has admin privileges, defaults to False.
    is_admin = Column(Boolean, default=False)
    # created_at: Date, stores the creation date, defaults to today's date.
    created_at = Column(Date, default=datetime.date.today)

    # Defines the string representation of a User object, useful for debugging.
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

# Define the Employee model, representing the 'employees' table.
class Employee(Base):
    __tablename__ = "employees"

    # id: Primary key.
    id = Column(Integer, primary_key=True, index=True)
    # first_name: String, indexed, cannot be null.
    first_name = Column(String, index=True, nullable=False)
    # last_name: String, indexed, cannot be null.
    last_name = Column(String, index=True, nullable=False)
    # email: String, unique, indexed, cannot be null.
    email = Column(String, unique=True, index=True, nullable=False)
    # phone_number: Optional string for phone number.
    phone_number = Column(String, nullable=True)
    # position: String, cannot be null.
    position = Column(String, nullable=False)
    # is_active: Boolean, defaults to True.
    is_active = Column(Boolean, default=True)
    # registration_date: Date, defaults to today's date.
    registration_date = Column(Date, default=datetime.date.today)
    # documents: Defines a one-to-many relationship with the Document model.
    #            back_populates establishes a bidirectional relationship.
    #            cascade="all, delete-orphan" ensures that if an employee is deleted,
    #            their associated documents are also deleted.
    documents = relationship("Document", back_populates="employee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Employee(id={self.id}, name='{self.first_name} {self.last_name}')>"

# Define the Trucker model, representing the 'truckers' table.
class Trucker(Base):
    __tablename__ = "truckers"

    # id: Primary key.
    id = Column(Integer, primary_key=True, index=True)
    # first_name: String, indexed, cannot be null.
    first_name = Column(String, index=True, nullable=False)
    # last_name: String, indexed, cannot be null.
    last_name = Column(String, index=True, nullable=False)
    # email: Optional string, unique, indexed.
    email = Column(String, unique=True, index=True, nullable=True)
    # phone_number: String, cannot be null.
    phone_number = Column(String, nullable=False)
    # driver_license_number: String, unique, indexed, cannot be null.
    driver_license_number = Column(String, unique=True, index=True, nullable=False)
    # province_of_issue: String, cannot be null.
    province_of_issue = Column(String, nullable=False)
    # truck_id_number: Optional string, unique, indexed.
    truck_id_number = Column(String, unique=True, index=True, nullable=True)
    # company_name: Optional string.
    company_name = Column(String, nullable=True)
    # is_active: Boolean, defaults to True.
    is_active = Column(Boolean, default=True)
    # registration_date: Date, defaults to today's date.
    registration_date = Column(Date, default=datetime.date.today)
    # documents: Defines a one-to-many relationship with the Document model,
    #            with cascade for deletion.
    documents = relationship("Document", back_populates="trucker", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Trucker(id={self.id}, license='{self.driver_license_number}')>"

# Define the Document model, representing the 'documents' table.
class Document(Base):
    __tablename__ = "documents"

    # id: Primary key.
    id = Column(Integer, primary_key=True, index=True)
    # document_type: String, cannot be null.
    document_type = Column(String, nullable=False)
    # file_path: String, stores the path to the document file, cannot be null.
    file_path = Column(String, nullable=False)
    # upload_date: Date, defaults to today's date.
    upload_date = Column(Date, default=datetime.date.today)
    # is_verified: Boolean, indicates if the document has been verified, defaults to False.
    is_verified = Column(Boolean, default=False)
    # verification_date: Optional date for when the document was verified.
    verification_date = Column(Date, nullable=True)
    # verified_by: Optional string for who verified the document.
    verified_by = Column(String, nullable=True)
    # employee_id: Foreign key to the 'employees' table, optional.
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    # trucker_id: Foreign key to the 'truckers' table, optional.
    trucker_id = Column(Integer, ForeignKey("truckers.id"), nullable=True)

    # employee: Defines a many-to-one relationship with the Employee model.
    employee = relationship("Employee", back_populates="documents")
    # trucker: Defines a many-to-one relationship with the Trucker model.
    trucker = relationship("Trucker", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, type='{self.document_type}')>"

# Define the ArchivedEmployee model for storing deactivated/deleted employee records.
class ArchivedEmployee(Base):
    __tablename__ = "archived_employees"

    # id: Primary key for the archive record.
    id = Column(Integer, primary_key=True, index=True)
    # original_id: Stores the ID of the employee from the 'employees' table, unique.
    original_id = Column(Integer, nullable=False, unique=True)
    # first_name: Stored for historical record.
    first_name = Column(String, nullable=False)
    # last_name: Stored for historical record.
    last_name = Column(String, nullable=False)
    # email: Stored for historical record.
    email = Column(String, nullable=False)
    # phone_number: Stored for historical record.
    phone_number = Column(String, nullable=True)
    # position: Stored for historical record.
    position = Column(String, nullable=False)
    # is_active: Stored for historical record (will be False if deactivated/deleted).
    is_active = Column(Boolean, nullable=False)
    # registration_date: Stored for historical record.
    registration_date = Column(Date, nullable=False)
    # archive_date: Date when the record was moved to archive, defaults to today.
    archive_date = Column(Date, default=datetime.date.today)
    # archived_reason: Text field to store the reason for archiving.
    archived_reason = Column(Text, nullable=True)

# Define the ArchivedTrucker model for storing deactivated/deleted trucker records.
class ArchivedTrucker(Base):
    __tablename__ = "archived_truckers"

    # id: Primary key for the archive record.
    id = Column(Integer, primary_key=True, index=True)
    # original_id: Stores the ID of the trucker from the 'truckers' table, unique.
    original_id = Column(Integer, nullable=False, unique=True)
    # first_name: Stored for historical record.
    first_name = Column(String, nullable=False)
    # last_name: Stored for historical record.
    last_name = Column(String, nullable=False)
    # email: Stored for historical record.
    email = Column(String, nullable=True)
    # phone_number: Stored for historical record.
    phone_number = Column(String, nullable=False)
    # driver_license_number: Stored for historical record.
    driver_license_number = Column(String, nullable=False)
    # province_of_issue: Stored for historical record.
    province_of_issue = Column(String, nullable=False)
    # truck_id_number: Stored for historical record.
    truck_id_number = Column(String, nullable=True)
    # company_name: Stored for historical record.
    company_name = Column(String, nullable=True)
    # is_active: Stored for historical record.
    is_active = Column(Boolean, nullable=False)
    # registration_date: Stored for historical record.
    registration_date = Column(Date, nullable=False)
    # archive_date: Date when the record was moved to archive.
    archive_date = Column(Date, default=datetime.date.today)
    # archived_reason: Text field to store the reason for archiving.
    archived_reason = Column(Text, nullable=True)

# Define the ArchivedDocument model for storing deactivated/deleted document records.
class ArchivedDocument(Base):
    __tablename__ = "archived_documents"

    # id: Primary key for the archive record.
    id = Column(Integer, primary_key=True, index=True)
    # original_id: Stores the ID of the document from the 'documents' table, unique.
    original_id = Column(Integer, nullable=False, unique=True)
    # document_type: Stored for historical record.
    document_type = Column(String, nullable=False)
    # file_path: Stored for historical record.
    file_path = Column(String, nullable=False)
    # upload_date: Stored for historical record.
    upload_date = Column(Date, nullable=False)
    # is_verified: Stored for historical record.
    is_verified = Column(Boolean, nullable=False)
    # verification_date: Stored for historical record.
    verification_date = Column(Date, nullable=True)
    # verified_by: Stored for historical record.
    verified_by = Column(String, nullable=True)
    # employee_id: Stored for historical record, original employee association.
    employee_id = Column(Integer, nullable=True)
    # trucker_id: Stored for historical record, original trucker association.
    trucker_id = Column(Integer, nullable=True)
    # archive_date: Date when the record was moved to archive.
    archive_date = Column(Date, default=datetime.date.today)
    # archived_reason: Text field to store the reason for archiving.
    archived_reason = Column(Text, nullable=True)
