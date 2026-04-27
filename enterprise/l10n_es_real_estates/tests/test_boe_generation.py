
from odoo.addons.l10n_es_reports.tests.common import TestEsAccountReportsCommon
from odoo import fields
from odoo.tests import tagged

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRealEstateBOEGeneration(TestEsAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.estate = cls.env['l10n_es_reports.real.estate'].create({
            'name': "Estate",
            'cadastral_reference': '1',
            'street_type': 'type',
            'street_name': 'street',
            'street_number_type': 'NUM',
            'municipality': 'ES',
            'municipality_code': '12345',
            'province_code': '12',
            'postal_code': '12345',
        })

    def test_boe_mod_347(self):
        for _dummy in range(0, 2):
            invoice = self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[50000], invoice_date=fields.Date.from_string('2020-12-15'))
            invoice.l10n_es_reports_mod347_invoice_type = 'real_estates'
            invoice.l10n_es_real_estate_id = self.estate
            invoice.action_post()
        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(report, fields.Date.from_string('2020-01-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 347)
