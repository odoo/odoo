
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

class TestEsAccountReportsCommon(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

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
