# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class SaftImportWizard(models.TransientModel):
    """ SAF-T import wizard to import LT specific files """
    _inherit = 'account.saft.import.wizard'

    def _get_account_types(self):
        """ Returns a mapping between the account types accepted for the SAF-T and the types in Odoo """
        # Overrides
        if self.company_id.country_code != 'LT':
            return super()._get_account_types()
        return {
            'IT': 'asset_non_current',
            'TT': 'asset_current',
            'I': 'liability_current',
            'NK': 'equity',
            'P': 'income',
            'S': 'expense',
            'KT': 'off_balance',
        }

    def _prepare_account_data(self, tree):
        if self.company_id.country_code == 'LT':
            nsmap = self._get_cleaned_namespace(tree)
            account_id_nodes = tree.findall('.//saft:AccountTableID', nsmap)
            for account_id_node in account_id_nodes:
                account_id_node.tag = account_id_node.tag.replace('AccountTableID', 'StandardAccountID')

        return super()._prepare_account_data(tree)

    def _prepare_partner_data(self, tree):
        if self.company_id.country_code == 'LT':
            nsmap = self._get_cleaned_namespace(tree)
            partner_id_nodes = tree.findall('.//saft:CustomerID', nsmap)
            for partner_id_node in partner_id_nodes:
                if partner_id_node.text == 'N/A':
                    partner_id_node.get_parent().remove(partner_id_node)

        return super()._prepare_partner_data(tree)

    def _prepare_move_data(self, journal_tree, default_currency, journal_id_saft, journal_id, map_accounts, map_taxes, map_currencies, map_partners):
        if self.company_id.country_code == 'LT':
            nsmap = self._get_cleaned_namespace(journal_tree)
            journal_tree = journal_tree.find('.//saft:Transactions', nsmap)

        return super()._prepare_move_data(journal_tree, default_currency, journal_id_saft, journal_id, map_accounts, map_taxes, map_currencies, map_partners)
