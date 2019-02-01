# encoding: utf-8


from odoo import models, api, fields, _


class res_company(models.Model):
    _inherit = 'res.company'
    _description = 'Company'

    ice = fields.Char(string='ICE', size=15, related="partner_id.ice", readonly=False)
