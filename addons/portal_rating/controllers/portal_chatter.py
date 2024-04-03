# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.portal.controllers import mail


class PortalChatter(mail.PortalChatter):

    def _portal_post_filter_params(self):
        fields = super(PortalChatter, self)._portal_post_filter_params()
        fields += ['rating_value', 'rating_feedback']
        return fields

    @http.route()
    def portal_chatter_post(self, thread_model, thread_id, post_data, **kwargs):
        if post_data.get('rating_value'):
            post_data['rating_feedback'] = post_data.pop('rating_feedback', post_data.get('body'))
        return super().portal_chatter_post(thread_model, thread_id, post_data, **kwargs)
