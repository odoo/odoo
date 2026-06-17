# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_np_customs_declaration_number = fields.Char(
        string="Customs Declaration Number",
        help="A unique tracking code assigned to each commercial or personal import/export shipment processed through the Department of Customs.",
    )
