# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools,  _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_related_user_id(self):
        self.ensure_one()
        user = self.env['res.users'].sudo().with_context(active_test=False).search([('partner_id', '=', self.id)], limit=1)
        if not user and self.commercial_partner_id:
            user = self.env['res.users'].sudo().with_context(active_test=False).search([('partner_id', '=', self.commercial_partner_id.id)],
                                                                                       limit=1)
        return user
