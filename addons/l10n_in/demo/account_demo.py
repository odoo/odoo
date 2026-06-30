# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.account.demo.account_demo import file_read
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _install_demo(self, companies):
        if not isinstance(companies, models.BaseModel):
            companies = self.env['res.company'].browse(companies)
        in_without_state = companies.filtered(lambda c: c.chart_template == "in" and not c.state_id)
        if in_without_state:
            _logger.warning('Error while loading Indian-Accounting demo data in the companies "%s". State is not set in the company.', companies.mapped('name'))
        return super()._install_demo(companies - in_without_state)

    @template(template='in', model='res.company', demo=True)
    def _l10n_in_res_company_demo(self):
        return {
            self.env.company.id: {
                'account_use_credit_limit': True,
                'account_credit_limit': 10000,
                'l10n_in_is_gst_registered': True,
                'l10n_in_tcs_feature': True,
                'l10n_in_tds_feature': True,
                'l10n_in_edi_production_env': False,
            },
        }

    @template(template='in', model='res.partner.category', demo=True)
    def _l10n_in_res_partner_category_demo(self):
        return {
            'res_partner_category_registered': {
                'name': 'Registered',
                'color': 2,
            },
            'res_partner_category_unregistered': {
                'name': 'Unregistered',
                'color': 3,
            },
        }

    @template(template='in', model='res.partner', demo=True)
    def _l10n_in_res_partner_demo(self):
        company = self.env.company
        inter_state_ref = 'base.state_in_ts'
        intra_state_ref = 'base.state_in_gj'
        default_partner_dict = {'country_id': 'base.in', 'company_id': company.id}
        return {
            'res_partner_registered_customer': {
                **default_partner_dict,
                'name': 'B2B Customer Intra State',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': '201, Second Floor, IT Tower 4',
                'street2': 'InfoCity Gate - 1, Infocity',
                'city': 'Gandhinagar',
                'state_id': 'base.state_in_gj',
                'zip': '382010',
                'vat': '24AABCT1332L2ZD',
            },
            'res_partner_registered_customer_inter_state': {
                **default_partner_dict,
                'name': 'B2B Customer Inter State',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': 'floor-1, Maddikunta-Ankanpally Village',
                'street2': 'Post box No 2, NH-65',
                'city': 'Hyderabad',
                'state_id': inter_state_ref,
                'zip': '500014',
                'vat': '36AAACM4154G1ZO',
            },
            'res_partner_unregistered_customer':{
                **default_partner_dict,
                'name': 'B2C Customer Intra State',
                'category_id': 'res_partner_category_unregistered',
                'l10n_in_gst_treatment': 'unregistered',
                'street': 'B105, yogeshwar Tower',
                'state_id': intra_state_ref,
                'city': 'Rajkot',
                'zip': '360001'
            },
            'res_partner_unregistered_customer_inter_state':{
                **default_partner_dict,
                'name': 'B2C Customer Inter State',
                'category_id': 'res_partner_category_unregistered',
                'l10n_in_gst_treatment': 'unregistered',
                'street': '80, Sarojini Devi Road',
                'city': 'Hyderabad',
                'state_id': inter_state_ref,
                'zip': '500003'
            },
            'res_partner_registered_supplier_1': {
                **default_partner_dict,
                'name': 'Supplier',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': '19, Ground Floor',
                'street2': 'Survey Road,Vadipatti',
                'city': 'Madurai',
                'state_id': 'base.state_in_tn',
                'zip': '625218',
                'vat': '33AACCT6304M1DB',
            },
            'res_partner_registered_supplier_2': {
                **default_partner_dict,
                'name': 'Odoo In Private Limited',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': '401, Fourth Floor, IT Tower 4',
                'street2': 'InfoCity Gate - 1, Infocity',
                'city': 'Hyderabad',
                'state_id': inter_state_ref,
                'zip': '500014',
                'vat': '36AACCT6304M1ZB',
            },
            'res_partner_overseas': {
                'name': 'Supplier Overseas',
                'l10n_in_gst_treatment': 'overseas',
                'street': '142 Street, Rigas building',
                'street2': 'Survey Road,',
                'city': 'City',
                'zip': '000000',
                'state_id': 'base.state_us_5',
                'country_id': 'base.us',
                'company_id': company.id,
            },
            'res_partner_sez': {
                'name': 'Coolware SEZ Unit',
                'l10n_in_gst_treatment': 'special_economic_zone',
                'street': 'Plot 102',
                'street2': 'Gift City',
                'city': 'Gandhinagar',
                'zip': '382335',
                'state_id': intra_state_ref,
                'country_id': 'base.in',
                'vat': '24AAACC1234F1Z7',
            },
        }

    @template(model='account.move', demo=True)
    def _get_demo_data_move(self, template_code):
        if template_code == "in":
            return {
                # Demo for GSTR-1
                # Demo of B2B (business-to-business) Taxable supplies made to other registered person.
                self.company_xmlid('demo_invoice_b2b_1'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 5,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_sale_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['sgst_sale_18'])],
                        }),
                    ],
                },
                self.company_xmlid('demo_invoice_b2b_2'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_15days',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 1,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_sale_18_rc'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 1,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18_rc'])],
                        }),
                    ],
                },
                self.company_xmlid('demo_invoice_b2b_3'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 3,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_sale_18'])],
                        }),
                    ],
                },
                #  Demo of B2CL (business to consumer - Large) Taxable supplies made to other unregistered Person and invoice value is more than INR 1 lakh.
                self.company_xmlid('demo_invoice_b2cl_1'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_30days',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 2,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 3,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                    ],
                },
                self.company_xmlid('demo_invoice_b2cl_2'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_gst_treatment': 'consumer',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 3,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                    ],
                },
                # Demo of Exports, SEZ/SEZ and deemed exports.
                self.company_xmlid('demo_invoice_export'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_overseas',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_shipping_bill_number': '999704',
                    'l10n_in_shipping_bill_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_shipping_port_code_id': 'l10n_in.port_code_inixy1',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 2,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_sale_18_exp'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 5,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18_exp'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_invoice_sez'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_sez',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_21days',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 2,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 1,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_invoice_deemed_exp'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_gst_treatment': 'deemed_export',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 4,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 1,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                    ],
                },
                # Demo of B2CS (business to consumer small) Taxable supplies made to other unregistered Person and below INR 1 lakh invoice value.
                self.company_xmlid('demo_invoice_b2cs'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_gst_treatment': 'consumer',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 1,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_sale_18'])],
                        }),
                    ],
                },
                # Demo of Nil Rated, Exempted and Non GST supplies.
                self.company_xmlid('demo_invoice_nil_rated'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_gst_treatment': 'consumer',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('NIL RATED PRODUCT'),
                            'quantity': 1,
                            'price_unit': 65000.0,
                            'tax_ids': [Command.set(['nil_rated_sale'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_invoice_exempt'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_15days',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_gst_treatment': 'consumer',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('EXEMPT PRODUCT'),
                            'quantity': 1,
                            'price_unit': 52000.0,
                            'tax_ids': [Command.set(['exempt_sale'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_invoice_ngst'): {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('NON GST PRODUCT'),
                            'quantity': 1,
                            'price_unit': 75000.0,
                            'tax_ids': [Command.set(['non_gst_supplies_sale'])],
                        }),
                    ]
                },
                # Demo of credit note for registered person (b2b).
                self.company_xmlid('demo_invoice_cdnr'): {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'reversed_entry_id': 'demo_invoice_b2b_3',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 3,
                            'price_unit': 50000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_sale_18'])],
                        }),
                    ]
                },
                # Demo of credit note for unregistered person (b2c).
                self.company_xmlid('demo_invoice_cdnur'): {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'l10n_in_gst_treatment': 'consumer',
                    'reversed_entry_id': 'demo_invoice_b2cl_2',
                    'journal_id': 'sale',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 3,
                            'price_unit': 40000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_sale_18'])],
                        }),
                    ]
                },
                # Demo data for GSTR-2B
                # Demo of Purchase Received From Registered Taxpayers
                self.company_xmlid('demo_bill_b2b_1'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_1',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_immediate',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 10,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 5,
                            'price_unit': 22000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_bill_b2b_2'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_15days',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 7,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 5,
                            'price_unit': 22000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_bill_b2b_3'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_1',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 5,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 2,
                            'price_unit': 22000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_bill_b2b_4'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 6,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 2,
                            'price_unit': 22000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                    ]
                },
                # Details of Credit/Debit Notes for Registered Taxpayers
                self.company_xmlid('demo_bill_cdnr'): {
                    'move_type': 'in_refund',
                    'partner_id': 'res_partner_registered_supplier_1',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 5,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 2,
                            'price_unit': 22000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_bill_dbnr'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_1',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'debit_origin_id': 'demo_bill_b2b_4',
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 2,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                        Command.create({
                            'name': self.env._('Refrigerator'),
                            'quantity': 1,
                            'price_unit': 22000.0,
                            'l10n_in_hsn_code': 8418,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                    ]
                },
                # Supplies received from compounding dealer and exempt/nil/non GST Supplies
                self.company_xmlid('demo_bill_exempt'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('EXEMPT PRODUCT'),
                            'quantity': 1,
                            'price_unit': 32000.0,
                            'tax_ids': [Command.set(['exempt_sale'])],
                        }),
                    ]
                },
                self.company_xmlid('demo_bill_nil_rated'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_unregistered_customer_inter_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date_due': fields.Date.today() - relativedelta(months=1),
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('NIL RATED PRODUCT'),
                            'quantity': 1,
                            'price_unit': 30000.0,
                            'tax_ids': [Command.set(['nil_rated_sale'])],
                        }),
                    ]
                },
                # Demo of IMP(Import) of supplies.
                self.company_xmlid('demo_bill_imp_of_supplies'): {
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_overseas',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Air Conditioner'),
                            'quantity': 10,
                            'price_unit': 20000.0,
                            'l10n_in_hsn_code': 8415,
                            'tax_ids': [Command.set(['igst_purchase_18'])],
                        }),
                    ]
                },
                # Demo bill with attachment
                self.company_xmlid('demo_bill_with_att'): {
                    'ref': 'MYS-91021146',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': False,
                    'invoice_date': fields.Date.today() - relativedelta(months=1),
                    'invoice_line_ids': [
                        Command.create({
                            'name': self.env._('Integrated Managed Infrastructure Service'),
                            'quantity': 1,
                            'account_id': 'p2112',
                            'price_unit': 69132.78,
                            'tax_ids': [Command.set(['sgst_purchase_18'])],
                        }),
                    ],
                    'message_main_attachment_id': 'ir_attachment_in_invoice_1',
                },
            }
        return super()._get_demo_data_move(template_code)

    @template(model='account.bank.statement', demo=True)
    def _get_demo_data_statement(self, template_code):
        return {} if template_code == 'in' else super()._get_demo_data_statement(template_code)

    @template(model='account.bank.statement.line', demo=True)
    def _get_demo_data_transactions(self, template_code):
        if template_code == 'in':
            last_day = int(self.env.company.fiscalyear_last_day)
            last_month = int(self.env.company.fiscalyear_last_month)
            move_date = fields.Date.today() - relativedelta(months=1)  # This date is set for all moves
            if move_date > date(move_date.year, last_month, last_day):
                fiscal_year = "%s-%s" % (move_date.strftime('%y'), (move_date + relativedelta(years=1)).strftime('%y'))
            else:
                fiscal_year = "%s-%s" % ((move_date + relativedelta(years=-1)).strftime('%y'), move_date.strftime('%y'))
            return {
                'demo_bank_statement_line_0': {
                    'journal_id': 'bank',
                    'payment_ref': 'Capital',
                    'amount': 100000.00,
                },
                'demo_bank_statement_line_1': {
                    'journal_id': 'bank',
                    'payment_ref': f'INV/{fiscal_year}/0001',
                    'amount': 200000.00,
                },
                'demo_bank_statement_line_2': {
                    'journal_id': 'bank',
                    'payment_ref': f'INV/{fiscal_year}/0002',
                    'amount': 90000.00,
                },
                'demo_bank_statement_line_3': {
                    'journal_id': 'bank',
                    'payment_ref': 'Rent',
                    'amount': -20000.00,
                },
                'demo_bank_statement_line_4': {
                    'journal_id': 'bank',
                    'payment_ref': f'BILL/{fiscal_year}/{move_date.month:02}/0001',
                    'amount': -110000.00,
                },
                'demo_bank_statement_line_5': {
                    'journal_id': 'bank',
                    'payment_ref': f'INV/{fiscal_year}/0009',
                    'amount': 59000.00,
                },
                'demo_bank_statement_line_6': {
                    'journal_id': 'bank',
                    'payment_ref': 'Bank Charges',
                    'amount': -5400.00,
                },
                'demo_bank_statement_line_7': {
                    'journal_id': 'bank',
                    'payment_ref': f'BILL/{fiscal_year}/{move_date.month:02}/0005',
                    'amount': -32000.00,
                },
            }
        else:
            return super()._get_demo_data_transactions(template_code)

    @template(model='ir.attachment', demo=True)
    def _get_demo_data_attachment(self, chart_template):
        if chart_template == "in":
            return {
                'ir_attachment_in_invoice_1': {
                    'type': 'binary',
                    'name': 'in_invoice_demo_1.pdf',
                    'res_model': 'account.move',
                    'res_id': 'demo_bill_with_att',
                    'raw': file_read('l10n_in/static/demo/in_invoice_demo_1.pdf'),
                }
            }
        return super()._get_demo_data_attachment(chart_template)

    @template(model='mail.message', demo=True)
    def _get_demo_data_mail_message(self, chart_template):
        if chart_template == "in":
            return {
                'mail_message_in_invoice_1': {
                    'model': 'account.move',
                    'res_id': 'demo_bill_with_att',
                    'body': 'Vendor Bill attachment',
                    'message_type': 'comment',
                    'author_id': 'base.partner_demo',
                    'attachment_ids': [Command.set([
                        'ir_attachment_in_invoice_1',
                    ])]
                },
            }
        return super()._get_demo_data_mail_message(chart_template)

    @template(model='mail.activity', demo=True)
    def _get_demo_data_mail_activity(self, template_code):
        return {} if template_code == 'in' else super()._get_demo_data_mail_activity(template_code)

    def _post_load_demo_data(self, template_code):
        if template_code == "in":
            invoices = (
                self.ref('demo_invoice_b2b_1')
                + self.ref('demo_invoice_b2b_2')
                + self.ref('demo_invoice_b2b_3')
                + self.ref('demo_invoice_b2cl_1')
                + self.ref('demo_invoice_b2cl_2')
                + self.ref('demo_invoice_export')
                + self.ref('demo_invoice_sez')
                + self.ref('demo_invoice_deemed_exp')
                + self.ref('demo_invoice_b2cs')
                + self.ref('demo_invoice_nil_rated')
                + self.ref('demo_invoice_exempt')
                + self.ref('demo_invoice_ngst')
                + self.ref('demo_invoice_cdnr')
                + self.ref('demo_invoice_cdnur')
                + self.ref('demo_bill_b2b_1')
                + self.ref('demo_bill_b2b_2')
                + self.ref('demo_bill_b2b_3')
                + self.ref('demo_bill_b2b_4')
                + self.ref('demo_bill_cdnr')
                + self.ref('demo_bill_dbnr')
                + self.ref('demo_bill_exempt')
                + self.ref('demo_bill_nil_rated')
                + self.ref('demo_bill_imp_of_supplies')
                + self.ref('demo_bill_with_att')
            )
            for move in invoices:
                try:
                    move.action_post()
                except (UserError, ValidationError):
                    _logger.exception('Error while posting demo data')
            if (bill := self.ref('demo_bill_with_att')).state == 'posted':
                try:
                    self.env['l10n_in.withhold.wizard'].with_context(
                        active_model='account.move',
                        active_ids=bill.ids,
                    ).create({
                        'tax_id': self.env.ref(f'account.{bill.company_id.id}_tds_10_us_393_1_6_iii_b').id,
                        'base': bill.amount_untaxed,
                        'date': bill.invoice_date,
                    }).action_create_and_post_withhold()
                except (UserError, ValidationError):
                    _logger.exception('Error while creating TDS Entry for demo data')
        else:
            super()._post_load_demo_data(template_code)
