# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_l10n_ph_invoice = fields.Boolean(
        string="Discount Privileges on Invoices",
    )
    module_l10n_ph_sale = fields.Boolean(
        string="Discount Privileges on Sale Orders",
    )
