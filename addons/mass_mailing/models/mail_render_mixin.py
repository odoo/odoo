# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    @api.model
    def _render_template_postprocess(self, model, rendered):
        # super will transform relative url to absolute
        rendered = super()._render_template_postprocess(model, rendered)

        # apply shortener after
        if self.env.context.get('post_convert_links'):
            for res_id, html in rendered.items():
                rendered[res_id] = self._shorten_links(
                    html,
                    self.env.context['post_convert_links'],
                    blacklist=['/unsubscribe_from_list', '/view', '/cards']
                )
        return rendered

    @api.model
    def _should_track_node(self, node):
        if node.attrib.has_key('data-no-tracking'):
            return False
        return super()._should_track_node(node)
