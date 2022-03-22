# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class AcquirerAdyen(models.Model):
    _inherit = 'payment.acquirer'

    adyen_api_key = fields.Char('API Key', groups='base.group_user')
