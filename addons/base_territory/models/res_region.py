# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResRegion(models.Model):
    _name = "res.region"
    _description = "Region"

    name = fields.Char(required=True)
    description = fields.Char()
    partner_id = fields.Many2one("res.partner", string="Region Manager")
