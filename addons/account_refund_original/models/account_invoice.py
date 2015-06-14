# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    refund_invoices_description = fields.Text('Refund invoices description')
    origin_invoices_ids = fields.Many2many(
        comodel_name='account.invoice', column1='refund_invoice_id',
        column2='original_invoice_id', relation='account_invoice_refunds_rel',
        string='Refund invoice', help='Links to original invoice which is '
                                      'referred by current refund invoice')
