# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        if company.account_fiscal_country_id.code == "PK":
            return {
                'res.partner': self._get_l10n_pk_demo_data_partner(company),
                'account.move': self._get_demo_data_move(company),
                'res.config.settings': self._get_l10n_pk_demo_data_config_settings(company),
            }
        else:
            return super()._get_demo_data(company)

    @api.model
    def _get_l10n_pk_demo_data_partner(self, company=False):
        company = company or self.env.company
        state_id = self.env.ref('l10n_pk.state_pk_is')
        default_partner_dict = {
            'company_id': company.id,
            'country_id': self.env.ref('base.pk').id,
            'is_company': True
        }
        return {
            'res_partner_punjab': {
                **default_partner_dict,
                'name': 'Punjab Customer',
                'street': '38/A Gulberg Main Boulevard',
                'street2': 'Gulberg III, Lahore',
                'city': 'Lahore',
                'state_id': company.state_id.id,
                'zip': '54000',
                'vat': '4174942',
                'phone': '+929876543210',
                'email': 'p086adrh7w@guerrillamail.com',
                'website': 'punjabpartner.odoo.com',
            },
            'res_partner_islamabad': {
                **default_partner_dict,
                'name': 'Islamabad Vendor',
                'street': 'Office 12, 3rd Floor, Giga Mall',
                'street2': 'Main GT Road, DHA Phase II',
                'city': 'Taxila',
                'state_id': state_id.id,
                'zip': '40000',
                'vat': False,
                'is_company': False,
                'phone': '+921234567890',
                'email': 'adrh7wp086@guerrillamail.com',
                'website': 'islamabadvendor.odoo.com',
            },
        }

    @api.model
    def _get_demo_data_move(self, company=False):
        cid = (company or self.env.company).id
        if company.account_fiscal_country_id.code == "PK":
            sale_journal = self.env['account.journal'].search(
                domain=[
                    *self.env['account.journal']._check_company_domain(cid),
                    ('type', '=', 'sale'),
                ], limit=1)
            return {
                'demo_invoice_1': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_punjab',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=1),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_17',
                                'pk_tax_wh_S_1'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 4,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_5'
                            ])],
                        }),
                    ],
                },
                'demo_invoice_2': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_punjab',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=2),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 2,
                            'price_unit': 4000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 3,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_5'
                            ])],
                        }),
                    ],
                },
                'demo_invoice_3': {
                    'move_type': 'out_invoice',
                    'partner_id': 'base.res_partner_3',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=3),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_4',
                            'quantity': 10,
                            'price_unit': 800.0,
                            'tax_ids': False,
                        }),
                    ]
                },
                'demo_reconcile_1': {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_punjab',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=1),
                    'delivery_date': fields.Datetime.today() - relativedelta(days=1),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10',
                                'pk_tax_wh_S_5'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 4,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_5'
                            ])],
                        }),
                    ],
                },
                'demo_reconcile_2': {
                    'move_type': 'out_refund',
                    'partner_id': 'base.res_partner_3',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=2),
                    'delivery_date': fields.Datetime.today() - relativedelta(days=2),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_4',
                            'quantity': 10,
                            'price_unit': 800.0,
                            'tax_ids': False,
                        }),
                    ]
                },
                'demo_vendor_bill_1': {
                    'ref': 'INV/001',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_islamabad',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=1),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_15'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10',
                                'pk_tax_wh_S_1'
                            ])],
                        }),
                    ]
                },
                'demo_vendor_bill_2': {
                    'ref': 'INV/002',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_islamabad',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=2),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 4,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_17'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_7',
                            'quantity': 3,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10'
                            ])],
                        }),
                    ]
                },
                'demo_vendor_bill_3': {
                    'ref': 'INV/003',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_islamabad',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=3),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_17'
                            ])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([
                                'pk_sales_tax_services_10',
                                'pk_tax_wh_S_5'
                            ])],
                        }),
                    ]
                },
            }
        return super()._get_demo_data_move(company)

    @api.model
    def _get_l10n_pk_demo_data_config_settings(self, company=False):
        return {
            'sales_credit_limit': {
                'account_use_credit_limit': True,
                'account_default_credit_limit': '10000'
            }
        }

    def _post_load_demo_data(self, company=False):
        company = company or self.env.company
        if company.account_fiscal_country_id.code != "PK":
            return super()._post_load_demo_data(company)
        invoices = (
            self.ref('demo_invoice_1')
            + self.ref('demo_invoice_2')
            + self.ref('demo_invoice_3')
            + self.ref('demo_reconcile_1')
            + self.ref('demo_reconcile_2')
            + self.ref('demo_vendor_bill_1')
            + self.ref('demo_vendor_bill_2')
            + self.ref('demo_vendor_bill_3')
        )
        for move in invoices:
            move.action_post()
