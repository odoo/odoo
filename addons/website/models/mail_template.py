# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def apply_website_domain(self):
        changed = False
        for template in self.search([('body_html', 'like', ' t-attf-href="/web/login')]):
            # Replace does not work on markup safe
            html = str(template.body_html)
            html = html.replace(
                ' t-attf-href="/web/login',
                ' t-attf-href="{{object.env[\'website\'].get_current_website().domain}}/web/login'
            )
            template.body_html = html
            changed = True
        return changed
