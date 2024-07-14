#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def _get_default_journal_id(self):
        default_structure = self.env.ref('hr_payroll.default_structure', False)
        return default_structure.journal_id if default_structure else False

    journal_id = fields.Many2one(
        'account.journal', 'Salary Journal', readonly=False, required=True,
        company_dependent=True, default=lambda self: self._get_default_journal_id())

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for record_sudo in self.sudo():
            if record_sudo.journal_id.currency_id and record_sudo.journal_id.currency_id != record_sudo.journal_id.company_id.currency_id:
                raise ValidationError(
                    _('Incorrect journal: The journal must be in the same currency as the company')
                )
