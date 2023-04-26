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
        # This is a generator because data created here might be referenced by xml_id to data
        # created later but defined in this same function.
        self._get_demo_data_products(company)
        return {
            'account.move': self._get_demo_data_move(company),
            'account.bank.statement': self._get_demo_data_statement(company),
            'account.bank.statement.line': self._get_demo_data_transactions(company),
            'account.reconcile.model': self._get_demo_data_reconcile_model(company),
            'ir.attachment': self._get_demo_data_attachment(company),
            'mail.message': self._get_demo_data_mail_message(company),
            'mail.activity': self._get_demo_data_mail_activity(company),
        }

    def _post_load_demo_data(self, company=False):
        invoices = (
            self.ref('demo_invoice_1')
            + self.ref('demo_invoice_2')
            + self.ref('demo_invoice_3')
            + self.ref('demo_invoice_followup')
            + self.ref('demo_invoice_5')
            + self.ref('demo_invoice_equipment_purchase')
        ).with_context(check_move_validity=False)

        # the invoice_extract acts like a placeholder for the OCR to be ran and doesn't contain
        # any lines yet
        for move in invoices:
            try:
                move.action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting demo data')

    @api.model
    def _get_demo_data_products(self, company=False):
        prod_templates = self.env['product.product'].search(['|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)])
        if self.env.company.account_sale_tax_id:
            prod_templates.write({'taxes_id': [Command.link(self.env.company.account_sale_tax_id.id)]})
        if self.env.company.account_purchase_tax_id:
            prod_templates.write({'supplier_taxes_id': [Command.link(self.env.company.account_purchase_tax_id.id)]})

    @api.model
    def _get_demo_data_move(self, company=False):
        fifteen_months_ago = fields.Date.today() + relativedelta(months=-15)
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
                'invoice_date': time.strftime('%Y-%m-08'),
                'delivery_date': time.strftime('%Y-%m-08'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 20}),
                ],
            },
            'demo_invoice_3': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_2',
                'invoice_user_id': False,
                'invoice_date': time.strftime('%Y-%m-08'),
                'delivery_date': time.strftime('%Y-%m-08'),
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
            },
        }

    @api.model
    def _get_demo_data_statement(self, company=False):
        cid = company.id or self.env.company.id
        bnk_journal = self.env['account.journal'].search(
            domain=[('type', '=', 'bank'), ('company_id', '=', cid)],
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
            domain=[('type', '=', 'bank'), ('company_id', '=', cid)],
            limit=1,
        )
        return {
            'demo_bank_statement_line_0': {
                'journal_id': bnk_journal.id,
                'payment_ref': 'Bank Fees',
                'amount': -32.58,
                'date': time.strftime('%Y-01-01'),
            },
            'demo_bank_statement_line_1': {
                'journal_id': bnk_journal.id,
                'payment_ref': 'Prepayment',
                'amount': 650,
                'date': time.strftime('%Y-01-01'),
                'partner_id': 'base.res_partner_12',
            },
            'demo_bank_statement_line_2': {
                'journal_id': bnk_journal.id,
                'payment_ref': time.strftime(f'First {formatLang(self.env, 2000, currency_obj=self.env.company.currency_id)} of invoice %Y/00001'),
                'amount': 2000,
                'date': time.strftime('%Y-01-01'),
                'partner_id': 'base.res_partner_12',
            },
            'demo_bank_statement_line_3': {
                'journal_id': bnk_journal.id,
                'payment_ref': 'Last Year Interests',
                'amount': 102.78,
                'date': time.strftime('%Y-01-01'),
            },
            'demo_bank_statement_line_4': {
                'journal_id': bnk_journal.id,
                'payment_ref': time.strftime('INV/%Y/00002'),
                'amount': 750,
                'date': time.strftime('%Y-01-01'),
                'partner_id': 'base.res_partner_2',
            },
            'demo_bank_statement_line_5': {
                'journal_id': bnk_journal.id,
                'payment_ref': f'R:9772938  10/07 AX 9415116318 T:5 BRT: {formatLang(self.env, 100.0, digits=2)} C/ croip',
                'amount': 96.67,
                'date': time.strftime('%Y-01-01'),
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
            or self.env['account.account'].search([
                ('account_type', '=', account_type),
                ('company_id', '=', company.id)
            ], limit=1)
            or self.env['account.account'].search([('company_id', '=', company.id)], limit=1)
        )
