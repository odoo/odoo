# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class WebsitePage(models.Model):
    _inherit = 'website.page'

    @api.model
    def _post_process_response_from_cache(self, request, response):
        super()._post_process_response_from_cache(request, response)
        request.website._get_livechat_channel_info()
