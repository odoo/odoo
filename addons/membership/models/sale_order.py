# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('order_line')
    def _constraint_unique_members_pricelist_and_grade(self):
        for so in self:
            if len(set(so.order_line.mapped('product_id.members_pricelist_id'))) > 1:
                raise ValidationError(_(
                    "You cannot confirm Sale Order %(sale_order_name)s because there are membership"
                    "membership products assigning different pricelists.", sale_order_name=so.name,
                ))
            if len(set(so.order_line.mapped('product_id.members_grade_id'))) > 1:
                raise ValidationError(_(
                    "You cannot confirm Sale Order %(sale_order_name)s because there are membership"
                    " products assigning different grades.", sale_order_name=so.name,
                ))

    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            membership_lines = so.order_line.filtered(lambda l: l.service_tracking == 'membership')
            if not membership_lines:
                continue
            partner_id = so.partner_id.commercial_partner_id
            if (pricelist_id := membership_lines.mapped('product_id.members_pricelist_id')[:1]):
                partner_id.specific_property_product_pricelist = pricelist_id
            if (grade_id := membership_lines.mapped('product_id.members_grade_id')[:1]):
                partner_id.grade_id = grade_id
        return res
