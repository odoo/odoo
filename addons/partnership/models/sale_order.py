# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    assigned_grade_id = fields.Many2one('res.partner.grade', compute='_compute_partnership')

    @api.constrains('order_line')
    def _constraint_unique_assigned_grade(self):
        for so in self:
            if len(set(so.order_line.mapped('product_id.grade_id'))) > 1:
                raise ValidationError(so.env._(
                    "You cannot confirm Sale Order %(sale_order_name)s because there are products"
                    " assigning different grades.", sale_order_name=so.name,
                ))

    @api.depends('order_line.product_id')
    def _compute_partnership(self):
        for so in self:
            partnership_lines = so.order_line.filtered(lambda l: l.service_tracking == 'partnership')
            so.assigned_grade_id = partnership_lines.mapped('product_id.grade_id')[:1]

    def action_confirm(self):
        res = super().action_confirm()
        self._add_partnership()
        return res

    def _add_partnership(self):
        for so in self:
            if not so.assigned_grade_id:
                continue
            so.partner_id.commercial_partner_id.grade_id = so.assigned_grade_id
