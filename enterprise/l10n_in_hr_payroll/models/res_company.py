# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_dearness_allowance = fields.Boolean(string='Dearness Allowance', default=True,
        help='Check this box if your company provide Dearness Allowance to employee')
    l10n_in_epf_employer_id = fields.Char(string="EPF Employer ID",
        help="Code of 10 numbers. The first seven numbers represent the establishment ID.\n Next three numbers represent the extension code.")
    l10n_in_esic_ip_number = fields.Char(string="ESIC IP Number",
        help="Code of 17 digits.\n The Identification number is assigned to the company if registered under the Indian provisions of the Employee\'s State Insurance (ESI) Act.")
    l10n_in_pt_number = fields.Char(string="PT Number",
        help="Code of 11 digit.\n The P TIN digit number with the first two digits indicating the State.")
    l10n_in_is_statutory_compliance = fields.Boolean(string="Statutory Compliance")
