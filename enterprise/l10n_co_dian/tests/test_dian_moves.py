from datetime import datetime
from lxml import etree

from odoo import Command
from odoo.tests import tagged, freeze_time
from .common import TestCoDianCommon
from odoo.addons.l10n_co_edi.models.account_invoice import L10N_CO_EDI_TYPE


@freeze_time('2024-01-30')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDianMoves(TestCoDianCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Alcohol Taxes
        cls.alcohol_tax_1 = cls.env['account.tax'].create({
            'name': "ICL >20%",
            'amount_type': 'fixed',
            'amount': 30,
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_18').id,  # ICL
        })
        cls.alcohol_tax_2 = cls.alcohol_tax_1.copy({
            'name': "ICL <=20%",
            'amount': 15,
        })

        # Alcohol Products
        cls.product_alcohol_1 = cls._create_product(
            name="Wine 50% ABV",
            l10n_co_edi_ref_nominal_tax=50,
            default_code='VINO1',
        )
        cls.product_alcohol_2 = cls._create_product(
            name="Beer 3% ABV",
            l10n_co_edi_ref_nominal_tax=3,
            default_code='BEER1',
        )

        # Plastic Bag Taxes (INC Bolsas)
        cls.plastic_bag_tax = cls.env['account.tax'].create({
            'name': "INC Plastic Bags",
            'amount_type': 'fixed',
            'amount': 70,  # Fixed rate per bag
            'type_tax_use': 'sale',
            'invoice_label': 'INC Plastic Bags',
            'description': 'INC Plastic Bags',
            'tax_group_id': cls.env['account.chart.template'].ref('l10n_co_tax_group_inc_bolsas').id,  # INC Bolsas
            'l10n_co_edi_type': cls.env.ref('l10n_co_edi.tax_type_9').id,  # INC Bolsas
        })

        # Plastic Bag Product
        cls.product_plastic_bag = cls._create_product(
            name="Bolsa Plastica",
            default_code='BOLSA1',
        )

        # 1 USD ~= 3919 COP
        usd = cls.env.ref('base.USD')
        cls.env['res.currency.rate'].create({
            'name': '2024-01-30',
            'inverse_company_rate': 3919.109578,
            'currency_id': usd.id,
            'company_id': cls.env.company.id,
        })

    def test_invoice_sugar(self):
        invoice = self._create_move(invoice_line_ids=[
            # Sugar taxes should not be grouped together in xml since they have different rates
            Command.create({
                'product_id': self.product_sugar_1.id,
                'quantity': 3,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_5.id, self.sugar_tax_1.id])],
            }),
            Command.create({
                'product_id': self.product_sugar_2.id,
                'quantity': 2,
                'price_unit': 200,
                'tax_ids': [Command.set([self.tax_iva_5.id, self.sugar_tax_2.id])],
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 10,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_5.id])],
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 5,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_19.id])],
            }),
        ])
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_sugar.xml")

    def test_invoice_sugar_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_invoice_sugar()

    def test_invoice_alcohol(self):
        invoice = self._create_move(invoice_line_ids=[
            Command.create({
                'product_id': self.product_alcohol_1.id,
                'quantity': 3,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_5.id, self.alcohol_tax_1.id])],
            }),
            Command.create({
                'product_id': self.product_alcohol_2.id,
                'quantity': 2,
                'price_unit': 200,
                'tax_ids': [Command.set([self.tax_iva_5.id, self.alcohol_tax_2.id])],
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 10,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_5.id])],
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 5,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_19.id])],
            }),
        ])
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_alcohol.xml")

    def test_invoice_alcohol_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_invoice_alcohol()

    def test_invoice_plastic_bags(self):
        invoice = self._create_move(invoice_line_ids=[
            Command.create({
                'product_id': self.product_plastic_bag.id,
                'quantity': 2,
                'price_unit': 100,
                'tax_ids': [Command.set([self.tax_iva_19.id, self.plastic_bag_tax.id])],
            }),
            Command.create({
                'product_id': self.product_a.id,
                'quantity': 5,
                'price_unit': 100,
                'tax_ids': [Command.set([self.plastic_bag_tax.id])],
            }),
        ])
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_plastic_bags.xml")

    def test_invoice_plastic_bags_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_invoice_plastic_bags()

    def test_multicurrency(self):
        """
        In the xml, all labels should be expressed in COP, not in the document's currency.
        Suppose we have the rate: 1 USD = 3919.109578 Pesos
        Using round per line, DIAN tests will fail and we are forced to used round globally

        ## Rule
            DIAN checks that the base amount * the percentage is roughly (a tolerance of +5 or -5 pesos is allowed)
            equal to the tax amount
            In the example, 226.98 USD = 889559.49 COP -> tax amount should roughly be 169016,30

        ## Round per Line:
            Base amount = 889559.49
            Tax amount = 169031.20 (rejected because not in [169011,30; 169021,30])
            Total = 1058590.69

        ## Round globally:
            Base amount = 889559.49
            Tax amount = 169016.30 (accepted)
            Total = 1058575.79
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        invoice = self._create_move(
            currency_id=self.env.ref('base.USD').id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 226.98,
                    'tax_ids': [Command.set([self.tax_iva_19.id])],
                })
            ]
        )
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_multicurrency.xml")

    def test_multicurrency_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_multicurrency()

    def test_credit_note_20(self):
        """ Credit note referencing an invoice """
        invoice = self._create_move()
        xml = self._generate_xml(invoice)
        self.env['l10n_co_dian.document']._create_document(xml, invoice, state='invoice_accepted')

        credit_note = self._create_move(
            move_type='out_refund',
            reversed_entry_id=invoice.id,
            ref="broken product",
            l10n_co_edi_type=L10N_CO_EDI_TYPE['Credit Note'],
            l10n_co_edi_operation_type='20',  # "Nota Crédito que referencia una factura electrónica"
            l10n_co_edi_description_code_credit='1',  # "Devolución parcial de los bienes"
        )
        xml = self._generate_xml(credit_note)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/credit_note_20.xml")
        self.assertFalse('xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures"' in xml.decode())
        self.assertTrue('xmlns:sts="dian:gov:co:facturaelectronica:Structures-2-1"' in xml.decode())

    def test_credit_note_20_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_credit_note_20()

    def test_credit_note_22(self):
        """ Credit note not referencing an invoice """
        credit_note = self._create_move(
            move_type='out_refund',
            ref="broken product",
            l10n_co_edi_type=L10N_CO_EDI_TYPE['Credit Note'],
            l10n_co_edi_operation_type='22',  # "Nota Crédito sin referencia a facturas"
            l10n_co_edi_description_code_credit='6',  # "Descuento comercial por volumen de ventas"
        )
        xml = self._generate_xml(credit_note)
        self.env['l10n_co_dian.document']._create_document(xml, credit_note, state='invoice_accepted')
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/credit_note_22.xml")
        self.assertFalse('xmlns:sts="http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures"' in xml.decode())
        self.assertTrue('xmlns:sts="dian:gov:co:facturaelectronica:Structures-2-1"' in xml.decode())

    def test_credit_note_22_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_credit_note_22()

    def test_invoice_exportation(self):
        """ Invoice to a non-Colombian customer. Also checks the rounding of the tax amounts. """
        self.partner_a.write({
            'country_id': self.env.ref('base.us').id,
            'vat': 'US12345673',
            'l10n_co_edi_obligation_type_ids': [Command.set(self.env.ref('l10n_co_edi.obligation_type_5').ids)],  # R-99-PN
            'l10n_latam_identification_type_id': self.env.ref('l10n_co.external_id').id,  # "Nit de otro país"
        })
        self.product_a.write({
            'l10n_co_edi_customs_code': '0123456789',
            'l10n_co_edi_brand': 'BRAND',
        })
        invoice = self._create_move(
            partner_id=self.partner_a.id,
            l10n_co_edi_type=L10N_CO_EDI_TYPE['Export Invoice'],
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 750,
                    'tax_ids': [Command.set([self.tax_iva_19.id, self.tax_ret_ica_0414.id])],
                }),
            ]
        )
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_exportation.xml")

    def test_invoice_exportation_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_invoice_exportation()

    def test_invoice_with_stmt_lines_and_exchange_diff(self):
        """ Partially paid invoice in USD with 2 statement lines, one in COP and the second in USD """
        # Invoice: 1050 USD (=3919109.58 COP)
        usd = self.env.ref('base.USD')
        invoice = self._create_move(currency_id=usd.id)
        self.assertEqual(invoice.amount_residual, 1050.00)

        # Create a 1st bank statement line (in COP) and reconcile with the invoice
        bank_stmt_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'Payment ref 1',
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': 1000000,
            'date': '2024-01-30',
        })
        suspense = bank_stmt_line.line_ids.filtered(lambda l: l.account_type == 'asset_current')
        line = invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
        suspense.account_id = line.account_id
        (suspense + line).reconcile()
        self.assertEqual(invoice.amount_residual, 794.84)

        # Create a 2nd bank statement line (in USD) with an exchange difference and reconcile with the invoice
        bank_stmt_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'Payment ref 2 (!= rate)',
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': '2024-01-30',
            'amount': 390000,
            'amount_currency': 100,  # bank rate: 1 USD = 3900 COP, odoo rate: 1 USD = ~3919.10 COP
            'foreign_currency_id': usd.id,
        })
        suspense = bank_stmt_line.line_ids.filtered(lambda l: l.account_type == 'asset_current')
        line = invoice.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
        suspense.account_id = line.account_id
        (suspense + line).reconcile()
        self.assertEqual(invoice.amount_residual, 694.84)

        # The xml should include 2 'PrepaidPayment'
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_prepaid_payment_1.xml")

    def test_invoice_with_stmt_lines_and_exchange_diff_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_invoice_with_stmt_lines_and_exchange_diff()

    def test_invoice_with_payment(self):
        """ Partially paid invoice (payment registered then reconciled with a statement line) """
        invoice = self._create_move()
        self.assertEqual(invoice.amount_residual, 4115065.06)

        # Payment
        payment = self.env['account.payment'].create({
            'date': invoice.date,
            'amount': 500,
            'partner_id': self.partner_a.id,
        })
        payment.action_post()
        lines = (invoice + payment.move_id).line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        lines.reconcile()
        self.assertEqual(invoice.amount_residual, 4114565.06)

        # The xml should already include 1 'PrepaidPayment'
        xml = self._generate_xml(invoice)
        root = etree.fromstring(xml)
        self.assertEqual(len(root.findall('.//{*}PrepaidPayment')), 1)
        self.assertEqual(root.findtext('.//{*}PrepaidPayment/{*}PaidAmount'), "500.00")
        self.assertEqual(root.findtext('.//{*}PrepaidPayment/{*}ID'), "Manual Payment")

        # Bank Statement line
        bank_stmt_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'Payment ref',
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': 500,
            'date': '2024-01-30',
        })
        outstanding = payment.move_id.line_ids.filtered(lambda x: x.account_type == 'asset_current')
        suspense = bank_stmt_line.line_ids.filtered(lambda x: x.account_type == 'asset_current')
        suspense.account_id = outstanding.account_id
        (outstanding + suspense).reconcile()
        self.assertEqual(invoice.amount_residual, 4114565.06)

        # The xml should still include 1 'PrepaidPayment'
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_prepaid_payment_2.xml")

    def test_invoice_with_payment_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_invoice_with_payment()

    def test_invoice_withholding(self):
        """ Invoice containing retention taxes (should fill the 'WithholdingTaxTotal' nodes) """
        invoice = self._create_move(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set([
                        self.tax_iva_19.id,
                        self.env["account.chart.template"].ref('l10n_co_tax_56').id,
                        self.tax_ret_ica_0414.id,
                    ])],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set([
                        self.tax_iva_5.id,
                        self.env["account.chart.template"].ref('l10n_co_tax_55').id,
                    ])],
                }),
            ],
        )
        xml = self._generate_xml(invoice)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_withholding.xml")

    def test_invoice_withholding_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        invoice = self._create_move(
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set([
                        self.tax_iva_19.id,
                        self.env["account.chart.template"].ref('l10n_co_tax_56').id,
                        self.tax_ret_ica_0414.id,
                    ])],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set([
                        self.tax_iva_5.id,
                        self.env["account.chart.template"].ref('l10n_co_tax_55').id,
                    ])],
                }),
            ],
        )
        xml = self.env['account.edi.xml.ubl_dian']._export_invoice(invoice)[0]
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/invoice_withholding_new.xml")

    def test_debit_note_30(self):
        """ Debit note referencing an invoice """
        invoice = self._create_move()
        xml = self._generate_xml(invoice)
        self.env['l10n_co_dian.document']._create_document(xml, invoice, state='invoice_accepted')

        wizard = self.env['account.debit.note']\
            .with_context(active_model="account.move", active_ids=invoice.ids)\
            .create({
                'l10n_co_edi_description_code_debit': '1',
                'copy_lines': True,
                'reason': 'The value of the product just went up',
                'journal_id': self.debit_note_journal.id,
            })
        wizard.create_debit()
        debit_note = invoice.debit_note_ids
        debit_note.l10n_co_edi_description_code_debit = '3'  # "Cambio del valor"
        debit_note.action_post()
        self.assertEqual(debit_note.l10n_co_edi_operation_type, '30')  # "Nota Débito que referencia una factura electrónica"
        xml = self._generate_xml(debit_note)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/debit_note_30.xml")

    def test_debit_note_30_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_debit_note_30()

    def test_debit_note_32(self):
        """ Debit note not referencing an invoice """
        debit_note = self._create_move(
            journal_id=self.debit_note_journal.id,
            l10n_co_edi_description_code_debit='4',  # Otros
        )
        self.assertFalse(debit_note.debit_origin_id, False)
        self.assertEqual(debit_note.l10n_co_edi_operation_type, '32')
        xml = self._generate_xml(debit_note)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/debit_note_32.xml")

    def test_debit_note_32_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_debit_note_32()

    def test_support_document(self):
        """
        - RetICA taxes should not be reported in Support Documents
        - RetIVA taxes for Support Documents should be reported ONLY with percentage 15.00 or 100.00
          In addition, the taxable amount of these taxes should be the tax amount of the taxes with type '01'
        """
        bill = self._create_move(
            move_type="in_invoice",
            invoice_date=datetime.today(),
            journal_id=self.support_document_journal.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(self.tax_iva_19.ids + self.tax_ret_ica_1_104.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(self.tax_iva_19.ids + self.tax_ret_iva_2_85.ids)],
                }),
            ],
        )
        bill.partner_id.country_id = self.env.ref('base.us')
        xml = self._generate_xml(bill)
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/support_document.xml")

    def test_support_document_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_support_document()

    def test_support_document_credit_note(self):
        """ Support Document credit note referencing another support document """
        bill = self._create_move(
            move_type='in_invoice',
            invoice_date=datetime.today(),
            journal_id=self.support_document_journal.id,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(self.tax_iva_19.ids + self.tax_ret_ica_1_104.ids)],
                }),
            ],
        )
        xml = self._generate_xml(bill)
        self.env['l10n_co_dian.document']._create_document(xml, bill, state='invoice_accepted')

        credit_note = self._create_move(
            move_type='in_refund',
            invoice_date=datetime.today(),
            journal_id=self.support_document_journal.id,
            reversed_entry_id=bill.id,
            l10n_co_edi_operation_type='10',  # "Estandar"
            l10n_co_edi_description_code_credit='1',  # "Devolución parcial de los bienes"
        )
        xml = self._generate_xml(credit_note)
        self._assert_document_dian(xml, 'l10n_co_dian/tests/attachments/support_document_credit_note.xml')

    def test_support_document_credit_note_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_support_document_credit_note()

    def test_dian_import_vendor_xml(self):
        kwargs = {
            'subfolder': 'tests/attachments',
            'invoice_vals': {
                'currency_id': self.currency.id,
                'amount_total': 224.00,
                'amount_tax': 24.00,
                'l10n_co_edi_cufe_cude_ref': '8007424c5ee187a2aa3bb99fdbfaee9354c0b2a355ce9654fcd97eae289ad827e19460b71e4390b3e9b1cc6c293fb247',
                'invoice_lines': [
                    {'price_subtotal': 100.00, 'price_unit': 100.00},
                    {'price_subtotal': 100.00, 'price_unit': 100.00},
                ],
            },
        }
        self._assert_imported_invoice_from_file(filename='import_attached_document.xml', **kwargs)

    def test_dian_invoicing_access_rights(self):
        self.user.groups_id = [Command.unlink(self.env.ref('base.group_system').id)]
        invoice = self._create_move()
        xml = self._generate_xml(invoice)
        self.env.invalidate_all()  # certificates are available in cache, we still need to test the access through `_build_and_send_request`
        self.env['l10n_co_dian.document']._create_document(xml, invoice, state='invoice_accepted')
        self._mock_get_status_zip(invoice, 'GetStatusZip_pending.xml')
        self.assertEqual(invoice.l10n_co_dian_state, 'invoice_pending')

    def test_credit_note_foreign_currency(self):
        self.env['res.currency.rate'].create({
            'name': '2025-01-01',
            'rate': 1.5,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.company.id
        })
        credit_note = self._create_move(
            move_type='out_refund',
            ref="broken product",
            l10n_co_edi_type=L10N_CO_EDI_TYPE['Credit Note'],
            l10n_co_edi_operation_type='22',
            l10n_co_edi_description_code_credit='6',
            currency_id=self.env.ref('base.USD').id,
        )
        xml = self._generate_xml(credit_note)
        self.env['l10n_co_dian.document']._create_document(xml, credit_note, state='invoice_accepted')
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/credit_note_foreign_currency.xml")

    def test_credit_note_foreign_currency_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_credit_note_foreign_currency()

    def test_support_documents_report_name(self):
        """ Test that we get the right report for support documents """
        bill = self._create_move(
            move_type='in_invoice',
            invoice_date=datetime.today(),
            journal_id=self.support_document_journal.id,
        )
        self.assertEqual(bill._get_name_invoice_report(), 'l10n_co_dian.report_vendor_document')
        xml = self._generate_xml(bill)
        self.env['l10n_co_dian.document']._create_document(xml, bill, state='invoice_accepted')
        self.assertEqual(bill._get_name_invoice_report(), 'l10n_co_dian.report_vendor_document')

        credit_note = self._create_move(
            move_type='in_refund',
            invoice_date=datetime.today(),
            journal_id=self.support_document_journal.id,
            reversed_entry_id=bill.id,
            l10n_co_edi_operation_type='10',  # "Estandar"
            l10n_co_edi_description_code_credit='1',  # "Devolución parcial de los bienes"
        )
        self.assertEqual(credit_note._get_name_invoice_report(), 'l10n_co_dian.report_vendor_document')
        xml = self._generate_xml(credit_note)
        self.env['l10n_co_dian.document']._create_document(xml, credit_note, state='invoice_accepted')
        self.assertEqual(credit_note._get_name_invoice_report(), 'l10n_co_dian.report_vendor_document')

        invoice = self._create_move(
            move_type='out_invoice',
            invoice_date=datetime.today(),
            journal_id=self.company_data['default_journal_sale'].id,
        )
        self.assertEqual(invoice._get_name_invoice_report(), 'account.report_invoice_document')
        xml = self._generate_xml(invoice)
        self.env['l10n_co_dian.document']._create_document(xml, invoice, state='invoice_accepted')
        self.assertEqual(invoice._get_name_invoice_report(), 'l10n_co_dian.report_invoice_document')

        credit_note = self._create_move(
            move_type='out_refund',
            invoice_date=datetime.today(),
            journal_id=self.company_data['default_journal_sale'].id,
            reversed_entry_id=invoice.id,
            l10n_co_edi_operation_type='10',  # "Estandar"
            l10n_co_edi_description_code_credit='1',  # "Devolución parcial de los bienes"
        )
        self.assertEqual(credit_note._get_name_invoice_report(), 'account.report_invoice_document')
        xml = self._generate_xml(credit_note)
        self.env['l10n_co_dian.document']._create_document(xml, credit_note, state='invoice_accepted')
        self.assertEqual(credit_note._get_name_invoice_report(), 'l10n_co_dian.report_invoice_document')
