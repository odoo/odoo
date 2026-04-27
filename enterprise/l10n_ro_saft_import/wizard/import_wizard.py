# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class SaftImportWizard(models.TransientModel):
    """ SAF-T import wizard to import RO specific files """
    _inherit = 'account.saft.import.wizard'

    def _get_account_types(self):
        """ Returns a mapping between the account types accepted for the SAF-T and the types in Odoo """
        # Overrides
        if self.company_id.country_code != 'RO':
            return super()._get_account_types()
        return {
            'Activ': 'asset_current',
            'Pasiv': 'liability_current',
            'Bifunctional': 'income',
        }

    def _prepare_account_data(self, tree):
        if self.company_id.country_code == 'RO':
            nsmap = self._get_cleaned_namespace(tree)
            account_id_nodes = tree.findall('.//saft:AccountID', nsmap)
            standard_id_nodes = tree.findall('.//saft:StandardAccountID', nsmap)
            for account_id_node in account_id_nodes:
                account_id_node.tag = account_id_node.tag.replace('AccountID', 'StandardAccountID')
            for standard_id_node in standard_id_nodes:
                standard_id_node.tag = standard_id_node.tag.replace('StandardAccountID', 'AccountID')

        return super()._prepare_account_data(tree)
