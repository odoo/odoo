# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class L10nBrOperationType(models.Model):
    _name = "l10n_br.operation.type"
    _description = "Operation Type"

    active = fields.Boolean(default=True)
    technical_name = fields.Char(
        required=True,
        string="Technical Name",
        help="The name that will be sent as operationType to the Brazilian Avatax API.",
    )
    name = fields.Char(
        required=True,
        string="Name",
        translate=True,
    )
