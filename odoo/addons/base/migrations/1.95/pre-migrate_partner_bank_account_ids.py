import logging

from odoo.tools.module_data import rename_field, rename_in_stored_expressions

_logger = logging.getLogger(__name__)

OLD = "bank_ids"
NEW = "bank_account_ids"
MODELS = ("res.partner", "base.document.layout")


def migrate(cr, version):
    if not version:
        return

    for model in MODELS:
        rename_field(cr, model, OLD, NEW)
    rewritten = rename_in_stored_expressions(cr, OLD, NEW, unique=True)
    _logger.info(
        "%s -> %s on %s, %d stored expression(s) rewritten",
        OLD,
        NEW,
        ", ".join(MODELS),
        rewritten,
    )
