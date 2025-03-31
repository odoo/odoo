from odoo import models, _
from odoo.exceptions import RedirectWarning


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        for config in self:
            if (
                    config.company_id.country_id.code == 'SA'
                    and config.invoice_journal_id
                    and (config.invoice_journal_id.edi_format_ids.filtered(lambda f: f.code == "sa_zatca")
                         and not config.invoice_journal_id._l10n_sa_ready_to_submit_einvoices())
            ):
                msg = _("The invoice journal of the point of sale %s must be properly onboarded "
                        "according to ZATCA specifications.\n", config.name)
                action = {
                    "view_mode": "form",
                    "res_model": "account.journal",
                    "type": "ir.actions.act_window",
                    "res_id": config.invoice_journal_id.id,
                    "views": [[False, "form"]],
                }
                raise RedirectWarning(msg, action, _('Go to Journal configuration'))
        return super().open_ui()
