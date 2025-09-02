# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
MAX_INT32 = 2147483647


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available('check_printing'):
            res |= self.env.ref('account_check_printing.account_payment_method_check')
        return res

    check_manual_sequencing = fields.Boolean(
        string='Manual Numbering',
        default=False,
        help="Check this option if your pre-printed checks are not numbered.",
    )
    check_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Check Sequence',
        readonly=True,
        copy=False,
        help="Checks numbering sequence.",
    )
    check_next_number = fields.Char(
        string='Next Check Number',
        compute='_compute_check_next_number',
        inverse='_inverse_check_next_number',
        help="Sequence number of the next printed check.",
    )

    bank_check_printing_layout = fields.Selection(
        selection='_get_check_printing_layouts',
        string="Check Layout",
    )

    def _get_check_printing_layouts(self):
        """ Returns available check printing layouts for the company, excluding disabled options """
        selection = self.company_id._fields['account_check_printing_layout'].selection
        return [(value, label) for value, label in selection if value != 'disabled']

    @api.depends('check_manual_sequencing')
    def _compute_check_next_number(self):
        for journal in self:
            sequence = journal.check_sequence_id
            if sequence:
                journal.check_next_number = sequence.get_next_char(sequence.number_next_actual)
            else:
                journal.check_next_number = 1

    def _inverse_check_next_number(self):
        for journal in self:
            next_num = int(journal.check_next_number)
            if journal.check_next_number and not re.match(r'^[0-9]+$', journal.check_next_number):
                raise ValidationError(_('Next Check Number should only contains numbers.'))
            if next_num < journal.check_sequence_id.number_next_actual:
                raise ValidationError(_(
                    "The last check number was %s. In order to avoid a check being rejected "
                    "by the bank, you can only use a greater number.",
                    journal.check_sequence_id.number_next_actual
                ))
            if journal.check_sequence_id:
                if next_num > MAX_INT32:
                    raise ValidationError(_(
                        "The check number you entered (%(num)s) exceeds the maximum allowed value of %(max)d. "
                        "Please enter a smaller number.",
                        num=next_num,
                        max=MAX_INT32,
                    ))
                journal.check_sequence_id.sudo().number_next_actual = next_num
                journal.check_sequence_id.sudo().padding = len(journal.check_next_number)

    @api.model_create_multi
    def create(self, vals_list):
        journals = super().create(vals_list)
        journals.filtered(lambda j: not j.check_sequence_id)._create_check_sequence()
        return journals

    def _create_check_sequence(self):
        """ Create a check sequence for the journal """
        for journal in self:
            journal.check_sequence_id = self.env['ir.sequence'].sudo().create({
                'name': _("%(journal)s: Check Number Sequence", journal=journal.name),
                'implementation': 'no_gap',
                'padding': 5,
                'number_increment': 1,
                'company_id': journal.company_id.id,
            })

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        self._fill_dashboard_data_count(dashboard_data, 'account.payment', 'num_checks_to_print', [
            ('payment_method_line_id.code', '=', 'check_printing'),
            ('state', '=', 'in_process'),
            ('is_sent', '=', False),
        ])
        return dashboard_data

    def action_checks_to_print(self):
        payment_method_line_id = self.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'check_printing')[:1].id
        return {
            'name': _('Checks to Print'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form,graph',
            'res_model': 'account.payment',
            'context': dict(
                self.env.context,
                search_default_checks_to_send=1,
                journal_id=self.id,
                default_journal_id=self.id,
                default_payment_type='outbound',
                default_payment_method_line_id=payment_method_line_id,
            ),
        }
