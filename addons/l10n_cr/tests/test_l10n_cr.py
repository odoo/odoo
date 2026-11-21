from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCr(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('cr')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.country_id = cls.env.ref('base.cr')

    def test_district_onchange_fills_canton_and_province(self):
        san_rafael = self.env.ref('l10n_cr.district_cr_20108')
        with Form(self.env['res.partner']) as partner_form:
            partner_form.name = 'Coyol'
            partner_form.country_id = self.env.ref('base.cr')
            partner_form.l10n_cr_district_id = san_rafael
            self.assertEqual(partner_form.city_id, self.env.ref('l10n_cr.city_cr_201'))
            self.assertEqual(partner_form.state_id, self.env.ref('base.state_A'))
            partner_form.city_id = self.env.ref('l10n_cr.city_cr_101')
            self.assertFalse(partner_form.l10n_cr_district_id)
        self.assertEqual(san_rafael.display_name, 'San Rafael (Alajuela)')
        partner = self.env['res.partner'].create({'name': 'Coyol', 'country_id': self.env.ref('base.cr').id, 'l10n_cr_district_id': san_rafael.id})
        with Form(partner) as partner_form:
            partner_form.city_id = self.env.ref('l10n_cr.city_cr_201')
            partner_form.state_id = self.env.ref('base.state_SJ')
            self.assertFalse(partner_form.city_id)
            self.assertFalse(partner_form.l10n_cr_district_id)
            self.assertEqual(partner_form.state_id, self.env.ref('base.state_SJ'))

    def test_nite(self):
        """A NITE has 10 digits: 3-120 for foreign individuals, 3-130 for entities without legal personality."""
        cr = self.env.ref('base.cr')
        individual = self.env['res.partner'].create({
            'name': 'Foreign Consultant',
            'country_id': cr.id,
            'additional_identifiers': {'CR_NITE': '3-120-123456'},
        })
        entity = self.env['res.partner'].create({
            'name': 'Consorcio Ejemplo',
            'country_id': cr.id,
            'additional_identifiers': {'CR_NITE': '3130654321'},
        })
        self.assertEqual(individual._get_additional_identifier('CR_NITE'), '3120123456')
        self.assertFalse(individual.is_company)
        self.assertTrue(entity.is_company)
        for wrong_nite in ('2000000000', '312012345', '3120A23456'):
            with self.subTest(nite=wrong_nite), self.assertRaises(ValidationError):
                individual._set_additional_identifier('CR_NITE', wrong_nite)
