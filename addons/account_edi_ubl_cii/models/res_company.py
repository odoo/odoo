from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    routing_scheme = fields.Selection(related='partner_id.routing_scheme', readonly=False)
    routing_endpoint = fields.Char(related='partner_id.routing_endpoint', readonly=False)
    routing_identifier = fields.Char(related='partner_id.routing_identifier', readonly=False)
