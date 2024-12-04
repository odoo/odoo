from odoo import models, fields, api, release
from datetime import datetime

class ComplianceLetter(models.Model):
    _name = 'compliance.letter'
    _description = 'Compliance Letter for EXO Number'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    vat_number = fields.Char(string='VAT Number', related='company_id.vat', readonly=True)
    company_address = fields.Char(string='Company Address', related='company_id.partner_id.contact_address', readonly=True)

    def generate_letter(self):
        # Generate the compliance letter
        return self.env.ref('l10n_mt_pos.report_compliance_letter').report_action(self)

    def get_formatted_date(self):
        """Returns the formatted date as 'Date (Month, xxth, 20XX)'."""
        date_obj = datetime.strptime(str(fields.Date.today()), '%Y-%m-%d')
        day = date_obj.day
        day_suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        formatted_date = date_obj.strftime(f"%B {day}{day_suffix}, %Y")
        return formatted_date

    def get_odoo_version(self):
        return release.major_version
