# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class RoomOffice(models.Model):
    _name = "room.office"
    _description = "Room Office"
    _order = "name, id"

    name = fields.Char(string="Office Name", required=True, translate=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company, required=True)

    @api.depends("company_id")
    def _compute_display_name(self):
        super()._compute_display_name()
        for office in self:
            office.display_name = f"{office.name} - {office.company_id.name}"
