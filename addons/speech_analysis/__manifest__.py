{
    "name": "Speech - Analysis",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "What a transcribed conversation committed to, asked and decided",
    "description": """
Speech - Analysis
=================

``mixin.speech.analysis`` gives any recording owner -- a Discuss call, a VoIP
call, a conversation -- the reading of its whole transcript, through
``extract`` like any other document: the ``speech_analysis`` schema, the
generative strategy of ``extract_ai``, the owner's company, and the
``speech.analysis`` purpose, which is sensitive, so a company's policy decides
whether a vendor may read it.

It reads a summary and topics onto the owner, and three kinds of finding, each
belonging to its owner by ``res_model``/``res_id`` and visible to whoever may
read the owner:

- ``speech.commitment``: something a speaker undertook, with its due date;
- ``speech.question``: a question, who asked it, and whether it was answered;
- ``speech.moment``: a decision, agreement, objection, concern, risk,
  complaint, praise or next step, quoted.

Each finding names the ``speech.speaker`` it came from, and so the person, and
the offset it was said at. Each speaker is rated for sentiment, engagement,
interruptions and questions asked.

The analysis is queued when the owner's timeline is fully transcribed and
``_speech_analysis_ready`` says the recording is finished; a live recording
answers False until it ends. ``action_analyse_speech`` runs it again.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "speech",
        "extract_ai",
    ],
    "data": [
        "security/ir.access.csv",
        "data/gateway_ml_purpose_data.xml",
        "views/speech_commitment_views.xml",
        "views/speech_question_views.xml",
        "views/speech_moment_views.xml",
        "views/speech_analysis_menus.xml",
    ],
}
