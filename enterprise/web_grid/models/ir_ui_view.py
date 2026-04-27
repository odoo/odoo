# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('grid', "Grid")])

    def _get_view_info(self):
        return {'grid': {'icon': 'fa fa-th'}} | super()._get_view_info()

    def unlink(self):
        if not any(v.type == "grid" for v in self):
            return super().unlink()
        self.env["ir.actions.act_window.view"].search(
            [("view_mode", "=", "grid"), ("view_id", "in", self.ids)]
        ).unlink()
        res = super().unlink()
        grid_models = list(set(self.search([("type", "=", "grid")]).mapped("model")))
        for action in self.env["ir.actions.act_window"].search(
            [("view_mode", "like", "grid"), ("res_model", "not in", grid_models)]
        ):
            action.view_mode = ",".join(mode for mode in action.view_mode.split(",") if mode != "grid")
        return res
