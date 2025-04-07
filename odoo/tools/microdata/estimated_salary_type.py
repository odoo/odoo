from __future__ import annotations
from .core.object_type import Intangible, City, State, Country, MonetaryAmountDistribution


class Occupation(Intangible):
    __description__ = """
        A profession, may involve prolonged training and/or a formal qualification.
    """
    __schema_properties__ = Intangible.__schema_properties__ | {
        "educationRequirements": ['r', "EducationalOccupationalCredential", "Text"],
        "estimatedSalary": ['r', "MonetaryAmount", "MonetaryAmountDistribution", "Number"],
        "experienceRequirements": ['r', "OccupationalExperienceRequirements", "Text"],
        "occupationLocation": ['r', "AdministrativeArea"],
        "occupationalCategory": ['r', "CategoryCode", "Text"],
        "qualifications": ['r', "EducationalOccupationalCredential", "Text"],
        "responsibilities": ['r', "Text"],
        "skills": ['r', "DefinedTerm", "Text"]
    }

    __gsc_required_properties__ = [
        'estimatedSalary',
        'estimatedSalary.duration',
        'estimatedSalary.name',
        'name',
        'occupationLocation',
    ]

    def __init__(self,
                 estimated_salary: list[MonetaryAmountDistribution] | MonetaryAmountDistribution,
                 name: str,
                 occupation_location: list[City | State | Country] | City | State | Country,
                 description: str | None = None,
                 **kwargs) -> None:
        super().__init__(
            estimated_salary=estimated_salary,
            name=name,
            occupation_location=occupation_location,
            description=description,
            **kwargs)


class OccupationAggregationByEmployer(Intangible):
    __description__ = """
        The OccupationAggregationByEmployer provides job-related data that is
        grouped by employer. For example, you can specify the industry and
        hiring organization for a group of occupations when they are aggregated
        by the employer.
        OccupationAggregationByEmployer is a new schema.org extension proposed
        by Google. It may not be available on schema.org yet.
    """
    __context_url__ = "http://schema.googleapis.com"
    __schema_properties__ = Intangible.__schema_properties__ | {
        "estimatedSalary": ['r', "MonetaryAmountDistribution"],
        "hiringOrganization": "Organization",
        "name": "Text",
        "occupationLocation": ['r', "City", "State", "Country"],
        "description": "Text",
        "industry": "Text",
        "jobBenefits": ['r', "Text"],
        "mainEntityOfPage": "WebPage",
        "sampleSize": "Number",
        "yearsExperienceMax": "Number",
        "yearsExperienceMin": "Number",
    }

    def __init__(self,
                 estimated_salary: list[MonetaryAmountDistribution] | MonetaryAmountDistribution,
                 name: str,
                 occupation_location: list[City | State | Country] | City | State | Country,
                 description: str | None = None,
                 **kwargs) -> None:
        super().__init__(
            estimated_salary=estimated_salary,
            name=name,
            occupation_location=occupation_location,
            description=description,
            **kwargs)
