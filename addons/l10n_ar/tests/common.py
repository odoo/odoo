# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import Form
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
import random
import logging
import time

_logger = logging.getLogger(__name__)


class TestAr(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(self, chart_template_ref='l10n_ar.l10nar_ri_chart_template'):
        super(TestAr, self).setUpClass(chart_template_ref=chart_template_ref)

        print(" ------ Common.TestAr setUpClass()")
        # ==== Company ====
        self.company_data['company'].write({
            'parent_id': self.env.ref('base.main_company').id,
            'currency_id': self.env.ref('base.ARS').id,
            'name': '(AR) Responsable Inscripto (Unit Tests)',
            "l10n_ar_afip_start_date":  time.strftime('%Y-01-01'),
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

        # ==== Partners for testing ====
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
            'l10n_ar_afip_responsibility_type_id':  self.env.ref("l10n_ar.res_IVARI").id,
        })

        self.partner_cf = self.env['res.partner'].create({
            "id": 'par_cfa',
            "name": "Consumidor Final Anónimo",
            "l10n_latam_identification_type_id": self.env.ref('l10n_ar.it_Sigd').id,
            "l10n_ar_afip_responsibility_type_id": self.env.ref("l10n_ar.res_CF").id,
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
            'l10n_ar_afip_responsibility_type_id':  self.env.ref("l10n_ar.res_IVA_LIB").id,
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
            'l10n_ar_afip_responsibility_type_id':  self.env.ref("l10n_ar.res_IVARI").id,
        })

        self.partner_mipyme_ex = self.partner_mipyme.copy({'name': 'MiPyme Exento', 'l10n_ar_afip_responsibility_type_id': self.env.ref('l10n_ar.res_IVAE').id})

        # ==== Taxes ====
        self.tax_21 = self._search_tax(self, 'iva_21')
        self.tax_27 = self._search_tax(self, 'iva_27')

        # ==== Products ====
        self.product_iva_21 = self.env['product.product'].create({
            'name': 'Large Cabinet (VAT 21)',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 320.0,
            'standard_price': 800.0,
            'type': "consu",
            'default_code': 'E-COM07',
            # 'property_account_income_id': self.company_data['default_account_revenue'].id,
            # 'property_account_expense_id': self.company_data['default_account_expense'].id,
        })

        self.service_iva_27 = self.env['product.product'].create({
            'name': 'Telephone service (VAT 27)',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
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
