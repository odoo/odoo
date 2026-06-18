from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    x_wps_cic_number = fields.Char(
        string='CIC Number (رقم العميل)',
        help='Customer Identification Code for the WPS bank file.',
    )
    x_wps_debit_account = fields.Char(
        string='Debit Account (IBAN)',
        help='Company IBAN that salaries are debited from in the WPS file.',
    )
    x_wps_mol_id = fields.Char(
        string='MOL ID',
        help='Ministry of Labor establishment ID for WPS.',
    )
    x_file_type = fields.Selection(
        [
            ('wps', 'WPS (Bank Transfer)'),
            ('kawthar', 'Kawthar (Itqan Payroll Card)'),
        ],
        string='Payroll File Type',
        help='The bank file format used when exporting payroll for '
             'employees assigned to this bank account.',
    )
