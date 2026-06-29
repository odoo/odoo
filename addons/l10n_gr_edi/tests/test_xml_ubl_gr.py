from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLGr(AccountTestInvoicingCommon):

    _test_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'name': 'Test GR Company',
            'street': 'Odos Str 10',
            'city': 'Athens',
            'zip': '10100',
            'vat': 'EL123456783',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'odoodev',
            'l10n_gr_edi_aade_key': '20ea658627fd8c7d90594fe4601d3327',
        })
        cls.env.company.partner_id.write({
            'routing_endpoint': 'EL123456783',
            'routing_scheme': '9933',
        })

        cls.partner_a.write({
            'name': 'Greek Govt customer',
            'street': 'Kallirois Str 5',
            'city': 'Athens',
            'zip': '10100',
            'country_id': cls.env.ref('base.gr').id,
            'vat': 'EL094259216',
            'l10n_gr_edi_contracting_authority_name': 'Ministry of justice',
            'l10n_gr_edi_contracting_authority_code': '2048.8010430600.00061',
            'routing_endpoint': 'EL094259216',
            'routing_scheme': '9933',
        })

        cls.product_a.write({'default_code': 'E-COM08', 'l10n_gr_edi_cpv_code': '123123'})
        cls.product_b.write({'default_code': 'FURN_0001', 'l10n_gr_edi_cpv_code': '243234'})

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _create_gr_invoice(self, move_type='out_invoice', **kwargs):
        b2g_defaults = {
            'invoice_date': '2025-01-01',
            'invoice_date_due': '2025-01-01',
            'l10n_gr_edi_budget_type': '1',
            'l10n_gr_edi_project_reference': '13213422222',
            'l10n_gr_edi_contract_reference': '0121221212',
            'l10n_gr_edi_inv_type': '1.1',
            'invoice_payment_term_id': False,
        }
        b2g_defaults.update(kwargs)
        return self._create_invoice(
            move_type=move_type,
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, quantity=1.0, price_unit=15.8,
                                           tax_ids=self.company_data['default_tax_sale']),
                self._prepare_invoice_line(product_id=self.product_b, quantity=1.0, price_unit=5.1,
                                           tax_ids=self.company_data['default_tax_sale']),
            ],
            **b2g_defaults,
        )

    def _mark_as_sent(self, invoice, mark=400001958317039):
        invoice.l10n_gr_edi_state = 'invoice_sent'
        invoice.l10n_gr_edi_mark = mark

    def _export_ubl_gr_invoice(self, invoice):
        xml_content, _ = self.env['account.edi.xml.ubl_gr']._export_invoice(invoice)
        return xml_content

    def _assert_xml_fixture_equal(self, invoice, fixture_name):
        # Export an invoice and compare it against the XML fixture file
        xml_content = self._export_ubl_gr_invoice(invoice)
        with misc.file_open(f'{self.test_module}/tests/test_files/from_odoo/{fixture_name}.xml', 'rb') as f:
            expected_xml = f.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml_content),
            self.get_xml_tree_from_string(expected_xml),
        )

    # -------------------------------------------------------------------------
    # BASIC EXPORT TESTS
    # -------------------------------------------------------------------------

    def test_export_greek_invoice(self):
        invoice = self._create_gr_invoice()
        self._mark_as_sent(invoice)
        self._assert_xml_fixture_equal(invoice, 'grcius_out_invoice')

    def test_export_greek_credit_note(self):
        original_invoice = self._create_gr_invoice()
        self._mark_as_sent(original_invoice, mark=123456789)

        refund = self._create_gr_invoice(
            move_type='out_refund',
            invoice_date='2025-01-01',
            l10n_gr_edi_inv_type='5.1',
            l10n_gr_edi_project_reference='ADA123456',
            l10n_gr_edi_contract_reference=None,
        )
        refund.reversed_entry_id = original_invoice.id
        self._mark_as_sent(refund, mark=400001958317040)

        self._assert_xml_fixture_equal(refund, 'grcius_out_refund')
