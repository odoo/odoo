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
        link_tracker_vals = self.env.context.get('post_convert_links')
        if link_tracker_vals:
            # rendering may be done on the composer or on its template: rely on
            # the mailing given in the link tracker values
            mailing = self.env['mailing.mailing'].browse(link_tracker_vals.get('mass_mailing_id'))
            blocked_res_ids = mailing._get_click_tracking_blocked_res_ids(model, list(rendered)) if mailing and model else set()
            for res_id, html in rendered.items():
                if res_id in blocked_res_ids:
                    continue
                rendered[res_id] = self._shorten_links(
                    html,
                    link_tracker_vals,
                    blacklist=['/unsubscribe_from_list', '/view', '/cards']
                )
        return rendered
