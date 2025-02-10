from __future__ import annotations
from .learning_resource_type import LearningResource
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .object_type import Duration


class Syllabus(LearningResource):
    __description__ = """
        A syllabus that describes the material covered in a course, often with
        several such sections per Course so that a distinct timeRequired can be
        provided for that section of the Course.
    """

    def __init__(self,
                 name: str,
                 description: str | None = None,
                 time_required: Duration | str | None = None,
                 **kwargs) -> None:

        super().__init__(name=name, description=description, time_required=time_required, **kwargs)
