import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE event_track_visitor AS track
           SET partner_id = visitor.partner_id
          FROM website_visitor AS visitor
         WHERE track.visitor_id = visitor.id
           AND track.partner_id IS NULL
           AND visitor.partner_id IS NOT NULL
    """)
    _logger.debug("Backfilled partners on %s event-track visitor links", cr.rowcount)
