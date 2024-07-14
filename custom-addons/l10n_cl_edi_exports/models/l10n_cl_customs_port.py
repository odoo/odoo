# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class CustomsPort(models.Model):
    _name = 'l10n_cl.customs_port'
    _description = 'Chilean customs ports and codes.'

    name = fields.Char(required=True)
    code = fields.Integer(required=True)
    country_id = fields.Many2one(comodel_name='res.country', required=True)

    @api.depends('code')
    def _compute_display_name(self):
        for port in self:
            port.display_name = f'({port.code}) {port.name}'
