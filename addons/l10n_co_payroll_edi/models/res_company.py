# Part of GPCB. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_co_payroll_edi_enabled = fields.Boolean(
        string='Electronic Payroll Enabled',
        help='Enable DIAN electronic payroll (nomina electronica) for this company.',
    )
    l10n_co_payroll_edi_employer_type = fields.Selection(
        selection=[
            ('persona_juridica', 'Persona Jurídica'),
            ('persona_natural', 'Persona Natural'),
        ],
        string='Employer Type',
        default='persona_juridica',
    )
    l10n_co_payroll_edi_arl_code = fields.Char(
        string='ARL Code',
        help='DIAN code for the company ARL (Administradora de Riesgos Laborales).',
    )
