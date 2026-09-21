from odoo.tools.module_data import rename_field

ATTACHMENT = {
    "speech_state": "transcript_state",
    "speech_cues": "transcript_cues",
    "speech_transcript": "transcript_text",
    "speech_language": "transcript_language",
    "speech_engine": "transcript_engine",
    "speech_error": "transcript_error",
}
SEGMENT = {
    "transcription_state": "transcript_state",
    "speech_cues": "transcript_cues",
}
DOCUMENT = {
    "speech_state": "transcript_state",
    "speech_transcript": "transcript_text",
}
TIMELINE = {
    "media_transcript": "timeline_transcript",
    "transcription_state": "timeline_transcript_state",
}


def migrate(cr, version):
    if not version:
        return
    for model, renames in (
        ("ir.attachment", ATTACHMENT),
        ("media.segment", SEGMENT),
        ("document.document", DOCUMENT),
    ):
        for old, new in renames.items():
            rename_field(cr, model, old, new)
    cr.execute("DROP INDEX IF EXISTS ir_attachment__speech_state_index")
    cr.execute(
        """
        SELECT DISTINCT model FROM ir_model_fields
         WHERE name = 'media_transcript'
            OR (name = 'transcription_state' AND model != 'media.segment')
        """
    )
    for (model,) in cr.fetchall():
        for old, new in TIMELINE.items():
            rename_field(cr, model, old, new)
