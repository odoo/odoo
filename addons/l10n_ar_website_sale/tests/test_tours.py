# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPortalEditInformation(HttpCaseWithUserPortal):

    def test_portal_edit_information(self):
        self.env.user.company_id.country_id = self.env.ref('base.ar')
        self.start_tour("/", 'portal_edit_information', login="portal")
