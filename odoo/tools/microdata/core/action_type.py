from __future__ import annotations
from .object_type import Thing


class Action(Thing):
    __description__ = "An action performed by a direct agent and indirect participants upon a direct object. Optionally happens at a location with the help of an inanimate instrument. The execution of the action may produce a result. Specific action sub-type documentation specifies the exact expectation of each argument/role."
    __schema_properties__ = Thing.__schema_properties__ | {
        "actionProcess": "HowTo",
        "actionStatus": "ActionStatusType",
        "agent": ["Organization", "Person"],
        "endTime": ["DateTime", "Time"],
        "error": "Thing",
        "instrument": "Thing",
        "location": ["Place", "PostalAddress", "Text", "VirtualLocation"],
        "object": "Thing",
        "participant": ['r', "Organization", "Person"],
        "provider": ['r', "Organization", "Person"],
        "result": ['r', "Thing"],
        "startTime": ["DateTime", "Time"],
        "target": ["EntryPoint", "URL"]
    }


class SeekToAction(Action):
    __description__ = "This is the Action of navigating to a specific startOffset timestamp within a VideoObject, typically represented with a URL template structure."
    __schema_properties__ = Action.__schema_properties__ | {
        "startOffset": ["HyperTocEntry", "Number"]
    }

    def __init__(self,
                 target: str,
                 start_offset__input: str = "required name=seek_to_second_number",
                 **kwargs
                ) -> None:
        super().__init__(target=target, start_offset__input=start_offset__input, **kwargs)


class SolveMathAction(Action):
    __description__ = """
        The action that takes in a math expression and directs users to a page
        potentially capable of solving/simplifying that expression.
    """
    __schema_properties__ = Action.__schema_properties__ | {
        "eduQuestionType": ['r', "Text"],
        "mathExpression": "Text"
    }

    def __init__(self,
                 edu_question_type: str,
                 **kwargs) -> None:
        super().__init__(edu_question_type=edu_question_type, **kwargs)


class ConsumeAction(Action):
    __description__ = "The act of ingesting information/resources/food."
    __schema_properties__ = Action.__schema_properties__ | {
        "actionAccessibilityRequirement": "ActionAccessSpecification",
        "expectsAcceptanceOf": "Offer"
    }


class DrinkAction(ConsumeAction):
    __description__ = "The act of swallowing liquids."


class EatAction(ConsumeAction):
    __description__ = "The act of swallowing solid objects."


class InstallAction(ConsumeAction):
    __description__ = "The act of installing an application."


class ListenAction(ConsumeAction):
    __description__ = "The act of consuming audio content."


class PlaygameAction(ConsumeAction):
    __description__ = "The act of playing a video game."


class ReadAction(ConsumeAction):
    __description__ = "The act of consuming written content."


class UseAction(ConsumeAction):
    __description__ = "The act of applying an object to its intended purpose."


class ViewAction(ConsumeAction):
    __description_ = "The act of consuming static visual content."


class WatchAction(ConsumeAction):
    __description__ = "The act of consuming dynamic/moving visual content."


class AssessAction(Action):
    __description__ = "The act of forming one's opinion, reaction or sentiment."


class ReactAction(AssessAction):
    __description__ = """The act of responding instinctively and emotionally to
        an object, expressing a sentiment.
    """


class AgreeAction(ReactAction):
    pass


class DisagreeAction(ReactAction):
    pass


class DislikeAction(ReactAction):
    pass


class EndorseAction(ReactAction):
    pass


class LikeAction(ReactAction):
    pass


class WantAction(ReactAction):
    pass


class CreateAction(Action):
    __description__ = """
        The act of deliberately creating/producing/generating/building a result
        out of the agent.
    """


class WriteAction(CreateAction):
    pass


class CookAction(CreateAction):
    pass


class DrawAction(CreateAction):
    pass


class FilmAction(CreateAction):
    pass


class PaintAction(CreateAction):
    pass


class PhotographAction(CreateAction):
    pass


class InteractAction(Action):
    pass


class CommunicateAction(InteractAction):
    __description__ = """
        The act of conveying information to another person via a communication
        medium (instrument) such as speech, email, or telephone conversation.
    """
    __schema_properties__ = InteractAction.__schema_properties__ | {
        "about": ['r', "Thing"],
        "inLanguage": ['r', "Language", "Text"],
        "recipient": ['r', "Audience", "ContactPoint", "Organization", "Person"]
    }


class AskAction(CommunicateAction):
    __schema_properties__ = CommunicateAction.__schema_properties__ | {
        "question": "Question"
    }


class CheckInAction(CommunicateAction):
    pass


class CheckOutAction(CommunicateAction):
    pass


class CommentAction(CommunicateAction):
    __schema_properties__ = CommunicateAction.__schema_properties__ | {
        "resultComment": "Comment"
    }


class InformAction(CommunicateAction):
    __schema_properties__ = CommunicateAction.__schema_properties__ | {
        "event": ['r', "Event"]
    }


class InviteAction(CommunicateAction):
    __schema_properties__ = CommunicateAction.__schema_properties__ | {
        "event": ['r', "Event"]
    }


class ReplyAction(CommunicateAction):
    __schema_properties__ = CommunicateAction.__schema_properties__ | {
        "resultComment": "Comment"
    }


class ShareAction(CommunicateAction):
    pass
