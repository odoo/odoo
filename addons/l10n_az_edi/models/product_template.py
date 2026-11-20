import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_az_eqf_product_code = fields.Char(
        string="National Goods/Services Code",
        help="10-digit code of the national goods and services classification, reported on the electronic invoice (EQF).",
    )

    @api.constrains('l10n_az_eqf_product_code')
    def _check_l10n_az_eqf_product_code(self):
        for template in self:
            if template.l10n_az_eqf_product_code and not re.fullmatch(r'[0-9]{10}', template.l10n_az_eqf_product_code):
                raise ValidationError(self.env._("The National Goods/Services Code must be exactly 10 digits."))
