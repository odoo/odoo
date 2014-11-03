# -*- coding: utf-8 -*-
##############################################################################
#
#    Account reversal module for OpenERP
#    Copyright (C) 2011 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    Copyright (c) 2012-2013 Camptocamp SA (http://www.camptocamp.com)
#    @author Guewen Baconnier
#
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


class account_move_reversal(models.TransientModel):
    _name = "account.move.reverse"
    _description = "Create reversal of account moves"

    def _next_period_first_date(self):
        res = False
        period_obj = self.env['account.period']
        today_period_id = period_obj.with_context({'account_period_prefer_normal': True}).find()
        if today_period_id:
            today_period = today_period_id[0]
            next_period_id = today_period.next(1)[0]
            if next_period_id:
                res = next_period_id.date_start
        return res

    date = fields.Date(
        'Reversal Date',
        default=_next_period_first_date,
        required=True,
        help="Enter the date of the reversal account entries. "
             "By default, OpenERP proposes the first day of "
             "the next period.")
    period_id = fields.Many2one(
        'account.period',
        'Reversal Period',
        help="If empty, take the period of the date.")
    journal_id = fields.Many2one(
        'account.journal',
        'Reversal Journal',
        help='If empty, uses the journal of the journal entry '
             'to be reversed.')
    move_prefix = fields.Char(
        'Entries Ref. Prefix',
        size=32,
        help="Prefix that will be added to the 'Ref' of the journal "
             "entry to be reversed to create the 'Ref' of the "
             "reversal journal entry (no space added after the prefix).")
    move_line_prefix = fields.Char(
        'Items Name Prefix',
        default='REV -',
        size=32,
        help="Prefix that will be added to the name of the journal "
             "item to be reversed to create the name of the reversal "
             "journal item (a space is added after the prefix).")

    @api.multi
    def action_reverse(self):
        assert 'active_ids' in self.env.context, "active_ids missing in context"

        move_obj = self.env['account.move']
        active_ids = self.env.context['active_ids']

        move_ids = move_obj.browse(active_ids)

        reversed_move_ids = move_ids.create_reversals(
            self.date,
            reversal_period_id=self.period_id,
            reversal_journal_id=self.journal_id,
            move_prefix=self.move_prefix,
            move_line_prefix=self.move_line_prefix,
        )

        return {'type': 'ir.actions.act_window_close'}
