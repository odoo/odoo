# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):

    _inherit = "res.users"

    im_status = fields.Char('IM Status', compute='_compute_im_status')

    def _compute_im_status(self):
        """Compute the im_status of the users"""
        presence_by_user = {
            presence.user_id: presence.status
            for presence in self.env["bus.presence"].search([("user_id", "in", self.ids)])
        }
        for user in self:
            user.im_status = presence_by_user.get(user, "offline")
