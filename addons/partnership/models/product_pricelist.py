# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    partners_count = fields.Integer(compute='_compute_partners_count')
    partners_label = fields.Char(compute='_compute_partners_label')

    def _compute_partners_count(self):
        partners_data = self.env['res.partner']._read_group(
            domain=[('specific_property_product_pricelist', 'in', self.ids)],
            groupby=['specific_property_product_pricelist'],
            aggregates=['__count'],
        )
        mapped_data = {pricelist.id: count for pricelist, count in partners_data}
        for pricelist in self:
            pricelist.partners_count = mapped_data.get(pricelist.id, 0)

    @api.depends('company_id.partnership_label')
    def _compute_partners_label(self):
        for pricelist in self:
            pricelist.partners_label = pricelist.company_id.partnership_label or self.env.company.partnership_label
