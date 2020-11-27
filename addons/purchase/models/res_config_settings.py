# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lock_confirmed_po = fields.Boolean("Lock Confirmed Orders", default=lambda self: self.env.company.po_lock == 'lock')
    po_lock = fields.Selection(related='company_id.po_lock', string="Purchase Order Modification *", readonly=False)
    po_order_approval = fields.Boolean("Purchase Order Approval", default=lambda self: self.env.company.po_double_validation == 'two_step')
    po_double_validation = fields.Selection(related='company_id.po_double_validation', string="Levels of Approvals *", readonly=False)
    po_double_validation_amount = fields.Monetary(related='company_id.po_double_validation_amount', string="Minimum Amount", currency_field='company_currency_id', readonly=False)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency", readonly=True,
        help='Utility field to express amount currency')
    default_purchase_method = fields.Selection([
        ('purchase', 'Ordered quantities'),
        ('receive', 'Received quantities'),
        ], string="Bill Control", default_model="product.template",
        help="This default value is applied to any new product created. "
        "This can be changed in the product detail form.", default="receive")
    group_warning_purchase = fields.Boolean("Purchase Warnings", implied_group='purchase.group_warning_purchase')
    module_account_3way_match = fields.Boolean("3-way matching: purchases, receptions and bills")
    module_purchase_requisition = fields.Boolean("Purchase Agreements")
    module_purchase_product_matrix = fields.Boolean("Purchase Grid Entry")
    po_lead = fields.Float(related='company_id.po_lead', readonly=False)
    use_po_lead = fields.Boolean(
        string="Security Lead Time for Purchase",
        config_parameter='purchase.use_po_lead',
        help="Margin of error for vendor lead times. When the system generates Purchase Orders for reordering products,they will be scheduled that many days earlier to cope with unexpected vendor delays.")

    group_send_reminder = fields.Boolean("Receipt Reminder", implied_group='purchase.group_send_reminder', default=True,
        help="Allow automatically send email to remind your vendor the receipt date")

    @api.onchange('use_po_lead')
    def _onchange_use_po_lead(self):
        if not self.use_po_lead:
            self.po_lead = 0.0

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.po_lock = 'lock' if self.lock_confirmed_po else 'edit'
        self.po_double_validation = 'two_step' if self.po_order_approval else 'one_step'
