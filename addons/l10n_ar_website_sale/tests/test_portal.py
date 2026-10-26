# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon
from odoo.addons.l10n_ar_website_sale.controllers.portal import L10nARCustomerPortal
from odoo.addons.website.tools import MockRequest


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestArWebsiteSalePortal(TestArCommon):

    def test_portal_values_website_company(self):
        """ The Argentine portal values are given when the company of the
        website is Argentine, as the portal templates check it, also when
        the current company of the user is another one. """
        website = self.env['website'].create({'name': 'Test AR Website', 'company_id': self.env.company.id})
        other_company = self.env['res.company'].create({
            'name': 'Other Company',
            'country_id': self.env.ref('base.us').id,
        })
        self.env.user.company_ids |= other_company
        with MockRequest(self.env, website=website, context={'allowed_company_ids': other_company.ids}) as request:
            self.assertEqual(request.env.company, other_company)
            values = L10nARCustomerPortal()._prepare_portal_layout_values()
        self.assertEqual(values.get('partner_sudo'), self.env.user.partner_id)
