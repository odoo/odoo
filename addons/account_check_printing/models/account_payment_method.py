# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    code = fields.Selection(
        selection_add=[('check_printing', 'check_printing')],
        ondelete={'check_printing': 'cascade'},
    )
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

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['check_printing'] = {'type': ('bank',)}
        return res

    def _get_check_printing_layouts(self):
        """ Returns available check printing layouts for the company, excluding disabled options """
        selection = self.company_id._fields['account_check_printing_layout'].selection
        return [(value, label) for value, label in selection if value != 'disabled']

    @api.depends('check_manual_sequencing')
    def _compute_check_next_number(self):
        for method in self:
            sequence = method.check_sequence_id
            if sequence:
                method.check_next_number = sequence.get_next_char(sequence.number_next_actual)
            else:
                method.check_next_number = 1

    def _inverse_check_next_number(self):
        for method in self:
            if method.check_next_number and not re.match(r'^[0-9]+$', method.check_next_number):
                raise ValidationError(_('Next Check Number should only contains numbers.'))
            if int(method.check_next_number) < method.check_sequence_id.number_next_actual:
                raise ValidationError(_(
                    "The last check number was %s. In order to avoid a check being rejected "
                    "by the bank, you can only use a greater number.",
                    method.check_sequence_id.number_next_actual
                ))
            if method.check_sequence_id:
                method.check_sequence_id.sudo().number_next_actual = int(method.check_next_number)
                method.check_sequence_id.sudo().padding = len(method.check_next_number)

    @api.model_create_multi
    def create(self, vals_list):
        payment_method = super().create(vals_list)
        if payment_method.filtered(lambda r: r.code == 'check_printing'):
            payment_method.filtered(lambda r: not r.check_sequence_id)._create_check_sequence()
        return payment_method

    def _create_check_sequence(self):
        """ Create a check sequence for the journal """
        for method in self:
            method.check_sequence_id = self.env['ir.sequence'].sudo().create({
                'name': _("%(method)s: Check Number Sequence", method=method.name),
                'implementation': 'no_gap',
                'padding': 5,
                'number_increment': 1,
                'company_id': method.company_id.id,
            })
