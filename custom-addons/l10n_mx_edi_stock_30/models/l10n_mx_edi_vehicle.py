# -*- coding: utf-8 -*-

from odoo import models, fields


class Vehicle(models.Model):
    _inherit = 'l10n_mx_edi.vehicle'

    gross_vehicle_weight = fields.Float(
        string="Gross Vehicle Weight",
        help="Permitted weight of the vehicle (in tons) in accordance with NOM-SCT-012-2017.",
    )
