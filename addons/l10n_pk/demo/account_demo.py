# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(template='pk', model='account.move', demo=True)
    def _l10n_pk_account_move_demo(self):
        return {
                'l10n_pk_demo_invoice_1': {
                    'move_type': 'out_invoice',
                    'partner_id': 'l10n_pk.res_partner_punjab',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=1),
                    'journal_id': 'sale',
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
                'l10n_pk_demo_invoice_2': {
                    'move_type': 'out_invoice',
                    'partner_id': 'l10n_pk.res_partner_punjab',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=2),
                    'journal_id': 'sale',
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
                'l10n_pk_demo_invoice_3': {
                    'move_type': 'out_invoice',
                    'partner_id': 'base.res_partner_3',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Datetime.today() - relativedelta(days=3),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_4',
                            'quantity': 10,
                            'price_unit': 800.0,
                            'tax_ids': False,
                        }),
                    ]
                },
                'l10n_pk_demo_reconcile_1': {
                    'move_type': 'out_refund',
                    'partner_id': 'l10n_pk.res_partner_punjab',
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
                'l10n_pk_demo_reconcile_2': {
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
                'l10n_pk_demo_vendor_bill_1': {
                    'ref': 'INV/001',
                    'move_type': 'in_invoice',
                    'partner_id': 'l10n_pk.res_partner_islamabad',
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
                'l10n_pk_demo_vendor_bill_2': {
                    'ref': 'INV/002',
                    'move_type': 'in_invoice',
                    'partner_id': 'l10n_pk.res_partner_islamabad',
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
                'l10n_pk_demo_vendor_bill_3': {
                    'ref': 'INV/003',
                    'move_type': 'in_invoice',
                    'partner_id': 'l10n_pk.res_partner_islamabad',
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

    def _post_load_demo_data(self, template_code):
        if template_code == "pk":
            invoices = (
                self.ref('l10n_pk_demo_invoice_1')
                + self.ref('l10n_pk_demo_invoice_2')
                + self.ref('l10n_pk_demo_invoice_3')
                + self.ref('l10n_pk_demo_reconcile_1')
                + self.ref('l10n_pk_demo_reconcile_2')
                + self.ref('l10n_pk_demo_vendor_bill_1')
                + self.ref('l10n_pk_demo_vendor_bill_2')
                + self.ref('l10n_pk_demo_vendor_bill_3')
            )
            for move in invoices:
                move.action_post()
        super()._post_load_demo_data(template_code)
