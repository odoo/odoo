# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests import Form
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
import random
import logging
import time

_logger = logging.getLogger(__name__)


class TestAr(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('ar_ri')
    def setUpClass(cls):
        super().setUpClass()

        # ==== Company ====
        cls.company_data['company'].write({
            'name': '(AR) Responsable Inscripto (Unit Tests)',
            "l10n_ar_afip_start_date": time.strftime('%Y-01-01'),
            'l10n_ar_gross_income_type': 'local',
            'l10n_ar_gross_income_number': '901-21885123',
        })
        cls.company_ri = cls.company_data['company']

        cls.company_ri.partner_id.write({
            'name': '(AR) Responsable Inscripto (Unit Tests)',
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVARI").id,
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': '30111111118',
            "street": 'Calle Falsa 123',
            "city": 'Rosario',
            "country_id": cls.env.ref("base.ar").id,
            "state_id": cls.env.ref("base.state_ar_s").id,
            "zip": '2000',
            "phone": '+1 555 123 8069',
            "email": 'info@example.com',
            "website": 'www.example.com',
        })
        cls.partner_ri = cls.company_ri.partner_id

        # ==== Company MONO ====
        cls.company_mono = cls._create_company(
            name='(AR) Monotributista (Unit Tests)',
            currency_id=cls.env.ref('base.ARS').id,
            l10n_ar_afip_start_date=time.strftime('%Y-01-01'),
            l10n_ar_gross_income_type='exempt',
        )
        cls.company_mono.partner_id.write({
            'name': '(AR) Monotributista (Unit Tests)',
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_RM").id,
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': '20222222223',
            "street": 'Calle Falsa 123',
            "city": 'Rosario',
            "country_id": cls.env.ref("base.ar").id,
            "state_id": cls.env.ref("base.state_ar_s").id,
            "zip": '2000',
            "phone": '+1 555 123 8069',
            "email": 'info@example.com',
            "website": 'www.example.com',
        })
        cls.partner_mono = cls.company_mono.partner_id

        # ==== Bank Account ====
        cls.bank_account_ri = cls.env['res.partner.bank'].create({
            'acc_number': '7982898111100056688080',
            'partner_id': cls.company_ri.partner_id.id,
            'company_id': cls.company_ri.id,
        })

        # ==== Partners / Customers ====
        cls.partner_afip = cls.env.ref("l10n_ar.partner_afip")
        cls.res_partner_adhoc = cls.env['res.partner'].create({
            "name": "ADHOC SA",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": cls.env.ref("base.state_ar_s").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Ovidio Lagos 41 bis",
            "email": "info@adhoc.com.ar",
            "phone": "(+54) (341) 208 0203",
            "website": "http://www.adhoc.com.ar",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "30714295698",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVARI").id,
        })
        cls.partner_cf = cls.env['res.partner'].create({
            "name": "Consumidor Final Anonimo",
            "l10n_latam_identification_type_id": cls.env.ref('l10n_ar.it_Sigd').id,
            "l10n_ar_afip_responsibility_type_id": cls.env.ref("l10n_ar.res_CF").id,
        })
        cls.res_partner_gritti_mono = cls.env['res.partner'].create({
            "name": "Gritti Agrimensura (Monotributo)",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": cls.env.ref("base.state_ar_s").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Calle Falsa 123",
            "email": "info@example.com.ar",
            "phone": "(+54) (341) 111 2222",
            "website": "http://www.grittiagrimensura.com",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "27320732811",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_RM").id,
        })
        cls.res_partner_montana_sur = cls.env['res.partner'].create({
            "name": "Montana Sur",
            "is_company": 1,
            "city": "San Martin de los Andes",
            "state_id": cls.env.ref("base.state_ar_v").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Ruta 3 km 26",
            "email": "contacto@montanasur.com.ar.com",
            "phone": "(+54) (297) 4876 123",
            "website": "http://www.montanasur.com.ar/",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "27333333339",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVA_LIB").id,
        })
        cls.res_partner_servicios_globales = cls.env['res.partner'].create({
            "name": "Servicios Globales SRL (IVA Sujeto Exento)",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": cls.env.ref("base.state_ar_s").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Bv. Oroño 789",
            "email": "contacto@serviciosglobales.com.ar",
            "phone": "(+54) (341) 333 4444",
            "website": "http://www.serviciosglobales.com.ar/",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "30684679372",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVAE").id,
        })
        cls.res_partner_barcelona_food = cls.env['res.partner'].create({
            "name": "Barcelona Food",
            "is_company": 1,
            "city": "Barcelona",
            "zip": "11002",
            "country_id": cls.env.ref("base.es").id,
            "street": "La gran avenida 123",
            "email": "info@barcelonafoods.com",
            "phone": "(+00) (11) 222 3333",
            "website": "http://www.barcelonafoods.com/",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_latam_base.it_fid").id,
            'vat': "2222333344445555",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_EXT").id,
        })
        cls.partner_mipyme = cls.env['res.partner'].create({
            "name": "Trenes Argentinos (Mipyme)",
            "is_company": 1,
            "city": "Buenos Aires",
            "zip": "1524",
            "state_id": cls.env.ref("base.state_ar_c").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Santa Cruz 4636",
            "email": "mipyme@example.com",
            "phone": "(123)-456-7890",
            "website": "http://www.mypime-inc.com",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "30714101443",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVARI").id,
        })
        cls.partner_mipyme_ex = cls.partner_mipyme.copy({'name': 'MiPyme Exento', 'l10n_ar_afip_responsibility_type_id': cls.env.ref('l10n_ar.res_IVAE').id})

        # ==== Taxes ====
        cls.tax_21 = cls._search_tax(cls, 'iva_21')
        cls.tax_27 = cls._search_tax(cls, 'iva_27')
        cls.tax_0 = cls._search_tax(cls, 'iva_0')
        cls.tax_10_5 = cls._search_tax(cls, 'iva_105')
        cls.tax_no_gravado = cls._search_tax(cls, 'iva_no_gravado')
        cls.tax_perc_iibb = cls._search_tax(cls, 'percepcion_iibb_ba')
        cls.tax_iva_exento = cls._search_tax(cls, 'iva_exento')

        cls.tax_national = cls.env['account.tax'].create({
            "name": "National Tax",
            "description": "National Tax",
            "amount": "4",
            "amount_type": "percent",
            "type_tax_use": "sale",
            "country_id": cls.env.ref("base.ar").id,
            "company_id": cls.company_ri.id,
            "tax_group_id": cls.env.ref(f"account.{cls.company_ri.id}_tax_group_national_taxes").id,
        })
        cls.tax_internal = cls.env['account.tax'].create({
            "name": "Internal Tax",
            "description": "Internal Tax",
            "amount": "3",
            "amount_type": "percent",
            "type_tax_use": "sale",
            "country_id": cls.env.ref("base.ar").id,
            "company_id": cls.company_ri.id,
            "tax_group_id": cls.env.ref(f"account.{cls.company_ri.id}_tax_impuestos_internos").id,
        })
        cls.tax_other = cls.env['account.tax'].create({
            "name": "Other Tax",
            "description": "Other Tax",
            "amount": "100",
            "amount_type": "fixed",
            "type_tax_use": "sale",
            "country_id": cls.env.ref("base.ar").id,
            "company_id": cls.company_ri.id,
            "tax_group_id": cls.env.ref(f"account.{cls.company_ri.id}_tax_group_otros_impuestos").id,
        })

        cls.tax_21_purchase = cls._search_tax(cls, 'iva_21', type_tax_use='purchase')
        cls.tax_no_gravado_purchase = cls._search_tax(cls, 'iva_no_gravado', type_tax_use='purchase')

        # ==== Products ====
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')

        cls.product_iva_21 = cls.env['product.product'].create({
            'name': 'Large Cabinet (VAT 21)',
            'uom_id': uom_unit.id,
            'lst_price': 320.0,
            'standard_price': 800.0,
            'type': "consu",
            'default_code': 'E-COM07',
        })
        cls.service_iva_27 = cls.env['product.product'].create({
            # demo 'product_product_telefonia'
            'name': 'Telephone service (VAT 27)',
            'uom_id': uom_unit.id,
            'lst_price': 130.0,
            'standard_price': 250.0,
            'type': 'service',
            'default_code': 'TELEFONIA',
            'taxes_id': [(6, 0, cls.tax_27.ids)],
        })
        cls.product_iva_cero = cls.env['product.product'].create({
            # demo 'product_product_cero'
            'name': 'Non-industrialized animals and vegetables (VAT Zero)',
            'uom_id': uom_unit.id,
            'list_price': 160.0,
            'standard_price': 200.0,
            'type': 'consu',
            'default_code': 'CERO',
            'taxes_id': [(6, 0, cls.tax_0.ids)],
        })
        cls.product_iva_105 = cls.env['product.product'].create({
            # demo 'product.product_product_27'
            'name': 'Laptop Customized (VAT 10,5)',
            'uom_id': uom_unit.id,
            'standard_price': 4500.0,
            'type': 'consu',
            'default_code': '10,5',
            'taxes_id': [(6, 0, cls.tax_10_5.ids)],
        })
        cls.service_iva_21 = cls.env['product.product'].create({
            # demo data product.product_product_2
            'name': 'Virtual Home Staging (VAT 21)',
            'uom_id': uom_hour.id,
            'list_price': 38.25,
            'standard_price': 45.5,
            'type': 'service',
            'default_code': 'VAT 21',
            'taxes_id': [(6, 0, cls.tax_21.ids)],
        })
        cls.product_no_gravado = cls.env['product.product'].create({
            # demo data product_product_no_gravado
            'name': 'Untaxed concepts (VAT NT)',
            'uom_id': uom_unit.id,
            'list_price': 40.00,
            'standard_price': 50.0,
            'type': 'consu',
            'default_code': 'NOGRAVADO',
            'taxes_id': [(6, 0, cls.tax_no_gravado.ids)],
        })
        cls.product_iva_105_perc = cls.env['product.product'].create({
            # product.product_product_25
            "name": "Laptop E5023 (VAT 10,5)",
            'uom_id': uom_unit.id,
            "standard_price": 3280.0,
            'type': 'consu',
            'default_code': '10,5',
            # agregamos percecipn aplicada y sufrida tambien
            'taxes_id': [(6, 0, [cls.tax_10_5.id, cls.tax_perc_iibb.id])],
        })
        cls.product_iva_exento = cls.env['product.product'].create({
            # demo product_product_exento
            'name': 'Book: Development in Odoo (VAT Exempt)',
            'uom_id': uom_unit.id,
            'standard_price': 100.0,
            "list_price": 80.0,
            'type': 'consu',
            'default_code': 'EXENTO',
            'taxes_id': [(6, 0, cls.tax_iva_exento.ids)],
        })
        cls.service_wo_tax = cls.env['product.product'].create({
            # demo product_product_quote_despacho
            'name': 'Service WO TAX',
            'type': 'service',
            'uom_id': uom_unit.id,
            'default_code': 'ARCA_DESPACHO',
        })
        cls.service_iva_no_gravado = cls.env['product.product'].create({
            # demo product_product_arancel
            'name': 'Server VAT Untaxed',
            'type': 'service',
            'uom_id': uom_unit.id,
            'default_code': 'ARCA_ARANCEL',
            "supplier_taxes_id": [(6, 0, (cls.tax_no_gravado_purchase).ids)],
        })

        # ==== Document Types ====
        cls.document_type = {
            'invoice_a': cls.env.ref('l10n_ar.dc_a_f'),
            'credit_note_a': cls.env.ref('l10n_ar.dc_a_nc'),
            'invoice_b': cls.env.ref('l10n_ar.dc_b_f'),
            'credit_note_b': cls.env.ref('l10n_ar.dc_b_nc'),
            'invoice_e': cls.env.ref('l10n_ar.dc_e_f'),
            'invoice_mipyme_a': cls.env.ref('l10n_ar.dc_fce_a_f'),
            'invoice_mipyme_b': cls.env.ref('l10n_ar.dc_fce_b_f'),
        }

        # ==== Journals ====
        cls.sale_expo_journal_ri = cls.env["account.journal"].create({
            'name': "Expo Sales Journal",
            'company_id': cls.company_ri.id,
            'type': "sale",
            'code': "S0002",
            'l10n_latam_use_documents': "True",
            'l10n_ar_afip_pos_number': 2,
            'l10n_ar_afip_pos_partner_id': cls.partner_ri.id,
            'l10n_ar_afip_pos_system': "FEERCEL",
            'refund_sequence': False,
        })

        # ==== Invoices ====
        cls.demo_invoices = {}
        cls.demo_credit_notes = {}
        cls.demo_bills = {}

    def _create_test_invoices_like_demo(self, use_current_date=True):
        """ Create in the unit tests the same invoices created in demo data """
        payment_term_id = self.env.ref("account.account_payment_term_end_following_month")
        invoice_user_id = self.env.user
        incoterm = self.env.ref("account.incoterm_EXW")

        decimal_price = self.env.ref('product.decimal_price')
        decimal_price.digits = 4

        invoices_to_create = {
            'test_invoice_1': {
                "ref": "test_invoice_1: Invoice to gritti support service, vat 21",
                "partner_id": self.res_partner_gritti_mono,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "out_invoice",
                "invoice_date": "2021-03-01",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21}
                ],
            },
            'test_invoice_2': {
                "ref": "test_invoice_2: Invoice to Servicios Globales with vat 21, 27 and 10,5",
                "partner_id": self.res_partner_servicios_globales,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "out_invoice",
                "invoice_date": "2021-03-05",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2}
                ],
            },
            'test_invoice_3': {
                "ref": "test_invoice_3: Invoice to ADHOC with vat cero and 21",
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-01",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1}
                ],
            },
            'test_invoice_4': {
                'ref': 'test_invoice_4: Invoice to ADHOC with vat exempt and 21',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-01",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.1234, 'quantity': 5},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.5678, 'quantity': 1},
                ],
            },
            'test_invoice_5': {
                'ref': 'test_invoice_5: Invoice to ADHOC with all type of taxes',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                    {'product_id': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1}
                ],
            },
            'test_invoice_6': {
                'ref': 'test_invoice_6: Invoice to Montana Sur, fiscal position changes taxes to exempt',
                "partner_id": self.res_partner_montana_sur,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-03",
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                    {'product_id': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                ],
            },
            'test_invoice_7': {
                'ref': 'test_invoice_7: Export invoice to Barcelona food, fiscal position changes tax to exempt (type 4 because it have services)',
                "partner_id": self.res_partner_barcelona_food,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-03",
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2},
                    {'product_id': self.product_no_gravado, 'price_unit': 50.0, 'quantity': 10},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                ],
            },
            'test_invoice_8': {
                'ref': 'test_invoice_8: Invoice to consumidor final',
                "partner_id": self.partner_cf,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 642.0, 'quantity': 1},
                ],
            },
            'test_invoice_10': {
                'ref': 'test_invoice_10; Invoice to ADHOC in USD and vat 21',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 1000.0, 'quantity': 5},
                ],
                "currency_id": self.env.ref("base.USD"),
            },
            'test_invoice_11': {
                'ref': 'test_invoice_11: Invoice to ADHOC with many lines in order to prove rounding error, with 4 decimals of precision for the currency and 2 decimals for the product the error apperar',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 1'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 3'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 4'},
                ],
            },
            'test_invoice_12': {
                'ref': 'test_invoice_12: Invoice to ADHOC with many lines in order to test rounding error, it is required to use a 4 decimal precision in prodct in order to the error occur',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 15.7076, 'quantity': 1, 'name': 'Support Services 1'},
                    {'product_id': self.service_iva_21, 'price_unit': 5.3076, 'quantity': 2, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 3.5384, 'quantity': 2, 'name': 'Support Services 3'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.6376, 'quantity': 2, 'name': 'Support Services 4'},
                ],
            },
            'test_invoice_13': {
                'ref': 'test_invoice_13: Invoice to ADHOC with many lines in order to test zero amount invoices y rounding error. it is required to set the product decimal precision to 4 and change 260.59 for 260.60 in order to reproduce the error',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 1'},
                    {'product_id': self.service_iva_21, 'price_unit': 260.59, 'quantity': 1, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 48.72, 'quantity': 1, 'name': 'Support Services 3'},
                    {'product_id': self.service_iva_21, 'price_unit': 13.666, 'quantity': 1, 'name': 'Support Services 4'},
                    {'product_id': self.service_iva_21, 'price_unit': 11.329, 'quantity': 2, 'name': 'Support Services 5'},
                    {'product_id': self.service_iva_21, 'price_unit': 68.9408, 'quantity': 1, 'name': 'Support Services 6'},
                    {'product_id': self.service_iva_21, 'price_unit': 4.7881, 'quantity': 2, 'name': 'Support Services 7'},
                    {'product_id': self.service_iva_21, 'price_unit': 12.0625, 'quantity': 2, 'name': 'Support Services 8'},
                ],
            },
            'test_invoice_14': {
                'ref': 'test_invoice_14: Export invoice to Barcelona food, fiscal position changes tax to exempt (type 1 because only products)',
                "partner_id": self.res_partner_barcelona_food,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-20",
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                ],
            },
            'test_invoice_15': {
                'ref': 'test_invoice_15: Export invoice to Barcelona food, fiscal position changes tax to exempt (type 2 because only service)',
                "partner_id": self.res_partner_barcelona_food,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-20",
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                ],
            },
            'test_invoice_16': {
                'ref': 'test_invoice_16: Export invoice to Barcelona food, fiscal position changes tax to exempt (type 1 because it have products only, used to test refund of expo)',
                "partner_id": self.res_partner_barcelona_food,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-22",
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                ],
            },
            'test_invoice_17': {
                'ref': 'test_invoice_17: Invoice to ADHOC with 100%% of discount',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8', 'discount': 100},
                ],
            },
            'test_invoice_18': {
                'ref': 'test_invoice_18: Invoice to ADHOC with 100%% of discount and with different VAT aliquots',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8', 'discount': 100},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1, 'discount': 100},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 1},
                ],
            },
            'test_invoice_19': {
                'ref': 'test_invoice_19: Invoice to ADHOC with multiple taxes and perceptions',
                "partner_id": self.res_partner_adhoc,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                "invoice_date": "2021-03-13",
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8'},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 1},
                ],
            }
        }

        for key, values in invoices_to_create.items():
            with Form(self.env['account.move'].with_context(default_move_type=values['move_type'])) as invoice_form:
                invoice_form.ref = values['ref']
                invoice_form.partner_id = values['partner_id']
                invoice_form.invoice_payment_term_id = values['invoice_payment_term_id']
                if not use_current_date:
                    invoice_form.invoice_date = values['invoice_date']
                if values.get('invoice_incoterm_id'):
                    invoice_form.invoice_incoterm_id = values['invoice_incoterm_id']
                for line in values['invoice_line_ids']:
                    with invoice_form.invoice_line_ids.new() as line_form:
                        line_form.product_id = line.get('product_id')
                        line_form.price_unit = line.get('price_unit')
                        line_form.quantity = line.get('quantity')
                        if line.get('tax_ids'):
                            line_form.tax_ids = line.get('tax_ids')
                        line_form.name = 'xxxx'
                        line_form.account_id = self.company_data['default_account_revenue']
            invoice = invoice_form.save()
            self.demo_invoices[key] = invoice

    def _create_invoice_from_dict(self, values, use_current_date=True):
        if not values.get('invoice_payment_term_id'):
            values['invoice_payment_term_id'] = self.env.ref("account.account_payment_term_end_following_month")
        if use_current_date:
            values.pop('invoice_date', False)

        for key, value in values.items():
            if key.endswith("_id"):
                values[key] = value.id

        for line in values['invoice_line_ids']:
            for key, value in line.items():
                if key.endswith("_id"):
                    line[key] = value.id

        values['invoice_line_ids'] = [(0, 0, line_data) for line_data in values['invoice_line_ids']]
        return self.env['account.move'].with_context(default_move_type=values['move_type']).create(values)

    # Helpers

    @classmethod
    def _get_afip_pos_system_real_name(cls):
        return {'PREPRINTED': 'II_IM'}

    def _create_journal(self, afip_ws, data=None):
        """ Create a journal of a given ARCA ws type.
        If there is a problem because we are using a ARCA certificate that is already been in use then change the certificate and try again """
        data = data or {}
        afip_ws = afip_ws.upper()
        pos_number = str(random.randint(0, 99999))
        if 'l10n_ar_afip_pos_number' in data:
            pos_number = data.get('l10n_ar_afip_pos_number')
        values = {'name': '%s %s' % (afip_ws.replace('WS', ''), pos_number),
                  'type': 'sale',
                  'code': pos_number,
                  'l10n_ar_afip_pos_system': self._get_afip_pos_system_real_name().get(afip_ws),
                  'l10n_ar_afip_pos_number': pos_number,
                  'l10n_latam_use_documents': True,
                  'company_id': self.env.company.id,
                  'l10n_ar_afip_pos_partner_id': self.partner_ri.id,
                  'sequence': 1}
        values.update(data)

        journal = self.env['account.journal'].create(values)
        _logger.info('Created journal %s for company %s', journal.name, self.env.company.name)
        return journal

    def _create_invoice(self, data=None, invoice_type='out_invoice'):
        data = data or {}
        with Form(self.env['account.move'].with_context(default_move_type=invoice_type)) as invoice_form:
            invoice_form.partner_id = data.get('partner', self.partner)
            if 'in_' not in invoice_type:
                invoice_form.journal_id = data.get('journal', self.journal)

            if data.get('document_type'):
                invoice_form.l10n_latam_document_type_id = data.get('document_type')
            if data.get('document_number'):
                invoice_form.l10n_latam_document_number = data.get('document_number')
            if data.get('incoterm'):
                invoice_form.invoice_incoterm_id = data.get('incoterm')
            if data.get('currency'):
                invoice_form.currency_id = data.get('currency')
            for line in data.get('lines', [{}]):
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.display_type = line.get('display_type', 'product')
                    if line.get('display_type') in ('line_section', 'line_subsection', 'line_note'):
                        invoice_line_form.name = line.get('name', 'not invoice line')
                    else:
                        invoice_line_form.product_id = line.get('product', self.product_iva_21)
                        invoice_line_form.quantity = line.get('quantity', 1)
                        invoice_line_form.price_unit = line.get('price_unit', 100)
            invoice_form.invoice_date = invoice_form.date
        invoice = invoice_form.save()
        return invoice

    def _create_invoice_product(self, data=None):
        data = data or {}
        return self._create_invoice(data)

    def _create_invoice_service(self, data=None):
        data = data or {}
        newlines = []
        for line in data.get('lines', [{}]):
            line.update({'product': self.service_iva_27})
            newlines.append(line)
        data.update({'lines': newlines})
        return self._create_invoice(data)

    def _create_invoice_product_service(self, data=None):
        data = data or {}
        newlines = []
        for line in data.get('lines', [{}]):
            line.update({'product': self.product_iva_21})
            newlines.append(line)
        data.update({'lines': newlines + [{'product': self.service_iva_27}]})
        return self._create_invoice(data)

    def _create_credit_note(self, invoice, data=None):
        data = data or {}
        refund_wizard = self.env['account.move.reversal'].with_context({'active_ids': [invoice.id], 'active_model': 'account.move'}).create({
            'reason': data.get('reason', 'Mercadería defectuosa'),
            'journal_id': invoice.journal_id.id})

        forced_document_type = data.get('document_type')
        if forced_document_type:
            refund_wizard.l10n_latam_document_type_id = forced_document_type.id

        res = refund_wizard.refund_moves() if data.get('refund_method', 'refund') == 'refund' else refund_wizard.modify_moves()
        refund = self.env['account.move'].browse(res['res_id'])
        return refund

    def _create_debit_note(self, invoice, data=None):
        data = data or {}
        debit_note_wizard = self.env['account.debit.note'].with_context(
            {'active_ids': [invoice.id], 'active_model': 'account.move', 'default_copy_lines': True}).create({
                'reason': data.get('reason', 'Mercadería defectuosa')})
        res = debit_note_wizard.create_debit()
        debit_note = self.env['account.move'].browse(res['res_id'])
        return debit_note

    def _search_tax(self, tax_type, type_tax_use='sale'):
        res = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', type_tax_use),
            ('company_id', '=', self.env.company.id),
            ('tax_group_id', '=', self.env.ref(f'account.{self.env.company.id}_tax_group_{tax_type}').id)], limit=1)
        self.assertTrue(res, '%s Tax was not found' % (tax_type))
        return res

    def _search_fp(self, name):
        return self.env['account.fiscal.position'].search([('company_id', '=', self.env.company.id), ('name', '=', name)])

    def _post(self, invoice):
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    def _prepare_multicurrency_values(self):
        # Enable multi currency
        self.env.user.write({'group_ids': [(4, self.env.ref('base.group_multi_currency').id)]})
        # Set ARS as main currency
        self._set_today_rate(self.env.ref('base.ARS'), 1.0)
        # Set Rates for USD currency
        self._set_today_rate(self.env.ref('base.USD'), 1.0 / 162.013)

    def _set_today_rate(self, currency, value):
        rate_obj = self.env['res.currency.rate']
        rate = rate_obj.search([('currency_id', '=', currency.id), ('name', '=', fields.Date.to_string(fields.Date.today())),
                                ('company_id', '=', self.env.company.id)])
        if rate:
            rate.rate = value
        else:
            rate_obj.create({'company_id': self.env.company.id, 'currency_id': currency.id, 'rate': value})
