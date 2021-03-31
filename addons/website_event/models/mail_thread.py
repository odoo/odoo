# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _replace_local_links(self, html, base_url=None):
        ctx = self.env.context
        if not base_url and ctx.get('active_model') == 'event.event' and 'active_id' in ctx:
            domain = self.env['event.event'].browse(ctx['active_id']).website_id.domain
            base_url = ("http://%s" % domain) if domain else None
        return super()._replace_local_links(html, base_url=base_url)
