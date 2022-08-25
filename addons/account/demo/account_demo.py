# -*- coding: utf-8 -*-
import logging
import time
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import file_open, formatLang

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self):
        """Generate the demo data related to accounting."""
        # This is a generator because data created here might be referenced by xml_id to data
        # created later but defined in this same function.
        yield self._get_demo_data_move()
        yield self._get_demo_data_statement()
        yield self._get_demo_data_reconcile_model()
        yield self._get_demo_data_attachment()
        yield self._get_demo_data_mail_message()
        yield self._get_demo_data_mail_activity()

    @api.model
    def _get_demo_data_move(self):
        cid = self.env.company.id
        ref = self.env.ref
        return ('account.move', {
            f'{cid}_demo_invoice_1': {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_02').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 5}),
                ],
            },
            f'{cid}_demo_invoice_2': {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': False,
                'invoice_date': time.strftime('%Y-%m-08'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.consu_delivery_01').id, 'quantity': 20}),
                ],
            },
            f'{cid}_demo_invoice_3': {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': False,
                'invoice_date': time.strftime('%Y-%m-08'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_01').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 5}),
                ],
            },
            f'{cid}_demo_invoice_followup': {
                'move_type': 'out_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_immediate').id,
                'invoice_date': (fields.Date.today() + timedelta(days=-15)).strftime('%Y-%m-%d'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_02').id, 'quantity': 5}),
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 5}),
                ],
            },
            f'{cid}_demo_invoice_5': {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 10.0, 'quantity': 1}),
                    Command.create({'product_id': ref('product.product_order_01').id, 'price_unit': 4.0, 'quantity': 5}),
                ],
            },
            f'{cid}_demo_invoice_extract': {
                'move_type': 'in_invoice',
                'invoice_user_id': ref('base.user_demo').id,
            },
            f'{cid}_demo_invoice_equipment_purchase': {
                'move_type': 'in_invoice',
                'ref': 'INV/2018/0057',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': False,
                'invoice_date': '2018-09-17',
                'invoice_line_ids': [
                    Command.create({'name': 'Redeem Reference Number: PO02529', 'quantity': 1, 'price_unit': 541.10}),
                ],
            },
        })

    @api.model
    def _get_demo_data_statement(self):
        cid = self.env.company.id
        ref = self.env.ref
        return ('account.bank.statement', {
            f'{cid}_demo_bank_statement_1': {
                'journal_id': self.env['account.journal'].search([
                    ('type', '=', 'bank'),
                    ('company_id', '=', cid),
                ], limit=1).id,
                'date': time.strftime('%Y')+'-01-01',
                'balance_end_real': 9944.87,
                'balance_start': 5103.0,
                'line_ids': [
                    Command.create({
                        'payment_ref': time.strftime('INV/%Y/00002 and INV/%Y/00003'),
                        'amount': 1275.0,
                        'date': time.strftime('%Y-01-01'),
                        'partner_id': ref('base.res_partner_12').id
                    }),
                    Command.create({
                        'payment_ref': 'Bank Fees',
                        'amount': -32.58,
                        'date': time.strftime('%Y-01-01'),
                    }),
                    Command.create({
                        'payment_ref': 'Prepayment',
                        'amount': 650,
                        'date': time.strftime('%Y-01-01'),
                        'partner_id': ref('base.res_partner_12').id
                    }),
                    Command.create({
                        'payment_ref': time.strftime(f'First {formatLang(self.env, 2000, currency_obj=self.env.company.currency_id)} of invoice %Y/00001'),
                        'amount': 2000,
                        'date': time.strftime('%Y-01-01'),
                        'partner_id': ref('base.res_partner_12').id
                    }),
                    Command.create({
                        'payment_ref': 'Last Year Interests',
                        'amount': 102.78,
                        'date': time.strftime('%Y-01-01'),
                    }),
                    Command.create({
                        'payment_ref': time.strftime('INV/%Y/00002'),
                        'amount': 750,
                        'date': time.strftime('%Y-01-01'),
                        'partner_id': ref('base.res_partner_2').id
                    }),
                    Command.create({
                        'payment_ref': f'R:9772938  10/07 AX 9415116318 T:5 BRT: {formatLang(self.env, 96.67, currency_obj=self.env.company.currency_id)} C/ croip',
                        'amount': 96.67,
                        'date': time.strftime('%Y-01-01'),
                    }),
                ]
            },
        })

    @api.model
    def _get_demo_data_reconcile_model(self):
        cid = self.env.company.id
        return ('account.reconcile.model', {
            f'{cid}_reconcile_from_label': {
                'name': 'Line with Bank Fees',
                'rule_type': 'writeoff_suggestion',
                'match_label': 'contains',
                'match_label_param': 'BRT',
                'decimal_separator': ',',
                'line_ids': [
                    Command.create({
                        'label': 'Due amount',
                        'account_id': self._get_demo_account(
                            'income',
                            'income',
                            self.env.company,
                        ).id,
                        'amount_type': 'regex',
                        'amount_string': r'BRT: ([\d,]+)',
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
        })

    @api.model
    def _get_demo_data_attachment(self):
        cid = self.env.company.id
        ref = self.env.ref
        return ('ir.attachment', {
            f'{cid}_ir_attachment_bank_statement_1': {
                'type': 'binary',
                'name': 'bank_statement_yourcompany_demo.pdf',
                'res_model': 'account.bank.statement',
                'res_id': ref(f'account.{cid}_demo_bank_statement_1').id,
                'raw': file_open(
                    'account/static/demo/bank_statement_yourcompany_1.pdf', 'rb'
                ).read()
            },
            f'{cid}_ir_attachment_in_invoice_1': {
                'type': 'binary',
                'name': 'in_invoice_yourcompany_demo.pdf',
                'res_model': 'account.move',
                'res_id': ref(f'account.{cid}_demo_invoice_extract').id,
                'raw': file_open(
                    'account/static/demo/in_invoice_yourcompany_demo_1.pdf', 'rb'
                ).read()
            },
            f'{cid}_ir_attachment_in_invoice_2': {
                'type': 'binary',
                'name': 'in_invoice_yourcompany_demo.pdf',
                'res_model': 'account.move',
                'res_id': ref(f'account.{cid}_demo_invoice_equipment_purchase').id,
                'raw': file_open(
                    'account/static/demo/in_invoice_yourcompany_demo_2.pdf', 'rb'
                ).read()
            },
        })

    @api.model
    def _get_demo_data_mail_message(self):
        cid = self.env.company.id
        ref = self.env.ref
        return ('mail.message', {
            f'{cid}_mail_message_bank_statement_1': {
                'model': 'account.bank.statement',
                'res_id': ref(f'account.{cid}_demo_bank_statement_1').id,
                'body': 'Bank statement attachment',
                'message_type': 'comment',
                'author_id': ref('base.partner_demo').id,
                'attachment_ids': [Command.set([
                    ref(f'account.{cid}_ir_attachment_bank_statement_1').id
                ])]
            },
            f'{cid}_mail_message_in_invoice_1': {
                'model': 'account.move',
                'res_id': ref(f'account.{cid}_demo_invoice_extract').id,
                'body': 'Vendor Bill attachment',
                'message_type': 'comment',
                'author_id': ref('base.partner_demo').id,
                'attachment_ids': [Command.set([
                    ref(f'account.{cid}_ir_attachment_in_invoice_1').id
                ])]
            },
            f'{cid}_mail_message_in_invoice_2': {
                'model': 'account.move',
                'res_id': ref(f'account.{cid}_demo_invoice_equipment_purchase').id,
                'body': 'Vendor Bill attachment',
                'message_type': 'comment',
                'author_id': ref('base.partner_demo').id,
                'attachment_ids': [Command.set([
                    ref(f'account.{cid}_ir_attachment_in_invoice_2').id
                ])]
            },
        })

    @api.model
    def _get_demo_data_mail_activity(self):
        cid = self.env.company.id
        ref = self.env.ref
        return ('mail.activity', {
            f'{cid}_invoice_activity_1': {
                'res_id': ref(f'account.{cid}_demo_invoice_3').id,
                'res_model_id': ref('account.model_account_move').id,
                'activity_type_id': ref('mail.mail_activity_data_todo').id,
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'summary': 'Follow-up on payment',
                'create_uid': ref('base.user_admin').id,
                'user_id': ref('base.user_admin').id,
            },
            f'{cid}_invoice_activity_2': {
                'res_id': ref(f'account.{cid}_demo_invoice_2').id,
                'res_model_id': ref('account.model_account_move').id,
                'activity_type_id': ref('mail.mail_activity_data_call').id,
                'date_deadline': fields.Datetime.today().strftime('%Y-%m-%d %H:%M'),
                'create_uid': ref('base.user_admin').id,
                'user_id': ref('base.user_admin').id,
            },
            f'{cid}_invoice_activity_3': {
                'res_id': ref(f'account.{cid}_demo_invoice_1').id,
                'res_model_id': ref('account.model_account_move').id,
                'activity_type_id': ref('mail.mail_activity_data_todo').id,
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'summary': 'Include upsell',
                'create_uid': ref('base.user_admin').id,
                'user_id': ref('base.user_admin').id,
            },
            f'{cid}_invoice_activity_4': {
                'res_id': ref(f'account.{cid}_demo_invoice_extract').id,
                'res_model_id': ref('account.model_account_move').id,
                'activity_type_id': ref('mail.mail_activity_data_todo').id,
                'date_deadline': (fields.Datetime.today() + relativedelta(days=5)).strftime('%Y-%m-%d %H:%M'),
                'summary': 'Update address',
                'create_uid': ref('base.user_admin').id,
                'user_id': ref('base.user_admin').id,
            },
        })

    @api.model
    def _post_create_demo_data(self, created):
        cid = self.env.company.id
        if created._name == 'account.move':
            # the invoice_extract acts like a placeholder for the OCR to be ran and doesn't contain
            # any lines yet
            for move in created - self.env.ref(f'account.{cid}_demo_invoice_extract'):
                try:
                    move.action_post()
                except Exception:
                    _logger.exception('Error while posting demo data')
        elif created._name == 'account.bank.statement':
            created.button_post()

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
