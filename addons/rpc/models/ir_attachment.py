import logging

from odoo import api, models

from ..tools.cache import doc_cache_generation, stale_index_domain

logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.autovacuum
    def _gc_doc_index(self):
        """Garbage collect the ``/doc/index.json`` documents that can no longer
        be served.

        A cached index is keyed by the database state it was built from, by
        language and by the reader's groups, so there is one per distinct
        audience and they are all superseded at once when that state moves.
        Selecting the survivors by name pattern keeps the whole decision in
        SQL, however many audiences the database has accumulated.
        """
        stale = self.search(stale_index_domain(doc_cache_generation(self.env)))
        if stale:
            stale.unlink()
            logger.info("GC'd %s /doc cached index", len(stale))
