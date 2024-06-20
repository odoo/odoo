# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
import logging
from odoo import api, models, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):

    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        if company.account_fiscal_country_id.code == "UY":
            super()._get_demo_data_products(company)
            return {
                'res.partner': self._l10n_uy_get_demo_data_res_partner(company),
                'account.move': self._l10n_uy_get_demo_data_move(company),
                'account.move.reversal': self._l10n_uy_get_demo_data_move_reversal(company),
            }
        else:
            return super()._get_demo_data(company)

    def _post_load_demo_data(self, company=False):
        if company.account_fiscal_country_id.code != "UY":
            return super()._post_load_demo_data(company)
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
        )
        for move in invoices_to_revert:
            try:
                self.env['account.move'].browse(move.refund_moves().get('res_id')).action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting reversal moves')

    @api.model
    def _l10n_uy_get_demo_data_move(self, company=False):
        cid = company.id or self.env.company.id
        sale_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'sale')
            ], limit=1,
        )
        purchase_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'purchase')
            ], limit=1,
        )
        return {
            # Customer invoice demo
            'demo_invoice_1': {
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_4',
                'journal_id': sale_journal.id,
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'base.res_partner_4',
                'invoice_user_id': 'base.user_demo',
                'journal_id': sale_journal.id,
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'journal_id': sale_journal.id,
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'demo_partner_4',
                'invoice_user_id': 'base.user_demo',
                'journal_id': sale_journal.id,
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'res_partner_foreign',
                'invoice_user_id': 'base.user_demo',
                'journal_id': sale_journal.id,
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'l10n_uy.partner_cfu',
                'invoice_user_id': 'base.user_demo',
                'journal_id': sale_journal.id,
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
                'company_id': company.id,
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'demo_partner_5',
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
                'company_id': company.id,
                'move_type': 'out_invoice',
                'partner_id': 'demo_partner_4',
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'demo_partner_5',
                'invoice_user_id': 'base.user_demo',
                'journal_id': purchase_journal.id,
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_foreign',
                'invoice_user_id': 'base.user_demo',
                'journal_id': purchase_journal.id,
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'demo_partner_4',
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
                'company_id': company.id,
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_foreign',
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'res_partner_foreign',
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'demo_partner_5',
                'invoice_user_id': 'base.user_demo',
                'journal_id': purchase_journal.id,
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
                'company_id': company.id,
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'demo_partner_4',
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
                'company_id': company.id,
                'move_type': 'in_invoice',
                'partner_id': 'demo_partner_5',
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

    @api.model
    def _l10n_uy_get_demo_data_move_reversal(self, company=False):
        cid = company.id or self.env.company.id
        sale_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'sale')
            ], limit=1,
        )
        purchase_journal = self.env['account.journal'].search(
            domain=[
                *self.env['account.journal']._check_company_domain(cid),
                ('type', '=', 'purchase')
            ], limit=1,
        )
        return {
            # Account Customer Refund

            # Create draft refund for invoice 3
            'demo_refund_invoice_1': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_1',
                'journal_id': sale_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },
            # Create draft refund for invoice 4
            'demo_refund_invoice_2': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_4',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
                'journal_id': sale_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_refund_invoice_3': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_5',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv_exp',
                'journal_id': sale_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_refund_invoice_4': {
                'reason': 'Venta Cancelada',
                'move_ids': 'demo_invoice_6',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
                'journal_id': sale_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },

            # Account supplier refund
            'demo_sup_refund_invoice_3': {
                'reason': 'Mercadería defectuosa',
                'l10n_latam_document_number': 'BB0123456',
                'move_ids': 'demo_sup_invoice_1',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv',
                'journal_id': purchase_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_sup_refund_invoice_2': {
                'reason': 'Venta cancelada',
                'l10n_latam_document_number': 'BB0123457',
                'move_ids': 'demo_sup_invoice_2',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_inv_exp',
                'journal_id': purchase_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },
            'demo_sup_refund_invoice_1': {
                'reason': 'Venta cancelada',
                'l10n_latam_document_number': 'BB0123458',
                'move_ids': 'demo_sup_invoice_7',
                'l10n_latam_document_type_id': 'l10n_uy.dc_cn_e_ticket',
                'journal_id': purchase_journal.id,
                'date': time.strftime('%Y-%m') + '-01'
            },
        }

    @api.model
    def _l10n_uy_get_demo_data_res_partner(self, company=False):
        return {
            'demo_partner_4': {
                'name': 'IEB Internacional',
                'l10n_latam_identification_type_id': 'l10n_uy.it_rut',
                'vat': '218435730016',
                'street': 'Bach 0',
                'city': 'Aeroparque',
                'state_id': 'base.state_uy_02',
                'country_id': 'base.uy',
                'email': 'rut@example.com',
            },
            'demo_partner_5': {
                'name': 'MELI URUGUAY S.R.L.',
                'l10n_latam_identification_type_id': 'l10n_uy.it_rut',
                'vat': '216748870015',
                'street': 'Paraguay 2141',
                'city': 'Zona Franca Aguada Park',
                'state_id': 'base.state_uy_10',
                'country_id': 'base.uy',
                'email': 'meli@example.com',
            },
            'demo_partner_6': {
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
            'res_partner_foreign': {
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
            'res_partner_resident_alien': {
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
