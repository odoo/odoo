# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _set_partner_account_payable(self, company=False):
        fee_partner = self.env.ref('l10n_cl.demo_partner_cl_fee_receipts')
        account_payable = self.env.ref(f'account.{company.id}_account_210520')
        fee_partner.property_account_payable_id = account_payable
        return fee_partner

    @api.model
    def _get_demo_data_move(self, company=False):
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code != "CL":
            return move_data
        ref = self.env.ref
        currency_rate_obj = self.env['res.currency.rate']
        currency_usd = ref('base.USD')
        currency_uf = ref('l10n_cl.UF')
        today = fields.Date.today()
        first_day_of_rate = (today - timedelta(days=60)).replace(day=1)
        last_date_of_rate = (today + timedelta(days=60)).replace(day=1) - timedelta(days=1)
        usd_rate_value = 1/980.0
        uf_rate_value = 1/38400.0
        currency_rate_obj.create({
            'currency_id': currency_usd.id,
            'rate': usd_rate_value,
            'name': first_day_of_rate,
            'company_id': company.id,
        })
        currency_rate_obj.create({
            'currency_id': currency_usd.id,
            'rate': usd_rate_value,
            'name': last_date_of_rate,
            'company_id': company.id,
        })
        currency_rate_obj.create({
            'currency_id': currency_uf.id,
            'rate': uf_rate_value,
            'name': first_day_of_rate,
            'company_id': company.id,
        })
        currency_rate_obj.create({
            'currency_id': currency_uf.id,
            'rate': uf_rate_value,
            'name': last_date_of_rate,
            'company_id': company.id,
        })
        exports_purchase_journal = ref(f'account.{company.id}_purchase')
        local_sale_journal = self.env['account.journal'].search([
            ('company_id', '=', company.id), ('type', '=', 'sale')], limit=1)
        local_purchase_journal = self.env['account.journal'].search([
            ('company_id', '=', company.id), ('type', '=', 'purchase'), ('sequence', '=', 2)], limit=1)
        fiscal_position_exempt = ref(f'account.{company.id}_afpt_sale_exempt').id
        fiscal_position_exports = ref(f'account.{company.id}_afpt_sale_exports').id
        fiscal_position_imports = ref(f'account.{company.id}_afpt_purchase_imports').id
        fiscal_position_fees = ref(f'account.{company.id}_afpt_purchase_fees').id
        fiscal_position_supermarket = ref(f'account.{company.id}_afpt_purchase_supermarket').id
        fiscal_position_purchase_exempt = ref(f'account.{company.id}_afpt_purchase_exempt').id
        exports_purchase_journal.l10n_latam_use_documents = False

        # adapted existent moves for Chile
        # Export sale invoices (out_invoice) in USD
        move_data['demo_invoice_1']['l10n_latam_document_type_id'] = 'l10n_cl.dc_fe_dte'
        move_data['demo_invoice_1']['currency_id'] = 'base.USD'
        move_data['demo_invoice_1']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_invoice_2']['l10n_latam_document_type_id'] = 'l10n_cl.dc_fe_dte'
        move_data['demo_invoice_2']['currency_id'] = 'base.USD'
        move_data['demo_invoice_2']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_invoice_3']['l10n_latam_document_type_id'] = 'l10n_cl.dc_fe_dte'
        move_data['demo_invoice_3']['currency_id'] = 'base.USD'
        move_data['demo_invoice_3']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_invoice_followup']['l10n_latam_document_type_id'] = 'l10n_cl.dc_fe_dte'
        move_data['demo_invoice_followup']['currency_id'] = 'base.USD'
        move_data['demo_invoice_followup']['fiscal_position_id'] = fiscal_position_exports

        # Import purchase invoices (in_invoice)
        move_data['demo_invoice_5']['journal_id'] = exports_purchase_journal.id
        move_data['demo_invoice_5']['currency_id'] = 'base.USD'
        move_data['demo_invoice_5']['fiscal_position_id'] = fiscal_position_imports

        move_data['demo_invoice_extract']['journal_id'] = exports_purchase_journal.id
        move_data['demo_invoice_5']['fiscal_position_id'] = fiscal_position_imports

        move_data['demo_invoice_equipment_purchase']['journal_id'] = exports_purchase_journal.id
        move_data['demo_invoice_equipment_purchase']['currency_id'] = 'base.USD'
        move_data['demo_invoice_5']['fiscal_position_id'] = fiscal_position_imports

        # Export credit notes in USD (out_refund)
        move_data['demo_move_auto_reconcile_1']['l10n_latam_document_type_id'] = 'l10n_cl.dc_ncex_dte'
        move_data['demo_move_auto_reconcile_1']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_1']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_move_auto_reconcile_2']['l10n_latam_document_type_id'] = 'l10n_cl.dc_ncex_dte'
        move_data['demo_move_auto_reconcile_2']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_2']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_move_auto_reconcile_5']['l10n_latam_document_type_id'] = 'l10n_cl.dc_ncex_dte'
        move_data['demo_move_auto_reconcile_5']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_5']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_move_auto_reconcile_6']['l10n_latam_document_type_id'] = 'l10n_cl.dc_ncex_dte'
        move_data['demo_move_auto_reconcile_6']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_6']['fiscal_position_id'] = fiscal_position_exports

        move_data['demo_move_auto_reconcile_7']['l10n_latam_document_type_id'] = 'l10n_cl.dc_ncex_dte'
        move_data['demo_move_auto_reconcile_7']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_7']['fiscal_position_id'] = fiscal_position_exports

        # Purchase export credit notes (in_refund)
        move_data['demo_move_auto_reconcile_3']['journal_id'] = exports_purchase_journal.id
        move_data['demo_move_auto_reconcile_3']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_3']['fiscal_position_id'] = fiscal_position_imports

        move_data['demo_move_auto_reconcile_4']['journal_id'] = exports_purchase_journal.id
        move_data['demo_move_auto_reconcile_4']['currency_id'] = 'base.USD'
        move_data['demo_move_auto_reconcile_4']['fiscal_position_id'] = fiscal_position_imports

        # new moves for Chile
        # Local sale invoices (out_invoice) in CLP
        move_data['demo_cl_invoice_1'] = {
            'company_id': company.id,
            'move_type': 'out_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_a_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_1',
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_2', 'price_unit': 64200.0, 'quantity': 1}),
                Command.create({'product_id': 'product.product_product_12', 'price_unit': 12500.0, 'quantity': 3}),
                Command.create({'product_id': 'product.product_product_16', 'price_unit': 2520.0, 'quantity': 15}),
                Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 4}),
            ],
        }
        move_data['demo_cl_invoice_2'] = {
            'company_id': company.id,
            'move_type': 'out_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_a_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_2',
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_2', 'price_unit': 64200.0, 'quantity': 3}),
                Command.create({'product_id': 'product.product_product_16', 'price_unit': 2520.0, 'quantity': 10}),
                Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 2}),
            ],
        }
        # sale - exempt invoice
        move_data['demo_cl_exempt_invoice_1'] = {
            'company_id': company.id,
            'move_type': 'out_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_y_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_3',
            'fiscal_position_id': fiscal_position_exempt,
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 1230000.0, 'quantity': 1}),
            ],
        }
        # sale in uf
        move_data['demo_cl_invoice_uf_1'] = {
            'company_id': company.id,
            'move_type': 'out_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_a_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_1',
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'currency_id': 'l10n_cl.UF',
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_2', 'price_unit': 3.0, 'quantity': 1}),
            ],
        }
        # credit note in CLP cancelling demo_cl_exempt_invoice_1
        move_data['demo_cl_credit_note_1'] = {
            'company_id': company.id,
            'move_type': 'out_refund',
            'l10n_latam_document_type_id': 'l10n_cl.dc_nc_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_3',
            'fiscal_position_id': fiscal_position_exempt,
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 1230000.0, 'quantity': 1}),
            ],
        }
        # credit note with a discount over product product_product_2 for invoice demo_cl_invoice_1
        move_data['demo_cl_credit_note_discount_1'] = {
            'company_id': company.id,
            'move_type': 'out_refund',
            'l10n_latam_document_type_id': 'l10n_cl.dc_nc_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_1',
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'invoice_line_ids': [
                Command.create({'name': 'Discount','price_unit': 24200.0, 'quantity': 1}),
            ],
        }
        # debit note cancelling discount credit note
        move_data['demo_cl_debit_note_discount_1'] = {
            'company_id': company.id,
            'move_type': 'out_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_nd_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_1',
            'journal_id': local_sale_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today,
            'invoice_line_ids': [
                Command.create({'name': 'Discount', 'price_unit': 24200.0, 'quantity': 1}),
            ],
        }
        # 5 receipts
        products_for_receipts = [
            '1', '2', '5', '7', '9', '10', '11', '16', '20', '22', '24', '27',
        ]
        for receipt in range(1, 5):
            move_data[f'demo_cl_boleta_{receipt}'] = {
                'company_id': company.id,
                'move_type': 'out_invoice',
                'l10n_latam_document_type_id': 'l10n_cl.dc_b_f_dte',
                'partner_id': 'l10n_cl.par_cfa',
                'journal_id': local_sale_journal.id,
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': today - relativedelta(months=1),
                'invoice_line_ids': [
                    Command.create({'product_id': f'product.product_product_{products_for_receipts[receipt % len(products_for_receipts)]}', 'quantity': 1}),
                    Command.create({'product_id': f'product.product_product_{products_for_receipts[(receipt * 2) % len(products_for_receipts)]}', 'quantity': 3}),
                    Command.create({'product_id': f'product.product_product_{products_for_receipts[(receipt * 3) % len(products_for_receipts)]}', 'quantity': 4}),
                ],
            }

        # Local purchase invoices (in_invoice) in CLP
        move_data['demo_cl_invoice_3'] = {
            'company_id': company.id,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_a_f_dte',
            'l10n_latam_document_number': '25',
            'partner_id': 'l10n_cl.demo_partner_cl_3',
            'journal_id': local_purchase_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today - relativedelta(months=1),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_16', 'price_unit': 1008.0, 'quantity': 100}),
                Command.create({'product_id': 'product.product_product_20', 'price_unit': 980.0, 'quantity': 200}),
            ],
        }
        move_data['demo_cl_invoice_4'] = {
            'company_id': company.id,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_y_f_dte',
            'l10n_latam_document_number': '832',
            'fiscal_position_id': fiscal_position_purchase_exempt,
            'partner_id': 'l10n_cl.res_partner_bmya',
            'journal_id': local_purchase_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today - relativedelta(months=1),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 890500.0, 'quantity': 3}),
            ],
        }
        # purchase supermarket bill
        move_data['demo_cl_invoice_5'] = {
            'company_id': company.id,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_a_f_dte',
            'l10n_latam_document_number': '10512',
            'fiscal_position_id': fiscal_position_supermarket,
            'partner_id': 'l10n_cl.demo_partner_supermarket',
            'journal_id': local_purchase_journal.id,
            'invoice_date': today - timedelta(days=29),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.monitor_stand_product_template', 'price_unit': 28500.0, 'quantity': 1}),
            ],
        }
        # Purchase fees bill (in_invoice) in CLP
        move_data['demo_cl_fee_bill_1'] = {
            'company_id': company.id,
            'fiscal_position_id': fiscal_position_fees,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_m_d_dtn',
            'l10n_latam_document_number': '22',
            'partner_id': self._set_partner_account_payable(company).id,
            'journal_id': local_purchase_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today - timedelta(days=30),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 1000000.0, 'quantity': 1}),
            ],
        }
        # national purchase credit note
        move_data['demo_cl_credit_note_2'] = {
            'company_id': company.id,
            'move_type': 'in_refund',
            'fiscal_position_id': fiscal_position_purchase_exempt,
            'l10n_latam_document_type_id': 'l10n_cl.dc_nc_f_dte',
            'l10n_latam_document_number': '51',
            'partner_id': 'l10n_cl.res_partner_bmya',
            'journal_id': local_purchase_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today - timedelta(days=29),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 890500.0, 'quantity': 3}),
            ],
        }
        return move_data

    def _post_load_demo_data(self, company=False):
        if company.account_fiscal_country_id.code != "CL":
            return super()._post_load_demo_data(company)
        moves = self.env['account.move'].search([
            ('company_id', '=', company.id),
            ('partner_id', '!=', False),
            ('move_type', '!=', 'entry')])
        for move in moves:
            try:
                move.action_post()
            except (UserError, ValidationError):
                _logger.exception('Error while posting moves')
