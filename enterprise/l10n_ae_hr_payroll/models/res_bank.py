# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    l10n_ae_routing_code = fields.Char(string="UAE Routing Code Agent ID")
