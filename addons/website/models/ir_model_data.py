import logging

from odoo import api, models
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    @api.model
    def _process_end_unlink_record(self, record):
        if record.env.context["module"].startswith("theme_"):
            theme_records = self.env["ir.module.module"]._theme_model_names.values()
            if record._name in theme_records:
                copy_ids = record.with_context(
                    **{"active_test": False, MODULE_UNINSTALL_FLAG: True}
                ).copy_ids
                if request:
                    current_website = self.env["website"].get_current_website()
                    copy_ids = copy_ids.filtered(
                        lambda c: c.website_id == current_website
                    )

                _logger.info(
                    "Deleting %s@%s (theme `copy_ids`) for website %s",
                    copy_ids.ids,
                    record._name,
                    copy_ids.mapped("website_id"),
                )
                _debug.lifecycle(
                    "theme_copies_unlinked",
                    model=record._name,
                    record=record.id,
                    copies=len(copy_ids),
                )
                copy_ids.unlink()

        return super()._process_end_unlink_record(record)
