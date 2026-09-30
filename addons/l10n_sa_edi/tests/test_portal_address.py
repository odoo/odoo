# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Request
from odoo.tests import HttpCase, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSaPortalAddress(BaseCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.saudi_arabia = cls.quick_ref('base.sa')
        cls.env.company.write({
            'country_id': cls.saudi_arabia.id,
            'account_fiscal_country_id': cls.saudi_arabia.id,
        })
        cls.portal_user = cls._create_new_portal_user()

    def _submit_address(self, **values):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        return self.url_open('/my/address/submit', data={
            'name': 'Riyadh Customer',
            'email': 'riyadh@customer.sa',
            'street': 'King Fahd Road',
            'city': 'Riyadh',
            'zip': '12345',
            'country_id': self.saudi_arabia.id,
            'phone': '+966500000000',
            'address_type': 'billing',
            'csrf_token': Request.csrf_token(self),
            **values,
        }).json()

    def test_delivery_address_form_country_change_raises_no_error(self):
        """The SA fields are only rendered on billing addresses"""
        belgium = self.quick_ref('base.be')
        self.browser_js(
            '/my/address?address_type=delivery',
            code=f"""
                const form = document.querySelector('form.address_autoformat');
                form.phone.placeholder = '';
                form.country_id.value = '{belgium.id}';
                form.country_id.dispatchEvent(new Event('change'));
                // The country change is processed once the phone placeholder is updated
                const interval = setInterval(() => {{
                    if (form.phone.placeholder === '+{belgium.phone_code}') {{
                        clearInterval(interval);
                        setTimeout(() => console.log('test successful'));
                    }}
                }}, 50);
            """,
            ready="!!document.querySelector('form.address_autoformat')",
            login=self.portal_user.login,
        )

    def test_address_without_sa_fields_can_be_saved(self):
        """The SA fields are missing from the form until the module is upgraded"""
        feedback = self._submit_address(vat='')
        self.assertEqual(feedback, {'redirectUrl': '/my/addresses'})

    def test_address_without_vat_accepts_empty_sa_fields(self):
        """The VAT field isn't rendered on the checkout unless B2B fields are enabled"""
        feedback = self._submit_address(
            l10n_sa_edi_building_number='', l10n_sa_edi_plot_identification='',
        )
        self.assertEqual(feedback, {'redirectUrl': '/my/addresses'})

    def test_address_rejects_non_four_digit_building_number(self):
        feedback = self._submit_address(l10n_sa_edi_building_number='12')
        self.assertIn('l10n_sa_edi_building_number', feedback.get('invalid_fields', []))

    def test_delivery_address_is_not_flagged_as_company(self):
        self.portal_user.partner_id.vat = '310175397400003'
        self._submit_address(address_type='delivery', use_delivery_as_billing='False')
        self.assertFalse(self.portal_user.partner_id.child_ids.is_company)
