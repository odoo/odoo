# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    members_grade_id = fields.Many2one('res.partner.grade', compute='_compute_membership')
    members_pricelist_id = fields.Many2one('product.pricelist', compute='_compute_membership')

    @api.constrains('order_line')
    def _constraint_unique_members_pricelist_and_grade(self):
        for so in self:
            if len(set(so.order_line.mapped('product_id.members_pricelist_id'))) > 1:
                raise ValidationError(so.env._(
                    "You cannot confirm Sale Order %(sale_order_name)s because there are membership"
                    " products assigning different pricelists.", sale_order_name=so.name,
                ))
            if len(set(so.order_line.mapped('product_id.members_grade_id'))) > 1:
                raise ValidationError(so.env._(
                    "You cannot confirm Sale Order %(sale_order_name)s because there are membership"
                    " products assigning different grades.", sale_order_name=so.name,
                ))

    @api.depends('order_line.product_id.members_pricelist_id', 'order_line.product_id.members_grade_id')
    def _compute_membership(self):
        self.members_pricelist_id = False
        self.members_grade_id = False
        for so in self:
            membership_lines = so.order_line.filtered(lambda l: l.service_tracking == 'membership')
            so.members_pricelist_id = membership_lines.mapped('product_id.members_pricelist_id')[:1]
            so.members_grade_id = membership_lines.mapped('product_id.members_grade_id')[:1]

    def action_confirm(self):
        res = super().action_confirm()
        self._add_membership()
        return res

    def _add_membership(self):
        for so in self:
            partner_id = so.partner_id.commercial_partner_id
            if so.members_pricelist_id:
                partner_id.specific_property_product_pricelist = so.members_pricelist_id
            if so.members_grade_id:
                partner_id.grade_id = so.members_grade_id
