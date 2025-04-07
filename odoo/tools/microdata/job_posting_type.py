from __future__ import annotations
from enum import Enum
from .core.object_type import (
    AdministrativeArea, Intangible, Organization, Place,
    MonetaryAmount, PropertyValue
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.data_type import Date, DateTime, Boolean


class EmploymentType(Enum):
    FullTime = "FULL_TIME"
    PartTime = "PART_TIME"
    Contractor = "CONTRACTOR"
    Temporary = "TEMPORARY"
    Intern = "INTERN"
    Volunteer = "VOLUNTEER"
    PerDiem = "PER_DIEM"
    Other = "OTHER"


class JobPosting(Intangible):
    __description__ = """
        A listing that describes a job opening in a certain organization.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "applicantLocationRequirements": ['r', "AdministrativeArea"],
        "applicationContact": ['r', "ContactPoint"],
        "baseSalary": ["MonetaryAmount", "Number", "PriceSpecification"],
        "datePosted": ["Date", "DateTime"],
        "directApply": "Boolean",
        "educationRequirements": ['r', "EducationalOccupationalCredential", "Text"],
        "eligibilityToWorkRequirement": "Text",
        "employerOverview": "Text",
        "employmentType": "Text",
        "employmentUnit": ['r', "Organization"],
        "estimatedSalary": ["MonetaryAmount", "MonetaryAmountDistribution", "Number"],
        "experienceInPlaceOfEducation": "Boolean",
        "experienceRequirements": ['r', "OccupationalExperienceRequirements", "Text"],
        "hiringOrganization": ["Organization", "Person"],
        "incentiveCompensation": ['r', "Text"],
        "industry": ['r', "DefinedTerm", "Text"],
        "jobBenefits": ['r', "Text"],
        "jobImmediateStart": "Boolean",
        "jobLocation": "Place",
        "jobLocationType": "Text",
        "jobStartDate": ["Date", "DateTime", "Text"],
        "occupationalCategory": ['r', "CategoryCode", "Text"],
        "physicalRequirement": ['r', "DefinedTerm", "Text", "URL"],
        "qualifications": ['r', "EducationalOccupationalCredential", "Text"],
        "relevantOccupation": "Occupation",
        "responsibilities": ['r', "Text"],
        "salaryCurrency": "Text",
        "securityClearanceRequirement": ['r', "Text", "URL"],
        "sensoryRequirement": ['r', "Text", "DefinedTerm", "URL"],
        "skills": ['r', "DefinedTerm", "Text"],
        "specialCommitments": ['r', "Text"],
        "title": "Text",
        "totalJobOpenings": "Integer",
        "validThrough": ["Date", "DateTime"],
        "workHours": "Text"
    }

    def __init__(self,
                 title: str,
                 description: str,
                 job_location: Place,
                 hiring_organization: Organization,
                 date_posted: Date | DateTime | str,
                 applicant_location_requirements: AdministrativeArea | list[AdministrativeArea] | None = None,
                 base_salary: MonetaryAmount | None = None,
                 direct_apply: Boolean | None = None,
                 employment_type: EmploymentType | str | None = None,
                 identifier: PropertyValue | None = None,
                 job_location_type: str | None = None,
                 valid_through: DateTime | Date | str | None = None,
                 ) -> None:
        super().__init__(
            title=title,
            description=description,
            job_location=job_location,
            hiring_organization=hiring_organization,
            date_posted=date_posted,
            applicant_location_requirements=applicant_location_requirements,
            base_salary=base_salary,
            direct_apply=direct_apply,
            employment_type=employment_type,
            identifier=identifier,
            job_location_type=job_location_type,
            valid_through=valid_through
        )
