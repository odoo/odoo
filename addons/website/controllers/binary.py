from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.binary import Binary


class WebsiteBinary(Binary):
    @http.route([
        '/web/assets/<int:website_id>/<unique>/<string:filename>',
        '/web/assets/<int:website_id>/draft/<unique>/<string:filename>',
        ], type='http', auth="public", readonly=True)
    def content_assets_website(self, website_id=None, **kwargs):
        if not request.env['website'].browse(website_id).exists():
            raise request.not_found()
        assets_params = {'website_id': website_id}
        if request.httprequest.path.startswith(f'/web/assets/{website_id}/draft/'):
            assets_params['draft_preview'] = True
        return super().content_assets(**kwargs, assets_params=assets_params)
