from __future__ import annotations
from .core.object_type import Person, Organization, WebPage
from .core.data_type import DateTime, Date
from .education_qa_type import Question


class QAPage(WebPage):
    __description__ = """
        A QAPage is a WebPage focussed on a specific Question and its Answer(s),
        e.g. in a question answering site or documenting Frequently Asked
        Questions (FAQs).
    """
    __gsc_required_properties__ = [
        'mainEntity',
        'mainEntity.answerCount',
        (['mainEntity.acceptedAnswer', 'mainEntity.suggestedAnswer'], 'or'),
        'mainEntity.name'
    ]

    def __init__(self,
                 main_entity: Question,
                 **kwargs) -> None:
        super().__init__(main_entity=main_entity, **kwargs)
