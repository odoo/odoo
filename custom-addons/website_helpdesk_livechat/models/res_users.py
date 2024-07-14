# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class Users(models.Model):
    _inherit = 'res.users'

    def _init_messaging(self):
        domain = [('use_website_helpdesk_livechat', '=', True)]
        if self.env.context.get('allowed_company_ids'):
            domain.append(('company_id', 'in', self.env.context.get('allowed_company_ids')))
        helpdesk_livechat_active = self.env['helpdesk.team'].sudo().search(domain, limit=1)
        res = super()._init_messaging()
        res['helpdesk_livechat_active'] = bool(helpdesk_livechat_active)
        return res
