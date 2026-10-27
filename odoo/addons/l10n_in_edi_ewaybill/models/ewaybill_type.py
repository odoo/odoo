# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EWayBillType(models.Model):
    _name = "l10n.in.ewaybill.type"
    _description = "E-Waybill Document Type"

    name = fields.Char("Type")
    code = fields.Char("Type Code")
    sub_type = fields.Char("Sub-type")
    sub_type_code = fields.Char("Sub-type Code")
    allowed_supply_type = fields.Selection(
        [
            ("both", "Incoming and Outgoing"),
            ("out", "Outgoing"),
            ("in", "Incoming"),
        ],
        string="Allowed for supply type",
    )
    active = fields.Boolean("Active", default=True)

    @api.depends('sub_type')
    def _compute_display_name(self):
        """Show name and sub_type in name"""
        for ewaybill_type in self:
            ewaybill_type.display_name = _("%s (Sub-Type: %s)", ewaybill_type.name, ewaybill_type.sub_type)
