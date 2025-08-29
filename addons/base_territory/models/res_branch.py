# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResBranch(models.Model):
    _name = "res.branch"
    _description = "branch"

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", string="Branch Manager")
    district_id = fields.Many2one("res.district", string="District")
    description = fields.Char()
