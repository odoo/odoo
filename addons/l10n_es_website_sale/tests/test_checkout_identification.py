from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tools import urls

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.l10n_es_website_sale.models.res_partner import ResPartner


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestCheckoutIdentification(BaseCommon, HttpCase):
    """ Outside Spain's VAT territory (non-EU countries, and the Canary Islands/Ceuta/Melilla,
    which are part of Spain but excluded from it), checkout must require identification (VAT or
    an alternative ES ID document), since a full invoice -- never simplified -- is always issued
    to those customers (see l10n_es's invoice-type computation). The order amount is kept below
    the simplified-invoice limit throughout, so the pre-existing amount-based VAT requirement
    (see `ResPartner._get_mandatory_billing_address_fields`) stays out of the way and only the
    new country-based rule is being exercised. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            'country_id': cls.env.ref('base.es').id,
            'account_fiscal_country_id': cls.env.ref('base.es').id,
            'l10n_es_simplified_invoice_limit': 3000.0,
        })
        cls.website = cls.env['website'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.product = cls.env['product.product'].create({
            'name': 'Cheap Product',
            'list_price': 100.0,
            'website_published': True,
        })
        cls.portal_user = cls._create_new_portal_user()
        cls.partner = cls.portal_user.partner_id
        cls.es = cls.env.ref('base.es')
        cls.us = cls.env.ref('base.us')
        cls.be = cls.env.ref('base.be')
        cls.california = cls.env.ref('base.state_us_5')
        cls.canary_state = cls.env.ref('base.state_es_gc')
        cls.default_values = {
            'name': 'Customer',
            'email': 'customer@example.com',
            'street': '123 Main St',
            'city': 'Somewhere',
            'zip': '10001',
            'phone': '+15550000000',
        }
        cls.submit_url = urls.urljoin(cls.base_url(), '/shop/address/submit')

    def _add_to_cart(self):
        self.make_jsonrpc_request('/shop/cart/add', {
            'product_template_id': self.product.product_tmpl_id.id,
            'product_id': self.product.id,
            'quantity': 1,
        })

    def _submit(self, **extra):
        values = {
            **self.default_values,
            'csrf_token': self.csrf_token(),
            'partner_id': self.partner.id,
            **extra,
        }
        return self.url_open(self.submit_url, data=values).json()

    def test_non_eu_without_identification_is_blocked(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.us.id, state_id=self.california.id)
        self.assertTrue(res.get('messages'))

    def test_non_eu_with_vat_is_allowed(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.us.id, state_id=self.california.id, vat='US-123456')
        self.assertNotIn('invalid_fields', res)

    def test_non_eu_with_alternative_identifier_is_allowed(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.us.id, state_id=self.california.id, ES_FOREIGN_ID='FID-1')
        self.assertNotIn('invalid_fields', res)

    def test_canary_islands_requires_identification(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.es.id, state_id=self.canary_state.id)
        self.assertTrue(res.get('messages'))

    def test_spain_mainland_does_not_require_identification(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.es.id)
        self.assertNotIn('invalid_fields', res)

    def test_eu_country_does_not_require_identification(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        with patch.object(ResPartner, '_l10n_es_ecommerce_is_eu_oss_installed', return_value=False):
            res = self._submit(country_id=self.be.id)
        self.assertNotIn('invalid_fields', res)

    def test_eu_country_requires_identification_with_oss(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        with patch.object(ResPartner, '_l10n_es_ecommerce_is_eu_oss_installed', return_value=True):
            res = self._submit(country_id=self.be.id)
        self.assertTrue(res.get('messages'))

    def test_eu_country_with_vat_is_allowed_with_oss(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        with patch.object(ResPartner, '_l10n_es_ecommerce_is_eu_oss_installed', return_value=True):
            res = self._submit(country_id=self.be.id, vat='BE0477472701')
        self.assertNotIn('invalid_fields', res)
        self.assertFalse(res.get('messages'))

    def test_id_type_selector_is_rendered_next_to_company_name(self):
        """ The ID-type selector + value field render as a single unit, right after "Company"
        (same row), folding VAT in as one of its options and hiding the plain VAT field --
        instead of the generic multi-field "Add identifier" dropdown. """
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        html = self.url_open(urls.urljoin(self.base_url(), '/shop/address')).text
        self.assertIn('o_l10n_es_id_type_select', html)
        self.assertIn('o_l10n_es_id_value_input', html)
        company_idx = html.find('company_name_div')
        select_idx = html.find('o_l10n_es_id_type_select')
        self.assertTrue(0 <= company_idx < select_idx)
        # VAT is folded into the selector as an option, and the plain VAT field is hidden.
        self.assertIn('<option value="vat"', html)
        self.assertNotIn('id="div_vat"', html)
        # Not offered a second time through the generic dropdown.
        self.assertNotIn('data-identifier-key="ES_FOREIGN_ID"', html)
