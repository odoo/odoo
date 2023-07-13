# -*- coding: utf-8 -*-

from odoo import api, fields, models


class BaseModuleUpdate(models.TransientModel):
    _name = "base.module.update"
    _description = "Update Module"

    def update_module(self):
        self.env['ir.module.module'].update_list()
