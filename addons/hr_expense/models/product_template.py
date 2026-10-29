# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_be_expensed = fields.Boolean(string="Expenses", compute='_compute_can_be_expensed',
        init_storage=lambda model: None,  # skip initialization (False)
        store=True, readonly=False, help="Specify whether the product can be selected in an expense.")

    @api.depends('type', 'purchase_ok')
    def _compute_can_be_expensed(self):
        self.filtered(lambda p: p.type not in ['consu', 'service'] or not p.purchase_ok).update({'can_be_expensed': False})

    @api.depends('can_be_expensed')
    def _compute_purchase_ok(self):
        for record in self:
            if record.can_be_expensed:
                record.purchase_ok = True
