from odoo.addons.extract.tools import FieldSpec, register_schema

DOCUMENT_TYPE = "speech_analysis"
PURPOSE = "speech.analysis"

MOMENT_KINDS = (
    "decision",
    "agreement",
    "objection",
    "concern",
    "risk",
    "complaint",
    "praise",
    "next_step",
    "fact",
    "highlight",
)
SENTIMENTS = ("positive", "neutral", "negative")
ENGAGEMENTS = ("high", "medium", "low")

_AT = FieldSpec("str", help="The [mm:ss] stamp of the line it comes from")
_SPEAKER = FieldSpec("str", help="The speaker exactly as the transcript names them")

INSTRUCTIONS = (
    "You analyse the transcript of a recorded conversation: a meeting, a call "
    "or a visit. Each line reads [mm:ss] speaker: words. Name speakers exactly "
    "as the transcript does and cite the stamp of the line a finding comes "
    "from. Write in the language the conversation is held in. Report only "
    "what was said; an empty list is a correct answer."
)

register_schema(
    DOCUMENT_TYPE,
    fields={
        "summary": FieldSpec(
            "str",
            required=True,
            help="What was discussed and how it ended, in a few sentences",
        ),
        "topics": FieldSpec(
            "list",
            help="The subjects discussed, a few words each",
            items={"name": FieldSpec("str", required=True), "at": _AT},
        ),
        "commitments": FieldSpec(
            "list",
            help="Something a speaker undertook to do",
            items={
                "what": FieldSpec("str", required=True, help="What will be done"),
                "who": _SPEAKER,
                "due": FieldSpec("date", help="By when, if a date was said"),
                "at": _AT,
            },
        ),
        "questions": FieldSpec(
            "list",
            help="A question put to someone in the conversation",
            items={
                "question": FieldSpec("str", required=True),
                "asked_by": _SPEAKER,
                "answered": FieldSpec("bool", help="Whether it got an answer"),
                "answer": FieldSpec("str", help="The answer, in brief"),
                "at": _AT,
            },
        ),
        "moments": FieldSpec(
            "list",
            help="A turn worth finding again",
            items={
                "kind": FieldSpec("str", required=True, choices=MOMENT_KINDS),
                "quote": FieldSpec(
                    "str", required=True, help="The words, quoted briefly"
                ),
                "speaker": _SPEAKER,
                "at": _AT,
            },
        ),
        "speakers": FieldSpec(
            "list",
            help="How each speaker took part",
            items={
                "speaker": FieldSpec("str", required=True),
                "name_guess": FieldSpec(
                    "str",
                    help="Their full name, when what is said or the context tells it",
                ),
                "sentiment": FieldSpec("str", choices=SENTIMENTS),
                "engagement": FieldSpec("str", choices=ENGAGEMENTS),
                "interruptions": FieldSpec("int", help="Times they cut someone off"),
                "questions_asked": FieldSpec("int"),
            },
        ),
    },
    instructions=INSTRUCTIONS,
    optimize_for="balanced",
    purpose=PURPOSE,
)
