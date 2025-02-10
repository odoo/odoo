from __future__ import annotations
from .course_info_type import LearningResource
from .discussion_forum_type import Comment
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.object_type import Thing, AlignmentObject


class Answer(Comment):
    __description__ = """
        An answer offered to a question; perhaps correct, perhaps opinionated or wrong.
    """
    __schema_properties__ = Comment.__schema_properties__ | {
        "answerExplanation": ["Comment", "WebContent"],
        "parentItem": ["Comment", "CreativeWork"]
    }

    def __init__(self, text: str, **kwargs) -> None:
        super().__init__(text=text, **kwargs)


class Question(Comment):
    __description__ = """
        A specific question - e.g. from a user seeking answers
        online, or collected in a Frequently Asked Questions (FAQ) document.
    """
    __schema_properties__ = Comment.__schema_properties__ | {
        "acceptedAnswer": ['r', "Answer", "ItemList"],
        "answerCount": "Integer",
        "eduQuestionType": "Text",
        "parentItem": ["Comment", "CreativeWork"],
        "suggestedAnswer": ['r', "Answer", "ItemList"]
    }

    def __init__(self,
                 accepted_answer: Answer,
                 name: str | None = None,
                 text: str | None = None,
                 edu_question_type: str | None = None,
                 **kwargs) -> None:
        super().__init__(
            accepted_answer=accepted_answer,
            name=name,
            text=text,
            edu_question_type=edu_question_type,
            **kwargs)


class Quiz(LearningResource):
    __description__ = """
        Quiz: A test of knowledge, skills and abilities.
    """
    __gsc_required_properties__ = [
        'hasPart',
        'hasPart.acceptedAnswer',
        'hasPart.eduQuestionType',
        'hasPart.text'
    ]

    def __init__(self,
                 has_part: list[Question] | Question,
                 about: list[Thing] | Thing | None = None,
                 educational_alignment: list[AlignmentObject] | AlignmentObject | None = None,
                 **kwargs
    ) -> None:
        super().__init__(
            has_part=has_part,
            about=about,
            educational_alignment=educational_alignment,
            **kwargs
        )
