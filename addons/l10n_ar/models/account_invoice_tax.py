# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _
from odoo.exceptions import ValidationError


class AccountInvoiceTax(models.Model):

    _inherit = "account.invoice.tax"

    @api.constrains('manual', 'tax_id')
    def check_vat_not_manual(self):
        """ Do not let the user to add VAT taxes manually, this one should be
        added on the invoice lines.
        """
        if self.filtered(
           lambda rec: rec.manual and
           rec.tax_id.tax_group_id.l10n_ar_type == 'tax' and
           rec.tax_id.tax_group_id.l10n_ar_tax == 'vat'):
            raise ValidationError(_(
                'You can not add VAT taxes manually, you should add it to'
                ' the invoice lines'))
