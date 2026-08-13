from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_ewaybill_port_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Port Address",
        domain="[('country_code', '=', 'IN')]",
        help="Used for overseas transactions via Air/Sea. Represents the port used for dispatch or receipt.",
    )
