from odoo import models, fields, release, _
from datetime import datetime
from odoo.exceptions import UserError

class ComplianceLetter(models.TransientModel):
    _name = 'compliance.letter.wizard'
    _description = 'Compliance Letter for EXO Number'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    def generate_letter(self):
        if self.company_id.country_id.code != 'MT':
            raise UserError(_("Compliance letters can only be created for companies registered in Malta. Please ensure the company's country is set to Malta."))

        data = {
            "version": self.get_odoo_version(),
            "date": self.get_formatted_date(),
            "name": self.company_id.name,
            "vat": self.company_id.vat,
            "address": self.company_id.partner_id.contact_address,
        }
        return self.env.ref('l10n_mt_pos.report_compliance_letter').report_action([], data=data)

    def get_formatted_date(self):
        """Returns the formatted date as 'Date (Month, xxth, 20XX)'."""
        date_obj = datetime.strptime(str(fields.Date.today()), '%Y-%m-%d')
        day = date_obj.day
        day_suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        formatted_date = date_obj.strftime(f"%B {day}{day_suffix}, %Y")
        return formatted_date

    def get_odoo_version(self):
        return release.major_version
