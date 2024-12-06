# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo import api, models, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = {}
        if company.account_fiscal_country_id.code == "PK":
            if company.state_id:
                demo_data = {
                    'res.partner': self._get_demo_data_partner(company),
                    'account.move': self._get_demo_data_move(company),
                    'res.config.settings': self._get_demo_data_config_settings(company),
                }
            else:
                _logger.error('Error while loading Pakistan-Accounting demo data in the company "%s".', company.name)
        else:
            demo_data = super()._get_demo_data(company)
        return demo_data

    @api.model
    def _get_demo_data_partner(self, company=False):
        company = company or self.env.company
        state_id_b2b = self.env['res.country.state'].search([
            ('code', '=', company.state_id.code),
            ('country_id', '=', company.country_id.id)
        ], limit=1)
        state_id_b2c = self.env['res.country.state'].search([
            ('code', '=', 'IS/ICT'),
            ('country_id', '=', company.country_id.id)
        ], limit=1)
        default_partner_dict = {'company_id': company.id, 'country_id': 'base.pk', 'is_company': True}
        return {
            'res_partner_b2b': {
                **default_partner_dict,
                'name': 'B2B - Punjab Partner',
                'street': '38/A Gulberg Main Boulevard',
                'street2': 'Gulberg III, Lahore',
                'city': 'Lahore',
                'state_id': state_id_b2b.id,
                'zip': '54000',
                'vat': '4174942',
                'phone': '+929876543210',
                'email': 'p086adrh7w@guerrillamail.com',
                'website': 'www.punjabpartner.com',
            },
            'res_partner_b2c': {
                **default_partner_dict,
                'name': 'B2C - Islamabad Partner',
                'street': 'Office 12, 3rd Floor, Giga Mall',
                'street2': 'Main GT Road, DHA Phase II',
                'city': 'Taxila',
                'state_id': state_id_b2c.id,
                'zip': '40000',
                'vat': False,
                'is_company': False,
                'phone': '+921234567890',
                'email': 'adrh7wp086@guerrillamail.com',
                'website': 'www.islamabadpartner.com',
            },
        }

    @api.model
    def _get_demo_data_move(self, company=False):
        cid = company.id or self.env.company.id

        def _get_tax_by_id(tax_id):
            tax = self.env.ref('account.%s_%s' % ((cid), (tax_id)))
            return tax.id

        if company.account_fiscal_country_id.code == "PK":
            sale_journal = self.env['account.journal'].search(
                domain=[
                    *self.env['account.journal']._check_company_domain(cid),
                    ('type', '=', 'sale'),
                ], limit=1)
            return {
                # Demo of B2B (business-to-business) Invoice. Taxable supplies made to B2B Entity.
                'demo_invoice_b2b_1': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_b2b',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10'), _get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 4,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                    ],
                },
                'demo_invoice_b2b_2': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_b2b',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 2,
                            'price_unit': 4000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 3,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                    ],
                },
                # Demo of B2C (business-to-consumer) Invoice. Taxable supplies made to Unregistered Entity.
                'demo_invoice_b2c_1': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_b2c',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_16',
                            'quantity': 1,
                            'price_unit': 1500.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_20',
                            'quantity': 1,
                            'price_unit': 2300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_5'), _get_tax_by_id('pk_sales_tax_services_2')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_22',
                            'quantity': 1,
                            'price_unit': 2600.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_17')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_24',
                            'quantity': 2,
                            'price_unit': 1655.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_1')])],
                        }),
                    ]
                },
                'demo_invoice_b2c_2': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_b2c',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 1,
                            'price_unit': 100000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 5,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10'), _get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 10,
                            'price_unit': 3000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                    ],
                },
                # Demo of B2C (business-to-business) Credit Note. Taxable supplies reversed to B2B Entity.
                'demo_reconcile_b2b_1': {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_b2b',
                    'invoice_date': datetime.now(),
                    'delivery_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10'), _get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 4,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_5')])],
                        }),
                    ],
                },
                # Demo of B2B (business-to-business) Vendor Bill. Taxable supplies from to B2B Entity.
                'demo_vendor_bill_b2b_1': {
                    'ref': 'INV/001',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_b2b',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_15')])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10'), _get_tax_by_id('pk_sales_tax_services_2')])],
                        }),
                    ]
                },
                'demo_vendor_bill_b2b_2': {
                    'ref': 'INV/002',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_b2b',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 4,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_17')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_7',
                            'quantity': 3,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10')])],
                        }),
                    ]
                },
                'demo_vendor_bill_b2b_3': {
                    'ref': 'INV/003',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_b2b',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_17')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('pk_sales_tax_services_10'), _get_tax_by_id('pk_sales_tax_services_1')])],
                        }),
                    ]
                },
            }
        else:
            return super()._get_demo_data_move(company)

    @api.model
    def _get_demo_data_config_settings(self, company=False):
        return {
            'sales_credit_limit': {
                'account_use_credit_limit': True,
                'account_default_credit_limit': '10000'
            }
        }

    def _post_load_demo_data(self, company=False):
        if company.account_fiscal_country_id.code == "PK":
            if company.state_id:
                invoices = (
                    self.ref('demo_invoice_b2b_1')
                    + self.ref('demo_invoice_b2b_2')
                    + self.ref('demo_invoice_b2c_1')
                    + self.ref('demo_invoice_b2c_2')
                    + self.ref('demo_reconcile_b2b_1')
                    + self.ref('demo_vendor_bill_b2b_1')
                    + self.ref('demo_vendor_bill_b2b_2')
                    + self.ref('demo_vendor_bill_b2b_3')
                )
                for move in invoices:
                    try:
                        move.action_post()
                    except (UserError, ValidationError):
                        _logger.exception('Error while posting demo data')
        else:
            return super()._post_load_demo_data(company)
