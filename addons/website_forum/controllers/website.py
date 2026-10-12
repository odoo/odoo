from odoo import http

from odoo.addons.website.controllers.main import Website


class ForumWebsite(Website):

    @http.route()
    def track(self, res_model, res_id, **kwargs):
        # EXTENDS website
        res = super().track(res_model, res_id, **kwargs)
        if res_model == 'forum.post':
            # increment view counter
            question = self.env['forum.post'].browse(int(res_id))
            question.sudo()._set_viewed()
        return res
