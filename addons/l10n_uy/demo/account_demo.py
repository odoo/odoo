# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
import logging
from odoo import models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, chart_template):
        if chart_template != "uy":
            super()._post_load_demo_data(chart_template)
            return
        invoices = (
            self.ref('demo_invoice_1')
            + self.ref('demo_invoice_2')
            + self.ref('demo_invoice_3')
            + self.ref('demo_invoice_4')
            + self.ref('demo_invoice_5')
            + self.ref('demo_invoice_6')
            + self.ref('demo_invoice_8')
            + self.ref('demo_invoice_9')
            + self.ref('demo_sup_invoice_1')
            + self.ref('demo_sup_invoice_2')
            + self.ref('demo_sup_invoice_3')
            + self.ref('demo_sup_invoice_6')
            + self.ref('demo_sup_invoice_7')
            + self.ref('demo_sup_invoice_8')
            + self.ref('demo_sup_invoice_9')
        )
        # the invoice_extract acts like a placeholder for the OCR to be ran and
        # doesn't contain any lines yet
        for move in invoices:
            try:
                move.action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting invoices')

        # Post the reversal moves
        invoices_to_revert = (
            self.ref('demo_refund_invoice_1')
            + self.ref('demo_refund_invoice_2')
            + self.ref('demo_refund_invoice_3')
            + self.ref('demo_refund_invoice_4')
            + self.ref('demo_sup_refund_invoice_3')
            + self.ref('demo_sup_refund_invoice_2')
            + self.ref('demo_sup_refund_invoice_1')
        )
        for reversal in invoices_to_revert:
            try:
                self.env['account.move'].browse(reversal.refund_moves().get('res_id')).action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting reversal moves')

    @template(model='account.move', demo=True)
    def _get_demo_data_move(self, template_code):
        if template_code != 'uy':
            return super()._get_demo_data_move(template_code)
        return {
            # Customer invoice demo
            'demo_invoice_1': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_4',
                'journal_id': 'sale',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-01'),
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 642.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_16', 'price_unit': 25.0, 'quantity': 20}),
                    Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 4}),
                ],
            },
            'demo_invoice_2': {
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_4',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'sale',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-05'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_25', 'price_unit': 3245.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'price_unit': 4000.0, 'quantity': 5}),
                ],
            },
            'demo_invoice_3': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'sale',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-10'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 642.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_delivery_02', 'price_unit': 40.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_order_01', 'price_unit': 280.0, 'quantity': 3}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 2}),
                ],
            },
            'demo_invoice_4': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.demo_partner_4',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'sale',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-13'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 1000.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_13', 'price_unit': 85.0, 'quantity': 3}),
                ],
                'currency_id': 'base.USD',
            },
            'demo_invoice_5': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.res_partner_foreign',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'sale',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-11'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv_exp',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_02', 'price_unit': 4000.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_13', 'price_unit': 85.0, 'quantity': 3}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'price_unit': 2350.0, 'quantity': 1}),

                ],
                'currency_id': 'base.USD',
            },
            'demo_invoice_6': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'sale',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-14'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_1', 'price_unit': 216.0, 'quantity': 9}),
                    Command.create({'product_id': 'product.product_delivery_01', 'price_unit': 70.0, 'quantity': 11}),
                    Command.create({'product_id': 'product.product_delivery_02', 'price_unit': 40.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_order_01', 'price_unit': 280.0, 'quantity': 3}),
                    Command.create({'product_id': 'product.consu_delivery_02', 'price_unit': 4000.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_13', 'price_unit': 85.0, 'quantity': 3}),
                    Command.create({'product_id': 'product.product_product_16', 'price_unit': 25.0, 'quantity': 20}),
                    Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 4}),
                ],
            },
            'demo_invoice_7': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-14'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_1', 'price_unit': 216.0, 'quantity': 3}),
                    Command.create({'product_id': 'product.product_delivery_01', 'price_unit': 70.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_delivery_02', 'price_unit': 40.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 7}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_16', 'price_unit': 25.0, 'quantity': 16}),
                    Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 2}),
                ],
            },
            'demo_invoice_8': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.demo_partner_5',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-01'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_dn_e_inv',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_25', 'price_unit': 3245.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'price_unit': 4000.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 3}),
                ],
            },
            'demo_invoice_9': {
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.demo_partner_4',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m-05'),
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_25', 'price_unit': 3245.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'price_unit': 4000.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_delivery_02', 'price_unit': 4000.0, 'quantity': 1}),
                ],
            },

            # Supplier invoice demo
            'demo_sup_invoice_1': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.demo_partner_5',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'purchase',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv',
                'l10n_latam_document_number': 'AA0000008',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 642.0, 'quantity': 3}),
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 228.0, 'quantity': 1}),
                ],
            },
            'demo_sup_invoice_2': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.res_partner_foreign',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'purchase',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv_exp',
                'l10n_latam_document_number': 'AA0000009',
                'currency_id': 'base.USD',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 2584.0, 'quantity': 2}),
                ],
            },
            'demo_sup_invoice_3': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.demo_partner_4',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-26',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv',
                'l10n_latam_document_number': 'AA0000010',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 1642.0, 'quantity': 8}),
                ],
            },
            'demo_sup_invoice_4': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-26',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'l10n_latam_document_number': 'AA0000011',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 1642.0, 'quantity': 3}),
                ],
            },
            'demo_sup_invoice_5': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.res_partner_foreign',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv_exp',
                'l10n_latam_document_number': 'AA0000012',
                'currency_id': 'base.USD',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 3245.0, 'quantity': 1}),
                ],
            },
            'demo_sup_invoice_6': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.res_partner_foreign',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_inv_exp',
                'l10n_latam_document_number': 'AA0000013',
                'currency_id': 'base.USD',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 335.0, 'quantity': 8}),
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 9584.0, 'quantity': 16}),
                ],
            },
            'demo_sup_invoice_7': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.demo_partner_5',
                'invoice_user_id': 'base.user_demo',
                'journal_id': 'purchase',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'l10n_latam_document_number': 'AA0000014',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 642.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_product_25', 'price_unit': 3245.0, 'quantity': 2}),
                    Command.create({'product_id': 'product.consu_delivery_01', 'price_unit': 4000.0, 'quantity': 5}),
                    Command.create({'product_id': 'product.product_delivery_02', 'price_unit': 4000.0, 'quantity': 1}),
                ],
            },
            'demo_sup_invoice_8': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'l10n_latam_document_number': 'AA0000015',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.consu_delivery_02', 'price_unit': 4000.0, 'quantity': 7}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 6}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_product_13', 'price_unit': 85.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.consu_delivery_03', 'price_unit': 2350.0, 'quantity': 4}),
                ],
            },
            'demo_sup_invoice_9': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.demo_partner_4',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_type_id': 'l10n_uy.dc_e_ticket',
                'l10n_latam_document_number': 'AA0000016',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_27', 'price_unit': 1000.0, 'quantity': 8}),
                    Command.create({'product_id': 'product.product_product_3', 'price_unit': 450.0, 'quantity': 7}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_product_13', 'price_unit': 85.0, 'quantity': 2}),
                ],
            },
            'demo_sup_invoice_10': {
                'move_type': 'in_invoice',
                'partner_id': 'l10n_uy.demo_partner_5',
                'invoice_user_id': 'base.user_demo',
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': time.strftime('%Y-%m') + '-01',
                'l10n_latam_document_number': 'AA0000017',
                'invoice_line_ids': [
                    Command.create({'product_id': 'product.product_product_2', 'price_unit': 642.0, 'quantity': 1}),
                    Command.create({'product_id': 'product.product_product_12', 'price_unit': 120.0, 'quantity': 4}),
                    Command.create({'product_id': 'product.product_product_16', 'price_unit': 25.0, 'quantity': 20}),
                    Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 4}),
                ],
            },
        }

    @template(model='account.bank.statement', demo=True)
    def _get_demo_data_statement(self, template_code):
        return {} if template_code == 'uy' else super()._get_demo_data_statement(template_code)

    @template(model='account.bank.statement.line', demo=True)
    def _get_demo_data_transactions(self, template_code):
        return {} if template_code == 'uy' else super()._get_demo_data_transactions(template_code)

    @template(model='ir.attachment', demo=True)
    def _get_demo_data_attachment(self, template_code):
        return {} if template_code == 'uy' else super()._get_demo_data_attachment(template_code)

    @template(model='mail.message', demo=True)
    def _get_demo_data_mail_message(self, template_code):
        return {} if template_code == 'uy' else super()._get_demo_data_mail_message(template_code)

    @template(model='mail.activity', demo=True)
    def _get_demo_data_mail_activity(self, template_code):
        return {} if template_code == 'uy' else super()._get_demo_data_mail_activity(template_code)

    @template(template='uy', model='account.move.reversal', demo=True)
    def _l10n_uy_get_demo_data_move_reversal(self, company=False):
        return {
            # Account Customer Refund

            # Create draft refund for invoice 3
            'demo_refund_invoice_1': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_1',
                'journal_id': 'sale',
                'date': time.strftime('%Y-%m') + '-01'
            },
            # Create draft refund for invoice 4
            'demo_refund_invoice_2': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_4',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
                'journal_id': 'sale',
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_refund_invoice_3': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_5',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv_exp',
                'journal_id': 'sale',
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_refund_invoice_4': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_6',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
                'journal_id': 'sale',
                'date': time.strftime('%Y-%m') + '-01'
            },

            # Account supplier refund
            'demo_sup_refund_invoice_3': {
                'reason': 'Mercadería defectuosa',
                'l10n_latam_document_number': 'BB0123456',
                'move_ids': 'demo_sup_invoice_1',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv',
                'journal_id': 'purchase',
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_sup_refund_invoice_2': {
                'reason': 'Venta cancelada',
                'l10n_latam_document_number': 'BB0123457',
                'move_ids': 'demo_sup_invoice_2',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv_exp',
                'journal_id': 'purchase',
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_sup_refund_invoice_1': {
                'reason': 'Venta cancelada',
                'l10n_latam_document_number': 'BB0123458',
                'move_ids': 'demo_sup_invoice_7',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
                'journal_id': 'purchase',
                'date': time.strftime('%Y-%m') + '-01'
            },
        }

    @template(template='uy', model='res.partner', demo=True)
    def _l10n_uy_get_demo_data_res_partner(self, company=False):
        return {
            'l10n_uy.demo_partner_4': {
                'name': 'Global Solutions Corp',
                'l10n_latam_identification_type_id': 'l10n_uy.it_rut',
                'vat': '218435730016',
                'street': 'Avenida Central 5678',
                'city': 'Punta del Este',
                'state_id': 'base.state_uy_01',
                'country_id': 'base.uy',
                'email': 'info@globalsolutions.com',
            },
            'l10n_uy.demo_partner_5': {
                'name': 'Tech Innovations S.A.',
                'l10n_latam_identification_type_id': 'l10n_uy.it_rut',
                'vat': '219999830019',
                'street': 'Avenida de la Libertad 1234',
                'city': 'Montevideo',
                'state_id': 'base.state_uy_01',
                'country_id': 'base.uy',
                'email': 'contact@techinnovations.com',
            },
            'l10n_uy.demo_partner_6': {
                'name': 'CORREO URUGUAYO',
                'l10n_latam_identification_type_id': 'l10n_uy.it_rut',
                'vat': '214130990011',
                'street': 'Buenos Aires 451',
                'city': 'Montevideo',
                'state_id': 'base.state_uy_10',
                'country_id': 'base.uy',
                'email': 'correo@example.com',
            },
            # Foreign Company
            'l10n_uy.res_partner_foreign': {
                'name': 'Foreign Inc',
                'l10n_latam_identification_type_id': 'l10n_latam_base.it_vat',
                'is_company': True,
                'vat': '17-2038053',
                'zip': '95380',
                'street': '7841 Red Road',
                'city': 'San Francisco',
                'state_id': 'base.state_us_5',
                'country_id': 'base.us',
                'email': 'foreing@example.com',
                'phone': '(123)-456-7890',
                'website': 'http://www.foreign-inc.com',
            },
            # Resident Alien (Foreign living at Uruguay)
            'l10n_uy.res_partner_resident_alien': {
                'name': 'Resident Alien',
                'l10n_latam_identification_type_id': 'l10n_uy.it_nie',
                'vat': '93:402.010-1',
                'zip': '2343',
                'street': 'Calle False 1234',
                'city': 'Montevideo',
                'state_id': 'base.state_uy_10',
                'country_id': 'base.uy',
                'email': 'nie@example.com',
            },
        }
