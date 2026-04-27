from odoo import Command, tools
from odoo.tests import freeze_time, tagged
from odoo.addons.l10n_pl_reports.tests.test_jpk_generation import TestJpkExport


@freeze_time('2023-02-10 18:00:00')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSAFTIncomeTaxExport(TestJpkExport):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write(
            {
                'state_id': cls.env.ref('l10n_pl.state_pl_ds'),
                'street': "ul. Słoneczna 15/7",
            },
        )

    def test_jpk_kr_pd_generation(self):
        """ Test that the generation of the JPK KR PD corresponds to the expectations """

        # Initial balance move
        self.env['account.move'].create(
            {
                'move_type': 'out_invoice',
                'invoice_date': '2022-12-01',
                'date': '2022-12-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'quantity': 2.0,
                        'price_unit': 750.0,
                        'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
        ).action_post()

        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, '2023-01-01', '2023-01-31')
        generated_xml = self.env[report.custom_handler_model_name].l10n_pl_export_saft_income_tax_to_xml(options)['file_content']
        with tools.file_open('l10n_pl_reports_account_saft/tests/expected_xmls/jpk_kr_pd.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(generated_xml),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )
