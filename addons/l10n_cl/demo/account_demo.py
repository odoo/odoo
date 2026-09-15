# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _set_partner_account_payable(self):
        fee_partner = self.env.ref('l10n_cl.demo_partner_cl_fee_receipts')
        account_payable = self.ref('account_210520')
        fee_partner.property_account_payable_id = account_payable
        return fee_partner

    @api.model
    def _get_demo_data_move(self, company=False):
        # EXTEND account
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code != "CL":
            return move_data

        self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(company),
            ('type', '=', 'purchase'),
        ]).l10n_latam_use_documents = False

        today = fields.Date.today()

        # Create currency rates
        usd_rate_value = 1 / 980.0
        uf_rate_value = 1 / 38400.0
        currency_usd = self.env.ref('base.USD')
        currency_uf = self.env.ref('l10n_cl.UF')
        first_day_of_rate = (today - timedelta(days=60)).replace(day=1)
        last_date_of_rate = (today + timedelta(days=60)).replace(day=1) - timedelta(days=1)

        self.env['res.currency.rate'].create([
            {
                'currency_id': currency_usd.id,
                'rate': usd_rate_value,
                'name': first_day_of_rate,
                'company_id': company.id,
            },
            {
                'currency_id': currency_usd.id,
                'rate': usd_rate_value,
                'name': last_date_of_rate,
                'company_id': company.id,
            },
            {
                'currency_id': currency_uf.id,
                'rate': uf_rate_value,
                'name': first_day_of_rate,
                'company_id': company.id,
            },
            {
                'currency_id': currency_uf.id,
                'rate': uf_rate_value,
                'name': last_date_of_rate,
                'company_id': company.id,
            },
        ])

        exports_purchase_journal = self.ref('purchase')
        exports_purchase_journal.l10n_latam_use_documents = False

        local_sale_journal = self.env['account.journal'].search([('company_id', '=', company.id), ('type', '=', 'sale')], limit=1)
        local_purchase_journal = self.env['account.journal'].search(
            [('company_id', '=', company.id), ('type', '=', 'purchase'), ('sequence', '=', 2)],
            limit=1
        )

        fp_exempt_id = self.ref('afpt_sale_exempt').id
        fp_exports_id = self.ref('afpt_sale_exports').id
        fp_imports_id = self.ref('afpt_purchase_imports').id
        fp_fees_id = self.ref('afpt_purchase_fees').id
        fp_supermarket_id = self.ref('afpt_purchase_supermarket').id
        fp_purchase_exempt_id = self.ref('afpt_purchase_exempt').id

        sale_tax_id = self.ref('ITAX_19').id
        ila_18_id = self.ref('ila_a_180_s').id
        purchase_tax_id = self.ref('OTAX_19').id
        ret_tax_id = self.ref('I_RTI').id
        supermarket_tax_id = self.ref('iva_supermercado_recup').id

        # Modify existing moves
        move_data[self.company_xmlid('demo_invoice_1')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_invoice_2')].update({
            'journal_id': local_sale_journal.id,
            # use the invoice date as the same as this credit note, to have a consistent positive value in sales
            'invoice_date': move_data[self.company_xmlid('demo_move_auto_reconcile_2')]['invoice_date'],
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_invoice_3')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_invoice_followup')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_invoice_5')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_imports_id,
        })

        move_data[self.company_xmlid('demo_invoice_6')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_imports_id,
        })

        move_data[self.company_xmlid('demo_invoice_7')].update({
            'journal_id': local_sale_journal.id,
            # use the invoice date as the same as this credit note, to have a consistent positive value in sales
            'invoice_date': move_data[self.company_xmlid('demo_move_auto_reconcile_2')]['invoice_date'],
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_imports_id,
        })

        move_data[self.company_xmlid('demo_invoice_8')].update({
            'l10n_latam_document_type_id': 'l10n_cl.dc_fc_f_dte',
            'invoice_line_ids': [
                Command.clear(),
                Command.create({
                    'product_id': 'product.product_product_2',
                    'price_unit': 34.50 / usd_rate_value,
                    'quantity': 1,
                    'tax_ids': [Command.set([
                        purchase_tax_id,
                        ret_tax_id,
                    ])]
                })
            ]
        })

        move_data[self.company_xmlid('demo_invoice_9')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_invoice_10')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_fe_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_invoice_equipment_purchase')].update({
            'journal_id': exports_purchase_journal.id,
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_imports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_1')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_ncex_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_2')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_ncex_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_5')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_ncex_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_6')].update({
            'l10n_latam_document_type_id': 'l10n_cl.dc_ncex_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_7')].update({
            'l10n_latam_document_type_id': 'l10n_cl.dc_ncex_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_exports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_3')].update({
            'journal_id': exports_purchase_journal.id,
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_imports_id,
        })

        move_data[self.company_xmlid('demo_move_auto_reconcile_4')].update({
            'journal_id': local_sale_journal.id,
            'l10n_latam_document_type_id': 'l10n_cl.dc_ncex_dte',
            'currency_id': 'base.USD',
            'fiscal_position_id': fp_imports_id,
        })

        # Create new moves
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
                Command.create({'product_id': 'product.product_product_2', 'price_unit': 64200.0, 'quantity': 1, 'tax_ids': [Command.set([sale_tax_id])]}),
                Command.create({'product_id': 'product.product_product_12', 'price_unit': 12500.0, 'quantity': 3, 'tax_ids': [Command.set([sale_tax_id])]}),
                Command.create({'product_id': 'product.product_product_16', 'price_unit': 2520.0, 'quantity': 15, 'tax_ids': [Command.set([sale_tax_id])]}),
                Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 4, 'tax_ids': [Command.set([sale_tax_id])]}),
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
                Command.create({'product_id': 'product.product_product_2', 'price_unit': 64200.0, 'quantity': 3, 'tax_ids': [Command.set([sale_tax_id])]}),
                Command.create({'product_id': 'product.product_product_16', 'price_unit': 2520.0, 'quantity': 10, 'tax_ids': [Command.set([ila_18_id])]}),
                Command.create({'product_id': 'product.product_product_20', 'price_unit': 1950.0, 'quantity': 2}),
            ],
        }

        # sale - exempt invoice
        move_data['demo_cl_exempt_invoice_1'] = {
            'company_id': company.id,
            'move_type': 'out_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_y_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_3',
            'fiscal_position_id': fp_exempt_id,
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
                Command.create({'product_id': 'product.product_product_2', 'price_unit': 3.0, 'quantity': 1, 'tax_ids': [Command.set([sale_tax_id])]}),
            ],
        }
        # credit note in CLP cancelling demo_cl_exempt_invoice_1
        move_data['demo_cl_credit_note_1'] = {
            'company_id': company.id,
            'move_type': 'out_refund',
            'l10n_latam_document_type_id': 'l10n_cl.dc_nc_f_dte',
            'partner_id': 'l10n_cl.demo_partner_cl_3',
            'fiscal_position_id': fp_exempt_id,
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
                Command.create({'name': 'Discount', 'price_unit': 24200.0, 'quantity': 1}),
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
            ('1', '2', '5'),
            ('2', '5', '7'),
            ('5', '7', '9'),
            ('7', '9', '10'),
        ]
        for receipt, (prod1, prod2, prod3) in zip(range(1, 5), products_for_receipts):
            move_data[f'demo_cl_boleta_{receipt}'] = {
                'company_id': company.id,
                'move_type': 'out_invoice',
                'l10n_latam_document_type_id': 'l10n_cl.dc_b_f_dte',
                'partner_id': 'l10n_cl.par_cfa',
                'journal_id': local_sale_journal.id,
                'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
                'invoice_date': today - relativedelta(months=1),
                'invoice_line_ids': [
                    Command.create({'product_id': f'product.product_product_{prod1}', 'quantity': 1, 'tax_ids': [Command.set([sale_tax_id])]}),
                    Command.create({'product_id': f'product.product_product_{prod2}', 'quantity': 3, 'tax_ids': [Command.set([sale_tax_id])]}),
                    Command.create({'product_id': f'product.product_product_{prod3}', 'quantity': 4, 'tax_ids': [Command.set([sale_tax_id])]}),
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
                Command.create({'product_id': 'product.product_product_16', 'price_unit': 1008.0, 'quantity': 100, 'tax_ids': [Command.set([purchase_tax_id])]}),
                Command.create({'product_id': 'product.product_product_20', 'price_unit': 980.0, 'quantity': 200, 'tax_ids': [Command.set([purchase_tax_id])]}),
            ],
        }
        move_data['demo_cl_invoice_4'] = {
            'company_id': company.id,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_y_f_dte',
            'l10n_latam_document_number': '832',
            'fiscal_position_id': fp_purchase_exempt_id,
            'partner_id': 'l10n_cl.res_partner_bmya',
            'journal_id': local_purchase_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today - relativedelta(months=1),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 890500.0, 'quantity': 3, 'tax_ids': [Command.set([purchase_tax_id])]}),
            ],
        }
        # purchase supermarket bill
        move_data['demo_cl_invoice_5'] = {
            'company_id': company.id,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_a_f_dte',
            'l10n_latam_document_number': '10512',
            'fiscal_position_id': fp_supermarket_id,
            'partner_id': 'l10n_cl.demo_partner_supermarket',
            'journal_id': local_purchase_journal.id,
            'invoice_date': today - timedelta(days=29),
            'invoice_line_ids': [
                Command.create({'product_id': 'product.monitor_stand_product_template', 'price_unit': 28500.0, 'quantity': 1, 'tax_ids': [Command.set([supermarket_tax_id])]}),
            ],
        }
        # Purchase fees bill (in_invoice) in CLP
        move_data['demo_cl_fee_bill_1'] = {
            'company_id': company.id,
            'fiscal_position_id': fp_fees_id,
            'move_type': 'in_invoice',
            'l10n_latam_document_type_id': 'l10n_cl.dc_m_d_dtn',
            'l10n_latam_document_number': '22',
            'partner_id': self._set_partner_account_payable().id,
            'journal_id': local_purchase_journal.id,
            'invoice_payment_term_id': 'account.account_payment_term_end_following_month',
            'invoice_date': today - timedelta(days=30),
            'invoice_date_due': today,
            'invoice_line_ids': [
                Command.create({'product_id': 'product.product_product_1_product_template', 'price_unit': 1000000.0, 'quantity': 1}),
            ],
        }
        # national purchase credit note
        move_data['demo_cl_credit_note_2'] = {
            'company_id': company.id,
            'move_type': 'in_refund',
            'fiscal_position_id': fp_purchase_exempt_id,
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
            super()._post_load_demo_data(company)
            return

        moves = self.env['account.move'].search([
            ('company_id', '=', company.id),
            ('partner_id', '!=', False),
            ('move_type', '!=', 'entry')
        ])

        for move in moves:
            move.action_post()
