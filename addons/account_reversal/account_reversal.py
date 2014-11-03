# -*- coding: utf-8 -*-
##############################################################################
#
#    Account reversal module for OpenERP
#    Copyright (C) 2011 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    with the kind advice of Nicolas Bessi from Camptocamp
#    Copyright (C) 2012-2013 Camptocamp SA (http://www.camptocamp.com)
#    @author Guewen Baconnier <guewen.baconnier@camptocamp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models


class account_move(models.Model):
    _inherit = "account.move"

    reversal_id = fields.Many2one('account.move', 'Reversal Entry',
                                  ondelete='set null', readonly=True)

    @api.one
    def _move_reversal(self, reversal_date, reversal_period_id=False,
                       reversal_journal_id=False, move_prefix=False, move_line_prefix=False):
        """
        Creates the move reversal

        :param reversal_date: when the reversal should be input
        :param reversal_period_id: optional period to write on the move
                                   (use the period of the date if empty)
        :param reversal_journal_id: optional journal in which the move will be created
        :param move_prefix: prefix for the move name
        :param move_line_prefix: prefix for the move lines names

        :return: Returns the created reversal move
        """
        context_update = {
            'company_id': self.company_id.id,
            'account_period_prefer_normal': True,
        }
        period_obj = self.env['account.period'].with_context(context_update)

        if not reversal_period_id:
            reversal_period_id = period_obj.find(reversal_date)
        if not reversal_journal_id:
            reversal_journal_id = self.journal_id

        reversal_ref = ''.join([x for x in [move_prefix, self.ref] if x])
        reversal_move_id = self.copy(default={
            'date': reversal_date,
            'period_id': reversal_period_id.id,
            'ref': reversal_ref,
            'journal_id': reversal_journal_id.id,
        })

        self.write({'reversal_id': reversal_move_id.id})

        for reversal_move_line in reversal_move_id.line_id:
            reversal_ml_name = ' '.join(
                [x for x in [move_line_prefix, reversal_move_line.name] if x]
            )
            reversal_move_line.write(
                {'debit': reversal_move_line.credit,
                 'credit': reversal_move_line.debit,
                 'amount_currency': reversal_move_line.amount_currency * -1,
                 'name': reversal_ml_name},
                check=True, update_check=True
            )

        reversal_move_id.validate()
        return reversal_move_id

    @api.multi
    def create_reversals(self, reversal_date,
                         reversal_period_id=False, reversal_journal_id=False,
                         move_prefix=False, move_line_prefix=False):
        """
        Create the reversal of one or multiple moves

        :param reversal_date: when the reversal should be input
        :param reversal_period_id: optional period to write on the move
                                   (use the period of the date if empty
        :param reversal_journal_id: optional journal in which the move will be created
        :param move_prefix: prefix for the move name
        :param move_line_prefix: prefix for the move lines names

        :return: Returns a list of ids of the created reversal moves
        """
        reversed_move_ids = []
        for src_move in self:
            if src_move.reversal_id:
                continue  # skip the reversal creation if already done

            reversal_move_id = src_move._move_reversal(
                reversal_date,
                reversal_period_id=reversal_period_id,
                reversal_journal_id=reversal_journal_id,
                move_prefix=move_prefix,
                move_line_prefix=move_line_prefix,
            )[0]

            if reversal_move_id:
                reversed_move_ids.append(reversal_move_id)

        return reversed_move_ids
