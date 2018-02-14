# coding: utf-8
from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestDummyInvoice(AccountingTestCase):
    def setUp(self):
        super(TestDummyInvoice, self).setUp()
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.tax_model = self.env['account.tax']
        self.partner_agrolait = self.env.ref("base.res_partner_2")
        self.product = self.env.ref("product.product_product_3")
        self.company = self.env.user.company_id
        self.account_settings = self.env['account.config.settings']
        self.fiscal_position_model = self.env['account.fiscal.position']
        self.fiscal_position = self.fiscal_position_model.create({
            'name': 'Personas morales del régimen general'})
        self.account_payment = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
        })
        self.rate_model = self.env['res.currency.rate']
        self.mxn = self.env.ref('base.MXN')
        self.usd = self.env.ref('base.USD')
        self.ova = self.env['account.account'].search([
            ('user_type_id', '=', self.env.ref(
                'account.data_account_type_current_assets').id)], limit=1)

    def create_invoice(self, inv_type='out_invoice', currency_id=None):
        if currency_id is None:
            currency_id = self.usd.id
        invoice = self.invoice_model.create({
            'partner_id': self.partner_agrolait.id,
            'type': inv_type,
            'currency_id': currency_id,
        })
        self.create_invoice_line(invoice)
        invoice.compute_taxes()
        return invoice

    def create_invoice_line(self, invoice_id):
        invoice_line = self.invoice_line_model.new({
            'product_id': self.product.id,
            'invoice_id': invoice_id,
            'quantity': 1,
        })
        invoice_line._onchange_product_id()
        invoice_line_dict = invoice_line._convert_to_write({
            name: invoice_line[name] for name in invoice_line._cache})
        invoice_line_dict['price_unit'] = 450
        self.invoice_line_model.create(invoice_line_dict)

    def l10n_mx_edi_get_attachment(self, invoice):
        self.mail_obj = self.env['mail.compose.message']
        self.att_obj = self.env['ir.attachment']
        data_mail = invoice.action_invoice_sent()
        context = data_mail.get('context', {})
        tmp_id = context.get('default_template_id', '')
        wizard_mail = self.mail_obj.with_context(context).create({})
        res = wizard_mail.onchange_template_id(
            tmp_id, wizard_mail.composition_mode, 'account_invoice',
            invoice.id)
        wizard_mail.write({
            'attachment_ids': res.get('value', {}).get('attachment_ids', [])})
        wizard_mail.send_mail()
        attachment = self.att_obj.search([
            ('res_id', '=', invoice.id),
            ('res_model', '=', 'account.invoice'),
            ('name', '=', '%s%s.pdf' % ('INV', invoice.number.replace(
                '/', '')))], limit=1)
        return attachment

    def test_generate_dummy_invoice(self):
        invoice = self.create_invoice()
        invoice.action_invoice_open()
        attachment = self.l10n_mx_edi_get_attachment(invoice)
        self.assertTrue(attachment)
