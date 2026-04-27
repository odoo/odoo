from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class SDDTestCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.EUR').active = True

        cls.env.user.write({
            'email': "ruben.rybnik@sorcerersfortress.com",
            'groups_id': [Command.link(cls.env.ref('account.group_validate_bank_account').id)]
        })

        cls.country_belgium, cls.country_china, cls.country_germany = cls.env['res.country'].search([('code', 'in', ['BE', 'CN', 'DE'])], limit=3, order='name ASC')

        # We setup our test company
        cls.sdd_company = cls.env.company
        cls.sdd_company.country_id = cls.country_belgium
        cls.sdd_company.city = 'Company 1 City'
        cls.sdd_company.sdd_creditor_identifier = 'BE30ZZZ300D000000042'
        cls.sdd_company_bank_journal = cls.company_data['default_journal_bank']
        cls.sdd_company_bank_journal.bank_acc_number = 'CH9300762011623852957'
        cls.bank_ing = cls.env['res.bank'].create({'name': 'ING', 'bic': 'BBRUBEBB'})
        cls.bank_bnp = cls.env['res.bank'].create({'name': 'BNP Paribas', 'bic': 'GEBABEBB'})
        cls.bank_no_bic = cls.env['res.bank'].create({'name': 'NO BIC BANK'})
        cls.sdd_company_bank_journal.bank_account_id.bank_id = cls.bank_ing
        sdd_method_line = cls.sdd_company_bank_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'sdd')
        sdd_method_line.payment_account_id = cls.inbound_payment_method_line.payment_account_id

        # Then we setup the banking data and mandates of two customers (one with a one-off mandate, the other with a recurrent one)
        cls.partner_agrolait = cls.env['res.partner'].create({'name': 'Agrolait', 'city': 'Agrolait Town', 'country_id': cls.country_germany.id})
        cls.partner_bank_agrolait = cls.create_account('DE44500105175407324931', cls.partner_agrolait, cls.bank_ing)
        cls.mandate_agrolait = cls.create_mandate(cls.partner_agrolait, cls.partner_bank_agrolait, False, cls.sdd_company)
        cls.mandate_agrolait.action_validate_mandate()

        cls.partner_china_export = cls.env['res.partner'].create({'name': 'China Export', 'city': 'China Town', 'country_id': cls.country_china.id})
        cls.partner_bank_china_export = cls.create_account('SA0380000000608010167519', cls.partner_china_export, cls.bank_bnp)
        cls.mandate_china_export = cls.create_mandate(cls.partner_china_export, cls.partner_bank_china_export, True, cls.sdd_company)
        cls.mandate_china_export.action_validate_mandate()

        cls.partner_no_bic = cls.env['res.partner'].create({'name': 'NO BIC Co', 'city': 'NO BIC City', 'country_id': cls.country_belgium.id})
        cls.partner_bank_no_bic = cls.create_account('BE68844010370034', cls.partner_no_bic, cls.bank_no_bic)
        cls.mandate_no_bic = cls.create_mandate(cls.partner_no_bic, cls.partner_bank_no_bic, True, cls.sdd_company)
        cls.mandate_no_bic.action_validate_mandate()

        # Finally, we create one invoice for each of our test customers ...
        cls.invoice_agrolait = cls.create_invoice(cls.partner_agrolait)
        cls.invoice_china_export = cls.create_invoice(cls.partner_china_export)
        cls.invoice_no_bic = cls.create_invoice(cls.partner_no_bic)

        # Pay the invoices with mandates
        cls.pay_with_mandate(cls.invoice_agrolait)
        cls.pay_with_mandate(cls.invoice_china_export)
        cls.pay_with_mandate(cls.invoice_no_bic)

    @classmethod
    def create_account(cls, number, partner, bank):
        return cls.env['res.partner.bank'].create({
            'acc_number': number,
            'partner_id': partner.id,
            'bank_id': bank.id
        })

    @classmethod
    def create_mandate(cls, partner, partner_bank, one_off=False, company=None, scheme='CORE'):
        company = company or cls.env.company
        return cls.env['sdd.mandate'].create({
            'partner_bank_id': partner_bank.id,
            'one_off': one_off,
            'start_date': fields.Date.today(),
            'partner_id': partner.id,
            'company_id': company.id,
            'sdd_scheme': scheme,
        })

    @classmethod
    def create_invoice(cls, partner):
        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'currency_id': cls.env.ref('base.EUR').id,
            'payment_reference': 'invoice to client',
            'invoice_line_ids': [Command.create({
                'product_id': cls.env['product.product'].create({'name': 'A Test Product'}).id,
                'quantity': 1,
                'price_unit': 42,
                'name': 'something',
            })],
        })
        invoice.action_post()
        return invoice

    @classmethod
    def pay_with_mandate(cls, invoice):
        journal = cls.company_data['default_journal_bank']
        sdd_method_line = journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'sdd')
        return cls.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.invoice_date_due or invoice.invoice_date,
            'journal_id': journal.id,
            'payment_method_line_id': sdd_method_line.id,
        })._create_payments()

    @classmethod
    def reconcile_payments(cls, payments):
        for payment in payments:
            st_line = cls.env['account.bank.statement.line'].create({
                'amount': payment.amount,
                'date': fields.Date.context_today(payment.sdd_mandate_id),
                'payment_ref': 'test',
                'journal_id': cls.company_data['default_journal_bank'].id,
            })
            st_suspense_lines = st_line._seek_for_lines()[1]
            liquidity_line = payment._seek_for_lines()[0]
            st_suspense_lines.account_id = liquidity_line.account_id
            (st_suspense_lines + liquidity_line).reconcile()
