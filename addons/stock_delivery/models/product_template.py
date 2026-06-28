# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # The computed fields only get filled in when there's only one product_variant
    hs_code = fields.Char(
        string='HS Code',
        compute='_compute_variant_hs_code', inverse='_inverse_variant_hs_code',
        help="Standardized code for international shipping and goods declaration.")

    country_of_origin = fields.Many2one(
        string='Origin of Goods',
        compute='_compute_country_of_origin', inverse='_inverse_variant_country_of_origin',
        comodel_name='res.country',
        help="Rules of origin determine where goods originate, i.e. not where they have been shipped from, but where they have been produced or manufactured.\n"
        "As such, the ‘origin’ is the 'economic nationality' of goods traded in commerce.")

    def _compute_variant_hs_code(self):
        for template in self:
            if template.product_variant_count == 1:
                template.hs_code = template.product_variant_id.hs_code
            else:
                template.hs_code = False

    def _inverse_variant_hs_code(self):
        self._set_product_variant_field('hs_code')

    def _compute_country_of_origin(self):
        for template in self:
            if template.product_variant_count == 1:
                template.country_of_origin = template.product_variant_id.country_of_origin
            else:
                template.country_of_origin = False

    def _inverse_variant_country_of_origin(self):
        self._set_product_variant_field('country_of_origin')
