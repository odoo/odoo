# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import account


class ResConfigSettings(account.ResConfigSettings):

    pay_invoices_online = fields.Boolean(config_parameter='account_payment.enable_portal_payment')
