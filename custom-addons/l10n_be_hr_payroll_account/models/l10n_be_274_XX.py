# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nBe274XX(models.Model):
    _inherit = 'l10n_be.274_xx'

    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, index='btree_not_null')

    def action_post_account_entries(self):
        self.ensure_one()
        self.state = 'done'

        config_fields = [
            'exemption_doctor_master_account_id', 'exemption_bachelor_account_id',
            'exemption_bachelor_capping_account_id', 'exemption_journal_id',
        ]
        for config_field in config_fields:
            if not self.company_id[config_field]:
                raise ValidationError(_('Please make sure that the journal and the accounts are correctly configured on the Payroll Settings.'))

        today = fields.Date.today()

        move_vals = {
            'narration': _('Withholding Taxes Exemption for %s', self.date_start.strftime('%B %Y')),
            'ref': self.date_start.strftime('%B %Y'),
            'journal_id': self.company_id.exemption_journal_id.id,
            'date': today,
            'line_ids': [(0, 0, {
                'name': _("Exemption for doctors/civil engineers/masters"),
                'account_id': self.company_id.exemption_doctor_master_account_id.id,
                'journal_id': self.company_id.exemption_journal_id.id,
                'date': today,
                'debit': 0,
                'credit': self.deducted_amount_32 + self.deducted_amount_33,
            }), (0, 0, {
                'name': _("Exemption for bachelors"),
                'account_id': self.company_id.exemption_bachelor_account_id.id,
                'journal_id': self.company_id.exemption_journal_id.id,
                'date': today,
                'debit': 0,
                'credit': self.deducted_amount_34,
            })]
        }
        credit_sum = self.deducted_amount_32 + self.deducted_amount_33 + self.deducted_amount_34

        if self.capped_amount_34 < self.deducted_amount_34:
            move_vals['line_ids'].append((0, 0, {
                'name': _("Exemption Capping for bachelors"),
                'account_id': self.company_id.exemption_bachelor_capping_account_id.id,
                'journal_id': self.company_id.exemption_journal_id.id,
                'date': today,
                'debit': self.deducted_amount_34 - self.capped_amount_34,
                'credit': 0,
            }))
            debit_sum = self.deducted_amount_34 - self.capped_amount_34
        else:
            debit_sum = 0

        # Create adjustment line, as credit > debit
        acc_id = self.company_id.exemption_journal_id.default_account_id.id
        if not acc_id:
            raise UserError(_('Please define a default journal on the exmption journal!'))

        move_vals['line_ids'].append((0, 0, {
            'name': _('Adjustment Entry'),
            'account_id': acc_id,
            'journal_id': self.company_id.exemption_journal_id.id,
            'date': today,
            'debit': credit_sum - debit_sum,
            'credit': 0.0,
        }))

        self.move_id = self.env['account.move'].create(move_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
