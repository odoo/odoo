# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_br_avatax_portal_email = fields.Char(string='Avatax Portal Email')
    l10n_br_avatax_api_identifier = fields.Char(string='Avalara Brazil API ID', groups='base.group_system')
    l10n_br_avatax_api_key = fields.Char(string='Avalara Brazil API KEY', groups='base.group_system')
    l10n_br_avalara_environment = fields.Selection(
        string="Avalara Brazil Environment",
        selection=[
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        required=True,
        default='sandbox',
    )
    l10n_br_icms_rate = fields.Float(string='Simplified Regime ICMS Rate')
