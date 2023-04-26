# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import Controller, request, route


class WebClient(Controller):
    @route('/web/tests/livechat', type='http', auth="user")
    def test_external_livechat(self, **kwargs):
        return request.render('im_livechat.qunit_external_suite', {
            'server_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
        })
