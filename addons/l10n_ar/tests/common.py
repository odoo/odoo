# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests.common import Form
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import SingleTransactionCase
from dateutil.relativedelta import relativedelta
import random
import logging
import time

_logger = logging.getLogger(__name__)


class TestAr(AccountTestInvoicingCommon, SingleTransactionCase):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_ar.l10nar_ri_chart_template'):
        super(TestAr, cls).setUpClass(chart_template_ref=chart_template_ref)

        print("------ Common.TestAr setUpClass()")
        # ==== Company ====
        cls.company_data['company'].write({
            'parent_id': cls.env.ref('base.main_company').id,
            'currency_id': cls.env.ref('base.ARS').id,
            'name': '(AR) Responsable Inscripto (Unit Tests)',
            "l10n_ar_afip_start_date": time.strftime('%Y-01-01'),
            'l10n_ar_gross_income_type': 'local',
            'l10n_ar_gross_income_number': '901-21885123',
            'l10n_ar_afip_ws_environment': 'testing',
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

        # ==== Bank Account ====
        cls.bank_account_ri = cls.env['res.partner.bank'].create({
            'acc_number': '7982898111100056688080',
            'partner_id': cls.company_ri.partner_id.id,
            'company_id': cls.company_ri.id,
        })


        # ==== Partners / Customers ====
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
            "name": "Consumidor Final Anónimo",
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
        cls.res_partner_cerrocastor = cls.env['res.partner'].create({
            "name": "Cerro Castor (Tierra del Fuego)",
            "is_company": 1,
            "city": "Ushuaia",
            "state_id": cls.env.ref("base.state_ar_v").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Ruta 3 km 26",
            "email": "info@cerrocastor.com",
            "phone": "(+00) (11) 4444 5556",
            "website": "http://www.cerrocastor.com",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "27333333339",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVA_LIB").id,
        })
        cls.res_partner_cmr = cls.env['res.partner'].create({
            "name": "Concejo Municipal de Rosario (IVA Sujeto Exento)",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": cls.env.ref("base.state_ar_s").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Cordoba 501",
            "email": "info@example.com.ar",
            "phone": "(+54) (341) 222 3333",
            "website": "http://www.concejorosario.gov.ar/",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_ar.it_cuit").id,
            'vat': "30684679372",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_IVAE").id,
        })
        cls.res_partner_expresso = cls.env['res.partner'].create({
            "name": "Expresso",
            "is_company": 1,
            "city": "Barcelona",
            "zip": "11002",
            "country_id": cls.env.ref("base.es").id,
            "street": "La gran avenida 123",
            "email": "info@expresso.com",
            "phone": "(+00) (11) 222 3333",
            "website": "http://www.expresso.com/",
            'l10n_latam_identification_type_id': cls.env.ref("l10n_latam_base.it_fid").id,
            'vat': "2222333344445555",
            'l10n_ar_afip_responsibility_type_id': cls.env.ref("l10n_ar.res_EXT").id,
        })
        cls.partner_mipyme = cls.env['res.partner'].create({
            "name": "Belgrano Cargas Y Logistica S (Mipyme)",
            "is_company": 1,
            "city": "Buenos Aires",
            "zip": "1425",
            "state_id": cls.env.ref("base.state_ar_c").id,
            "country_id": cls.env.ref("base.ar").id,
            "street": "Av. Santa Fe 4636",
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

        # ==== Products ====
        # TODO review not sure if we need to define the next values
        #   <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT Untaxed')]"/>

        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')

        cls.product_iva_21 = cls.env['product.product'].create({
            'name': 'Large Cabinet (VAT 21)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'lst_price': 320.0,
            'standard_price': 800.0,
            'type': "consu",
            'default_code': 'E-COM07',
            # 'property_account_income_id': cls.company_data['default_account_revenue'].id,
            # 'property_account_expense_id': cls.company_data['default_account_expense'].id,
        })
        cls.service_iva_27 = cls.env['product.product'].create({
            # demo 'product_product_telefonia'
            'name': 'Telephone service (VAT 27)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'lst_price': 130.0,
            'standard_price': 250.0,
            'type': 'service',
            'default_code': 'TELEFONIA',
            'taxes_id': [(6, 0, (cls.tax_27).ids)],

            # TODO maybe we need to extend _search_tax for vendor tax_27
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT 27%')]"/>
            # 'supplier_taxes_id': [(6, 0, (cls.tax_purchase_a + cls.tax_purchase_b).ids)],

            # 'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            # 'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
        })
        cls.product_iva_cero = cls.env['product.product'].create({
            # demo 'product_product_cero'
            'name': 'Non-industrialized animals and vegetables (VAT Zero)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'list_price': 160.0,
            'standard_price': 200.0,
            'type': 'consu',
            'default_code': 'CERO',
            'taxes_id': [(6, 0, (cls.tax_0).ids)],

            # TODO maybe we need to extend _search_tax for vendor tax_27
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT 0%')]"/>
            # 'supplier_taxes_id': [(6, 0, (cls.tax_purchase_a + cls.tax_purchase_b).ids)],
            # 'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            # 'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
        })
        cls.product_iva_105 = cls.env['product.product'].create({
            # demo 'product.product_product_27'
            'name': 'Laptop Customized (VAT 10,5)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'standard_price': 4500.0,
            'type': 'consu',
            'default_code': '10,5',
            'taxes_id': [(6, 0, (cls.tax_10_5).ids)],
            # TODO maybe we need to extend _search_tax for vendor tax_27
            # <field name="taxes_id" search="[('type_tax_use', '=', 'sale'), ('tax_group_id', '=', 'VAT 10.5%')]"/>
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT 10.5%')]"/>
            # 'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            # 'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
        })
        cls.service_iva_21 = cls.env['product.product'].create({
            # demo data product.product_product_2
            'name': 'Virtual Home Staging (VAT 21)',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'list_price': 38.25,
            'standard_price': 45.5,
            'type': 'service',
            'default_code': 'VAT 21',
            'taxes_id': [(6, 0, (cls.tax_21).ids)],
        })
        cls.product_no_gravado = cls.env['product.product'].create({
            # demo data product_product_no_gravado
            'name': 'Untaxed concepts (VAT NT)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'list_price': 40.00,
            'standard_price': 50.0,
            'type': 'consu',
            'default_code': 'NOGRAVADO',
            'taxes_id': [(6, 0, (cls.tax_no_gravado).ids)],
        })
        cls.product_iva_105_perc = cls.product_iva_105.copy({
            # product.product_product_25
            "name": "Laptop E5023 (VAT 10,5)",
            "standard_price": 3280.0,
            # agregamos percecipn aplicada y sufrida tambien
            'taxes_id': [(6, 0, [cls.tax_10_5.id, cls.tax_perc_iibb.id])],
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', 'in', ['VAT 10.5%', 'Percepción IIBB', 'Percepción Ganancias', 'Percepción IVA'])]"/>
        })
        cls.product_iva_exento = cls.env['product.product'].create({
            # demo product_product_exento
            'name': 'Book: Development in Odoo (VAT Exempt)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'standard_price': 100.0,
            "list_price": 80.0,
            'type': 'consu',
            'default_code': 'EXENTO',
            'taxes_id': [(6, 0, (cls.tax_iva_exento).ids)],
        })

        # # Document Types
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
        # cls._create_test_invoices_like_demo(cls)

    def _create_test_invoices_like_demo(self):
        """ Create in the unit tests the same invoices created in demo data """
        payment_term_id = self.env.ref("account.account_payment_term_end_following_month")
        invoice_user_id = self.env.user
        incoterm = self.env.ref("account.incoterm_EXW")
        today = fields.Date.today()

        # TODO check invoices dates
        invoices_to_create = {
            'demo_invoice_1': {
                "ref": "demo_invoice_1: Invoice to gritti support service, vat 21",
                "partner_id": self.res_partner_gritti_mono,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "out_invoice",
                # "invoice_date": fields.Date.start_of(today),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21}
                ],
            },
            'demo_invoice_2': {
                "ref": "demo_invoice_2: Invoice to CMR with vat 21, 27 and 10,5",
                "partner_id": self.res_partner_cmr,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": "out_invoice",
                # "invoice_date": today + relativedelta(day=5),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 2}
                ],
            },
            'demo_invoice_3': {
                "ref": "demo_invoice_3: Invoice to ADHOC with vat cero and 21",
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": fields.Date.start_of(today),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.product_iva_cero, 'price_unit': 200.0, 'quantity': 1}
                ],
            },
            'demo_invoice_4': {
                'ref': 'demo_invoice_4: Invoice to ADHOC with vat exempt and 21',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": fields.Date.start_of(today, "month"),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                    {'product_id': self.product_iva_exento, 'price_unit': 100.0, 'quantity': 1},
                ],
            },
            'demo_invoice_5': {
                'ref': 'demo_invoice_5: Invoice to ADHOC with all type of taxes',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
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
            'demo_invoice_6': {
                'ref': 'demo_invoice_6: Invoice to cerro castor, fiscal position changes taxes to exempt',
                "partner_id": self.res_partner_cerrocastor,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=3),
                "invoice_date": today,
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
            'demo_invoice_7': {
                'ref': 'demo_invoice_7: Export invoice to expresso, fiscal position changes tax to exempt (type 4 because it have services)',
                "partner_id": self.res_partner_expresso,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=3),
                "invoice_date": today,
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
            'demo_invoice_8': {
                'ref': 'demo_invoice_8: Invoice to consumidor final',
                "partner_id": self.partner_cf,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 642.0, 'quantity': 1},
                ],
            },
            'demo_invoice_10': {
                'ref': 'demo_invoice_10; Invoice to ADHOC in USD and vat 21',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 1000.0, 'quantity': 5},
                ],
                "currency_id": self.env.ref("base.USD"),
            },
            'demo_invoice_11': {
                'ref': 'demo_invoice_11: Invoice to ADHOC with many lines in order to prove rounding error, with 4 decimals of precision for the currency and 2 decimals for the product the error apperar',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 1'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 3'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 4'},
                ],
            },
            'demo_invoice_12': {
                'ref': 'demo_invoice_12: Invoice to ADHOC with many lines in order to test rounding error, it is required to use a 4 decimal precision in prodct in order to the error occur',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 15.7076, 'quantity': 1, 'name': 'Support Services 1'},
                    {'product_id': self.service_iva_21, 'price_unit': 5.3076, 'quantity': 2, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 3.5384, 'quantity': 2, 'name': 'Support Services 3'},
                    {'product_id': self.service_iva_21, 'price_unit': 1.6376, 'quantity': 2, 'name': 'Support Services 4'},
                ],
            },
            'demo_invoice_13': {
                'ref': 'demo_invoice_13: Invoice to ADHOC with many lines in order to test zero amount invoices y rounding error. it is required to set the product decimal precision to 4 and change 260.59 for 260.60 in order to reproduce the error',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 1'},
                    # TODO check: demo data has quantity -1
                    # {'product_id': self.service_iva_21, 'price_unit': 260.59, 'quantity': -1, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 260.59, 'quantity': 1, 'name': 'Support Services 2'},
                    {'product_id': self.service_iva_21, 'price_unit': 48.72, 'quantity': 1, 'name': 'Support Services 3'},
                    {'product_id': self.service_iva_21, 'price_unit': 13.666, 'quantity': 1, 'name': 'Support Services 4'},
                    {'product_id': self.service_iva_21, 'price_unit': 11.329, 'quantity': 2, 'name': 'Support Services 5'},
                    {'product_id': self.service_iva_21, 'price_unit': 68.9408, 'quantity': 1, 'name': 'Support Services 6'},
                    {'product_id': self.service_iva_21, 'price_unit': 4.7881, 'quantity': 2, 'name': 'Support Services 7'},
                    {'product_id': self.service_iva_21, 'price_unit': 12.0625, 'quantity': 2, 'name': 'Support Services 8'},
                ],
            },
            'demo_invoice_14': {
                'ref': 'demo_invoice_14: Export invoice to expresso, fiscal position changes tax to exempt (type 1 because only products)',
                "partner_id": self.res_partner_expresso,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=20),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                ],
            },
            'demo_invoice_15': {
                'ref': 'demo_invoice_15: Export invoice to expresso, fiscal position changes tax to exempt (type 2 because only service)',
                "partner_id": self.res_partner_expresso,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=20),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                ],
            },
            'demo_invoice_16': {
                'ref': 'demo_invoice_16: Export invoice to expresso, fiscal position changes tax to exempt (type 1 because it have products only, used to test refund of expo)',
                "partner_id": self.res_partner_expresso,
                "journal_id": self.sale_expo_journal_ri,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=22),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_incoterm_id": incoterm,
                "invoice_line_ids": [
                    {'product_id': self.product_iva_105, 'price_unit': 642.0, 'quantity': 5},
                ],
            },
            'demo_invoice_17': {
                'ref': 'demo_invoice_17: Invoice to ADHOC with 100% of discount',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8', 'discount': 100},
                ],
            },
            'demo_invoice_18': {
                'ref': 'demo_invoice_18: Invoice to ADHOC with 100% of discount and with different VAT aliquots',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8', 'discount': 100},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1, 'discount': 100},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 1},
                ],
            },
            'demo_invoice_19': {
                'ref': 'demo_invoice_19: Invoice to ADHOC with multiple taxes and perceptions',
                "partner_id": self.res_partner_adhoc,
                "invoice_user_id": invoice_user_id,
                "invoice_payment_term_id": payment_term_id,
                "move_type": 'out_invoice',
                # "invoice_date": today + relativedelta(day=13),
                "invoice_date": today,
                "company_id": self.company_ri,
                "invoice_line_ids": [
                    {'product_id': self.service_iva_21, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8'},
                    {'product_id': self.service_iva_27, 'price_unit': 250.0, 'quantity': 1},
                    {'product_id': self.product_iva_105_perc, 'price_unit': 3245.0, 'quantity': 1},
                ],
            }
        }

        for key, values in invoices_to_create.items():
            # print("----- New invoice Form: %s" % key)
            with Form(self.env['account.move'].with_context(default_move_type=values['move_type'])) as invoice_form:
                invoice_form.ref = values['ref']
                invoice_form.partner_id = values['partner_id']
                invoice_form.invoice_user_id = values['invoice_user_id']
                invoice_form.invoice_payment_term_id = values['invoice_payment_term_id']
                invoice_form.invoice_date = values['invoice_date']
                invoice_form.company_id = values['company_id']
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
            self.demo_invoices[key] = invoice

    # TODO: add this move lines
    #         <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
    #     <value model="account.move.line" search="[('move_id', '=', ref('demo_invoice_19')), ('product_id', '=', ref('product.product_product_2'))]"/>
    #     <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'sale'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '06')], limit=1).id)]}"/>
    # </function>

    # <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
    #     <value model="account.move.line" search="[('move_id', '=', ref('demo_invoice_19')), ('product_id', '=', ref('product_product_telefonia'))]"/>
    #     <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'sale'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '07')], limit=1).id)]}"/>
    # </function>

    # <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
    #     <value model="account.move.line" search="[('move_id', '=', ref('demo_invoice_19')), ('product_id', '=', ref('product.product_product_25'))]"/>
    #     <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'sale'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '99')], limit=1).id)]}"/>
    # </function>

    # Re used unit tests methods

    def _create_test_credit_notes_like_demo(self):
        # TODO test it
        """ Create in the unit tests the same credit notes created in demo data """
        reversal_moves = {
            "demo_refund_invoice_3": {
                "ref": "demo_refund_invoice_3: Create draft refund for invoice 3",
                "reason": "Mercadería defectuosa",
                "refund_method": "refund",
                "move_ids": [(4, self.demo_invoices['demo_invoice_3'])],
                "date": time.strftime('%Y-%m') + '-01',
            },
            "demo_refund_invoice_4": {
                "ref": "demo_refund_invoice_4: Create draft refund for invoice 4",
                "reason": "Venta cancelada",
                "refund_method": "cancel",
                "move_ids": [(4, self.demo_invoices['demo_invoice_4'])],
                "date": time.strftime('%Y-%m') + '-01',
            },
            "demo_refund_invoice_16": {
                "ref": "demo_refund_invoice_16: Create cancel refund for expo invoice 16 (las nc/nd expo invoice no requiere parametro permiso existennte, por eso agregamos este ejemplo)",
                "reason": "Venta cancelada",
                "refund_method": "cancel",
                "move_ids":  [(4, self.demo_invoices['demo_invoice_16'])],
                "date": time.strftime('%Y-%m') + '-01',
            }
        }

        for item in reversal_moves:
            rec = self.env["account.move.reversal"].create(item)
            rec.reverse_moves()


    """

    supplier_invoices = {
    "demo_sup_invoice_1": {
        "ref": "demo_sup_invoice_1: Invoice from gritti support service, auto fiscal position set VAT Not Applicable";

    },

    <record id="demo_sup_invoice_1" model="account.move">
        <field name="partner_id" ref="res_partner_gritti_agrimensura"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-01'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_2'), 'price_unit': 642.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product.product_product_27'), 'price_unit': 642.0, 'quantity': 5}),
            (0, 0, {'product_id': ref('product_product_telefonia'), 'price_unit': 250.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product_product_no_gravado'), 'price_unit': 50.0, 'quantity': 10}),
            (0, 0, {'product_id': ref('product_product_cero'), 'price_unit': 200.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product_product_exento'), 'price_unit': 100.0, 'quantity': 1}),
        ]"/>
    </record>


    # '': {
        
    # },

    }
    
    <!-- we add l10n_latam_document_number on on a separete line because we need l10n_latam_document_type_id to be auto assigned so that account.move.name can be computed with the _inverse_l10n_latam_document_number -->

    <!-- Invoice from Foreign with vat 21, 27 and 10,5 -->
    <record id="demo_sup_invoice_2" model="account.move">
        <field name="partner_id" ref="res_partner_foreign"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-01'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_27'), 'price_unit': 642.0, 'quantity': 5}),
            (0, 0, {'product_id': ref('product_product_telefonia'), 'price_unit': 250.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product.product_product_25'), 'price_unit': 3245.0, 'quantity': 2}),
        ]"/>
    </record>

    <!-- Invoice from Foreign with vat zero and 21 -->
    <record id="demo_sup_invoice_3" model="account.move">
        <field name="partner_id" ref="res_partner_foreign"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-11'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_27'), 'price_unit': 642.0, 'quantity': 5}),
            (0, 0, {'product_id': ref('product_product_cero'), 'price_unit': 200.0, 'quantity': 1}),
        ]"/>
    </record>

    <!-- Invoice to Foreign with vat exempt and 21 -->
    <record id="demo_sup_invoice_4" model="account.move">
        <field name="partner_id" ref="res_partner_foreign"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-15'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_27'), 'price_unit': 642.0, 'quantity': 5}),
            (0, 0, {'product_id': ref('product_product_exento'), 'price_unit': 100.0, 'quantity': 1}),
        ]"/>
    </record>

    <!-- Invoice to Foreign with all type of taxes  -->
    <record id="demo_sup_invoice_5" model="account.move">
        <field name="partner_id" ref="res_partner_foreign"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-18'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_27'), 'price_unit': 642.0, 'quantity': 5}),
            (0, 0, {'product_id': ref('product_product_telefonia'), 'price_unit': 250.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product.product_product_25'), 'price_unit': 3245.0, 'quantity': 2}),
            (0, 0, {'product_id': ref('product_product_no_gravado'), 'price_unit': 50.0, 'quantity': 10}),
            (0, 0, {'product_id': ref('product_product_cero'), 'price_unit': 200.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product_product_exento'), 'price_unit': 100.0, 'quantity': 1}),
        ]"/>
    </record>

    <!-- Service Import to Odoo, fiscal position changes tax not correspond -->
    <record id="demo_sup_invoice_6" model="account.move">
        <field name="partner_id" ref="res_partner_odoo"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-26'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_2'), 'price_unit': 1642.0, 'quantity': 1}),
        ]"/>
    </record>

    <!-- Similar to last one but with line that have tax not correspond with negative amount -->
    <record id="demo_sup_invoice_7" model="account.move">
        <field name="partner_id" ref="res_partner_odoo"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-27'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_2'), 'price_unit': 1642.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product_product_no_gravado'), 'price_unit': -50.0, 'quantity': 10}),
        ]"/>
    </record>

    <!-- Invoice to ADHOC with multiple taxes and perceptions -->
    <record id="demo_sup_invoice_8" model="account.move">
        <field name="partner_id" ref="l10n_ar.res_partner_adhoc"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-01'"/>
        <field name="company_id" ref="company_ri"/>
        <field name="invoice_line_ids" eval="[
            (0, 0, {'product_id': ref('product.product_product_27'), 'price_unit': 642.0, 'quantity': 5}),
            (0, 0, {'product_id': ref('product_product_telefonia'), 'price_unit': 250.0, 'quantity': 1}),
            (0, 0, {'product_id': ref('product.product_product_25'), 'price_unit': 3245.0, 'quantity': 2}),
        ]"/>
    </record>

    <!-- Import Cleareance -->
    <record id="demo_despacho_1" model="account.move">
        <field name="partner_id" ref="l10n_ar.partner_afip"/>
        <field name="invoice_user_id" ref="base.user_demo"/>
        <field name="invoice_payment_term_id" ref="account.account_payment_term_end_following_month"/>
        <field name="move_type">in_invoice</field>
        <!-- as we create lines separatelly we need to set journal, if not, misc journal is selected -->
        <field name="journal_id" model="account.journal" search="[('type', '=', 'purchase'), ('company_id', '=', obj().env.company.id)]"/>
        <field name="invoice_date" eval="time.strftime('%Y-%m')+'-13'"/>
        <field name="company_id" ref="company_ri"/>
    </record>
    <!-- create this lines manually to set taxes and prices -->
    <record id="demo_despacho_1_line_1" model="account.move.line" context="{'check_move_validity': False}">
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">5064.98</field>
        <field name="name">[AFIP_DESPACHO] Despacho de importación</field>
        <field name="quantity">1</field>
        <field name="product_id" ref="l10n_ar.product_product_quote_despacho"/>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA 21%'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('l10n_ar.product_product_quote_despacho').categ_id.property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_2" model="account.move.line" context="{'check_move_validity': False}">
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">152.08</field>
        <field name="name">[AFIP_TASA_EST] Tasa Estadística</field>
        <field name="quantity">1</field>
        <field name="product_id" ref="l10n_ar.product_product_tasa_estadistica"/>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA 21%'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('l10n_ar.product_product_tasa_estadistica').categ_id.property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_3" model="account.move.line" context="{'check_move_validity': False}">
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">10.0</field>
        <field name="name">[AFIP_ARANCEL] Arancel</field>
        <field name="quantity">1</field>
        <field name="product_id" ref="l10n_ar.product_product_arancel"/>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA No Gravado'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('l10n_ar.product_product_arancel').categ_id.property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_4" model="account.move.line" context="{'check_move_validity': False}">
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">28.00</field>
        <field name="name">[AFIP_SERV_GUARDA] Servicio de Guarda</field>
        <field name="quantity">1</field>
        <field name="product_id" ref="l10n_ar.product_product_servicio_de_guarda"/>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA No Gravado'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('l10n_ar.product_product_servicio_de_guarda').categ_id.property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_5" model="account.move.line" context="{'check_move_validity': False}">
        <field name="name">FOB Total</field>
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">28936.06</field>
        <field name="quantity">1</field>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA 21%'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('product.product_category_all').property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_6" model="account.move.line" context="{'check_move_validity': False}">
        <field name="name">Flete</field>
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">1350.00</field>
        <field name="quantity">1</field>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA 21%'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('product.product_category_all').property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_7" model="account.move.line" context="{'check_move_validity': False}">
        <field name="name">Seguro</field>
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">130.21</field>
        <field name="quantity">1</field>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA 21%'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('product.product_category_all').property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_8" model="account.move.line" context="{'check_move_validity': False}">
        <field name="name">-FOB Total</field>
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">-28936.06</field>
        <field name="quantity">1</field>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA No Gravado'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('product.product_category_all').property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_9" model="account.move.line" context="{'check_move_validity': False}">
        <field name="name">-Flete</field>
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">-1350.00</field>
        <field name="quantity">1</field>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA No Gravado'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('product.product_category_all').property_account_income_categ_id.id"/>
    </record>
    <record id="demo_despacho_1_line_10" model="account.move.line" context="{'check_move_validity': False}">
        <field name="name">-Seguro</field>
        <field name="move_id" ref="demo_despacho_1"/>
        <field name="price_unit">-130.21</field>
        <field name="quantity">1</field>
        <field name="product_uom_id" ref="uom.product_uom_unit"/>
        <field name="tax_ids" model="account.tax" eval="[(6, 0, obj().search([('company_id', '=', obj().env.ref('l10n_ar.company_ri').id), ('name', '=', 'IVA No Gravado'), ('type_tax_use', '=', 'purchase')], limit=1).ids)]"/>
        <field name="account_id" model="account.move.line" eval="obj().env.ref('product.product_category_all').property_account_income_categ_id.id"/>
    </record>

    <record id="demo_sup_invoice_1" model="account.move">
        <field name="l10n_latam_document_number">0001-00000008</field>
    </record>
    <record id="demo_sup_invoice_2" model="account.move">
        <field name="l10n_latam_document_number">0002-00000123</field>
    </record>
    <record id="demo_sup_invoice_3" model="account.move">
        <field name="l10n_latam_document_number">0003-00000312</field>
    </record>
    <record id="demo_sup_invoice_4" model="account.move">
        <field name="l10n_latam_document_number">0001-00000200</field>
    </record>
    <record id="demo_sup_invoice_5" model="account.move">
        <field name="l10n_latam_document_number">0001-00000222</field>
    </record>
    <record id="demo_sup_invoice_6" model="account.move">
        <field name="l10n_latam_document_number">0001-00000333</field>
    </record>
    <record id="demo_sup_invoice_7" model="account.move">
        <field name="l10n_latam_document_number">0001-00000334</field>
    </record>
    <record id="demo_sup_invoice_8" model="account.move">
        <field name="l10n_latam_document_number">0001-00000335</field>
    </record>
    <record id="demo_despacho_1" model="account.move">
        <field name="l10n_latam_document_number">16052IC04000605L</field>
    </record>

    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_1')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_2')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_3')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_4')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_5')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_6')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_7')]"/>
    </function>
    <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        <value eval="[ref('demo_despacho_1')]"/>
    </function>

    <function model="account.move.line" name="_onchange_product_id" context="{'check_move_validity': False}">
        <value model="account.move.line" eval="obj().search([('move_id', 'in', [ref('demo_sup_invoice_1'), ref('demo_sup_invoice_2'), ref('demo_sup_invoice_3'), ref('demo_sup_invoice_4'), ref('demo_sup_invoice_5'), ref('demo_sup_invoice_6'), ref('demo_sup_invoice_7'), ref('demo_sup_invoice_8')])]).ids"/>
    </function>

    <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
        <value model="account.move.line" search="[('move_id', '=', ref('demo_sup_invoice_8')), ('product_id', '=', ref('product.product_product_27'))]"/>
        <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'purchase'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '06')], limit=1).id)]}"/>
    </function>

    <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
        <value model="account.move.line" search="[('move_id', '=', ref('demo_sup_invoice_8')), ('product_id', '=', ref('product_product_telefonia'))]"/>
        <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'purchase'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '07')], limit=1).id)]}"/>
    </function>

    <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
        <value model="account.move.line" search="[('move_id', '=', ref('demo_sup_invoice_8')), ('product_id', '=', ref('product.product_product_25'))]"/>
        <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'purchase'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '99')], limit=1).id)]}"/>
    </function>

    <function model="account.move" name="_recompute_dynamic_lines" context="{'check_move_validity': False}">
        <value eval="[ref('demo_sup_invoice_1'), ref('demo_sup_invoice_2'), ref('demo_sup_invoice_3'), ref('demo_sup_invoice_4'), ref('demo_sup_invoice_5'), ref('demo_sup_invoice_6'), ref('demo_sup_invoice_7'), ref('demo_sup_invoice_8'), ref('demo_despacho_1')]"/>
        <value eval="True"/>
    </function>

    <function model="account.move" name="action_post">
        <value eval="[ref('demo_sup_invoice_1'), ref('demo_sup_invoice_2'), ref('demo_sup_invoice_3'), ref('demo_sup_invoice_4'), ref('demo_sup_invoice_5'), ref('demo_sup_invoice_6'), ref('demo_sup_invoice_7'), ref('demo_sup_invoice_8'), ref('demo_despacho_1')]"/>
    """

    # TODO improve used to set the values easier
    def _test_demo_cases(self, cases):
        for inv, test_case in cases.items():
            _logger.info('  * running test %s: %s' % (inv, test_case))
            invoice = self.demo_invoices[inv]
            self._edi_validate_and_review(invoice, error_msg=test_case)

    # Helpers

    @classmethod
    def _get_afip_pos_system_real_name(cls):
        return {'PREPRINTED': 'II_IM'}

    def _create_journal(self, afip_ws, data=None):
        """ Create a journal of a given AFIP ws type.
        If there is a problem because we are using a AFIP certificate that is already been in use then change the certificate and try again """
        data = data or {}
        afip_ws = afip_ws.upper()
        pos_number = str(random.randint(0, 99999))
        if 'l10n_ar_afip_pos_number' in data:
            pos_number = data.pop('l10n_ar_afip_pos_number')
        values = {'name': '%s %s' % (afip_ws.replace('WS', ''), pos_number),
                  'type': 'sale',
                  'code': afip_ws,
                  'l10n_ar_afip_pos_system': self._get_afip_pos_system_real_name().get(afip_ws),
                  'l10n_ar_afip_pos_number': pos_number,
                  'l10n_latam_use_documents': True,
                  'company_id': self.env.company.id,
                  'l10n_ar_afip_pos_partner_id': self.partner_ri.id,
                  'sequence': 1}
        values.update(data)

        journal = self.env['account.journal'].create(values)
        _logger.info('Created journal %s for company %s' % (journal.name, self.env.company.name))
        return journal

    def _create_invoice(self, data=None, invoice_type='out_invoice'):
        data = data or {}
        with Form(self.env['account.move'].with_context(default_move_type=invoice_type)) as invoice_form:
            invoice_form.partner_id = data.pop('partner', self.partner)
            if 'in_' not in invoice_type:
                invoice_form.journal_id = data.pop('journal', self.journal)

            if data.get('document_type'):
                invoice_form.l10n_latam_document_type_id = data.pop('document_type')
            if data.get('document_number'):
                invoice_form.l10n_latam_document_number = data.pop('document_number')
            if data.get('incoterm'):
                invoice_form.invoice_incoterm_id = data.pop('incoterm')
            if data.get('currency'):
                invoice_form.currency_id = data.pop('currency')
            for line in data.get('lines', [{}]):
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    if line.get('display_type'):
                        invoice_line_form.display_type = line.get('display_type')
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
            'refund_method': data.get('refund_method', 'refund')})

        forced_document_type = data.get('document_type')
        if forced_document_type:
            refund_wizard.l10n_latam_document_type_id = forced_document_type.id

        res = refund_wizard.reverse_moves()
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

    def _search_tax(self, tax_type):
        res = self.env['account.tax'].with_context(active_test=False).search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
            ('tax_group_id', '=', self.env.ref('l10n_ar.tax_group_' + tax_type).id)], limit=1)
        self.assertTrue(res, '%s Tax was not found' % (tax_type))
        return res

    def _search_fp(self, name):
        return self.env['account.fiscal.position'].search([('company_id', '=', self.env.company.id), ('name', '=', name)])
