{
    "name": "Media",
    "version": "19.0.1.1.0",
    "category": "Hidden",
    "summary": "Recordings kept as timelines of segments, and played as one",
    "description": """
Media
=====

A recording arrives in pieces -- a call recorded in chunks, a long interview
split for an engine's file-size limit -- and the pieces have to be played as one
timeline. A ``media.segment`` is one attachment plus the milliseconds it covers,
against an owner named by ``res_model``/``res_id``: generic on purpose, so a new
owner is not a schema change.

``mixin.media.timeline`` gives an owner its segments, their duration and the
``_add_media_segment`` a channel files a recording with. A segment is reachable
exactly as far as its owner is: reading it needs the owner readable, anything
else the owner writable.

An owner states how long its recordings are kept (``_media_retention_days``);
filing a segment stamps its attachment's ``content_expires_at`` from arrival,
and base's autovacuum then drops the bytes and keeps the row, so what was said
about a recording outlives the recording. ``_restamp_media_expiry`` applies a
changed policy to what is not released yet.

This module knows nothing about words. ``speech`` extends the segment and the
timeline with transcripts; the ``media_timeline`` widget plays, and speech's
``transcript_timeline`` follows the words along.
    """,
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "security/ir.access.csv",
        "views/media_segment_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "media/static/src/**/*",
        ],
    },
}
