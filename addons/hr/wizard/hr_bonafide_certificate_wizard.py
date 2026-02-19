# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrBonafideCertificateWizard(models.TransientModel):
    _name = 'hr.bonafide.certificate.wizard'
    _description = 'Bonafide Certificate Wizard'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    joining_date = fields.Date(
        string='Joining Date',
        required=True,
        compute='_compute_joining_date',
        store=True,
        readonly=False,
    )
    request_date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
    )
    reason_for_request = fields.Selection([
        ('visa_passport', 'Visa/Passport Application'),
        ('higher_education', 'Higher Education'),
        ('bank_account', 'Bank Account Opening'),
        ('loan', 'Loan Application'),
        ('others', 'Others'),
    ], string='Reason for Request', required=True)
    state_reason = fields.Char(string='State the Reason')

    def get_reason_display(self):
        self.ensure_one()
        if self.reason_for_request == 'others':
            return self.state_reason or 'Others'
        return dict(self._fields['reason_for_request']._description_selection(self.env)).get(self.reason_for_request, '')

    @api.depends('employee_id')
    def _compute_joining_date(self):
        for wizard in self:
            if wizard.employee_id:
                wizard.joining_date = wizard.employee_id._get_first_version_date()

    def action_print(self):
        return self.env.ref('hr.action_report_bonafide_certificate').report_action(self)
