# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import SUPERUSER_ID
from odoo.http import Controller, request, route


class TestAssetsBundleController(Controller):
    @route('/test_orm/js', type='http', auth='user')
    def bundle(self):
        env = request.env(user=SUPERUSER_ID)
        return env['ir.ui.view']._render_template('test_orm.template1')
