# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_round


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    unit_cost = fields.Float(
        'Unit Cost', help="Unit cost of the product based on its Bill of materials.",
        digits='Product Price', readonly=True, company_dependent=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_currency_id(self):
        currency = self.env.company.currency_id
        for bom in self:
            bom.currency_id = bom.company_id.currency_id or currency

    def action_update_product_cost_from_bom(self):
        company = self.env.company
        for bom in self:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
            bom.unit_cost = bom.with_company(bom.company_id or company)._compute_bom_cost(product, self)

    def _compute_bom_cost(self, product, boms_to_recompute=False):
        self.ensure_one()
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0

        for operation in self.operation_ids:
            if operation._skip_operation_line(product):
                continue
            total += operation.cost

        for line in self.bom_line_ids:
            if line._skip_bom_line(product):
                continue

            # Compute recursive if line has `child_line_ids`
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.child_bom_id._compute_bom_cost(line.product_id, boms_to_recompute)
                total += line.product_id.uom_id._compute_price(child_total, line.uom_id) * line.product_qty
            else:
                total += line.product_id.uom_id._compute_price(line.product_id.standard_price, line.uom_id) * line.product_qty

        byproduct_cost_share = sum(self.byproduct_ids.mapped('cost_share'))
        if byproduct_cost_share:
            total *= float_round(1 - byproduct_cost_share / 100, precision_rounding=0.0001)

        return self.uom_id._compute_price(total / self.product_qty, self.product_tmpl_id.uom_id)
