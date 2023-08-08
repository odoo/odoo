# Copyright 2022, Jarsa
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
# pylint: disable=method-inverse

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.users"

    see_all_ou = fields.Boolean(string="view operating unit", help="can or cant view all operating units")
