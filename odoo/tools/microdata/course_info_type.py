from __future__ import annotations
from .core.object_type import Offer, Person, Organization, Duration, CreativeWork

from .core.learning_resource_type import LearningResource
from .event_type import Event
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.aggregate_rating_type import AggregateRating
    from .core.data_type import URL, Date
    from .core.syllabus_type import Syllabus
    from .core.schedule_type import Schedule
    from .video_object_type import VideoObject
    from .review_type import Review


class EducationalLevel(Enum):
    Beginner = "Beginner"
    Intermediate = "Intermediate"
    Advanced = "Advanced"


class CredentialCategory(Enum):
    Certificate = "Certificate"
    Certification = "Certification"
    HighSchool = "high school"
    AssociateDegree = "associate degree"
    BachelorDegree = "bachelor degree"
    ProfessionalCertificate = "professional certificate"
    PostgraduateDegree = "postgraduate degree"


class EducationalOccupationalCredential(CreativeWork):
    __description__ = """
        An educational or occupational credential. A diploma, academic degree,
        certification, qualification, badge, etc., that may be awarded to a
        person or other entity that meets the requirements defined by the
        credentialer.
    """
    __schema_properties__ = CreativeWork.__schema_properties__ | {
        "competencyRequired": ['r', "DefinedTerm", "Text", "URL"],
        "credentialCategory": ["CredentialCategory", "DefinedTerm", "Text", "URL"],
        "educationalLevel": ["EducationalLevel", "DefinedTerm", "Text", "URL"],
        "recognizedBy": ["Organization"],
        "validFor": "Duration",
        "validIn": "AdministrativeArea"
    }

    def __init__(self,
                 name: str,
                 credential_category: CredentialCategory | None = None,
                 offers: list[Offer] | None = None,
                 url: URL | str | None = None,
                 **kwargs) -> None:
        super().__init__(
            name=name,
            credential_category=credential_category,
            offers=offers,
            url=url,
            **kwargs
        )


class CourseMode(Enum):
    Online = "Online"
    Onsite = "Onsite"
    Blended = "Blended"


class CourseInstance(Event):
    __description__ = """
        An instance of a Course which is distinct from other instances because
        it is offered at a different time or location or through different media
        or modes of study or to a specific section of students.
    """
    __schema_properties__ = Event.__schema_properties__ | {
        "courseMode": ["CourseMode", "Text", "URL"],
        "courseSchedule": ["Schedule"],
        "courseWorkload": ["Duration", "Text"],
        "instructor": ['r', "Person"]
    }

    def __init__(self,
                 course_mode: CourseMode,
                 course_schedule: Schedule | None = None,
                 course_workload: Duration | None = None,
                 image: URL | str | None = None,
                 instructor: list[Person] | Person | None = None,
                 location: str | None = None,
                 **kwargs) -> None:
        super().__init__(
            course_mode=course_mode,
            course_schedule=course_schedule,
            course_workload=course_workload,
            image=image,
            instructor=instructor,
            location=location,
            **kwargs)


class Course(LearningResource):
    __description__ = """
        A description of an educational course which may be offered as distinct
        instances which take place at different times or take place at different
        locations, or be offered through different media or modes of study. An
        educational course is a sequence of one or more educational events
        and/or creative works which aims to build knowledge, competence or
        ability of learners.
    """
    __schema_properties__ = LearningResource.__schema_properties__ | {
        "availableLanguage": ['r', "Language", "Text"],
        "courseCode": "Text",
        "coursePrerequisites": ['r', "Course", "AlignementObject", "Text"],
        "educationalCredentialAwarded": ['r', "EducationalOccupationalCredential", "Text", "URL"],
        "financialAidEligible": ["DefinedTerm", "Text"],
        "hasCourseInstance": ['r', "CourseInstance"],
        "numberOfCredits": ["Integer", "StructuredValue"],
        "occupationalCredentialAwarded": ['r', "EducationalOccupationalCredential", "Text", "URL"],
        "syllabusSections": ['r', "Syllabus"],
        "totalHistoricalEnrollment": "Integer"
    }

    __gsc_required_properties__ = [
        "name",
        "description",
        "provider",
        "provider.name",
        "offers",
        "offers.category",
        "hasCourseInstance",
        "hasCourseInstance.courseMode",
        (["hasCourseInstance.courseSchedule", "hasCourseInstance.courseWorkload"], "or"),
        "hasPart",
        "hasPart.name",
        "hasPart.url"
    ]

    def __init__(self,
                 name: str,
                 description: str,
                 provider: Organization,
                 offers: list[Offer] | None = None,
                 has_course_instance: list[CourseInstance] | None = None,
                 url: URL | str | None = None,
                 has_part: list[Course] | None = None,
                 about: list[str] | None = None,
                 aggregate_rating: AggregateRating | None = None,
                 available_language: list[str] | None = None,
                 course_prerequisites: list[str] | None = None,
                 date_published: Date | str | None = None,
                 educational_credential_awarded: list[EducationalOccupationalCredential] | None = None,
                 educational_level: EducationalLevel | None = None,
                 financial_aid_eligible: str | None = None,
                 image: list[URL | str] | None = None,
                 in_language: str | None = None,
                 publisher: Organization | None = None,
                 review: list[Review] | None = None,
                 syllabus_sections: list[Syllabus] | Syllabus | None = None,
                 teaches: list[str] | str | None = None,
                 total_historical_enrollment: int | None = None,
                 video: VideoObject | None = None,
                 **kwargs
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            image=image,
            url=url,
            provider=provider,
            offers=offers,
            has_course_instance=has_course_instance,
            has_part=has_part,
            about=about,
            aggregate_rating=aggregate_rating,
            available_language=available_language,
            course_prerequisites=course_prerequisites,
            date_published=date_published,
            educational_credential_awarded=educational_credential_awarded,
            educational_level=educational_level,
            financial_aid_eligible=financial_aid_eligible,
            in_language=in_language,
            publisher=publisher,
            review=review,
            syllabus_sections=syllabus_sections,
            teaches=teaches,
            total_historical_enrollment=total_historical_enrollment,
            video=video,
            **kwargs)
