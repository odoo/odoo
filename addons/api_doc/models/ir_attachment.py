import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.autovacuum
    def _gc_doc_index(self):
        """ Garbage collect the outdated /doc/index.json attachments. """
        sequence = str(self.env.registry.get_sequences(self.env.cr)[0])
        attachments = self.search_fetch(
            [('name', 'like', R'odoo-doc-index-%-%.json')],
            ['name'],
        ).filtered(
            lambda doc: doc.name.split('-')[3] != sequence,
        )
        if attachments:
            attachments.unlink()
        _logger.info("GC'd %s /doc cached index", len(attachments))
