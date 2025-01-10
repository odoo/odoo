# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    membership_label = fields.Char(compute='_compute_membership_label')
    members_count = fields.Integer(compute='_compute_members_count')

    def _compute_membership_label(self):
        if self.env['ir.config_parameter'].sudo().get_param('crm.membership_type') == 'Partner':
            self.membership_label = self.env._("Partners")
        else:
            self.membership_label = self.env._("Members")

    def _compute_members_count(self):
        partners_data = self.env['res.partner']._read_group(
            domain=[('specific_property_product_pricelist', 'in', self.ids)],
            groupby=['specific_property_product_pricelist'],
            aggregates=['__count'],
        )
        mapped_data = {pricelist.id: count for pricelist, count in partners_data}
        for pricelist in self:
            pricelist.members_count = mapped_data.get(pricelist.id, 0)
