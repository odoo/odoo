# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_display_name(self):
        """ In a string consisting of space-delimited substrings, force a double-space between
        substrings where (when looking right to left) the first substring ends with a numeral and
        the second begins with an Arabic character.
        """
        def repl(match_occurrence):
            # group(1): (\d) == numeral
            # group(3): ([\u0600-\u06FF]) == Arabic character
            return f'{match_occurrence.group(1)}  {match_occurrence.group(3)}'

        super()._compute_display_name()
        for product in self:
            if product.display_name:
                product.display_name = re.sub(r'(\d)(\s)([\u0600-\u06FF])', repl, product.display_name)
