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
    def setUpClass(self, chart_template_ref='l10n_ar.l10nar_ri_chart_template'):
        super(TestAr, self).setUpClass(chart_template_ref=chart_template_ref)

        print(" ------ Common.TestAr setUpClass()")
        # ==== Company ====
        self.company_data['company'].write({
            'parent_id': self.env.ref('base.main_company').id,
            'currency_id': self.env.ref('base.ARS').id,
            'name': '(AR) Responsable Inscripto (Unit Tests)',
            "l10n_ar_afip_start_date": time.strftime('%Y-01-01'),
            'l10n_ar_gross_income_type': 'local',
            'l10n_ar_gross_income_number': '901-21885123',
            'l10n_ar_afip_ws_environment': 'testing',
        })
        self.company_ri = self.company_data['company']

        self.company_ri.partner_id.write({
            'name': '(AR) Responsable Inscripto (Unit Tests)',
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_IVARI").id,
            'l10n_latam_identification_type_id': self.env.ref("l10n_ar.it_cuit").id,
            'vat': '30111111118',
            "street": 'Calle Falsa 123',
            "city": 'Rosario',
            "country_id": self.env.ref("base.ar").id,
            "state_id": self.env.ref("base.state_ar_s").id,
            "zip": '2000',
            "phone": '+1 555 123 8069',
            "email": 'info@example.com',
            "website": 'www.example.com',
        })
        self.partner_ri = self.company_ri.partner_id

        # ==== Bank Account ====
        self.bank_account_ri = self.env['res.partner.bank'].create({
            'acc_number': '7982898111100056688080',
            'partner_id': self.company_ri.partner_id.id,
            'company_id': self.company_ri.id,
        })

        # Set context to do not make cr.commit() for unit tests
        self.env = self.env(context={'l10n_ar_invoice_skip_commit': True})

        # ==== Partners / Customers ====
        self.res_partner_adhoc = self.env['res.partner'].create({
            "name": "ADHOC SA",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": self.env.ref("base.state_ar_s").id,
            "country_id": self.env.ref("base.ar").id,
            "street": "Ovidio Lagos 41 bis",
            "email": "info@adhoc.com.ar",
            "phone": "(+54) (341) 208 0203",
            "website": "http://www.adhoc.com.ar",
            'l10n_latam_identification_type_id': self.env.ref("l10n_ar.it_cuit").id,
            'vat': "30714295698",
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_IVARI").id,
        })
        self.partner_cf = self.env['res.partner'].create({
            "name": "Consumidor Final Anónimo",
            "l10n_latam_identification_type_id": self.env.ref('l10n_ar.it_Sigd').id,
            "l10n_ar_afip_responsibility_type_id": self.env.ref("l10n_ar.res_CF").id,
        })
        self.res_partner_gritti_mono = self.env['res.partner'].create({
            "name": "Gritti Agrimensura (Monotributo)",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": self.env.ref("base.state_ar_s").id,
            "country_id": self.env.ref("base.ar").id,
            "street": "Calle Falsa 123",
            "email": "info@example.com.ar",
            "phone": "(+54) (341) 111 2222",
            "website": "http://www.grittiagrimensura.com",
            'l10n_latam_identification_type_id': self.env.ref("l10n_ar.it_cuit").id,
            'vat': "27320732811",
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_RM").id,
        })
        self.res_partner_cerrocastor = self.env['res.partner'].create({
            "name": "Cerro Castor (Tierra del Fuego)",
            "is_company": 1,
            "city": "Ushuaia",
            "state_id": self.env.ref("base.state_ar_v").id,
            "country_id": self.env.ref("base.ar").id,
            "street": "Ruta 3 km 26",
            "email": "info@cerrocastor.com",
            "phone": "(+00) (11) 4444 5556",
            "website": "http://www.cerrocastor.com",
            'l10n_latam_identification_type_id': self.env.ref("l10n_ar.it_cuit").id,
            'vat': "27333333339",
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_IVA_LIB").id,
        })
        self.res_partner_cmr = self.env['res.partner'].create({
            "name": "Concejo Municipal de Rosario (IVA Sujeto Exento)",
            "is_company": 1,
            "city": "Rosario",
            "zip": "2000",
            "state_id": self.env.ref("base.state_ar_s").id,
            "country_id": self.env.ref("base.ar").id,
            "street": "Cordoba 501",
            "email": "info@example.com.ar",
            "phone": "(+54) (341) 222 3333",
            "website": "http://www.concejorosario.gov.ar/",
            'l10n_latam_identification_type_id': self.env.ref("l10n_ar.it_cuit").id,
            'vat': "30684679372",
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_IVAE").id,
        })
        self.res_partner_expresso = self.env['res.partner'].create({
            "name": "Expresso",
            "is_company": 1,
            "city": "Barcelona",
            "zip": "11002",
            "country_id": self.env.ref("base.es").id,
            "street": "La gran avenida 123",
            "email": "info@expresso.com",
            "phone": "(+00) (11) 222 3333",
            "website": "http://www.expresso.com/",
            'l10n_latam_identification_type_id': self.env.ref("l10n_latam_base.it_fid").id,
            'vat': "2222333344445555",
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_EXT").id,
        })
        self.partner_mipyme = self.env['res.partner'].create({
            "name": "Belgrano Cargas Y Logistica S (Mipyme)",
            "is_company": 1,
            "city": "Buenos Aires",
            "zip": "1425",
            "state_id": self.env.ref("base.state_ar_c").id,
            "country_id": self.env.ref("base.ar").id,
            "street": "Av. Santa Fe 4636",
            "email": "mipyme@example.com",
            "phone": "(123)-456-7890",
            "website": "http://www.mypime-inc.com",
            'l10n_latam_identification_type_id': self.env.ref("l10n_ar.it_cuit").id,
            'vat': "30714101443",
            'l10n_ar_afip_responsibility_type_id': self.env.ref("l10n_ar.res_IVARI").id,
        })
        self.partner_mipyme_ex = self.partner_mipyme.copy({'name': 'MiPyme Exento', 'l10n_ar_afip_responsibility_type_id': self.env.ref('l10n_ar.res_IVAE').id})

        # ==== Taxes ====
        self.tax_21 = self._search_tax(self, 'iva_21')
        self.tax_27 = self._search_tax(self, 'iva_27')
        self.tax_0 = self._search_tax(self, 'iva_0')
        self.tax_10_5 = self._search_tax(self, 'iva_105')
        self.tax_no_gravado = self._search_tax(self, 'iva_no_gravado')
        self.tax_perc_iibb = self._search_tax(self, 'percepcion_iibb_ba')
        self.tax_iva_exento = self._search_tax(self, 'iva_exento')

        # ==== Products ====
        # TODO review not sure if we need to define the next values
        #   <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT Untaxed')]"/>

        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_hour = self.env.ref('uom.product_uom_hour')

        self.product_iva_21 = self.env['product.product'].create({
            'name': 'Large Cabinet (VAT 21)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'lst_price': 320.0,
            'standard_price': 800.0,
            'type': "consu",
            'default_code': 'E-COM07',
            # 'property_account_income_id': self.company_data['default_account_revenue'].id,
            # 'property_account_expense_id': self.company_data['default_account_expense'].id,
        })
        self.service_iva_27 = self.env['product.product'].create({
            'name': 'Telephone service (VAT 27)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'lst_price': 130.0,
            'standard_price': 250.0,
            'type': 'service',
            'default_code': 'TELEFONIA',
            'taxes_id': [(6, 0, (self.tax_27).ids)],

            # TODO maybe we need to extend _search_tax for vendor tax_27
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT 27%')]"/>
            # 'supplier_taxes_id': [(6, 0, (self.tax_purchase_a + self.tax_purchase_b).ids)],

            # 'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
            # 'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
        })
        self.product_iva_cero = self.env['product.product'].create({
            # demo 'product_product_cero'
            'name': 'Non-industrialized animals and vegetables (VAT Zero)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'list_price': 160.0,
            'standard_price': 200.0,
            'type': 'consu',
            'default_code': 'CERO',
            'taxes_id': [(6, 0, (self.tax_0).ids)],

            # TODO maybe we need to extend _search_tax for vendor tax_27
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT 0%')]"/>
            # 'supplier_taxes_id': [(6, 0, (self.tax_purchase_a + self.tax_purchase_b).ids)],
            # 'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
            # 'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
        })
        self.product_iva_105 = self.env['product.product'].create({
            # demo 'product.product_product_27'
            'name': 'Laptop Customized (VAT 10,5)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'standard_price': 4500.0,
            'type': 'consu',
            'default_code': '10,5',
            'taxes_id': [(6, 0, (self.tax_10_5).ids)],
            # TODO maybe we need to extend _search_tax for vendor tax_27
            # <field name="taxes_id" search="[('type_tax_use', '=', 'sale'), ('tax_group_id', '=', 'VAT 10.5%')]"/>
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', '=', 'VAT 10.5%')]"/>
            # 'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
            # 'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
        })
        self.service_iva_21 = self.env['product.product'].create({
            # demo data product.product_product_2
            'name': 'Virtual Home Staging (VAT 21)',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'list_price': 38.25,
            'standard_price': 45.5,
            'type': 'service',
            'default_code': 'VAT 21',
            'taxes_id': [(6, 0, (self.tax_21).ids)],
        })
        self.product_no_gravado = self.env['product.product'].create({
            # demo data product_product_no_gravado
            'name': 'Untaxed concepts (VAT NT)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'list_price': 40.00,
            'standard_price': 50.0,
            'type': 'consu',
            'default_code': 'NOGRAVADO',
            'taxes_id': [(6, 0, (self.tax_no_gravado).ids)],
        })
        self.product_iva_105_perc = self.product_iva_105.copy({
            # product.product_product_25
            "name": "Laptop E5023 (VAT 10,5)",
            "standard_price": 3280.0,
            # agregamos percecipn aplicada y sufrida tambien
            'taxes_id': [(6, 0, [self.tax_10_5.id, self.tax_perc_iibb.id])],
            # <field name="supplier_taxes_id" search="[('type_tax_use', '=', 'purchase'), ('tax_group_id', 'in', ['VAT 10.5%', 'Percepción IIBB', 'Percepción Ganancias', 'Percepción IVA'])]"/>
        })
        self.product_iva_exento = self.env['product.product'].create({
            # demo product_product_exento
            'name': 'Book: Development in Odoo (VAT Exempt)',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'standard_price': 100.0,
            "list_price": 80.0,
            'type': 'consu',
            'default_code': 'EXENTO',
            'taxes_id': [(6, 0, (self.tax_iva_exento).ids)],
        })

        # # Document Types
        self.document_type = {
            'invoice_a': self.env.ref('l10n_ar.dc_a_f'),
            'credit_note_a': self.env.ref('l10n_ar.dc_a_nc'),
            'invoice_b': self.env.ref('l10n_ar.dc_b_f'),
            'credit_note_b': self.env.ref('l10n_ar.dc_b_nc'),
            'invoice_e': self.env.ref('l10n_ar.dc_e_f'),
            'invoice_mipyme_a': self.env.ref('l10n_ar.dc_fce_a_f'),
            'invoice_mipyme_b': self.env.ref('l10n_ar.dc_fce_b_f'),
        }

        # ==== Journals ====
        self.sale_expo_journal_ri = self.env["account.journal"].create({
            'name': "Expo Sales Journal",
            'company_id': self.company_ri.id,
            'type': "sale",
            'code': "S0002",
            'l10n_latam_use_documents': "True",
            'l10n_ar_afip_pos_number': 2,
            'l10n_ar_afip_pos_partner_id': self.partner_ri.id,
            'l10n_ar_afip_pos_system': "FEERCEL",
            'refund_sequence': False,
        })

    def _create_test_invoices_like_demo(self):
        """ Create in the unit tests the same invoices created in demo data """
        demo_invoices = self.env['account.move']

        payment_term_id = self.env.ref("account.account_payment_term_end_following_month")
        invoice_user_id = self.env.ref("base.user_demo")
        incoterm = self.env.ref("account.incoterm_EXW")
        today = fields.Date.today()

        invoices_to_create = [{
            "ref": "demo_invoice_1: Invoice to gritti support service, vat 21",
            "partner_id": self.res_partner_gritti_mono.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": "out_invoice",
            "invoice_date": fields.Date.start_of(today),
            "company_id":  self.company_ri,
            "invoice_line_ids":  [(0, 0, {
                'product_id': self.service_iva_21.id,
                # 'price_unit': 642.0,
                # 'quantity': 1
            })],
        }, {
            "ref": "demo_invoice_2: Invoice to CMR with vat 21, 27 and 10,5",
            "partner_id": self.res_partner_cmr,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": "out_invoice",
            "invoice_date": today + relativedelta(day=5),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_105_perc.id, 'price_unit': 3245.0, 'quantity': 2}),
            ],
        }, {
            "ref": "demo_invoice_3: Invoice to ADHOC with vat cero and 21",

            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": fields.Date.start_of(today),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
                (0, 0, {'product_id': self.product_iva_cero.id, 'price_unit': 200.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_4: Invoice to ADHOC with vat exempt and 21',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": fields.Date.start_of(today),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
                (0, 0, {'product_id': self.product_iva_exento.id, 'price_unit': 100.0, 'quantity': 1}),
            ],

        }, {
            'ref': 'demo_invoice_5: Invoice to ADHOC with all type of taxes',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_105_perc.id, 'price_unit': 3245.0, 'quantity': 2}),
                (0, 0, {'product_id': self.product_no_gravado.id, 'price_unit': 50.0, 'quantity': 10}),
                (0, 0, {'product_id': self.product_iva_cero.id, 'price_unit': 200.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_exento.id, 'price_unit': 100.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_6: Invoice to cerro castor, fiscal position changes taxes to exempt',
            "partner_id": self.res_partner_cerrocastor.id,
            "journal_id": self.sale_expo_journal_ri.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=3),
            "company_id": self.company_ri,
            "invoice_incoterm_id": incoterm.id,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_105_perc.id, 'price_unit': 3245.0, 'quantity': 2}),
                (0, 0, {'product_id': self.product_no_gravado.id, 'price_unit': 50.0, 'quantity': 10}),
                (0, 0, {'product_id': self.product_iva_cero.id, 'price_unit': 200.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_exento.id, 'price_unit': 100.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_7: Export invoice to expresso, fiscal position changes tax to exempt (type 4 because it have services)',
            "partner_id": self.res_partner_expresso,
            "journal_id": self.sale_expo_journal_ri.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=3),
            "company_id": self.company_ri,
            "invoice_incoterm_id": incoterm.id,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_105_perc.id, 'price_unit': 3245.0, 'quantity': 2}),
                (0, 0, {'product_id': self.product_no_gravado.id, 'price_unit': 50.0, 'quantity': 10}),
                (0, 0, {'product_id': self.product_iva_cero.id, 'price_unit': 200.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_exento.id, 'price_unit': 100.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_8: Invoice to consumidor final',
            "partner_id": self.partner_cf.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 642.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_10; Invoice to ADHOC in USD and vat 21',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 1000.0, 'quantity': 5}),
            ],
            "currency_id": self.env.ref("base.USD"),
        }, {
            'ref': 'demo_invoice_11: Invoice to ADHOC with many lines in order to prove rounding error, with 4 decimals of precision for the currency and 2 decimals for the product the error apperar',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 1'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 2'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 3'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 1.12, 'quantity': 1, 'name': 'Support Services 4'}),
            ],
        }, {
            'ref': 'demo_invoice_12: Invoice to ADHOC with many lines in order to test rounding error, it is required to use a 4 decimal precision in prodct in order to the error occur',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 15.7076, 'quantity': 1, 'name': 'Support Services 1'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 5.3076, 'quantity': 2, 'name': 'Support Services 2'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 3.5384, 'quantity': 2, 'name': 'Support Services 3'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 1.6376, 'quantity': 2, 'name': 'Support Services 4'}),
            ],
        }, {
            'ref': 'demo_invoice_13: Invoice to ADHOC with many lines in order to test zero amount invoices y rounding error. it is required to set the product decimal precision to 4 and change 260.59 for 260.60 in order to reproduce the error',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 1'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 260.59, 'quantity': -1, 'name': 'Support Services 2'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 48.72, 'quantity': 1, 'name': 'Support Services 3'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 13.666, 'quantity': 1, 'name': 'Support Services 4'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 11.329, 'quantity': 2, 'name': 'Support Services 5'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 68.9408, 'quantity': 1, 'name': 'Support Services 6'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 4.7881, 'quantity': 2, 'name': 'Support Services 7'}),
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 12.0625, 'quantity': 2, 'name': 'Support Services 8'}),
            ],
        }, {
            'ref': 'demo_invoice_14: Export invoice to expresso, fiscal position changes tax to exempt (type 1 because only products)',
            "partner_id": self.res_partner_expresso,
            "journal_id": self.sale_expo_journal_ri.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=20),
            "company_id": self.company_ri,
            "invoice_incoterm_id": incoterm.id,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
            ],

        }, {
            'ref': 'demo_invoice_15: Export invoice to expresso, fiscal position changes tax to exempt (type 2 because only service)',
            "partner_id": self.res_partner_expresso,
            "journal_id": self.sale_expo_journal_ri.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=20),
            "company_id": self.company_ri,
            "invoice_incoterm_id": incoterm.id,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_16: Export invoice to expresso, fiscal position changes tax to exempt (type 1 because it have products only, used to test refund of expo)',
            "partner_id": self.res_partner_expresso,
            "journal_id": self.sale_expo_journal_ri.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=22),
            "company_id": self.company_ri,
            "invoice_incoterm_id": incoterm.id,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.product_iva_105.id, 'price_unit': 642.0, 'quantity': 5}),
            ],
        }, {
            'ref': 'demo_invoice_17: Invoice to ADHOC with 100% of discount',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8', 'discount': 100}),
            ],
        }, {
            'ref': 'demo_invoice_18: Invoice to ADHOC with 100% of discount and with different VAT aliquots',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8', 'discount': 100}),
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1, 'discount': 100}),
                (0, 0, {'product_id': self.product_iva_105_perc.id, 'price_unit': 3245.0, 'quantity': 1}),
            ],
        }, {
            'ref': 'demo_invoice_19: Invoice to ADHOC with multiple taxes and perceptions',
            "partner_id": self.res_partner_adhoc.id,
            "invoice_user_id": invoice_user_id.id,
            "invoice_payment_term_id": payment_term_id.id,
            "move_type": 'out_invoice',
            "invoice_date": today + relativedelta(day=13),
            "company_id": self.company_ri,
            "invoice_line_ids": [
                (0, 0, {'product_id': self.service_iva_21.id, 'price_unit': 24.3, 'quantity': 3, 'name': 'Support Services 8'}),
                (0, 0, {'product_id': self.service_iva_27.id, 'price_unit': 250.0, 'quantity': 1}),
                (0, 0, {'product_id': self.product_iva_105_perc.id, 'price_unit': 3245.0, 'quantity': 1}),
            ],
        }]

        # <function model="account.move.line" name="_onchange_product_id" context="{'check_move_validity': False}">
        #     <value model="account.move.line" eval="obj().search([('move_id', 'in', [ref('demo_invoice_1'), ref('demo_invoice_2'), ref('demo_invoice_3'), ref('demo_invoice_4'), ref('demo_invoice_5'), ref('demo_invoice_6'), ref('demo_invoice_7'), ref('demo_invoice_8'), ref('demo_invoice_10'), ref('demo_invoice_11'), ref('demo_invoice_12'), ref('demo_invoice_13'), ref('demo_invoice_14'), ref('demo_invoice_15'), ref('demo_invoice_16'), ref('demo_invoice_17'), ref('demo_invoice_18'), ref('demo_invoice_19')])]).ids"/>
        # </function>

        # <function model="account.move" name="_onchange_partner_id" context="{'check_move_validity': False}">
        #     <value[ref('demo_invoice_6')],
        #     <value[ref('demo_invoice_7')],
        #     <value[ref('demo_invoice_14')],
        #     <value[ref('demo_invoice_15')],
        #     <value[ref('demo_invoice_16')],
        # </function>

        # <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
        #     <value model="account.move.line" search="[('move_id', '=', ref('demo_invoice_19')), ('product_id', '=', self.service_iva_21.id)],
        #     <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'sale'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '06')], limit=1).id)]}"/>
        # </function>

        # <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
        #     <value model="account.move.line" search="[('move_id', '=', ref('demo_invoice_19')), ('product_id', '=', self.service_iva_27.id)],
        #     <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'sale'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '07')], limit=1).id)]}"/>
        # </function>

        # <function model="account.move.line" name="write" context="{'check_move_validity': False, 'active_test': False}">
        #     <value model="account.move.line" search="[('move_id', '=', ref('demo_invoice_19')), ('product_id', '=', self.product_iva_105_perc.id)],
        #     <value model="account.tax" eval="{'tax_ids': [(4, obj().search([('company_id', '=', ref('company_ri')), ('type_tax_use', '=', 'sale'), ('tax_group_id.l10n_ar_tribute_afip_code', '=', '99')], limit=1).id)]}"/>
        # </function>

        # <function model="account.move" name="_recompute_dynamic_lines" context="{'check_move_validity': False}">
        #     <value[ref('demo_invoice_1'), ref('demo_invoice_2'), ref('demo_invoice_3'), ref('demo_invoice_4'), ref('demo_invoice_5'), ref('demo_invoice_6'), ref('demo_invoice_7'), ref('demo_invoice_8'), ref('demo_invoice_10'), ref('demo_invoice_11'), ref('demo_invoice_12'), ref('demo_invoice_13'), ref('demo_invoice_14'), ref('demo_invoice_15'), ref('demo_invoice_16'), ref('demo_invoice_17'), ref('demo_invoice_18'), ref('demo_invoice_19')],
        #     <value eval="True"/>
        # </function>

        for values in invoices_to_create:
            temp = demo_invoices.create(values)
            temp.action_post()
            demo_invoices += temp

        self.demo_invoices = demo_invoices

    # Re used unit tests methods

    # TODO improve used to set the values easier
    def _test_demo_cases(self, cases):
        for xml_id, test_case in cases.items():
            _logger.info('  * running test %s: %s' % (xml_id, test_case))
            invoice = self._duplicate_demo_invoice(xml_id)
            self._edi_validate_and_review(invoice, error_msg=test_case)

    def _duplicate_demo_invoice(self, xml_id):
        demo_invoice = self.env.ref('l10n_ar.' + xml_id)
        invoice = demo_invoice.copy({'journal_id': self.journal.id})
        invoice._onchange_partner_journal()
        invoice._onchange_partner_id()
        return invoice

    # Helpers

    def _get_afip_pos_system_real_name(self):
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
                  'l10n_ar_afip_pos_partner_id': self.partner_ri.id}
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
