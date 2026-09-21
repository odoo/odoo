{
    "name": "Discuss - Speech",
    "version": "19.0.1.2.0",
    "category": "Productivity/Discuss",
    "summary": "Record a Discuss call, and read back what was said in it",
    "description": """
Discuss - Speech
================

A call becomes a media timeline. ``discuss.call.history`` inherits
``mixin.media.timeline``, so a call owns segments and gains a duration, a joined
transcript and one rolled-up state without declaring any of them.

What upstream does differently, and why this does not
----------------------------------------------------
Upstream gives the call model one nullable foreign key per owner type, guarded
by a ``num_nonnulls(...) = 1`` constraint, so a second kind of call is a schema
change. It also stores a transcript AS an artifact beside the audio, which then
needs a flag to say which artifacts are media and an exclusion so transcripts
skip the overlap check. Here a transcript belongs to the attachment it
describes, so neither the flag nor the exclusion exists.

The recording itself
--------------------
``/discuss/call/upload_recording`` takes one chunk with the milliseconds it
covers. It refuses anyone who is not in the call, anything that is not audio or
video, and a span that does not move forward, and it queues the transcription
rather than running it in the request.
    """,
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "speech",
    ],
    "data": [
        "views/discuss_call_history_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_speech/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "mail_speech/static/tests/**/*",
        ],
    },
    "auto_install": True,
}
