from odoo import api, fields, models


class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    lead_message_template = fields.Text(string="Lead Message Template")