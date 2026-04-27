# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosBlackboxBeLog(models.Model):
    _name = "pos_blackbox_be.log"
    _description = "Track every changes made while using the Blackbox"
    _order = "id desc"

    user = fields.Many2one("res.users", readonly=True)
    action = fields.Selection(
        [("create", "create"), ("modify", "modify"), ("delete", "delete")],
        readonly=True,
    )
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    model_name = fields.Char(readonly=True)
    record_name = fields.Char(readonly=True)
    description = fields.Char(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("install_mode"):
            for vals in vals_list:
                vals['user'] = vals.get('user', self.env.uid)
        return super().create(vals_list)
