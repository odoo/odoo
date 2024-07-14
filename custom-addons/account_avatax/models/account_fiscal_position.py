# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _default_avatax_invoice_account_id(self):
        return self.env.company.account_sale_tax_id.invoice_repartition_line_ids.account_id

    def _default_avatax_refund_account_id(self):
        return self.env.company.account_sale_tax_id.refund_repartition_line_ids.account_id

    is_avatax = fields.Boolean(string="Use AvaTax API")
    avatax_invoice_account_id = fields.Many2one(
        comodel_name='account.account',
        default=_default_avatax_invoice_account_id,
        help="Account that will be used by Avatax taxes for invoices.",
    )
    avatax_refund_account_id = fields.Many2one(
        comodel_name='account.account',
        default=_default_avatax_refund_account_id,
        help="Account that will be used by Avatax taxes for refunds.",
    )
