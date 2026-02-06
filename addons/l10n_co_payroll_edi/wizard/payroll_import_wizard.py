# Part of GPCB. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PayrollImportWizard(models.TransientModel):
    _name = 'l10n_co.payroll.import.wizard'
    _description = 'Import Payroll Data from CSV'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    csv_file = fields.Binary(string='CSV File', required=True)
    csv_filename = fields.Char(string='Filename')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    settlement_date = fields.Date(string='Payment Date', required=True)

    def action_import(self):
        """Import payroll data from a CSV file.

        Expected CSV columns:
        employee_id_number, salary, transport, overtime_hed, overtime_hen,
        commission, bonus, health_eps, pension_afp, rtefte, other_deductions
        """
        self.ensure_one()

        if not self.csv_file:
            raise UserError(_('Please upload a CSV file.'))

        try:
            content = base64.b64decode(self.csv_file).decode('utf-8-sig')
        except Exception:
            raise UserError(_('Invalid CSV file. Ensure it is UTF-8 encoded.'))

        reader = csv.DictReader(io.StringIO(content))

        PayrollDoc = self.env['l10n_co.payroll.document']
        PayrollLine = self.env['l10n_co.payroll.document.line']
        Employee = self.env['hr.employee']

        documents = self.env['l10n_co.payroll.document']
        errors = []

        for row_num, row in enumerate(reader, start=2):
            emp_id = (row.get('employee_id_number') or '').strip()
            if not emp_id:
                errors.append(_('Row %d: Missing employee ID number.', row_num))
                continue

            employee = Employee.search([
                ('identification_id', '=', emp_id),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if not employee:
                errors.append(_(
                    'Row %d: Employee with ID %s not found.', row_num, emp_id,
                ))
                continue

            doc = PayrollDoc.create({
                'company_id': self.company_id.id,
                'employee_id': employee.id,
                'period_start': self.period_start,
                'period_end': self.period_end,
                'settlement_date': self.settlement_date,
            })

            # Create earning lines
            earning_fields = {
                'salary': 'Salario',
                'transport': 'Auxilio de Transporte',
                'overtime_hed': 'Hora Extra Diurna',
                'overtime_hen': 'Hora Extra Nocturna',
                'commission': 'Comisiones',
                'bonus': 'Bonificación',
                'vacation': 'Vacaciones',
                'prima': 'Prima de Servicios',
            }
            for field, concept in earning_fields.items():
                amount = self._parse_amount(row.get(field, '0'))
                if amount > 0:
                    PayrollLine.create({
                        'document_id': doc.id,
                        'line_type': 'earning',
                        'concept': concept,
                        'amount': amount,
                    })

            # Create deduction lines
            deduction_fields = {
                'health_eps': ('Salud (EPS)', 4.0),
                'pension_afp': ('Pensión (AFP)', 4.0),
                'solidarity_fsp': ('Fondo Solidaridad Pensional', 1.0),
                'rtefte': ('Retención en la Fuente', 0),
                'other_deductions': ('Otras Deducciones', 0),
            }
            for field, (concept, rate) in deduction_fields.items():
                amount = self._parse_amount(row.get(field, '0'))
                if amount > 0:
                    PayrollLine.create({
                        'document_id': doc.id,
                        'line_type': 'deduction',
                        'concept': concept,
                        'amount': amount,
                        'rate': rate,
                    })

            documents |= doc

        if errors:
            _logger.warning('Payroll import had %d errors', len(errors))

        if not documents:
            error_text = '\n'.join(errors) if errors else _('No valid rows found in the CSV.')
            raise UserError(error_text)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported Payroll Documents'),
            'res_model': 'l10n_co.payroll.document',
            'domain': [('id', 'in', documents.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def _parse_amount(self, value):
        """Safely parse a numeric amount from CSV."""
        try:
            return float((value or '0').replace(',', '').replace('$', '').strip())
        except ValueError:
            return 0.0
