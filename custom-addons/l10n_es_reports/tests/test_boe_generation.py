# -*- coding: utf-8 -*-

from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo import fields
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBOEGeneration(TestAccountReportsCommon):
    """ Basic tests checking the generation of BOE files is still possible.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(TestBOEGeneration, cls).setUpClass(chart_template_ref='es_pymes')

        cls.spanish_partner = cls.env['res.partner'].create({
            'name': "Bernardo Ganador",
            'street': "Avenida de los Informes Financieros, 42",
            'zip': 4242,
            'city': "Madrid",
            'country_id': cls.env.ref('base.es').id,
            'state_id': cls.env.ref('base.state_es_m').id,
            'vat': "ESA12345674",
        })

        base_tags = (
            cls.env.ref('l10n_es.mod_111_casilla_02_balance')
            + cls.env.ref('l10n_es.mod_115_casilla_02_balance')
            + cls.env.ref('l10n_es.mod_303_casilla_01_balance')
        )._get_matching_tags('+')
        base_refund_tags = cls.env.ref('l10n_es.mod_111_casilla_02_balance')._get_matching_tags('-') + cls.env.ref('l10n_es.mod_115_casilla_02_balance')._get_matching_tags('-') + cls.env.ref('l10n_es.mod_303_casilla_14_aeat_mod_303_14_sale_balance')._get_matching_tags('+')
        tax_tags = cls.env.ref('l10n_es.mod_111_casilla_03_balance')._get_matching_tags('-') + cls.env.ref('l10n_es.mod_115_casilla_03_balance')._get_matching_tags('-') + cls.env.ref('l10n_es.mod_303_casilla_03_balance')._get_matching_tags('+')
        tax_refund_tags = (
            cls.env.ref('l10n_es.mod_111_casilla_03_balance')
            + cls.env.ref('l10n_es.mod_115_casilla_03_balance')
            + cls.env.ref('l10n_es.mod_303_casilla_15_balance')
        )._get_matching_tags('+')

        cls.spanish_test_tax = cls.env['account.tax'].create({
            'name': "Test ES BOE tax",
            'amount_type': 'percent',
            'amount': 42,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': base_tags.ids,
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': tax_tags.ids,
                })
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': base_refund_tags.ids,
                }),

                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': tax_refund_tags.ids,
                })
            ],
        })

        cls.env.company.vat = "ESA12345674"

    def _check_boe_export(self, report, options, modelo_number, additional_context=None):
        wizard_model = self.env[report.custom_handler_model_name]
        if additional_context:
            wizard_model = wizard_model.with_context(**additional_context)
        wizard_action = wizard_model.open_boe_wizard(options, modelo_number)
        self.assertEqual(f'l10n_es_reports.aeat.boe.mod{modelo_number}.export.wizard', wizard_action['res_model'], "Wrong BOE export wizard returned")
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id
        self.assertTrue(self.env[report.custom_handler_model_name].export_boe(options), "Empty BOE")

    def _check_boe_111_to_303(self, modelo_number):
        self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today(), taxes=self.spanish_test_tax, post=True)
        report = self.env.ref('l10n_es.mod_%s' % modelo_number)
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, modelo_number)

    @freeze_time('2020-12-22')
    def test_boe_mod_111(self):
        self._check_boe_111_to_303('111')

    @freeze_time('2020-12-22')
    def test_boe_mod_115(self):
        self._check_boe_111_to_303('115')

    @freeze_time('2020-12-22')
    def test_boe_mod_303(self):
        self._check_boe_111_to_303('303')

    @freeze_time('2020-12-22')
    def test_boe_mod_347(self):
        invoice = self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod347_invoice_type = 'regular'
        invoice._post()
        report = self.env.ref('l10n_es_reports.mod_347')
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, fields.Date.from_string('2020-01-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 347)

    @freeze_time('2020-12-22')
    def test_boe_mod_349(self):
        self.partner_a.write({
            'country_id': self.env.ref('base.be').id,
            'vat': "BE0477472701",
        })
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10000], invoice_date=fields.Date.today())
        invoice.l10n_es_reports_mod349_invoice_type = 'E'
        invoice._post()
        report = self.env.ref('l10n_es_reports.mod_349')
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, fields.Date.from_string('2020-12-01'), fields.Date.from_string('2020-12-31'))
        self._check_boe_export(report, options, 349)

    @freeze_time('2020-12-22')
    def test_boe_mod_390(self):
        report = self.env.ref('l10n_es.mod_390')
        options = self._generate_options(report, '2020-01-01', '2020-12-31')
        self._check_boe_export(report, options, 390, additional_context={
            'default_physical_person_name': "Bernard Gagnant",
            'default_principal_activity': "Selling",
            'default_principal_iae_epigrafe': "EAAA",
            'default_principal_code_activity': "AAA",
            'default_judicial_person_name': "Bebert",
            'default_judicial_person_nif': "123",
            'default_judicial_person_procuration_date': '2020-01-01',
            'default_judicial_person_notary': "Maître Gagnant",
        })
