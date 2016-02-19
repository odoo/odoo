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


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    external_number = fields.Char('External Bank Statement Number',
                                  compute='compute_external_number',
                                  store=True)

    @api.multi
    @api.depends('statement_id', 'statement_id.external_number')
    def compute_external_number(self):
        """
        Compute the value of external_number field.
        The value of this field depends on the value of this same field into
        "statement_id" and must be the same.
        Returns:

        """
        for this in self:
            this.external_number = this.statement_id.external_number
