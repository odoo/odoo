# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4
import base64

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    sepa_export_date = fields.Date(string='Generation Date')
    sepa_export = fields.Binary(string='SEPA File', help="Export file related to this payslip")
    sepa_export_filename = fields.Char(string='File Name', help="Name of the export file generated for this payslip", store=True)
    sepa_uetr = fields.Char(
        string='UETR',
        help='Unique end-to-end transaction reference',
    )

    def action_open_sepa_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name' : 'Select a bank journal!',
            'res_model': 'hr.payslip.sepa.wizard',
            'view_mode': 'form',
            'view_id' : 'hr_payslip_sepa_xml_form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def _get_payments_vals(self, journal_id):
        self.ensure_one()

        payment_vals = {
            'id' : self.id,
            'name': self.number,
            'payment_date' : fields.Date.today(),
            'amount' : self.net_wage,
            'journal_id' : journal_id.id,
            'currency_id' : journal_id.currency_id.id,
            'payment_type' : 'outbound',
            'ref' : self.number,
            'partner_id' : self.employee_id.work_contact_id.id,
            'partner_bank_id': self.employee_id.bank_account_id.id,
        }
        if journal_id.sepa_pain_version == 'pain.001.001.09':
            if not self.sepa_uetr:
                payment_vals['sepa_uetr'] = self.sepa_uetr = str(uuid4())
            else:
                payment_vals['sepa_uetr'] = self.sepa_uetr

        return payment_vals

    def _create_xml_file(self, journal_id, file_name=None):
        employees = self.mapped('employee_id').filtered(lambda e: not e.work_contact_id)
        if employees:
            raise UserError(_("Some employees (%s) don't have a work contact.", ','.join(employees.mapped('name'))))
        employees = self.mapped('employee_id').filtered(lambda e: e.work_contact_id and not e.work_contact_id.name)
        if employees:
            raise UserError(_("Some employees (%s) don't have a valid name on the work contact.", ','.join(employees.mapped('name'))))
        employees = self.mapped('employee_id').filtered(lambda e: not e.bank_account_id)
        if employees:
            raise UserError(_("Some employees (%s) don't have a bank account.", ','.join(employees.mapped('name'))))
        if journal_id.bank_account_id.acc_type != 'iban':
            raise UserError(_("The journal '%s' requires a proper IBAN account to pay via SEPA. Please configure it first.", journal_id.name))

        # Map the necessary data
        payments_data = []
        sct_generic = (journal_id.currency_id or journal_id.company_id.currency_id).name != 'EUR' or journal_id.sepa_pain_version == 'iso_20022'
        for slip in self:
            payments_data.append(slip._get_payments_vals(journal_id))
            if not sct_generic and (not slip.employee_id.bank_account_id.bank_bic and not slip.employee_id.bank_account_id.acc_type == 'iban'):
                sct_generic = True

        # Generate XML File
        xml_doc = journal_id.sudo().with_context(
            sepa_payroll_sala=True,
            l10n_be_hr_payroll_sepa_salary_payment=journal_id.company_id.account_fiscal_country_id.code == "BE"
        ).create_iso20022_credit_transfer(payments_data, True, sct_generic)
        xml_binary = base64.encodebytes(xml_doc)

        # Save XML file on the payslip
        self.write({
            'sepa_export_date': fields.Date.today(),
            'sepa_export': xml_binary,
            'sepa_export_filename': (file_name or 'SEPA_export') + ('.xml' if file_name and not file_name.endswith('.xml') else ''),
        })

        # Set payslip runs to paid state, if needed
        self.mapped('payslip_run_id').write({
            'sepa_export_date': fields.Date.today(),
            'sepa_export': xml_binary,
            'sepa_export_filename': (file_name or 'SEPA_export') + ('.xml' if file_name and not file_name.endswith('.xml') else ''),
        })
        payslip_runs = self.mapped('payslip_run_id').filtered(
            lambda run: run.state == 'close' and all(slip.state in ['paid', 'cancel'] for slip in run.slip_ids))

    # Dashboard
    @api.model
    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()
        employee_bank_data = self.env['hr.employee']._get_account_holder_employees_data()
        invalid_iban_emp_ids = self.env['hr.employee']._get_invalid_iban_employee_ids(employee_bank_data)
        if invalid_iban_emp_ids:
            invalid_iban_str = _('Employees With Invalid Bank Accounts')
            res.append({
                'string': invalid_iban_str,
                'count': len(invalid_iban_emp_ids),
                'action': self._dashboard_default_action(invalid_iban_str, 'hr.employee', invalid_iban_emp_ids)
            })

        untrusted_banks_emp_ids = self.env['hr.employee']._get_untrusted_bank_employee_ids(employee_bank_data)
        if untrusted_banks_emp_ids:
            untrusted_banks_str = _('Employees with untrusted Bank Account numbers')
            res.append({
                'string': untrusted_banks_str,
                'count': len(untrusted_banks_emp_ids),
                'action': self._dashboard_default_action(untrusted_banks_str, 'hr.employee', untrusted_banks_emp_ids)
            })

        return res

    @api.model
    def _get_dashboard_batch_fields(self):
        return super()._get_dashboard_batch_fields() + ['sepa_export', 'sepa_export_filename']
