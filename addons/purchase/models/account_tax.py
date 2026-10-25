from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    purchase_order_line_ids = fields.Many2many(
        comodel_name='purchase.order.line',
        relation='account_tax_purchase_order_line_rel',
        column1='account_tax_id',
        column2='purchase_order_line_id',
        copy=False,
        readonly=True,
    )

    @api.depends('purchase_order_line_ids')
    def _compute_is_used(self):
        super()._compute_is_used()
        self.sudo().search([
            ('id', 'in', self.filtered(lambda t: not t.is_used).ids),
            ('purchase_order_line_ids', '!=', False),
        ]).is_used = True
