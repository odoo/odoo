from odoo import models, fields


class ResPartnerIndustry(models.Model):
    _inherit = 'res.partner.industry'

    monster_id = fields.Integer(string="Monster ID")
