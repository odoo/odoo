from odoo import api, fields, models


class PurchaseAdvancePaymentInv(models.TransientModel):
    _name = 'purchase.advance.payment.inv'
    _description = "Purchase Advance Payment Invoice"

    count = fields.Integer(string="Order Count", compute='_compute_count')
    purchase_order_ids = fields.Many2many(
        'purchase.order', default=lambda self: self.env.context.get('active_ids'))
    consolidated_billing = fields.Boolean(
        string="Consolidated Billing", default=True,
        help="Create one invoice for all orders related to same vendor and same invoicing address"
    )

    @api.depends('purchase_order_ids')
    def _compute_count(self):
        for wizard in self:
            wizard.count = len(wizard.purchase_order_ids)

    def create_invoices(self):
        self.ensure_one()
        # Set the context for consolidated billing
        ctx = self.env.context.copy()
        ctx.update({
            'consolidated_billing': self.consolidated_billing
        })
        invoices = self.purchase_order_ids.with_context(ctx).action_create_invoice()
        return invoices
