# -*- coding: utf-8 -*-
from odoo import fields, models


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('activity', 'Activity')])

    def _is_qweb_based_view(self, view_type):
        return view_type == "activity" or super()._is_qweb_based_view(view_type)
