# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    @api.model
    def render_post_process(self, html):
        # super will transform relative url to absolute
        html = super(MailTemplate, self).render_post_process(html)

        # apply shortener after
        if self.env.context.get('post_convert_links'):
            html = self.env['link.tracker'].convert_links(
                html,
                self.env.context['post_convert_links'],
                blacklist=['/unsubscribe_from_list']
            )
        return html
