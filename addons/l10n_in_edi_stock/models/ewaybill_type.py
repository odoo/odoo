# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EWayBillType(models.Model):
    _name = "l10n.in.ewaybill.type"
    _description = "E-Waybill Document Type"

    name = fields.Char("Document Type")
    code = fields.Char("Code")
    allowed_in_supply_type = fields.Selection(
        [
            ("both", "Incoming and Outgoing"),
            ("out", "Outgoing"),
            ("in", "Incoming"),
        ],
        string="Allowed in supply type",
    )
    active = fields.Boolean("Active", default=True)
    parent_type_ids = fields.Many2many(
        "l10n.in.ewaybill.type",
        "rel_ewaybill_type_subtype",
        "subtype_id",
        "type_id",
        "Parent Types",
    )
