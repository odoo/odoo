# -*- coding: utf-8 -*-

from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _get_unece_category_code(self, customer, supplier):
        """ By default, this method will try to compute the tax category (used by EDI for example) based on the amount
        and the tax repartition lines. This is hack-ish~ but a valid solution to get a default value in stable.

        In master, the Category selection field should be by default on taxes and filled for each tax in the demo data
        if possible.

        See https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5305.htm for the codes.
        """
        self.ensure_one()
        # Defaulting to standard tax.
        category = 'S'
        if self.type_tax_use == 'sale':
            eu_countries = self.env.ref('base.europe').country_ids
            if supplier.country_id in eu_countries and customer.country_id not in eu_countries:
                category = 'G'
            else:
                if customer.country_id != supplier.country_id \
                        and customer.country_id in eu_countries \
                        and supplier.country_id in eu_countries:
                    category = 'K'
                # Taxes with a Zero amount will get the E code. (Exempt)
                elif self.amount == 0:
                    category = 'E'

        return category
