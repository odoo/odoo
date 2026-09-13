import datetime

from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    @_debug.perf.timed
    def _load_module_terms(self, modules, langs, overwrite=False):
        super()._load_module_terms(modules, langs, overwrite=overwrite)
        if (
            not langs
            or langs == ["en_US"]
            or not modules
            or "account_reports" not in modules
        ):
            return

        recent_returns = self.env["account.return"].search(
            [("date_to", ">=", datetime.date.today() - relativedelta(years=1))]
        )
        for lang in langs:
            recent_returns.with_context(
                {"update_returns_translation_lang": lang}
            )._update_translated_name()
