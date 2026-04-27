# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountIntrastatServicesCode(models.Model):
    _inherit = 'account.intrastat.code'
    type = fields.Selection(selection_add=[('service', 'Service')], ondelete={'service': 'set default'})
