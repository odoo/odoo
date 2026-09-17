from unittest.mock import patch

from odoo.tests import HttpCase, tagged
from odoo.tools import urls

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.l10n_es_website_sale.models.res_partner import ResPartner


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestCheckoutIdentification(BaseCommon, HttpCase):
    """ Checkout must require identification (VAT or an alternative ES ID document) whenever a
    full invoice -- never simplified -- will be issued: outside Spain's VAT territory (non-EU
    countries, and the Canary Islands/Ceuta/Melilla), or above `l10n_es_simplified_invoice_limit`
    (see l10n_es's invoice-type computation). """

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

    def _add_to_cart(self, quantity=1):
        self.make_jsonrpc_request('/shop/cart/add', {
            'product_template_id': self.product.product_tmpl_id.id,
            'product_id': self.product.id,
            'quantity': quantity,
        })

    def _get_cart(self):
        return self.env['sale.order'].sudo().search(
            [('partner_id', '=', self.partner.id), ('website_id', '=', self.website.id)],
            order='id desc', limit=1,
        )

    def _submit(self, partner_id=True, **extra):
        values = {
            **self.default_values,
            'csrf_token': self.csrf_token(),
            **extra,
        }
        if partner_id:
            values['partner_id'] = self.partner.id
        return self.url_open(self.submit_url, data=values).json()

    def _assert_blocked(self, res, invalid_field='vat'):
        self.assertEqual(res.get('invalid_fields'), [invalid_field])
        self.assertNotIn('redirectUrl', res)
        self.assertTrue(res.get('messages'))

    def test_non_eu_without_identification_is_blocked(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        country_before = self.partner.country_id
        res = self._submit(country_id=self.us.id, state_id=self.california.id)
        self._assert_blocked(res)
        self.partner.invalidate_recordset(['country_id'])
        self.assertEqual(self.partner.country_id, country_before)

    def test_non_eu_with_vat_is_allowed(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.us.id, state_id=self.california.id, vat='US-123456')
        self.assertNotIn('invalid_fields', res)
        self.assertIn('redirectUrl', res)

    def test_non_eu_with_alternative_identifier_is_allowed(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.us.id, state_id=self.california.id, ES_FOREIGN_ID='FID-1')
        self.assertNotIn('invalid_fields', res)
        self.assertIn('redirectUrl', res)

    def test_non_eu_new_billing_address_without_identification_is_blocked(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        partner_count = self.env['res.partner'].search_count([])
        res = self._submit(partner_id=False, country_id=self.us.id, state_id=self.california.id)
        self._assert_blocked(res)
        self.assertEqual(self.env['res.partner'].search_count([]), partner_count)

    def test_non_eu_empty_alternative_identifier_flags_selected_key(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(
            country_id=self.us.id, state_id=self.california.id,
            l10n_es_id_type='ES_PASSPORT', ES_PASSPORT='',
        )
        self._assert_blocked(res, invalid_field='ES_PASSPORT')

    def test_canary_islands_requires_identification(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        country_before = self.partner.country_id
        res = self._submit(country_id=self.es.id, state_id=self.canary_state.id)
        self._assert_blocked(res)
        self.partner.invalidate_recordset(['country_id'])
        self.assertEqual(self.partner.country_id, country_before)

    def test_spain_mainland_does_not_require_identification(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.es.id)
        self.assertNotIn('invalid_fields', res)
        self.assertIn('redirectUrl', res)

    def test_eu_country_does_not_require_identification(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        with patch.object(ResPartner, '_l10n_es_ecommerce_is_eu_oss_installed', return_value=False):
            res = self._submit(country_id=self.be.id)
        self.assertNotIn('invalid_fields', res)
        self.assertIn('redirectUrl', res)

    def test_eu_country_requires_identification_with_oss(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        country_before = self.partner.country_id
        with patch.object(ResPartner, '_l10n_es_ecommerce_is_eu_oss_installed', return_value=True):
            res = self._submit(country_id=self.be.id)
        self._assert_blocked(res)
        self.partner.invalidate_recordset(['country_id'])
        self.assertEqual(self.partner.country_id, country_before)

    def test_eu_country_with_vat_is_allowed_with_oss(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        with patch.object(ResPartner, '_l10n_es_ecommerce_is_eu_oss_installed', return_value=True):
            res = self._submit(country_id=self.be.id, vat='BE0477472701')
        self.assertNotIn('invalid_fields', res)
        self.assertFalse(res.get('messages'))
        self.assertIn('redirectUrl', res)

    def test_spain_above_limit_with_alternative_identifier_is_allowed(self):
        """ Above the simplified-invoice limit a full invoice is issued, which accepts any ES
        identifier (see `_l10n_es_has_identification`), not only a VAT. """
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart(quantity=31)
        res = self._submit(country_id=self.es.id, l10n_es_id_type='ES_FOREIGN_ID', ES_FOREIGN_ID='FID-1')
        self.assertNotIn('invalid_fields', res)
        self.assertIn('redirectUrl', res)
        self.partner.invalidate_recordset(['additional_identifiers'])
        self.assertEqual(self.partner.additional_identifiers.get('ES_FOREIGN_ID'), 'FID-1')
        # The checkout step re-checks the billing address: it must not send the customer back.
        self.assertTrue(self.partner._check_billing_address(order_sudo=self._get_cart()))

    def test_spain_above_limit_without_identification_is_blocked(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart(quantity=31)
        res = self._submit(country_id=self.es.id, l10n_es_id_type='ES_FOREIGN_ID', ES_FOREIGN_ID='')
        self._assert_blocked(res, invalid_field='ES_FOREIGN_ID')

    def test_submitted_identifier_keeps_other_stored_identifiers(self):
        """ The selector only submits the selected identifier: the other identifiers stored on
        the partner must be kept, and only the selected one set or cleared. """
        self.partner.sudo().additional_identifiers = {'ES_RES_CERT': 'RC-1', 'ES_OTHER_ID': 'OID-1'}
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.es.id, l10n_es_id_type='ES_PASSPORT', ES_PASSPORT='PP-1')
        self.assertIn('redirectUrl', res)
        self.partner.invalidate_recordset(['additional_identifiers'])
        self.assertEqual(
            self.partner.additional_identifiers,
            {'ES_RES_CERT': 'RC-1', 'ES_OTHER_ID': 'OID-1', 'ES_PASSPORT': 'PP-1'},
        )

        res = self._submit(country_id=self.es.id, l10n_es_id_type='ES_OTHER_ID', ES_OTHER_ID='')
        self.assertIn('redirectUrl', res)
        self.partner.invalidate_recordset(['additional_identifiers'])
        self.assertEqual(
            self.partner.additional_identifiers,
            {'ES_RES_CERT': 'RC-1', 'ES_PASSPORT': 'PP-1'},
        )

    def test_switching_id_type_keeps_previous_identifier(self):
        """ Switching the ID type saves the new identifier without clearing the previous one,
        and the form reopens on the first identifier stored in the selector's order. """
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self._add_to_cart()
        res = self._submit(country_id=self.es.id, l10n_es_id_type='ES_PASSPORT', ES_PASSPORT='PP-1')
        self.assertIn('redirectUrl', res)
        html = self.url_open(urls.urljoin(self.base_url(), '/shop/address')).text
        self.assertIn('name="ES_PASSPORT"', html)

        res = self._submit(country_id=self.es.id, l10n_es_id_type='ES_FOREIGN_ID', ES_FOREIGN_ID='FID-1')
        self.assertIn('redirectUrl', res)
        self.partner.invalidate_recordset(['additional_identifiers'])
        self.assertEqual(
            self.partner.additional_identifiers,
            {'ES_PASSPORT': 'PP-1', 'ES_FOREIGN_ID': 'FID-1'},
        )
        html = self.url_open(urls.urljoin(self.base_url(), '/shop/address')).text
        self.assertIn('name="ES_FOREIGN_ID"', html)
        self.assertNotIn('name="ES_PASSPORT"', html)

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
