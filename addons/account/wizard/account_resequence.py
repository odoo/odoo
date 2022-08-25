# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import get_month, get_fiscal_year
from odoo.tools.misc import format_date

import re
from collections import defaultdict
import json


class ReSequenceWizard(models.TransientModel):
    _name = 'account.resequence.wizard'
    _description = 'Remake the sequence of Journal Entries.'

    sequence_number_reset = fields.Char(compute='_compute_sequence_number_reset')
    first_date = fields.Date(help="Date (inclusive) from which the numbers are resequenced.")
    end_date = fields.Date(help="Date (inclusive) to which the numbers are resequenced. If not set, all Journal Entries up to the end of the period are resequenced.")
    first_name = fields.Char(compute="_compute_first_name", readonly=False, store=True, required=True, string="First New Sequence")
    ordering = fields.Selection([('keep', 'Keep current order'), ('date', 'Reorder by accounting date')], required=True, default='keep')
    move_ids = fields.Many2many('account.move')
    new_values = fields.Text(compute='_compute_new_values')
    preview_moves = fields.Text(compute='_compute_preview_moves')

    @api.model
    def default_get(self, fields_list):
        values = super(ReSequenceWizard, self).default_get(fields_list)
        if 'move_ids' not in fields_list:
            return values
        active_move_ids = self.env['account.move']
        if self.env.context['active_model'] == 'account.move' and 'active_ids' in self.env.context:
            active_move_ids = self.env['account.move'].browse(self.env.context['active_ids'])
        if len(active_move_ids.journal_id) > 1:
            raise UserError(_('You can only resequence items from the same journal'))
        move_types = set(active_move_ids.mapped('move_type'))
        if (
            active_move_ids.journal_id.refund_sequence
            and ('in_refund' in move_types or 'out_refund' in move_types)
            and len(move_types) > 1
        ):
            raise UserError(_('The sequences of this journal are different for Invoices and Refunds but you selected some of both types.'))
        values['move_ids'] = [(6, 0, active_move_ids.ids)]
        return values

    @api.depends('first_name')
    def _compute_sequence_number_reset(self):
        for record in self:
            record.sequence_number_reset = record.move_ids[0]._deduce_sequence_number_reset(record.first_name)

    @api.depends('move_ids')
    def _compute_first_name(self):
        self.first_name = ""
        for record in self:
            if record.move_ids:
                record.first_name = min(record.move_ids._origin.mapped('name'))

    @api.depends('new_values', 'ordering')
    def _compute_preview_moves(self):
        """Reduce the computed new_values to a smaller set to display in the preview."""
        for record in self:
            new_values = sorted(json.loads(record.new_values).values(), key=lambda x: x['server-date'], reverse=True)
            changeLines = []
            in_elipsis = 0
            previous_line = None
            for i, line in enumerate(new_values):
                if i < 3 or i == len(new_values) - 1 or line['new_by_name'] != line['new_by_date'] \
                 or (self.sequence_number_reset == 'year' and line['server-date'][0:4] != previous_line['server-date'][0:4])\
                 or (self.sequence_number_reset == 'month' and line['server-date'][0:7] != previous_line['server-date'][0:7]):
                    if in_elipsis:
                        changeLines.append({'id': 'other_' + str(line['id']), 'current_name': _('... (%s other)', in_elipsis), 'new_by_name': '...', 'new_by_date': '...', 'date': '...'})
                        in_elipsis = 0
                    changeLines.append(line)
                else:
                    in_elipsis += 1
                previous_line = line

            record.preview_moves = json.dumps({
                'ordering': record.ordering,
                'changeLines': changeLines,
            })

    @api.depends('first_name', 'move_ids', 'sequence_number_reset')
    def _compute_new_values(self):
        """Compute the proposed new values.

        Sets a json string on new_values representing a dictionary thats maps account.move
        ids to a disctionay containing the name if we execute the action, and information
        relative to the preview widget.
        """
        def _get_move_key(move_id):
            if self.sequence_number_reset == 'year':
                return move_id.date.year
            elif self.sequence_number_reset == 'month':
                return (move_id.date.year, move_id.date.month)
            return 'default'

        self.new_values = "{}"
        for record in self.filtered('first_name'):
            moves_by_period = defaultdict(lambda: record.env['account.move'])
            for move in record.move_ids._origin:  # Sort the moves by period depending on the sequence number reset
                moves_by_period[_get_move_key(move)] += move

            format, format_values = self.env['account.move']._get_sequence_format_param(record.first_name)

            new_values = {}
            for j, period_recs in enumerate(moves_by_period.values()):
                # compute the new values period by period
                for move in period_recs:
                    new_values[move.id] = {
                        'id': move.id,
                        'current_name': move.name,
                        'state': move.state,
                        'date': format_date(self.env, move.date),
                        'server-date': str(move.date),
                    }

                new_name_list = [format.format(**{
                    **format_values,
                    'year': period_recs[0].date.year % (10 ** format_values['year_length']),
                    'month': period_recs[0].date.month,
                    'seq': i + (format_values['seq'] if j == (len(moves_by_period)-1) else 1),
                }) for i in range(len(period_recs))]

                # For all the moves of this period, assign the name by increasing initial name
                for move, new_name in zip(period_recs.sorted(lambda m: (m.sequence_prefix, m.sequence_number)), new_name_list):
                    new_values[move.id]['new_by_name'] = new_name
                # For all the moves of this period, assign the name by increasing date
                for move, new_name in zip(period_recs.sorted(lambda m: (m.date, m.name, m.id)), new_name_list):
                    new_values[move.id]['new_by_date'] = new_name

            record.new_values = json.dumps(new_values)

    def resequence(self):
        new_values = json.loads(self.new_values)
        if self.move_ids.journal_id and self.move_ids.journal_id.restrict_mode_hash_table:
            if self.ordering == 'date':
                raise UserError(_('You can not reorder sequence by date when the journal is locked with a hash.'))
        self.env['account.move'].browse(int(k) for k in new_values.keys()).name = False
        for move_id in self.move_ids:
            if str(move_id.id) in new_values:
                if self.ordering == 'keep':
                    move_id.name = new_values[str(move_id.id)]['new_by_name']
                else:
                    move_id.name = new_values[str(move_id.id)]['new_by_date']
