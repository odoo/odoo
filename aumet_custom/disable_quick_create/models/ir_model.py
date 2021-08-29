# -*- coding: utf-8 -*-
# © 2017-2018 Savoir-faire Linux
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    disable_create_edit = fields.Boolean(
        string='Disabling the Create and Edit option')
