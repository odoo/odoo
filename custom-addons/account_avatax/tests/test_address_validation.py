from odoo.tests.common import tagged
from .common import TestAvataxCommon
from .mocked_address_validation_response import response as address_validation_response
from odoo.exceptions import ValidationError


class TestAccountAvalaraAddressValidationCommon(TestAvataxCommon):
    """https://developer.avalara.com/certification/avatax/address-validation-badge/"""
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.country_us = cls.env['res.country'].search([('code', '=', 'US')])
        cls.country_not_us = cls.env['res.country'].search([('code', '=', 'BE')])
        cls.env.company.avalara_address_validation = True
        return res

    def _create_partner(self):
        return self.env['res.partner'].create({
            'name': 'Odoo Inc',
            'street': '250 executiv prk blvd',
            'street2': '3400',
            'city': '',
            'zip': '94134',
            'country_id': self.country_us.id,
        })

    def _test_address_validation_flow(self):
        partner = self._create_partner()
        wizard = self.env['avatax.validate.address'].create({'partner_id': partner.id})
        wizard.action_save_validated()

        self.assertEqual(partner.name, 'Odoo Inc', 'The name should not have changed.')
        self.assertEqual(partner.street, '250 Executive Park Blvd Ste 3400', 'The validated address is incorrect.')
        self.assertEqual(partner.street2, '', 'The validated address is incorrect.')
        self.assertEqual(partner.city, 'San Francisco', 'The validated address is incorrect.')
        self.assertEqual(partner.zip, '94134-3349', 'The validated address is incorrect.')


@tagged("-at_install", "post_install")
class TestAccountAvalaraAddressValidation(TestAccountAvalaraAddressValidationCommon):
    def test_address_validation_wizard(self):
        with self._capture_request(return_value=address_validation_response):
            self._test_address_validation_flow()

    def test_address_validation_NA_only(self):
        """Avalara Address Validation endpoint only works with US and Canadian Addresses.

        Do not call the service for other countries.
        """
        partner = self._create_partner()
        partner.country_id = self.country_not_us
        with self.assertRaises(ValidationError):
            wizard = self.env['avatax.validate.address'].create({'partner_id': partner.id})
            wizard._compute_validated_address()

    def test_auto_apply_fp_on_payment(self):
        self.partner.zip = False
        self.fp_avatax.auto_apply = True
        self.fp_avatax.state_ids = self.partner.state_id

        # ensure this doesn't raise ValidationError from _check_address
        self.env["account.payment"].create({"partner_id": self.partner.id})


@tagged("-standard", "external")
class TestAccountAvalaraAddressValidationExternal(TestAccountAvalaraAddressValidationCommon):
    def test_integration_address_validation_wizard(self):
        with self._skip_no_credentials():
            self._test_address_validation_flow()
