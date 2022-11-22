from odoo import models, api, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_invoice_journal(self):
        super()._check_company_invoice_journal()
        for config in self:
            journal = config.invoice_journal_id
            if journal and not journal._l10n_sa_can_submit_einvoices():
                raise ValidationError(_("The invoice journal of the point of sale %s must be properly onboarded according to ZATCA specifications.", config.name))
