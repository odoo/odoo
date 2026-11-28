from lxml import html
from markupsafe import Markup

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

DUAL_LANGUAGE_REPORT = 'l10n_eg.l10n_eg_report_invoice_document'
STANDARD_REPORT = 'account.report_invoice_document'


def has_class(css_class):
    return f"[contains(concat(' ', normalize-space(@class), ' '), ' {css_class} ')]"


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEgInvoice(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('eg')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ar_001')
        cls.company = cls.company_data['company']
        cls.company.l10n_eg_dual_language_invoice = True
        cls.partner_ar = cls.env['res.partner'].create({'name': 'Arabic Partner', 'lang': 'ar_001'})
        cls.product_a.update_field_translations('name', {'ar_001': 'منتج أ'})

    def _render_invoice(self, invoice):
        report_html = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)[0]
        return html.fromstring(report_html)

    def _texts(self, tree, xpath):
        return [' '.join(node.text_content().split()) for node in tree.xpath(xpath)]

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    def test_setting_is_company_dependent(self):
        company_2 = self.setup_other_company(name='Egyptian Company 2')['company']
        self.assertFalse(company_2.l10n_eg_dual_language_invoice)

        settings = self.env['res.config.settings'].with_company(company_2).create({})
        settings.l10n_eg_dual_language_invoice = True
        settings.execute()
        self.assertTrue(company_2.l10n_eg_dual_language_invoice)

        settings = self.env['res.config.settings'].with_company(self.company).create({})
        self.assertTrue(settings.l10n_eg_dual_language_invoice)
        settings.l10n_eg_dual_language_invoice = False
        settings.execute()
        self.assertFalse(self.company.l10n_eg_dual_language_invoice)
        self.assertTrue(company_2.l10n_eg_dual_language_invoice, "Other companies keep their own setting")

    # -------------------------------------------------------------------------
    # Report routing
    # -------------------------------------------------------------------------

    def test_report_routing(self):
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        bill = self.init_invoice('in_invoice', products=self.product_a)
        self.assertEqual(invoice._get_name_invoice_report(), DUAL_LANGUAGE_REPORT)
        self.assertEqual(bill._get_name_invoice_report(), DUAL_LANGUAGE_REPORT)

        self.company.l10n_eg_dual_language_invoice = False
        self.assertEqual(invoice._get_name_invoice_report(), STANDARD_REPORT)

        self.company.l10n_eg_dual_language_invoice = True
        self.company.country_id = self.env.ref('base.us')
        self.assertEqual(invoice._get_name_invoice_report(), STANDARD_REPORT, "Only Egyptian companies use the dual language report")

    def test_report_routing_uses_invoice_company(self):
        company_2 = self.setup_other_company(name='Egyptian Company 2')['company']
        invoice_2 = self.init_invoice('out_invoice', amounts=[100.0], company=company_2)
        # The current company has the setting enabled, the company of the invoice does not.
        self.assertEqual(invoice_2.with_company(self.company)._get_name_invoice_report(), STANDARD_REPORT)

        company_2.l10n_eg_dual_language_invoice = True
        self.company.l10n_eg_dual_language_invoice = False
        self.assertEqual(invoice_2.with_company(self.company)._get_name_invoice_report(), DUAL_LANGUAGE_REPORT)

    # -------------------------------------------------------------------------
    # Terms and conditions
    # -------------------------------------------------------------------------

    def test_invoice_narration_translation(self):
        """ The default terms are set in the language of the partner. """
        self.env['ir.config_parameter'].sudo().set_bool('account.use_invoice_terms', True)
        self.company.write({'invoice_terms': 'English Terms', 'terms_type': 'plain'})
        self.company.update_field_translations('invoice_terms', {
            'en_US': {'English Terms': 'English Terms'},
            'ar_001': {'English Terms': 'Arabic Terms'},
        })

        invoice_en = self.init_invoice('out_invoice', products=self.product_a)
        self.assertEqual(invoice_en.narration, Markup('<p>English Terms</p>'))
        invoice_ar = self.init_invoice('out_invoice', partner=self.partner_ar, products=self.product_a)
        self.assertEqual(invoice_ar.narration, Markup('<p>Arabic Terms</p>'))

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def test_render_english_partner(self):
        """ English primary layout, left to right, with Arabic as the secondary language. """
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, products=self.product_a, post=True)
        tree = self._render_invoice(invoice)

        # The PDF pages are rendered in this language, which gives their direction.
        self.assertEqual(tree.xpath(f"//div{has_class('article')}/@data-oe-lang"), ['en_US'])
        self.assertTrue(tree.xpath(f"//table{has_class('o_l10n_eg_invoice_line_table')}"))
        self.assertEqual(self._texts(tree, "//div[@name='invoice_date']/strong"), ['تاريخ الفاتورة', 'Invoice Date'])
        self.assertEqual(self._texts(tree, "//th[@name='th_description']/span"), ['الوصف', 'Description'])
        self.assertEqual(self._texts(tree, f"//tr{has_class('o_total')}/td[1]/strong")[-1], '/ الإجمالي')
        # The label is the English product name, the Arabic one is added.
        self.assertEqual(self._texts(tree, "//td[@name='account_invoice_line_name']/span"), ['منتج أ', 'product_a'])
        self.assertEqual(tree.xpath("//td[@name='account_invoice_line_name']/span[1]/@dir"), ['rtl'])

    def test_render_arabic_partner(self):
        """ Arabic primary layout, right to left as for any RTL language, with English as the secondary language. """
        invoice = self.init_invoice('out_invoice', partner=self.partner_ar, products=self.product_a, post=True)
        tree = self._render_invoice(invoice)

        # The PDF pages are rendered in Arabic, hence right to left like any RTL language.
        self.assertEqual(tree.xpath(f"//div{has_class('article')}/@data-oe-lang"), ['ar_001'])
        self.assertEqual(self._texts(tree, "//div[@name='invoice_date']/strong")[0], 'Invoice Date')
        self.assertEqual(self._texts(tree, "//th[@name='th_description']/span")[0], 'Description')
        self.assertEqual(self._texts(tree, f"//tr{has_class('o_total')}/td[1]/strong")[-1], '/ Total')
        # The label is the Arabic product name, the English one is added.
        self.assertEqual(self._texts(tree, "//td[@name='account_invoice_line_name']/span"), ['product_a', 'منتج أ'])
        # Otherwise the English name inherits the RTL direction of the report, which misplaces its brackets in the PDF.
        self.assertEqual(tree.xpath("//td[@name='account_invoice_line_name']/span[1]/@dir"), ['ltr'])

    def test_render_standard_invoice_when_disabled(self):
        self.company.l10n_eg_dual_language_invoice = False
        invoice = self.init_invoice('out_invoice', products=self.product_a, post=True)
        tree = self._render_invoice(invoice)

        self.assertFalse(tree.xpath(f"//table{has_class('o_l10n_eg_invoice_line_table')}"))
        self.assertEqual(self._texts(tree, "//div[@name='invoice_date']/strong"), ['Invoice Date'])
        self.assertEqual(self._texts(tree, "//th[@name='th_description']/span"), ['Description'])
        self.assertEqual(self._texts(tree, f"//tr{has_class('o_total')}/td[1]/strong"), ['Total'])

    def test_render_all_move_types(self):
        """ The dual language report renders for every type of move, including the reversals. """
        invoice = self.init_invoice('out_invoice', products=self.product_a, post=True)
        moves = (
            invoice
            + invoice._reverse_moves([{'invoice_date': invoice.invoice_date}])
            + self.init_invoice('in_invoice', products=self.product_a, post=True)
            + self.init_invoice('in_refund', products=self.product_a, post=True)
        )
        expected_dates = {
            'out_invoice': 'تاريخ الفاتورة',
            'out_refund': 'تاريخ إشعار الدائن',
            'in_invoice': 'تاريخ',
            'in_refund': 'تاريخ',
        }
        for move in moves:
            with self.subTest(move_type=move.move_type):
                tree = self._render_invoice(move)
                self.assertEqual(self._texts(tree, "//div[@name='invoice_date']/strong")[0], expected_dates[move.move_type])
