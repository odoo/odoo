# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time
from datetime import datetime, timedelta

from odoo import api, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = {}
        if company.account_fiscal_country_id.code == "IN":
            if company.state_id:
                demo_data = {
                    'res.partner.category': self._get_demo_data_res_partner_category(company),
                    'res.partner': self._get_demo_data_partner(company),
                    'account.move': self._get_demo_data_move(company),
                    'res.config.settings': self._get_demo_data_config_settings(company),
                    'ir.attachment': self._get_demo_data_attachment(company),
                    'mail.message': self._get_demo_data_mail_message(company),
                }
            else:
                _logger.warning('Error while loading Indian-Accounting demo data in the company "%s".State is not set in the company.', company.name)
        else:
            demo_data = super()._get_demo_data(company)
        return demo_data

    @api.model
    def _get_demo_data_config_settings(self, company=False):
        return{
            'sales_credit_limit':{
                'account_use_credit_limit': True,
                'account_default_credit_limit': '10000'
            }
        }

    @api.model
    def _get_demo_data_res_partner_category(self, company=False):
        return{
            'res_partner_category_registered': {
                'name': 'Registered',
                'color': 2,
            },
            'res_partner_category_unregistered': {
                'name': 'Unregistered',
                'color': 3,
            },
        }

    @api.model
    def _get_demo_data_partner(self, company=False):
        cid = company.id or self.env.company.id
        intra_state_id = company.state_id
        inter_state_id = self.env['res.country.state'].search([
            ('id', 'not in', intra_state_id.ids),
            ('country_id', '=', intra_state_id.country_id.id)
        ], order='name DESC', limit=1)
        default_partner_dict = {'city': 'City', 'zip': '000000', 'country_id': 'base.in', 'is_company': True}
        return{
            'res_partner_registered_customer': {
                **default_partner_dict,
                'name': 'B2B Customer Inter State',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': '201, Second Floor, IT Tower 4',
                'street2': 'InfoCity Gate - 1, Infocity',
                'state_id': inter_state_id.id,
                'company_id': cid,
                'vat': '%sAABCT1332L2ZD'%(inter_state_id.l10n_in_tin),
            },
            'res_partner_registered_customer_intra_state': {
                **default_partner_dict,
                'name': 'B2B Customer Intra State',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': 'floor-1, Maddikunta-Ankanpally Village',
                'street2': 'Post box No 2, NH-65',
                'state_id': intra_state_id.id,
                'company_id': cid,
                'vat': '%sAAACM4154G1ZO'%(intra_state_id.l10n_in_tin),
            },
            'res_partner_unregistered_customer':{
                **default_partner_dict,
                'name': 'B2C Customer Inter State',
                'category_id': 'res_partner_category_unregistered',
                'l10n_in_gst_treatment': 'unregistered',
                'street': 'B105, yogeshwar Tower',
                'state_id': inter_state_id.id,
                'company_id': cid,
            },
            'res_partner_unregistered_customer_intra_state':{
                **default_partner_dict,
                'name': 'B2C Customer Intra State',
                'category_id': 'res_partner_category_unregistered',
                'l10n_in_gst_treatment': 'unregistered',
                'street': '80, Sarojini Devi Road',
                'state_id': intra_state_id.id,
                'company_id': cid,
            },
            'res_partner_registered_supplier_1': {
                **default_partner_dict,
                'name': 'Supplier',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': '19, Ground Floor',
                'street2': 'Survey Road,Vadipatti',
                'state_id': inter_state_id.id,
                'company_id': cid,
                'vat': '%sAACCT6304M1DB'%(inter_state_id.l10n_in_tin),
            },
            'res_partner_registered_supplier_2': {
                **default_partner_dict,
                'name': 'Odoo In Private Limited',
                'category_id': 'res_partner_category_registered',
                'l10n_in_gst_treatment': 'regular',
                'street': '201, Second Floor, IT Tower 4',
                'street2': 'InfoCity Gate - 1, Infocity',
                'state_id': inter_state_id.id,
                'company_id': cid,
                'vat': '%sAACCT6304M1ZB'%(inter_state_id.l10n_in_tin),
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
                'is_company': True,
                'company_id': cid,
            },
        }

    @api.model
    def _get_demo_data_move(self, company=False):
        cid = company.id or self.env.company.id
        def _get_tax_by_id(tax_id):
            tax = self.env.ref('account.%s_%s'%((cid), (tax_id)))
            return tax.id
        if company.account_fiscal_country_id.code == "IN":
            sale_journal = self.env['account.journal'].search(
                domain=[
                    *self.env['account.journal']._check_company_domain(cid),
                    ('type', '=', 'sale'),
                ], limit=1)
            return {
                # Demo of B2B (business-to-business) Taxable supplies made to other registered person.
                'demo_invoice_b2b_1': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'regular',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_28')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_28'), _get_tax_by_id('cess_5_plus_1591_sale')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 4,
                            'price_unit': 300.0,
                            'tax_ids':[Command.set([_get_tax_by_id('igst_sale_18')])],
                        }),
                    ],
                },
                'demo_invoice_b2b_2': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer_intra_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'regular',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 2,
                            'price_unit': 4000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('sgst_sale_5')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 3,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('sgst_sale_5')])],
                        }),
                    ],
                },
                'demo_bill_b2b_1': {
                    'ref': 'INV/001',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                    ]
                },
                'demo_bill_b2b_2': {
                    'ref': 'INV/002',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 4,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 3,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                    ]
                },
                'demo_bill_b2b_3': {
                    'ref': 'INV/003',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_1',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 2,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 3,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                    ]
                },
                'demo_invoice_to_extract': {
                    'move_type': 'in_invoice',
                    'message_main_attachment_id': 'ir_attachment_in_invoice_1',
                },
                'demo_invoice_service': {
                    'ref': 'MYS-91021146',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': False,
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'name': 'Integrated Managed Infrastructure Service',
                            'quantity': 1,
                            'price_unit': 69132.78,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                    ],
                    'message_main_attachment_id': 'ir_attachment_in_invoice_2',
                },
                # Demo of IMP(Import) of supplies.
                'demo_bill_imp': {
                    'ref': 'BOE/123',
                    'move_type': 'in_invoice',
                    'partner_id': 'res_partner_overseas',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_4',
                            'quantity': 30,
                            'price_unit': 9000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                    ]
                },
                # Demo of cdnr(Credit/ Debit Note for registered business). Create credit note for demo b2b bill.
                'demo_bill_cdnr_1': {
                    'ref': 'CR/001',
                    'move_type': 'in_refund',
                    'partner_id': 'res_partner_registered_supplier_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now() - timedelta(days=1),
                    'l10n_in_gst_treatment': 'regular',
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                        }),
                    ]
                },
                'demo_bill_cdnr_2': {
                        'ref': '000072',
                        'move_type': 'in_refund',
                        'partner_id': 'res_partner_registered_supplier_1',
                        'invoice_user_id': 'base.user_demo',
                        'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                        'invoice_date': datetime.now(),
                        'l10n_in_gst_treatment': 'regular',
                        'invoice_line_ids': [
                            Command.create({
                                'product_id': 'product.consu_delivery_01',
                                'quantity': 1,
                                'price_unit': 1000.0,
                                'tax_ids': [Command.set([_get_tax_by_id('igst_purchase_18')])],
                            }),
                        ]
                    },
                # Demo of B2CS (business to consumer small) Taxable supplies made to other unregistered Person and below INR 2.5 lakhs invoice value.
                'demo_invoice_b2cs': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer_intra_state',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'consumer',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_16',
                            'quantity': 1,
                            'price_unit': 1500.0,
                            'tax_ids': [Command.set([_get_tax_by_id('sgst_sale_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_20',
                            'quantity': 1,
                            'price_unit': 2300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('sgst_sale_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_22',
                            'quantity': 1,
                            'price_unit': 2600.0,
                            'tax_ids': [Command.set([_get_tax_by_id('sgst_sale_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_24',
                            'quantity': 2,
                            'price_unit': 1655.0,
                            'tax_ids': [Command.set([_get_tax_by_id('sgst_sale_5')])],
                        }),
                    ]
                },
                #  Demo of B2CL (business to consumer - Large) Taxable supplies made to other unregistered Person and invoice value is more than INR 2.5 lakhs.
                'demo_invoice_b2cl': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_unregistered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'consumer',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 3,
                            'price_unit': 90000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_18')])],
                        }),
                    ]
                },
                # Demo of EXP(Export) supplies including supplies to SEZ/SEZ Developer or deemed exports.
                'demo_invoice_exp': {
                    'move_type': 'out_invoice',
                    'partner_id': 'base.res_partner_3',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'overseas',
                    'l10n_in_shipping_bill_number': '999704',
                    'l10n_in_shipping_bill_date': time.strftime('%Y-%m-02'),
                    'l10n_in_shipping_port_code_id': 'l10n_in.port_code_inixy1',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_4',
                            'quantity': 30,
                            'price_unit': 8000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_18_sez_exp')])],
                        }),
                    ]
                },
                # Demo of exempt(Nil Rated, Exempted and Non GST supplies). Set Nill rated and Exempted tax in line.
                'demo_invoice_nill': {
                    'move_type': 'out_invoice',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'regular',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_1',
                            'quantity': 2,
                            'price_unit': 25000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('exempt_sale')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_5',
                            'quantity': 1,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([_get_tax_by_id('nil_rated_sale')])],
                        }),
                    ]
                },
                # Demo of cdnr(Credit/ Debit Note for registered person). Create credit note for demo b2b invoice.
                'demo_invoice_cdnr_1': {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'regular',
                    'reversed_entry_id': 'demo_invoice_b2b_1',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 40000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_28')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 400.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_28'), _get_tax_by_id('cess_5_plus_1591_sale')])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 4,
                            'price_unit': 300.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_18')])],
                        }),
                    ]
                },
                'demo_invoice_cdnr_2': {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_registered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'regular',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 1,
                            'price_unit': 1000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_18')])],
                        }),
                        Command.create({
                            'product_id': 'product.consu_delivery_03',
                            'quantity': 1,
                            'price_unit': 2000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_18')])],
                        }),
                    ]
                },
                # Demo of cdnr(Credit/ Debit Note for unregistered person). Create credit note for demo b2cl invoice.
                'demo_invoice_cdnur': {
                    'move_type': 'out_refund',
                    'partner_id': 'res_partner_unregistered_customer',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                    'invoice_date': datetime.now(),
                    'l10n_in_gst_treatment': 'consumer',
                    'reversed_entry_id': 'demo_invoice_b2cl',
                    'journal_id': sale_journal.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': 'product.consu_delivery_01',
                            'quantity': 3,
                            'price_unit': 90000.0,
                            'tax_ids': [Command.set([_get_tax_by_id('igst_sale_18')])],
                        }),
                    ]
                },
            }
        else:
            return super()._get_demo_data_move(company)

    @api.model
    def _get_demo_data_attachment(self, company=False):
        if company.account_fiscal_country_id.code == "IN":
            return{
                'ir_attachment_in_invoice_1': {
                    'type': 'binary',
                    'name': 'in_invoice_demo_1.pdf',
                    'res_model': 'account.move',
                    'res_id': 'demo_invoice_to_extract',
                    'raw': file_open(
                        'l10n_in/static/demo/in_invoice_demo_1.pdf', 'rb'
                    ).read()
                },
                'ir_attachment_in_invoice_2': {
                    'type': 'binary',
                    'name': 'in_invoice_demo_2.pdf',
                    'res_model': 'account.move',
                    'res_id': 'demo_invoice_service',
                    'raw': file_open(
                        'l10n_in/static/demo/in_invoice_demo_2.pdf', 'rb'
                    ).read()
                }
            }
        else:
            return super()._get_demo_data_attachment(company)


    @api.model
    def _get_demo_data_mail_message(self, company=False):
        if company.account_fiscal_country_id.code == "IN":
            return {
                'mail_message_in_invoice_1': {
                    'model': 'account.move',
                    'res_id': 'demo_invoice_to_extract',
                    'body': 'Vendor Bill attachment',
                    'message_type': 'comment',
                    'author_id': 'base.partner_demo',
                    'attachment_ids': [Command.set([
                        'ir_attachment_in_invoice_1',
                    ])]
                },
                'mail_message_in_invoice_2': {
                    'model': 'account.move',
                    'res_id': 'demo_invoice_service',
                    'body': 'Vendor Bill attachment',
                    'message_type': 'comment',
                    'author_id': 'base.partner_demo',
                    'attachment_ids': [Command.set([
                        'ir_attachment_in_invoice_2',
                    ])]
                },
            }
        else:
            return super()._get_demo_data_mail_message(company)

    def _post_load_demo_data(self, company=False):
        if company.account_fiscal_country_id.code == "IN":
            if company.state_id:
                invoices = (
                    self.ref('demo_invoice_b2b_1')
                    + self.ref('demo_invoice_b2b_2')
                    + self.ref('demo_invoice_b2cs')
                    + self.ref('demo_invoice_b2cl')
                    + self.ref('demo_invoice_exp')
                    + self.ref('demo_invoice_nill')
                    + self.ref('demo_invoice_cdnr_1')
                    + self.ref('demo_invoice_cdnr_2')
                    + self.ref('demo_invoice_cdnur')
                    + self.ref('demo_bill_b2b_1')
                    + self.ref('demo_bill_b2b_2')
                    + self.ref('demo_bill_b2b_3')
                    + self.ref('demo_bill_imp')
                    + self.ref('demo_bill_cdnr_1')
                    + self.ref('demo_bill_cdnr_2')
                    + self.ref('demo_invoice_service')
                )
                for move in invoices:
                    try:
                        move.action_post()
                    except (UserError, ValidationError):
                        _logger.exception('Error while posting demo data')
        else:
            return super()._post_load_demo_data(company)
