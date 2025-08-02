from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_chop = fields.Binary('Company Chop')
