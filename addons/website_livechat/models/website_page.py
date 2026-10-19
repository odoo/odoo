# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, models


class WebsitePage(models.Model):
    _inherit = 'website.page'

    @api.model
    def _post_process_response_from_cache(self, request, response):
        super()._post_process_response_from_cache(request, response)
        html = response.response[0]
        if 'id="o_website_livechat_loader"' not in html:
            return
        # the livechat availability, options and bus id must be fresh
        info = request.website._get_livechat_channel_info()
        loader = ''
        if info:
            script = self.env['ir.qweb']._render('im_livechat.loader', {'info': info})
            loader = f'<script id="o_website_livechat_loader">{script}</script>'
        html = re.sub(
            r'<script id="o_website_livechat_loader">.*?</script>', lambda _match: loader, html, count=1, flags=re.DOTALL,
        )
        response.response = [html]
