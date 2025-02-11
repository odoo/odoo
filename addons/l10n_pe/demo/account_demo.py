# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import api, Command, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        def _get_tax_by_code(code, type_tax='sale'):
            taxes = self.env['account.tax'].search([
                ('type_tax_use', '=', type_tax), ('l10n_pe_edi_tax_code', '=', code)], limit=1)
            return [Command.set(taxes.ids)]

        move_data = super()._get_demo_data_move(company)
        ref = self.env.ref
        last_month_date = datetime.strptime(move_data['demo_invoice_1']['invoice_date'], '%Y-%m-%d') - timedelta(days=1)
        if company.account_fiscal_country_id.code == "PE":
            move_data['demo_invoice_1']['invoice_date'] = last_month_date
            move_data['demo_invoice_1']['l10n_latam_document_number'] = 'FFF-0000001'
            move_data['demo_invoice_1']['invoice_line_ids'] = [
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 25000.0, 'price_unit': 3.0, 'tax_ids': _get_tax_by_code('9997')}),
            ]
            move_data['demo_invoice_2']['invoice_date'] = last_month_date
            move_data['demo_invoice_2']['l10n_latam_document_number'] = 'FFF-0000002'
            move_data['demo_invoice_2']['invoice_line_ids'] = [
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 12500.0, 'price_unit': 3.0, 'tax_ids': _get_tax_by_code('1000')}),
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 1000.0, 'tax_ids': _get_tax_by_code('9997')}),
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 1500.0, 'tax_ids': _get_tax_by_code('9998')}),
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 12500.0, 'price_unit': 3.0, 'tax_ids': _get_tax_by_code('1000')}),
            ]
            move_data['demo_invoice_3']['invoice_date'] = last_month_date
            move_data['demo_invoice_3']['l10n_latam_document_type_id'] = ref('l10n_pe.document_type08').id,
            move_data['demo_invoice_3']['l10n_latam_document_number'] = 'NDI-0000001'
            move_data['demo_invoice_3']['invoice_line_ids'] = [
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 12500.0, 'price_unit': 3.0, 'tax_ids': _get_tax_by_code('1000')}),
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 1000.0, 'tax_ids': _get_tax_by_code('9997')}),
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 1500.0, 'tax_ids': _get_tax_by_code('9998')}),
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 12500.0, 'price_unit': 3.0, 'tax_ids': _get_tax_by_code('1000')}),
            ]
            move_data['demo_invoice_followup']['move_type'] = 'in_invoice'
            move_data['demo_invoice_followup']['partner_id'] = ref('base.res_partner_2').id
            move_data['demo_invoice_followup']['invoice_date'] = last_month_date
            move_data['demo_invoice_followup']['l10n_latam_document_number'] = 'FFF-100001'
            move_data['demo_invoice_followup']['invoice_line_ids'] = [
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 500.0}),
            ]
            move_data['demo_invoice_5']['partner_id'] = ref('base.res_partner_2').id
            move_data['demo_invoice_5']['invoice_date'] = last_month_date
            move_data['demo_invoice_5']['l10n_latam_document_number'] = 'FFF-100002'
            move_data['demo_invoice_5']['invoice_line_ids'] = [
                Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 500.0, 'tax_ids': _get_tax_by_code('1000', 'purchase')}),
            ]
            igv_gyng_tax = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('tax_group_id.name', '=', 'IGV GyNG')], limit=1)
            move_data['demo_invoice_equipment_purchase']['partner_id'] = ref('base.res_partner_2').id
            move_data['demo_invoice_equipment_purchase']['invoice_date'] = last_month_date
            move_data['demo_invoice_equipment_purchase']['l10n_latam_document_number'] = 'FFF-100003'
            move_data['demo_invoice_equipment_purchase']['invoice_line_ids'] = [
                Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 500.0, 'quantity': 1, 'tax_ids': [Command.set(igv_gyng_tax.ids)]}),
            ]
            move_data['demo_invoice_6'] = {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_2').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': 'FFF-100004',
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 500.0, 'quantity': 1, 'tax_ids': _get_tax_by_code('9997', 'purchase')}),
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 1000.0, 'quantity': 1, 'tax_ids': _get_tax_by_code('1000', 'purchase')}),
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 1500.0, 'quantity': 2, 'tax_ids': _get_tax_by_code('9996', 'purchase')}),
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 2000.0, 'quantity': 1, 'tax_ids': _get_tax_by_code('9998', 'purchase')}),
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 2500.0, 'quantity': 1, 'tax_ids': _get_tax_by_code('1000', 'purchase')}),
                ],
            }
            move_data['demo_invoice_7'] = {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': 'FFF-000005',
                'l10n_latam_document_type_id': ref('l10n_pe.document_type91').id,
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 25000.0, 'quantity': 3, 'tax_ids': _get_tax_by_code('9995', 'purchase')}),
                ],
            }
            move_data['demo_invoice_8'] = {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': '118-145266',
                'l10n_latam_document_type_id': ref('l10n_pe.document_type50').id,
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 3, 'quantity': 25000.0, 'tax_ids': _get_tax_by_code('9995', 'purchase')}),
                ],
            }
            move_data['demo_invoice_9'] = {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': 'FFF-100009',
                'l10n_latam_document_type_id': ref('l10n_pe.document_type91').id,
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.product_delivery_01').id, 'price_unit': 3, 'quantity': 25000.0, 'tax_ids': _get_tax_by_code('9995', 'purchase')}),
                ],
            }
            move_data['demo_invoice_10'] = {
                'move_type': 'out_refund',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': 'CNE-0000001',
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 25000.0, 'price_unit': 3.0, 'tax_ids': _get_tax_by_code('9997')}),
                ],
            }
            move_data['demo_invoice_11'] = {
                'move_type': 'in_refund',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': 'FFF-100005',
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 500.0}),
                ],
            }
            move_data['demo_invoice_12'] = {
                'move_type': 'in_invoice',
                'partner_id': ref('base.res_partner_12').id,
                'invoice_user_id': ref('base.user_demo').id,
                'l10n_latam_document_type_id': ref('l10n_pe.document_type08').id,
                'invoice_payment_term_id': ref('account.account_payment_term_end_following_month').id,
                'invoice_date': last_month_date,
                'l10n_latam_document_number': 'FFF-100006',
                'invoice_line_ids': [
                    Command.create({'product_id': ref('product.consu_delivery_03').id, 'quantity': 1.0, 'price_unit': 500.0}),
                ],
            }
            move_data['demo_move_auto_reconcile_3']['l10n_latam_document_number'] = 'FFF-100007'
            move_data['demo_move_auto_reconcile_4']['l10n_latam_document_number'] = 'FFF-100008'
        return move_data
