# -*- coding: utf-8 -*-
import logging
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command
from odoo.tools.misc import file_open, formatLang
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        """Generate the demo data related to accounting."""
        return {
            **self._get_demo_data_products(company),
            'account.move': self._get_demo_data_move(company),
            'account.bank.statement': self._get_demo_data_statement(company),
            'account.bank.statement.line': self._get_demo_data_transactions(company),
            'account.reconcile.model': self._get_demo_data_reconcile_model(company),
            'ir.attachment': self._get_demo_data_attachment(company),
            'mail.message': self._get_demo_data_mail_message(company),
            'mail.activity': self._get_demo_data_mail_activity(company),
            'res.partner.bank': self._get_demo_data_bank(company),
            'account.journal': self._get_demo_data_journal(company),
        }

    def _get_demo_exception_product_template_xml_ids(self):
        """ Return demo product template xml ids to not put taxes on"""
        return []

    def _get_demo_exception_product_variant_xml_ids(self):
        """ Return demo product variant xml ids to not put taxes on"""
        return ['product.office_combo']

    def _get_demo_data_products(self, company):
        # Only needed for the first company
        if company != self.env.ref('base.main_company', raise_if_not_found=False):
            return {}

        taxes = {}
        if company.account_sale_tax_id:
            taxes.update({'taxes_id': [Command.link(company.account_sale_tax_id.id)]})
        if company.account_purchase_tax_id:
            taxes.update({'supplier_taxes_id': [Command.link(company.account_purchase_tax_id.id)]})
        if not taxes:
            return {}
        IMD = self.env['ir.model.data'].sudo()
        product_templates = sorted(
            set(IMD.search([('model', '=', 'product.template')]).mapped('complete_name'))
            - set(self._get_demo_exception_product_template_xml_ids())
        )
        product_variants = sorted(
            set(IMD.search([('model', '=', 'product.product')]).mapped('complete_name'))
            - set(self._get_demo_exception_product_variant_xml_ids())
        )
        return {
            'product.template': {d: taxes for d in product_templates},
            'product.product': {d: taxes for d in product_variants},
        }

    def _post_load_demo_data(self, company=False):
        invoices = (
            self.ref('demo_invoice_1')
            + self.ref('demo_invoice_2')
            + self.ref('demo_invoice_3')
            + self.ref('demo_invoice_followup')
            + self.ref('demo_invoice_5')
            + self.ref('demo_invoice_equipment_purchase')
            + self.ref('demo_move_auto_reconcile_1')
            + self.ref('demo_move_auto_reconcile_2')
            + self.ref('demo_move_auto_reconcile_3')
            + self.ref('demo_move_auto_reconcile_4')
            + self.ref('demo_move_auto_reconcile_5')
            + self.ref('demo_move_auto_reconcile_6')
            + self.ref('demo_move_auto_reconcile_7')
            + self.ref('demo_move_auto_reconcile_8')
            + self.ref('demo_move_auto_reconcile_9')
        )

        # the invoice_extract acts like a placeholder for the OCR to be ran and doesn't contain
        # any lines yet
        for move in invoices:
            try:
                move.action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting demo data')

    @api.model
    def _get_demo_data_bank(self, company=False):
        if company.root_id.partner_id.bank_ids:
            return {}
        return {
            'demo_bank_1': {
                'acc_number': f'BANK{company.id}34567890',
                'partner_id': company.root_id.partner_id.id,
                'journal_id': 'bank',
            },
        }

    @api.model
    def _get_demo_data_journal(self, company=False):
        if company.partner_id.bank_ids:
            # if a bank is created in xml, link it to the journal
            return {
                'bank': {
                    'bank_account_id': company.partner_id.bank_ids[0].id,
                }
            }
        return {}

    @api.model
    def _get_demo_data_move(self, company=False):
        one_month_ago = fields.Date.today() + relativedelta(months=-1)
        fifteen_months_ago = fields.Date.today() + relativedelta(months=-15)
        cid = company.id or self.env.company.id
        misc_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'general'),
            ],
            limit=1,
        )
        bank_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'bank'),
            ],
            limit=1,
        )
        default_receivable = self.env.ref('base.res_partner_3').with_company(company or self.env.company).property_account_receivable_id
        income_account = self.env['account.account'].with_company(company or self.env.company).search([
            *self.env['account.account']._check_company_domain(cid),
            ('account_type', '=', 'income'),
            ('id', '!=', (company or self.env.company).account_journal_early_pay_discount_gain_account_id.id)
        ], limit=1)
        return {
            'demo_invoice_1': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_12',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-01'),
                'delivery_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                ],
            },
            'demo_invoice_2': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_2',
                'invoice_user_id': False,
                'invoice_date': (fields.Date.today() + timedelta(days=-2)).strftime('%Y-%m-%d'),
                'delivery_date': (fields.Date.today() + timedelta(days=-2)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 20}),
                ],
            },
            'demo_invoice_3': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_2',
                'invoice_user_id': False,
                'invoice_date': (fields.Date.today() + timedelta(days=-3)).strftime('%Y-%m-%d'),
                'delivery_date': (fields.Date.today() + timedelta(days=-3)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                ],
            },
            'demo_invoice_followup': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_2',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_immediate',
                'invoice_date': (fields.Date.today() + timedelta(days=-15)).strftime('%Y-%m-%d'),
                'delivery_date': (fields.Date.today() + timedelta(days=-15)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                ],
            },
            'demo_invoice_5': {
                'move_type': 'in_invoice',
                'partner_id': 'base.res_partner_12',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-01'),
                'delivery_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_delivery_01', 'price_unit': 10.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_order_01', 'price_unit': 4.0, 'quantity': 5}),
                ],
            },
            'demo_invoice_extract': {
                'move_type': 'in_invoice',
                'message_main_attachment_id': 'ir_attachment_in_invoice_1',
            },
            'demo_invoice_equipment_purchase': {
                'move_type': 'in_invoice',
                'ref': f'INV/{fifteen_months_ago.year}/0057',
                'partner_id': 'base.res_partner_12',
                'invoice_user_id': False,
                'invoice_date': fifteen_months_ago.strftime("%Y-%m-17"),
                'delivery_date': fifteen_months_ago.strftime("%Y-%m-17"),
                'invoice_line_ids': [
                    Command.create({'name': 'Redeem Reference Number: PO02529', 'quantity': 1, 'price_unit': 541.10,
                                    'tax_ids': self.env.company.account_purchase_tax_id.ids}),
                ],
                'message_main_attachment_id': 'ir_attachment_in_invoice_2',
            },
            'demo_move_auto_reconcile_1': {
                'move_type': 'out_refund',
                'partner_id': 'base.res_partner_12',
                'invoice_date': one_month_ago.strftime("%Y-%m-02"),
                'delivery_date': one_month_ago.strftime("%Y-%m-02"),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                ],
            },
            'demo_move_auto_reconcile_2': {
                'move_type': 'out_refund',
                'partner_id': 'base.res_partner_12',
                'invoice_date': one_month_ago.strftime("%Y-%m-03"),
                'delivery_date': one_month_ago.strftime("%Y-%m-03"),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5}),
                ],
            },
            'demo_move_auto_reconcile_3': {
                'move_type': 'in_refund',
                'partner_id': 'base.res_partner_12',
                'invoice_date': time.strftime('%Y-%m-01'),
                'delivery_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_delivery_01', 'price_unit': 10.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_order_01', 'price_unit': 4.0, 'quantity': 5}),
                ],
            },
            'demo_move_auto_reconcile_4': {
                'move_type': 'in_refund',
                'partner_id': 'base.res_partner_12',
                'invoice_date': fifteen_months_ago.strftime("%Y-%m-19"),
                'delivery_date': fifteen_months_ago.strftime("%Y-%m-19"),
                'invoice_line_ids': [
                    Command.create({'name': 'Redeem Reference Number: PO02529', 'quantity': 1, 'price_unit': 541.10,
                                    'tax_ids': self.env.company.account_purchase_tax_id.ids}),
                ],
            },
            'demo_move_auto_reconcile_5': {
                'move_type': 'out_refund',
                'partner_id': 'base.res_partner_2',
                'invoice_date': (fields.Date.today() + timedelta(days=-10)).strftime('%Y-%m-%d'),
                'delivery_date': (fields.Date.today() + timedelta(days=-10)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                ],
            },
            'demo_move_auto_reconcile_6': {
                'move_type': 'out_refund',
                'partner_id': 'base.res_partner_2',
                'invoice_user_id': False,
                'invoice_date': (fields.Date.today() + timedelta(days=-1)).strftime('%Y-%m-%d'),
                'delivery_date': (fields.Date.today() + timedelta(days=-1)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 20}),
                ],
            },
            'demo_move_auto_reconcile_7': {
                'move_type': 'out_refund',
                'partner_id': 'base.res_partner_2',
                'invoice_date': (fields.Date.today() + timedelta(days=-2)).strftime('%Y-%m-%d'),
                'delivery_date': (fields.Date.today() + timedelta(days=-2)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                ],
            },
            'demo_move_auto_reconcile_8': {
                'move_type': 'entry',
                'partner_id': 'base.res_partner_2',
                'date': (fields.Date.today() + timedelta(days=-20)).strftime('%Y-%m-%d'),
                'journal_id': misc_journal.id,
                'line_ids': [
                    Command.create({'debit': 0.0, 'credit': 2500.0, 'account_id': default_receivable.id}),
                    Command.create({'debit': 2500.0, 'credit': 0.0, 'account_id': bank_journal.default_account_id.id}),
                ],
            },
            'demo_move_auto_reconcile_9': {
                'move_type': 'entry',
                'partner_id': 'base.res_partner_2',
                'date': (fields.Date.today() + timedelta(days=-20)).strftime('%Y-%m-%d'),
                'journal_id': misc_journal.id,
                'line_ids': [
                    Command.create({'debit': 2500.0, 'credit': 0.0, 'account_id': default_receivable.id}),
                    Command.create({'debit': 0.0, 'credit': 2500.0, 'account_id': income_account.id}),
                ],
            },
        }

    @api.model
    def _get_demo_data_statement(self, company=False):
        cid = company.id or self.env.company.id
        bnk_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'bank'),
            ],
            limit=1,
        )
        return {
            'demo_bank_statement_1': {
                'name': f'{bnk_journal.name} - {time.strftime("%Y")}-01-01/1',
                'balance_end_real': 6378.0,
                'balance_start': 0.0,
                'line_ids': [
                    Command.create({
                        'journal_id': bnk_journal.id,
                        'payment_ref': 'Initial balance',
                        'amount': 5103.0,
                        'date': time.strftime('%Y-01-01'),
                    }),
                    Command.create({
                        'journal_id': bnk_journal.id,
                        'payment_ref': time.strftime('INV/%Y/00002 and INV/%Y/00003'),
                        'amount': 1275.0,
                        'date': time.strftime('%Y-01-01'),
                        'partner_id': 'base.res_partner_12',
                    }),
                ]
            },
        }

    @api.model
    def _get_demo_data_transactions(self, company=False):
        cid = company.id or self.env.company.id
        bnk_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'bank'),
            ],
            limit=1,
        )
        return {
            'demo_bank_statement_line_0': {
                'journal_id': bnk_journal.id,
                'payment_ref': 'Bank Fees',
                'amount': -32.58,
            },
            'demo_bank_statement_line_1': {
                'journal_id': bnk_journal.id,
                'payment_ref': 'Prepayment',
                'amount': 650,
                'partner_id': 'base.res_partner_12',
            },
            'demo_bank_statement_line_2': {
                'journal_id': bnk_journal.id,
                'payment_ref': time.strftime(f'First {formatLang(self.env, 2000, currency_obj=self.env.company.currency_id)} of invoice %Y/00001'),
                'amount': 2000,
                'partner_id': 'base.res_partner_12',
            },
            'demo_bank_statement_line_3': {
                'journal_id': bnk_journal.id,
                'payment_ref': 'Last Year Interests',
                'amount': 102.78,
            },
            'demo_bank_statement_line_4': {
                'journal_id': bnk_journal.id,
                'payment_ref': time.strftime('INV/%Y/00002'),
                'amount': 750,
                'partner_id': 'base.res_partner_2',
            },
            'demo_bank_statement_line_5': {
                'journal_id': bnk_journal.id,
                'payment_ref': f'R:9772938  10/07 AX 9415116318 T:5 BRT: {formatLang(self.env, 100.0, digits=2)} C/ croip',
                'amount': 96.67,
            },
        }

    @api.model
    def _get_demo_data_reconcile_model(self, company=False):
        return {
            'reconcile_from_label': {
                'name': 'Line with Bank Fees',
                'rule_type': 'writeoff_suggestion',
                'match_label': 'contains',
                'match_label_param': 'BRT',
                'line_ids': [
                    Command.create({
                        'label': 'Due amount',
                        'account_id': self._get_demo_account(
                            'income',
                            'income',
                            self.env.company,
                        ).id,
                        'amount_type': 'regex',
                        'amount_string': r'BRT: ([\d,.]+)',
                    }),
                    Command.create({
                        'label': 'Bank Fees',
                        'account_id': self._get_demo_account(
                            'cost_of_goods_sold',
                            'expense_direct_cost',
                            self.env.company,
                        ).id,
                        'amount_type': 'percentage',
                        'amount_string': '100',
                    }),
                ]
            },
        }

    @api.model
    def _get_demo_data_attachment(self, company=False):
        return {
            'ir_attachment_in_invoice_1': {
                'type': 'binary',
                'name': 'in_invoice_yourcompany_demo.pdf',
                'res_model': 'account.move',
                'res_id': 'demo_invoice_extract',
                'raw': file_open(
                    'account/static/demo/in_invoice_yourcompany_demo_1.pdf', 'rb'
                ).read()
            },
            'ir_attachment_in_invoice_2': {
                'type': 'binary',
                'name': 'in_invoice_yourcompany_demo.pdf',
                'res_model': 'account.move',
                'res_id': 'demo_invoice_equipment_purchase',
                'raw': file_open(
                    'account/static/demo/in_invoice_yourcompany_demo_2.pdf', 'rb'
                ).read()
            },
        }

    @api.model
    def _get_demo_data_mail_message(self, company=False):
        return {
            'mail_message_in_invoice_1': {
                'model': 'account.move',
                'res_id': 'demo_invoice_extract',
                'body': 'Vendor Bill attachment',
                'message_type': 'comment',
                'author_id': 'base.partner_demo',
                'attachment_ids': [Command.set([
                    'ir_attachment_in_invoice_1',
                ])]
            },
            'mail_message_in_invoice_2': {
                'model': 'account.move',
                'res_id': 'demo_invoice_equipment_purchase',
                'body': 'Vendor Bill attachment',
                'message_type': 'comment',
                'author_id': 'base.partner_demo',
                'attachment_ids': [Command.set([
                    'ir_attachment_in_invoice_2',
                ])]
            },
        }

    @api.model
    def _get_demo_data_mail_activity(self, company=False):
        return {
            'invoice_activity_1': {
                'res_id': 'demo_invoice_3',
                'res_model_id': 'account.model_account_move',
                'activity_type_id': 'mail.mail_activity_data_todo',
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'summary': 'Follow-up on payment',
                'create_uid': 'base.user_admin',
                'user_id': 'base.user_admin',
            },
            'invoice_activity_2': {
                'res_id': 'demo_invoice_2',
                'res_model_id': 'account.model_account_move',
                'activity_type_id': 'mail.mail_activity_data_call',
                'date_deadline': fields.Datetime.today().strftime('%Y-%m-%d %H:%M'),
                'create_uid': 'base.user_admin',
                'user_id': 'base.user_admin',
            },
            'invoice_activity_3': {
                'res_id': 'demo_invoice_1',
                'res_model_id': 'account.model_account_move',
                'activity_type_id': 'mail.mail_activity_data_todo',
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'summary': 'Include upsell',
                'create_uid': 'base.user_admin',
                'user_id': 'base.user_admin',
            },
            'invoice_activity_4': {
                'res_id': 'demo_invoice_extract',
                'res_model_id': 'account.model_account_move',
                'activity_type_id': 'mail.mail_activity_data_todo',
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'summary': 'Update address',
                'create_uid': 'base.user_admin',
                'user_id': 'base.user_admin',
            },
        }

    @api.model
    def _get_demo_account(self, xml_id, account_type, company):
        """Find the most appropriate account possible for demo data creation.

        :param xml_id (str): the xml_id of the account template in the generic coa
        :param account_type (str): the full xml_id of the account type wanted
        :param company (Model<res.company>): the company for which we search the account
        :return (Model<account.account>): the most appropriate record found
        """
        return (
            self.env['account.account'].browse(self.env['ir.model.data'].sudo().search([
                ('name', '=', '%d_%s' % (company.id, xml_id)),
                ('model', '=', 'account.account'),
                ('module', '=like', 'l10n%')
            ], limit=1).res_id)
            or self.env['account.account'].with_company(company).search([
                *self.env['account.account']._check_company_domain(company),
                ('account_type', '=', account_type),
            ], limit=1)
            or self.env['account.account'].with_company(company).search([
                *self.env['account.account']._check_company_domain(company),
            ], limit=1)
        )
