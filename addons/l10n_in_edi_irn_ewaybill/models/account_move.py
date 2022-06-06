# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_distance = fields.Integer("Distnace")
    l10n_in_mode = fields.Selection([
        ("0", "Managed by Transporter"),
        ("1", "By Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", copy=False)

    # Vehicle Number and Type required when transportation mode is By Road.
    l10n_in_vehicle_no = fields.Char("Vehicle Number", copy=False)
    l10n_in_vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "ODC")],
        string="Vehicle Type", copy=False)
    
    # Document number and date required in case of transportation mode is Rail, Air or Ship.
    l10n_in_transportation_doc_no = fields.Char(
        "Document Number",
        help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""", copy=False)
    l10n_in_transportation_doc_date = fields.Date("Document Date", help="Date on the transporter document", copy=False)
    
    # transporter id required when transportation done by other party.
    l10n_in_transporter_id = fields.Many2one("res.partner", "Transporter", copy=False)
