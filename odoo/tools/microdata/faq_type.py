from __future__ import annotations

from .core.object_type import WebPage
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .education_qa_type import Question


class FAQPage(WebPage):
    __description__ = """
        A FAQPage is a WebPage presenting one or more "Frequently asked questions" (see also QAPage).
    """
    __gsc_required_properties__ = [
        'mainEntity',
        'mainEntity.acceptedAnswer',
        'mainEntity.acceptedAnswer.text',
        'mainEntity.name',
    ]

    def __init__(self,
                 main_entity: Question | list[Question],
                 **kwargs) -> None:
        super().__init__(main_entity=main_entity, **kwargs)
