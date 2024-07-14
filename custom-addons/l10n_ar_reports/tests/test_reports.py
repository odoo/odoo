# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.addons.l10n_ar.tests.common import TestAr
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo.tools import file_open
import logging

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestReports(TestAr, TestAccountReportsCommon):

    def _create_test_credit_notes_like_demo(self):
        """ Create in the unit tests the same credit notes created in demo data """
        credit_notes = {
            "demo_refund_invoice_3": {
                # "ref": "demo_refund_invoice_3: Create draft refund for invoice 3",
                "reason": "Mercadería defectuosa",
                "is_refund": True,
                "move_ids": self.demo_invoices['test_invoice_3'],
                "date": '2021-03-01',
            },
            "demo_refund_invoice_4": {
                # "ref": "demo_refund_invoice_4: Create draft refund for invoice 4",
                "reason": "Venta cancelada",
                "is_refund": False,
                "move_ids": self.demo_invoices['test_invoice_4'],
                "date": '2021-03-01',
            },
            "demo_refund_invoice_16": {
                # "ref": "demo_refund_invoice_16: Create cancel refund for expo invoice 16 (las nc/nd expo invoice no requiere parametro permiso existennte, por eso agregamos este ejemplo)",
                "reason": "Venta cancelada",
                "is_refund": False,
                "move_ids": self.demo_invoices['test_invoice_16'],
                "date": '2021-03-01',
            },
            "demo_refund_bill_1": {
                "reason": "demo_sup_refund_invoice_5: liquido producto bill refund (credit note)",
                "is_refund": False,
                "move_ids": self.demo_bills['test_vendor_bill_8'],
                "date": '2021-03-27',
                "l10n_latam_document_number": "00011-00000012",
                "l10n_latam_document_type_id": self.document_type['liq_pro_doc'].id,
            }
        }

        refund_wizard = self.env['account.move.reversal']
        for key, values in credit_notes.items():
            origin_move = values.get("move_ids")
            is_refund = values.pop("is_refund")
            values.update({
                'date': fields.Date.from_string(values.get('date')),
                'journal_id': origin_move.journal_id.id,
            })
            move_reversal = refund_wizard.with_context(
                active_model="account.move",
                active_ids=origin_move.ids).create(values)
            reversal = move_reversal.refund_moves() if is_refund else move_reversal.modify_moves()
            reverse_move = self.env['account.move'].browse(reversal['res_id'])
            self.demo_credit_notes[key] = reverse_move

    def _create_test_vendor_bill_invoice_demo(self):
        """ Create in the unit tests the same vendor bills created in demo data """
        payment_term_id = self.env.ref("account.account_payment_term_end_following_month")
        purchase_journal = self.env["account.journal"].search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)])
        vendor_bills = {
            "test_vendor_bill_1": {
                "ref": "demo_sup_invoice_1: Invoice from Gritti support service, auto fiscal position set VAT Not Applicable",
                "l10n_latam_document_number": "0001-00000008",
                "partner_id": self.res_partner_gritti_mono,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-01',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 642.0, 'quantity': 1},
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                ],
            }, "test_vendor_bill_2": {
                "ref": "demo_sup_invoice_2: Invoice from Foreign with vat 21, 27 and 10,5",
                "l10n_latam_document_number": "0002-00000123",
                "partner_id": self.res_partner_expresso,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-01',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                ],
            }, "test_vendor_bill_3": {
                "ref": "demo_sup_invoice_3: Invoice from Foreign with vat zero and 21",
                "l10n_latam_document_number": "0003-00000312",
                "partner_id": self.res_partner_expresso,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-01',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                ],
            }, "test_vendor_bill_4": {
                "ref": "demo_sup_invoice_4: Invoice to Foreign with vat exempt and 21",
                "l10n_latam_document_number": "0001-00000200",
                "partner_id": self.res_partner_expresso,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-15',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                ],
            }, "test_vendor_bill_5": {
                "ref": "demo_sup_invoice_5: Invoice to Foreign with all type of taxes",
                "l10n_latam_document_number": "0001-00000222",
                "partner_id": self.res_partner_expresso,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-18',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                    {'product_id': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                ],
            }, "test_vendor_bill_6": {
                "ref": "demo_sup_invoice_6: Service Import to Odoo, fiscal position changes tax not correspond",
                "l10n_latam_document_number": "0001-00000333",
                "partner_id": self.res_partner_expresso,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-26',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 1642.0, 'quantity': 1},
                ],
            }, "test_vendor_bill_7": {
                "ref": "demo_sup_invoice_7: Similar to last one but with line that have tax not correspond with negative amount",
                "l10n_latam_document_number": "0001-00000334",
                "partner_id": self.res_partner_expresso,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-27',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 1642.0, 'quantity': 1},
                    {'product_id': self.product_no_gravado, 'price_unit': -50.0, 'quantity': 10},
                ],
            }, "test_vendor_bill_8": {
                "ref": "demo_sup_invoice_8: Invoice to ADHOC with multiple taxes and perceptions",
                "l10n_latam_document_number": "0001-00000335",
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-01',
                "company_id": self.env.company,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                ],
            }, "demo_despacho_1": {
                "ref": "demo_despacho_1: Import Cleareance ",
                "l10n_latam_document_number": "16052IC04000605L",
                "partner_id": self.partner_afip,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-13',
                "company_id": self.env.company,
                # as we create lines separatelly we need to set journal, if not, misc journal is selected
                "journal_id": purchase_journal,
                "invoice_line_ids": [
                    {'product_id': self.service_wo_tax, "name": "[AFIP_DESPACHO] Despacho de importación", 'price_unit': 5064.98, 'quantity': 1,
                     "tax_ids": [(6, 0, self.tax_21_purchase.ids)]},
                    {'product_id': self.service_wo_tax, "name": "[AFIP_TASA_EST] Tasa Estadística", 'price_unit': 152.08, 'quantity': 1,
                     "tax_ids": [(6, 0, self.tax_21_purchase.ids)]},
                    {'product_id': self.service_iva_no_gravado, "name": "[AFIP_ARANCEL] Arancel", 'price_unit': 10.0, 'quantity': 1,
                     "tax_ids": [(6, 0, self.tax_no_gravado_purchase.ids)]},

                ],
            },
            "test_vendor_bill_9": {
                "ref": " demo_liquido_producto_1: Vendor bill liquido producto (document type 186)",
                "l10n_latam_document_type_id": self.document_type['liq_pro_doc'],
                "l10n_latam_document_number": "00077-00000077",
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "in_invoice",
                "invoice_date": '2021-03-25',
                "company_id": self.env.company,
                # as we create lines separatelly we need to set journal, if not, misc journal is selected
                "journal_id": purchase_journal,
                "invoice_line_ids": [
                    {'product_id': self.service_wo_tax, "name": "[AFIP_DESPACHO] Despacho de importación", 'price_unit': 5064.98, 'quantity': 1,
                     "tax_ids": [(6, 0, self.tax_21_purchase.ids)]},
                    {'product_id': self.service_wo_tax, "name": "[AFIP_TASA_EST] Tasa Estadística", 'price_unit': 152.08, 'quantity': 1,
                     "tax_ids": [(6, 0, self.tax_21_purchase.ids)]},
                    {'product_id': self.service_iva_no_gravado, "name": "[AFIP_ARANCEL] Arancel", 'price_unit': 10.0, 'quantity': 1,
                     "tax_ids": [(6, 0, self.tax_no_gravado_purchase.ids)]},

                ],
            }
        }

        for key, values in vendor_bills.items():
            with Form(self.env['account.move'].with_context(default_move_type=values['move_type'])) as invoice_form:
                invoice_form.ref = values['ref']
                invoice_form.partner_id = values['partner_id']
                invoice_form.invoice_payment_term_id = values['invoice_payment_term_id']
                invoice_form.invoice_date = values['invoice_date']
                if values.get('l10n_latam_document_type_id'):
                    invoice_form.l10n_latam_document_type_id = values['l10n_latam_document_type_id']
                invoice_form.l10n_latam_document_number = values['l10n_latam_document_number']
                if values.get('invoice_incoterm_id'):
                    invoice_form.invoice_incoterm_id = values['invoice_incoterm_id']
                for line in values['invoice_line_ids']:
                    with invoice_form.invoice_line_ids.new() as line_form:
                        line_form.product_id = line.get('product_id')
                        line_form.price_unit = line.get('price_unit')
                        line_form.quantity = line.get('quantity')
                        # TODO: check this lines, should not be necessary to add
                        line_form.name = 'xxxx'
                        line_form.account_id = self.company_data['default_account_revenue']
            invoice = invoice_form.save()
            self.demo_bills[key] = invoice

    def _vat_book_report_create_test_data(self):
        purchase_journal = self.env["account.journal"].search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)])
        ar_partner = self.env['res.partner'].create({
            'name': 'BEST PARTNER',
            'vat': '30714295698',
            'l10n_latam_identification_type_id': self.env.ref('l10n_ar.it_cuit').id
        })
        test_tax_group = self.env['account.tax.group'].create({
            'name': "test tax group",
            'l10n_ar_vat_afip_code': '5',
        })
        test_tax_21 = self.env['account.tax'].create({
            'name': "test tax",
            'amount_type': 'percent',
            'amount': 21,
            'tax_group_id': test_tax_group.id,
        })
        test_product = self.env['product.product'].create({
            'name': "Test Product",
            'categ_id': self.env.ref("product.product_category_all").id,
            'lst_price': 100.0,
            'standard_price': 10.0,
            'property_account_income_id': self.company_data["default_account_revenue"].id,
            'property_account_expense_id': self.company_data["default_account_expense"].id,
        })
        invoices = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': ar_partner.id,
                'invoice_date': '2022-03-01',
                "journal_id": purchase_journal.id,
                "l10n_latam_document_number": "0001-00000001000",
                'invoice_line_ids': [(0, 0, {
                    'product_id': test_product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, [test_tax_21.id])],
                })],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': ar_partner.id,
                'invoice_date': '2022-03-10',
                "journal_id": purchase_journal.id,
                "l10n_latam_document_number": "0001-00000002000",
                'invoice_line_ids': [(0, 0, {
                    'product_id': test_product.id,
                    'price_unit': 500.0,
                    'tax_ids': [(6, 0, [test_tax_21.id])],
                })],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': ar_partner.id,
                'invoice_date': '2022-03-31',
                "journal_id": purchase_journal.id,
                "l10n_latam_document_number": "0001-00000003000",
                'invoice_line_ids': [(0, 0, {
                    'product_id': test_product.id,
                    'price_unit': 800.0,
                    'tax_ids': [(6, 0, [test_tax_21.id])],
                })],
            },
        ])
        invoices.action_post()

    @classmethod
    def setUpClass(cls, chart_template_ref='ar_ri'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.journal = cls._create_journal(cls, 'preprinted', data={'l10n_ar_afip_pos_number': 37928})
        cls.maxDiff = None
        cls.report = cls.env.ref('l10n_ar_reports.l10n_ar_vat_book_report')

        # Login to (AR) Responsable Inscripto company
        context = dict(cls.env.context, allowed_company_ids=[cls.company_ri.id])
        cls.env = cls.env(context=context)
        cls.env.user.write({'company_ids': [(4, cls.company_ri.id)]})

        # ==== Document Types ====
        cls.document_type.update({
            'liq_pro_doc': cls.env.ref('l10n_ar.dc_liq_cd_sp_a'),
        })

        # ==== Create VAT BOOK demo data ====
        cls._create_test_invoices_like_demo(cls, use_current_date=False)
        for _key, inv in cls.demo_invoices.items():
            inv.action_post()

        cls._create_test_vendor_bill_invoice_demo(cls)
        for _key, inv in cls.demo_bills.items():
            inv.action_post()

        # demo_credit_notes are automatically posted thanks to the refund type
        cls._create_test_credit_notes_like_demo(cls)

        cls.options = cls._generate_options(cls.report, fields.Date.from_string('2021-03-01'), fields.Date.from_string('2021-03-31'))
        cls._vat_book_report_create_test_data(cls)

    def _test_txt_file(self, filename, journal_type):
        filetype = 1 if 'IVA' in filename else 0
        out_txt = self.env['l10n_ar.tax.report.handler']._vat_book_get_txt_files(self.options, journal_type)[filetype].decode('ISO-8859-1')
        res_file = file_open('l10n_ar_reports/tests/' + filename, 'rb').read().decode('ISO-8859-1')
        self.assertEqual(out_txt, res_file)

    def test_01_sale_vat_book_vouchers(self):
        self.options['ar_vat_book_tax_type_selected'] = 'sale'
        self.options['txt_type'] = 'sale'
        self._test_txt_file('Ventas.txt', 'sale')

    def test_02_sale_vat_book_aliquots(self):
        self.options['ar_vat_book_tax_type_selected'] = 'sale'
        self.options['txt_type'] = 'sale'
        self._test_txt_file('IVA_Ventas.txt', 'sale')

    def test_03_purchase_vat_book_purchases_voucher(self):
        self.options['ar_vat_book_tax_type_selected'] = 'purchase'
        self.options['txt_type'] = 'purchases'
        self._test_txt_file('Compras.txt', 'purchase')

    def test_04_purchase_vat_book_purchases_aliquots(self):
        self.options['ar_vat_book_tax_type_selected'] = 'purchase'
        self.options['txt_type'] = 'purchases'
        self._test_txt_file('IVA_Compras.txt', 'purchase')

    def test_05_purchase_vat_book_goods_import_voucher(self):
        self.options['ar_vat_book_tax_type_selected'] = 'purchase'
        self.options['txt_type'] = 'goods_import'
        self._test_txt_file('Importaciones_de_Bienes.txt', 'purchase')

    def test_06_purchase_vat_book_goods_import_aliquots(self):
        self.options['ar_vat_book_tax_type_selected'] = 'purchase'
        self.options['txt_type'] = 'goods_import'
        self._test_txt_file('IVA_Importaciones_de_Bienes.txt', 'purchase')

    def test_vat_book_report(self):
        options = self._generate_options(self.report, date_from=fields.Date.from_string('2022-03-01'), date_to=fields.Date.from_string('2022-03-31'))
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #    Move Name              Partner Name    VAT            Taxed   VAT 21%   Total
            [    0,                     2,              4,             5,      8,        15],
            [
                ('DI 0001-00000001000', 'BEST PARTNER', '30714295698', -1000,  -210,     -1210),
                ('DI 0001-00000002000', 'BEST PARTNER', '30714295698', -500,   -105,     -605),
                ('DI 0001-00000003000', 'BEST PARTNER', '30714295698', -800,   -168,     -968),
            ],
            options,
        )
