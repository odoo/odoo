# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import sale_expense, sale_project


class AccountMoveLine(sale_project.AccountMoveLine, sale_expense.AccountMoveLine):

    def _sale_determine_order(self):
        """ For move lines created from expense, we override the normal behavior.
            Note: if no SO but an AA is given on the expense, we will determine anyway the SO from its project's AAs linked,
            using the same mecanism as in Vendor Bills.
        """
        mapping_from_project = self._get_so_mapping_from_project()
        mapping_from_expense = self._get_so_mapping_from_expense()
        mapping_from_project.update(mapping_from_expense)
        return mapping_from_project
