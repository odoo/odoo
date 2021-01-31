# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import fields, models


class IapAccount(models.Model):
    _inherit = "iap.account"

    endpoint = fields.Char()
