# -*- coding: utf-8 -*-
# Copyright 2014-now Equitania Software GmbH - Pforzheim - Germany
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class EQResCompany(models.Model):
    _inherit = "res.company"

    eq_background_image = fields.Binary(string="Home Menu Background Image", attachment=True)
    eq_background_image_name = fields.Char(string="Background Image Name")