from odoo import api, fields, models, _
import re

class ResPartner(models.Model):
    _inherit = 'res.partner'

    saudi_national_id = fields.Char(
        string="Saudi National ID",
        size=10,
        help="Saudi National ID (10 digits, starts with 1)."
    )
    saudi_iqama = fields.Char(string="Saudi Iqama", size=10)
    building_number = fields.Char(string="Building Number")
    street_name = fields.Char(string="Street Name")
    district = fields.Char(string="District")
    city = fields.Char(string="City")
    postal_code = fields.Char(string="Postal Code")
    additional_number = fields.Char(string="Additional Number")

    @api.constrains('saudi_national_id')
    def _check_saudi_national_id(self):
        for rec in self:
            id_val = rec.saudi_national_id
            if id_val and (not re.match(r"^1\d{9}$", id_val)):
                raise ValidationError(_("Saudi National ID must be 10 digits and start with 1"))
