from datetime import datetime

from odoo import Command, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(template='sa', model='res.partner', demo=True)
    def _l10n_sa_res_partner_demo(self):
        default_partner_dict = {'country_id': 'base.sa', 'company_id': self.env.company.id}
        return {
          'l10n_sa.partner_demo_customer_company_1_sa': {
                **default_partner_dict,
                'name': 'Gulf Seals LLC',
                'email': 'info@gulfseals.example.sa',
                'phone': '+966 12 345 6789',
                'street': 'King Fahd Road',
                'street2': 'Al Olaya District',
                'city': 'Riyadh',
                'state_id': 'base.state_sa_70',
                'zip': '12313',
                'website': 'https://www.gulfseals-example.sa',
                'vat': '301765432100003',
                'is_company': True,
            },
            'l10n_sa.partner_demo_customer_company_2_sa': {
                **default_partner_dict,
                'name': 'Royal Tech Solutions Co.',
                'email': 'info@royaltechsolutions.example.sa',
                'phone': '+966 11 456 7890',
                'street': 'KAFD Tower 9, Floor 15, King Fahd Road',
                'street2': 'King Abdullah Financial District',
                'city': 'Riyadh',
                'state_id': 'base.state_sa_70',
                'zip': '13511',
                'website': 'https://www.royaltech-solutions-example.com',
                'vat': '301456789000003',
                'is_company': True,
            },
            'l10n_sa.partner_demo_customer_individual_sa': {
                **default_partner_dict,
                'name': 'Omar Elhout',
                'email': 'o.elhout@mail.example.sa',
                'phone': '+966 50 352 8120',
                'street': '1605, Elhout Tower',
                'street2': 'Al-Murabba',
                'city': 'Riyadh',
                'state_id': 'base.state_sa_70',
                'zip': '35267',
                'is_company': False,
            },
            'l10n_sa.partner_demo_vendor_1_sa': {
                **default_partner_dict,
                'name': 'Aqua Steel',
                'email': 'info@aquasteel.example.sa',
                'phone': '+966 11 123 4567',
                'street': 'Al Bandariyyah Street',
                'street2': 'Al Falah',
                'city': 'Al Arid',
                'state_id': 'base.state_sa_70',
                'zip': '12321',
                'website': 'http://www.aquasteel-example.sa',
                'vat': '310105071360003',
                'is_company': True,
            },
            'l10n_sa.partner_demo_vendor_2_sa': {
                **default_partner_dict,
                'name': 'Horizon Industrial Services Co.',
                'email': 'info@horizon-industries.example.sa',
                'phone': '+966 11 987 6543',
                'street': 'Building 6529, Office 210',
                'street2': 'Olaya Street',
                'city': 'Riyadh',
                'state_id': 'base.state_sa_70',
                'zip': '12283',
                'website': 'https://www.horizon-industries-example.sa',
                'vat': '301234981200003',
                'is_company': True,
            },
        }

    @template(model='account.move', demo=True)
    def _get_demo_data_move(self, template_code):
        if template_code == "sa":
            data = super()._get_demo_data_move(template_code)
            data.update({
                'demo_sa_invoice_1': {
                    'move_type': 'out_invoice',
                    'partner_id': 'l10n_sa.partner_demo_customer_company_1_sa',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'journal_id': 'sale',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_8',
                            'quantity': 2,
                            'price_unit': 320.0,
                            'tax_ids': [Command.set(['sa_sales_tax_15'])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 47.0,
                            'tax_ids': [Command.set(['sa_sales_tax_15'])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 1,
                            'price_unit': 140.0,
                            'tax_ids': [Command.set(['sa_sales_tax_15'])],
                        }),
                    ],
                },
                'demo_sa_invoice_2': {
                    'move_type': 'out_invoice',
                    'partner_id': 'base.res_partner_2',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'journal_id': 'sale',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_6',
                            'quantity': 2,
                            'price_unit': 320.0,
                            'tax_ids': [Command.set(['sa_exempt_sales_tax_0'])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 3,
                            'price_unit': 47.0,
                            'tax_ids': [Command.set(['sa_exempt_sales_tax_0'])],
                        }),
                    ],
                },
                'demo_sa_invoice_3': {
                    'move_type': 'out_invoice',
                    'partner_id': 'l10n_sa.partner_demo_customer_company_2_sa',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'journal_id': 'sale',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_7',
                            'quantity': 2,
                            'price_unit': 14.0,
                            'tax_ids': [Command.set(['sa_exempt_sales_tax_0'])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 3,
                            'price_unit': 140.0,
                            'tax_ids': [Command.set(['sa_exempt_sales_tax_0'])],
                        }),
                    ],
                },
                'demo_sa_invoice_4': {
                    'move_type': 'out_invoice',
                    'partner_id': 'l10n_sa.partner_demo_customer_individual_sa',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'journal_id': 'sale',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_6',
                            'quantity': 2,
                            'price_unit': 320.0,
                            'tax_ids': [Command.set(['sa_sales_tax_15'])],
                        }),
                    ],
                },
                'demo_sa_bill_1': {
                    'move_type': 'in_invoice',
                    'partner_id': 'l10n_sa.partner_demo_vendor_1_sa',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'delivery_date': datetime.now(),
                    'journal_id': 'purchase',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_6',
                            'quantity': 2,
                            'price_unit': 90.0,
                            'tax_ids': [Command.set(['sa_purchase_tax_15'])],
                        }),
                        Command.create({
                            'product_id': 'product.product_product_7',
                            'quantity': 9,
                            'price_unit': 65.0,
                            'tax_ids': [Command.set(['sa_purchase_tax_15'])],
                        }),
                    ],
                },
                'demo_sa_bill_2': {
                    'move_type': 'in_invoice',
                    'partner_id': 'base.res_partner_3',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'delivery_date': datetime.now(),
                    'journal_id': 'purchase',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_10',
                            'quantity': 5,
                            'price_unit': 40.0,
                            'tax_ids': [Command.set(['sa_withholding_tax_5_rental'])],
                        }),
                    ],
                },
                'demo_sa_bill_3': {
                    'move_type': 'in_invoice',
                    'partner_id': 'base.res_partner_4',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'delivery_date': datetime.now(),
                    'journal_id': 'purchase',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_9',
                            'quantity': 4,
                            'price_unit': 30.0,
                            'tax_ids': [Command.set(['sa_import_tax_paid_15_paid_to_customs'])],
                        }),
                    ],
                },
                'demo_sa_bill_4': {
                    'move_type': 'in_invoice',
                    'partner_id': 'l10n_sa.partner_demo_vendor_2_sa',
                    'invoice_user_id': 'base.user_demo',
                    'invoice_date': datetime.now(),
                    'delivery_date': datetime.now(),
                    'journal_id': 'purchase',
                    'line_ids': [
                        Command.create({
                            'product_id': 'product.product_product_5',
                            'quantity': 10,
                            'price_unit': 35.0,
                            'tax_ids': [Command.set(['sa_purchases_tax_0'])],
                        }),
                    ],
                },
            })
            return data
        return super()._get_demo_data_move(template_code)

    def _post_load_demo_data(self, template_code):
        if template_code == "sa":
            invoices = (
                self.ref('demo_sa_invoice_1')
                + self.ref('demo_sa_invoice_2')
                + self.ref('demo_sa_invoice_3')
                + self.ref('demo_sa_invoice_4')
                + self.ref('demo_sa_bill_1')
                + self.ref('demo_sa_bill_2')
                + self.ref('demo_sa_bill_3')
                + self.ref('demo_sa_bill_4')
            )
            invoices.action_post()
        return super()._post_load_demo_data(template_code)
