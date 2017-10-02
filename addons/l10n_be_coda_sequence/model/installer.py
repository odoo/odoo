# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright Eezee-It
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api


class CodaInstaller(models.TransientModel):
    _name = "l10n_be_coda_sequence.installer"
    _inherit = 'res.config.installer'

    message = fields.Html('Message', readonly=True)
    problem = fields.Boolean('Problem', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """
        Get the compatibility message
        Args:
            fields_list: list of str

        Returns: dict

        """
        res = super(CodaInstaller, self).default_get(fields_list)
        compatibility_message = self.check_compatibility()
        res.update({
            'message': compatibility_message or False,
            'problem': bool(compatibility_message),
        })
        return res

    @api.multi
    def execute(self):
        """
        Use this method to execute an action after installation
        Returns:

        """
        return super(CodaInstaller, self).execute()

    def check_compatibility(self):
        """
        Check the compatibility of this module.
        With some criterion's:
            - Other module installation (who are incompatible)
            - Type on field
            - Unique constraint on a field
            - Journal has a link to only 1 (or 0) bank account
        Returns: str

        """
        message = ''
        module_obj = self.env['ir.module.module']
        bank_obj = self.env['res.partner.bank']
        # Modules compatibility check
        criterion_module = [('name', 'in', ['l10n_be_coda_advanced'])]
        modules = module_obj.search(criterion_module)
        if modules:
            message = 'These modules are incompatible: %s' \
                      % ', '.join([m.name for m in modules])
        # Relation type compatibility check
        journal_field = self.env.ref(
            'account.field_res_partner_bank_journal_id')
        # Unique constraint for Bank Account
        maximum = 0
        for bank_account in bank_obj.search([]):
            criterion_bank = [('acc_number', '=', bank_account.acc_number)]
            nb_acc_number = bank_account.search_count(criterion_bank)
            nb_journal = 0
            if bank_account.journal_id:
                # Search on bank account who has the same journal_id
                criterion_journal = [
                    ('journal_id', '=', bank_account.journal_id.id)]
                nb_journal = bank_account.search_count(criterion_journal)
            maximum = max([nb_acc_number, nb_journal, maximum])

        if journal_field.ttype != 'many2one' or maximum > 1:
            message = 'Your Odoo is <strong>incompatible</strong>' \
                      ' with this new module.'
        return message
