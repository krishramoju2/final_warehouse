# Import necessary components from pydantic for defining data models.
from pydantic import BaseModel, EmailStr, Field
# Import typing for type hints, including Optional, List, and Union.
from typing import Optional, List, Union
# Import datetime for handling date types.
import datetime

# Base schema for a user, containing common fields.
class UserBase(BaseModel):
    # username: String field, required, with min and max length constraints.
    username: str = Field(..., min_length=3, max_length=50)
    # email: EmailStr type, ensuring it's a valid email format.
    email: EmailStr
    # full_name: Optional string field.
    full_name: Optional[str] = None

# Schema for creating a new user, inherits from UserBase and adds password.
class UserCreate(UserBase):
    # password: String field, required, with min length constraint.
    password: str = Field(..., min_length=6)
    # is_admin: Boolean field, defaults to False.
    is_admin: bool = False

# Schema for outputting user data, inherits from UserBase and adds system-generated fields.
class UserOut(UserBase):
    # id: Integer field, representing the user's unique ID.
    id: int
    # is_active: Boolean field indicating active status.
    is_active: bool
    # is_admin: Boolean field indicating admin privileges.
    is_admin: bool
    # created_at: Date field, when the user was created.
    created_at: datetime.date

    # Pydantic configuration class.
    class Config:
        # from_attributes = True: Enables Pydantic to work with SQLAlchemy ORM models,
        #                       allowing it to read data directly from model instances.
        from_attributes = True

# Schema for the access token response during login.
class Token(BaseModel):
    # access_token: String field for the JWT token.
    access_token: str
    # token_type: String field, typically "bearer".
    token_type: str

# Schema for the data contained within a JWT token.
class TokenData(BaseModel):
    # username: Optional string field for the username stored in the token's subject.
    username: Optional[str] = None

# Base schema for a person (common fields for Employee and Trucker).
class PersonBase(BaseModel):
    # first_name: String field, required, with min and max length.
    first_name: str = Field(..., min_length=2, max_length=50)
    # last_name: String field, required, with min and max length.
    last_name: str = Field(..., min_length=2, max_length=50)
    # phone_number: String field, required, with min and max length.
    phone_number: str = Field(..., min_length=10, max_length=20)
    # email: Optional EmailStr field.
    email: Optional[EmailStr] = None

# Schema for creating a new employee, inherits from PersonBase and adds specific fields.
class EmployeeCreate(PersonBase):
    # email: EmailStr field, required (overrides optionality in PersonBase for employee creation).
    email: EmailStr
    # position: String field, required, with min and max length.
    position: str = Field(..., min_length=3, max_length=100)

# Schema for updating an existing employee, all fields are optional.
class EmployeeUpdate(BaseModel):
    # first_name: Optional string field with constraints.
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    # last_name: Optional string field with constraints.
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    # email: Optional EmailStr field.
    email: Optional[EmailStr] = None
    # phone_number: Optional string field with constraints.
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    # position: Optional string field with constraints.
    position: Optional[str] = Field(None, min_length=3, max_length=100)
    # is_active: Optional boolean field.
    is_active: Optional[bool] = None

# Schema for outputting employee data, inherits from PersonBase and adds system-generated fields.
class EmployeeOut(PersonBase):
    # id: Integer field.
    id: int
    # email: EmailStr field.
    email: EmailStr
    # position: String field.
    position: str
    # is_active: Boolean field.
    is_active: bool
    # registration_date: Date field.
    registration_date: datetime.date

    class Config:
        from_attributes = True

# Schema for creating a new trucker, inherits from PersonBase and adds specific fields.
class TruckerCreate(PersonBase):
    # driver_license_number: String field, required, with constraints, unique identifier.
    driver_license_number: str = Field(..., min_length=5, max_length=50)
    # province_of_issue: String field, required, with constraints, e.g., "ON", "QC".
    province_of_issue: str = Field(..., min_length=2, max_length=50)
    # truck_id_number: Optional string field with constraints, unique identifier for the truck.
    truck_id_number: Optional[str] = Field(None, min_length=5, max_length=50)
    # company_name: Optional string field with constraints.
    company_name: Optional[str] = Field(None, min_length=2, max_length=100)

# Schema for updating an existing trucker, all fields are optional.
class TruckerUpdate(BaseModel):
    # first_name: Optional string field with constraints.
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    # last_name: Optional string field with constraints.
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    # email: Optional EmailStr field.
    email: Optional[EmailStr] = None
    # phone_number: Optional string field with constraints.
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    # driver_license_number: Optional string field with constraints.
    driver_license_number: Optional[str] = Field(None, min_length=5, max_length=50)
    # province_of_issue: Optional string field with constraints.
    province_of_issue: Optional[str] = Field(None, min_length=2, max_length=50)
    # truck_id_number: Optional string field with constraints.
    truck_id_number: Optional[str] = Field(None, min_length=5, max_length=50)
    # company_name: Optional string field with constraints.
    company_name: Optional[str] = Field(None, min_length=2, max_length=100)
    # is_active: Optional boolean field.
    is_active: Optional[bool] = None

# Schema for outputting trucker data, inherits from PersonBase and adds system-generated fields.
class TruckerOut(PersonBase):
    # id: Integer field.
    id: int
    # driver_license_number: String field.
    driver_license_number: str
    # province_of_issue: String field.
    province_of_issue: str
    # truck_id_number: Optional string field.
    truck_id_number: Optional[str]
    # company_name: Optional string field.
    company_name: Optional[str]
    # is_active: Boolean field.
    is_active: bool
    # registration_date: Date field.
    registration_date: datetime.date

    class Config:
        from_attributes = True

# Schema for creating a new document.
class DocumentCreate(BaseModel):
    # document_type: String field, required, with constraints, e.g., "Driver's License", "Insurance".
    document_type: str = Field(..., min_length=3, max_length=100)
    # file_path: String field, required, with min length, represents where the file is stored.
    file_path: str = Field(..., min_length=5)
    # employee_id: Optional integer field, foreign key to employee.
    employee_id: Optional[int] = None
    # trucker_id: Optional integer field, foreign key to trucker.
    trucker_id: Optional[int] = None

    # Custom post-initialization validation.
    # Ensures that exactly one of employee_id or trucker_id is provided, but not both or none.
    def model_post_init(self, __context):
        if (self.employee_id is not None and self.trucker_id is not None) or \
           (self.employee_id is None and self.trucker_id is None):
            raise ValueError("Exactly one of employee_id or trucker_id must be provided.")

# Schema for updating an existing document, all fields are optional.
class DocumentUpdate(BaseModel):
    # document_type: Optional string field with constraints.
    document_type: Optional[str] = Field(None, min_length=3, max_length=100)
    # file_path: Optional string field with min length.
    file_path: Optional[str] = Field(None, min_length=5)
    # is_verified: Optional boolean field for verification status.
    is_verified: Optional[bool] = None
    # verified_by: Optional string field with constraints, name of the verifier.
    verified_by: Optional[str] = Field(None, min_length=2, max_length=50)

# Schema for outputting document data.
class DocumentOut(BaseModel):
    # id: Integer field.
    id: int
    # document_type: String field.
    document_type: str
    # file_path: String field.
    file_path: str
    # upload_date: Date field.
    upload_date: datetime.date
    # is_verified: Boolean field.
    is_verified: bool
    # verification_date: Optional date field for verification timestamp.
    verification_date: Optional[datetime.date]
    # verified_by: Optional string field.
    verified_by: Optional[str]
    # employee_id: Optional integer field.
    employee_id: Optional[int]
    # trucker_id: Optional integer field.
    trucker_id: Optional[int]

    class Config:
        from_attributes = True

# Schema for outputting an Employee along with their associated documents.
class EmployeeOutWithDocuments(EmployeeOut):
    # documents: List of DocumentOut schemas, representing associated documents.
    documents: List[DocumentOut] = []

# Schema for outputting a Trucker along with their associated documents.
class TruckerOutWithDocuments(TruckerOut):
    # documents: List of DocumentOut schemas, representing associated documents.
    documents: List[DocumentOut] = []

# Schema for a single live search result.
class LiveSearchResult(BaseModel):
    # type: String, indicates if it's "employee" or "trucker".
    type: str
    # id: Integer, the ID of the found entity.
    id: int
    # name: String, the full name of the person.
    name: str
    # identifier: String, a unique identifier like email or license number.
    identifier: str
    # is_active: Boolean, status of the entity.
    is_active: bool
    # details: Union type, can be either an EmployeeOut or TruckerOut schema,
    #          providing full details of the found entity.
    details: Union[EmployeeOut, TruckerOut]

# Schema for high-level compliance data/dashboard summary.
class ComplianceData(BaseModel):
    # total_employees: Integer, total number of employees registered.
    total_employees: int
    # active_employees: Integer, number of active employees.
    active_employees: int
    # total_truckers: Integer, total number of truckers registered.
    total_truckers: int
    # active_truckers: Integer, number of active truckers.
    active_truckers: int
    # documents_uploaded: Integer, total number of documents uploaded.
    documents_uploaded: int
    # documents_verified: Integer, number of verified documents.
    documents_verified: int
    # unverified_documents: Integer, number of unverified documents.
    unverified_documents: int

# Schema for a summary of archived records.
class ArchiveSummary(BaseModel):
    # archived_employees: Integer, count of archived employees.
    archived_employees: int
    # archived_truckers: Integer, count of archived truckers.
    archived_truckers: int
    # archived_documents: Integer, count of archived documents.
    archived_documents: int
    # message: String, a descriptive message about the archiving process.
    message: str

# New schemas for analytics data.

# Schema for a single point of registration growth.
class RegistrationGrowth(BaseModel):
    # date: Date, the specific date of registration.
    date: datetime.date
    # count: Integer, the number of registrations on that date.
    count: int

# Schema for employee growth analysis.
class EmployeeGrowthAnalysis(BaseModel):
    # monthly_growth: List of RegistrationGrowth, showing growth trends over time.
    monthly_growth: List[RegistrationGrowth]
    # total_employees: Integer, current total count of employees.
    total_employees: int
    # average_monthly_growth: Float, average growth rate per month.
    average_monthly_growth: float
    # projected_next_month: Optional integer, a predictive value for next month's growth.
    projected_next_month: Optional[int] = None # Future prediction could be added here from an ML model, simplified for now

# Schema for distribution of trucker types.
class TruckerTypeDistribution(BaseModel):
    # company_name: String, the name of the trucking company.
    company_name: str
    # count: Integer, number of truckers associated with this company.
    count: int
    # percentage: Float, percentage of total truckers this company represents.
    percentage: float

# Schema for overall trucker analysis.
class TruckerAnalysis(BaseModel):
    # province_distribution: Dictionary mapping provinces to trucker counts.
    province_distribution: dict
    # company_distribution: List of TruckerTypeDistribution, showing breakdown by company.
    company_distribution: List[TruckerTypeDistribution]
    # most_common_type: Optional string, e.g., the most common company type.
    most_common_type: Optional[str] = None
    # predictive_trend: Optional string, a qualitative description of a predictive trend,
    #                  e.g., "Increasing independent truckers".
    predictive_trend: Optional[str] = None # e.g., "Increasing independent truckers"

# Schema for business impact analysis.
class BusinessImpactAnalysis(BaseModel):
    # employee_churn_rate: Optional float, calculated rate of employee deactivations.
    employee_churn_rate: Optional[float] = None # Based on deactivations
    # trucker_churn_rate: Optional float, calculated rate of trucker deactivations.
    trucker_churn_rate: Optional[float] = None
    # document_compliance_rate: Optional float, ratio of verified to total documents.
    document_compliance_rate: Optional[float] = None # verified_documents / total_documents
    # potential_revenue_impact: Optional string, qualitative or simple quantitative assessment.
    potential_revenue_impact: Optional[str] = None # Qualitative or simple quantitative
    # operational_efficiency_impact: Optional string, qualitative assessment of operational changes.
    operational_efficiency_impact: Optional[str] = None # Qualitative
    # strategic_recommendations: Optional list of strings, providing strategic advice.
    strategic_recommendations: Optional[List[str]] = None
    # More advanced metrics and predictions could be integrated here
