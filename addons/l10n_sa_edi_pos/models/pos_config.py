from odoo import models, api, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_invoice_journal(self):
        """
            Override to make sure POS invoice journal was probably onboarded before being used
        """
        super()._check_company_invoice_journal()
        for config in self:
            if config.company_id.country_id.code == 'SA' and config.invoice_journal_id and not config.invoice_journal_id._l10n_sa_ready_to_submit_einvoices():
                raise ValidationError(_("The invoice journal of the point of sale %s must be properly onboarded according to ZATCA specifications.", config.name))
