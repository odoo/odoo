# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.addons.l10n_br_edi.models.account_move import FREIGHT_MODEL_SELECTION


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    l10n_br_edi_transporter_id = fields.Many2one(
        "res.partner",
        "Transporter Brazil",
        compute="_compute_l10n_br_edi_transporter_id",
        store=True,
        readonly=False,
        help="Brazil: If this uses a transport company, add its company contact here.",
    )
    l10n_br_edi_freight_model = fields.Selection(
        FREIGHT_MODEL_SELECTION,
        string="Freight Model",
        help="Brazil: Used to determine the freight model used on orders.",
    )

    @api.depends("l10n_br_edi_freight_model")
    def _compute_l10n_br_edi_transporter_id(self):
        for carrier in self:
            if carrier.l10n_br_edi_freight_model in ("SenderVehicle", "ReceiverVehicle"):
                carrier.l10n_br_edi_transporter_id = False
