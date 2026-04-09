# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_id_ebupot_doctype = fields.Selection(selection=[
        ('N/A', 'N/A'),
        ('Imprest', 'Imprest'),
        ('Direct', 'Direct')],
        default='N/A',
        string="GovTreasurerOpt",
    )
    l10n_id_ebupot_sp2dnum = fields.Char(string="SP2DNumber")

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['l10n_id_ebupot_doctype'] = self.l10n_id_ebupot_doctype
        payment_vals['l10n_id_ebupot_sp2dnum'] = self.l10n_id_ebupot_sp2dnum
        return payment_vals
