# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install')
class WebManifestRoutesTest(HttpCaseWithUserDemo):

    def test_web_manifest_scoped_shortcuts(self):
        manifest_url = '/web/manifest.scoped_app_manifest?app_id=industry_fsm&path=/'
        response = self.url_open(manifest_url)
        data = response.json()
        self.assertCountEqual(data['shortcuts'], [{
            'name': 'New task',
            'url': '/scoped_app/field-service/new',
        }, {
            'name': 'My Tasks',
            'url': '/scoped_app/field-service',
        }, {
            'name': 'My Calendar',
            'url': '/scoped_app/field-service?view_type=calendar',
        }])
