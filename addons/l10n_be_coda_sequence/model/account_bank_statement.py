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
from openerp import models, fields, api, _


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    external_number = fields.Char('External Bank Statement Number',
                                  readonly=True)

    _sql_constraints = [
        ('coda_number_unique_per_bank', 'unique (external_number,journal_id)',
         _('This CODA number is already loaded for this bank account')),
    ]

    @api.model
    def create(self, vals):
        """
        Update the name of bank statement if it's a CODA import
        Args:
            vals: dict

        Returns: self recordset

        """
        if vals.get('journal_id', False):
            self.update_name(vals, vals.get('journal_id', 0))
        res = super(AccountBankStatement, self).create(vals)
        return res

    def update_name(self, vals, journal_id):
        """
        In case of coda_import context:
        Update the name of future statement (with a '/', it'll activate
        the standard behaviour)
        and put the CODA number into the external_number field
        (By default, the CODA number is the name of statement)
        Args:
            vals: dict
            journal_id: int

        Returns: str (the coda number)

        """
        journal_obj = self.env['account.journal']
        journal = journal_obj.browse(journal_id)
        name = ""
        if self.env.context.get('coda_import', False) \
                and journal.force_sequence:
            # Put the previous name (Coda import number) into the
            # external_number field
            # and the name become '/' to call the standard behaviour
            name = vals.get('name', False)
            vals.update({
                'external_number': name,
                'name': '/',
            })
        return name
