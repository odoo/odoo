from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.l10n_es_reports.tests.test_boe_generation import TestBOEGeneration


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBOEGenerationModelo130(TestBOEGeneration):
    """ Basic tests checking the generation of BOE files is still possible.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()

    def _check_boe_130_export(self, report, options, additional_context=None):
        wizard_model = self.env[report.custom_handler_model_name]
        if additional_context:
            wizard_model = wizard_model.with_context(**additional_context)
        wizard_action = wizard_model.open_boe_wizard(options, '130')
        self.assertEqual('l10n_es_reports_modelo130.aeat.boe.mod130.export.wizard', wizard_action['res_model'], "Wrong BOE export wizard returned")
        wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
        options['l10n_es_reports_boe_wizard_id'] = wizard.id
        self.assertTrue(self.env[report.custom_handler_model_name].export_boe(options), "Empty BOE")

    def _check_boe_130(self):
        self.init_invoice('out_invoice', partner=self.spanish_partner, amounts=[10000], invoice_date=fields.Date.today(), taxes=self.spanish_test_tax, post=True)
        report = self.env.ref('l10n_es_modelo130.mod_130')
        report.filter_multi_company = 'disabled'
        options = self._generate_options(report, '2020-12-01', '2020-12-31')
        self._check_boe_130_export(report, options)

    @freeze_time('2020-12-22')
    def test_boe_mod_130(self):
        self._check_boe_130()
