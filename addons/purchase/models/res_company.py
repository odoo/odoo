# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain

from odoo.addons.base.models.res_company import company_default_for


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_bills_to_receive_id = fields.Many2one(
        'account.account',
        string='Bills to Receive Account',
        **company_default_for('account_bills_to_receive_id', 'product.category', 'property_account_bills_to_receive_id'),
        check_company=True,
    )

    account_billed_not_received_id = fields.Many2one(
        'account.account',
        string='Billed Not Received Account',
        **company_default_for('account_billed_not_received_id', 'product.category', 'property_account_billed_not_received_id'),
        check_company=True,
    )

    po_lock = fields.Selection([
        ('edit', 'Allow to edit purchase orders'),
        ('lock', 'Confirmed purchase orders are not editable')
        ], string="Purchase Order Modification", default="edit",
        help='Purchase Order Modification used when you want to purchase order editable after confirm')

    po_double_validation = fields.Selection([
        ('one_step', 'Confirm purchase orders in one step'),
        ('two_step', 'Get 2 levels of approvals to confirm a purchase order')
        ], string="Levels of Approvals", default='one_step',
        help="Provide a double validation mechanism for purchases")

    po_double_validation_amount = fields.Monetary(string='Double validation amount', default=5000,
        help="Minimum amount for which a double validation is required")

    def _get_accrual_candidate_lines(self, date=False):
        candidates = super()._get_accrual_candidate_lines(date=date)
        extra_domain = Domain([
            ('company_id', '=', self.id),
            ('product_id.is_storable', '=', True),
            ('product_id.valuation', '=', 'real_time'),
        ])
        order_lines = self.env['purchase.order.line']._get_accrual_line_ids(date=date, extra_domain=extra_domain)
        candidates['bills_to_receive'] = order_lines.filtered(lambda l: l.amount_to_invoice_at_date > 0)
        candidates['billed_not_received'] = order_lines.filtered(lambda l: l.amount_to_invoice_at_date < 0)
        return candidates
