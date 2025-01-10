# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            partner_id = so.partner_id.commercial_partner_id
            membership_lines = so.order_line.filtered(lambda l: l.service_tracking == 'membership')
            if not membership_lines:
                continue
            pricelist_ids = membership_lines.mapped('product_id.product_tmpl_id.pricelist_id')
            if pricelist_ids:
                if len(set(pricelist_ids)) > 1:
                    raise UserError(_(
                        "You cannot confirm Sale Order %(sale_order_name)s because there are "
                        "membership products assigning different pricelists.",
                        sale_order_name=so.name,
                    ))
                partner_id.specific_property_product_pricelist = pricelist_ids[0]
            grade_ids = membership_lines.mapped('product_id.product_tmpl_id.grade_id')
            if grade_ids:
                if len(set(grade_ids)) > 1:
                    raise UserError(_(
                        "You cannot confirm Sale Order %(sale_order_name)s because there are "
                        "membership products assigning different partner levels.",
                        sale_order_name=so.name,
                    ))
                partner_id.grade_id = grade_ids[0]
        return res
