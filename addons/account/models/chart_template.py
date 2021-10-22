# -*- coding: utf-8 -*-

from odoo import api, models, _, Command
from odoo.http import request
from odoo.modules import get_resource_path
from odoo.addons.base.models.ir_translation import IrTranslationImport
import csv
import ast
from collections import defaultdict

import logging

_logger = logging.getLogger(__name__)


    name = fields.Char(required=True)
    parent_id = fields.Many2one('account.chart.template', string='Parent Chart Template')
    code_digits = fields.Integer(string='# of Digits', required=True, default=6, help="No. of Digits to use for account code")
    visible = fields.Boolean(string='Can be Visible?', default=True,
        help="Set this to False if you don't want this template to be used actively in the wizard that generate Chart of Accounts from "
            "templates, this is useful when you want to generate accounts of this template only when loading its child template.")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    use_anglo_saxon = fields.Boolean(string="Use Anglo-Saxon accounting", default=False)
    use_storno_accounting = fields.Boolean(string="Use Storno accounting", default=False)
    account_ids = fields.One2many('account.account.template', 'chart_template_id', string='Associated Account Templates')
    tax_template_ids = fields.One2many('account.tax.template', 'chart_template_id', string='Tax Template List',
        help='List of all the taxes that have to be installed by the wizard')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts', required=True)
    cash_account_code_prefix = fields.Char(string='Prefix of the main cash accounts', required=True)
    transfer_account_code_prefix = fields.Char(string='Prefix of the main transfer accounts', required=True)
    income_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Gain Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Loss Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="The country this chart of accounts belongs to. None if it's generic.")

    def _load_data(self, data):
        def deref(values, model):
            for field, value in values.items():
                if field not in model._fields:
                    continue
                if model._fields[field].type in ('many2one', 'integer', 'many2one_reference') and isinstance(value, str):
                    values[field] = self.env.ref(value).id
                elif model._fields[field].type in ('one2many', 'many2many'):
                    if value and isinstance(value[0], (list, tuple)):
                        for command in value:
                            if command[0] in (Command.CREATE, Command.UPDATE):
                                deref(command[2], self.env[model._fields[field].comodel_name])
                            if command[0] == Command.SET:
                                for i, value in enumerate(command[2]):
                                    if isinstance(value, str):
                                        command[2][i] = self.env.ref(value).id
            return values

        def defer(all_data):
            created_models = set()
            while all_data:
                (model, data), *all_data = all_data
                created_models.add(model)
                to_delay = defaultdict(dict)
                for xml_id, vals in data.items():
                    for field_name, value in list(vals.items()):
                        if field_name in self.env[model]._fields:
                            field = self.env[model]._fields[field_name]
                            if (
                                field.relational
                                and field.comodel_name not in created_models
                                and field.comodel_name in dict(all_data)
                            ):
                                to_delay[xml_id][field_name] = vals.pop(field_name)
                if any(to_delay.values()):
                    all_data.append((model, to_delay))
                yield model, data

        irt_cursor = IrTranslationImport(self._cr, True)
        for model, data in defer(list(data.items())):
            translate_vals = defaultdict(list)
            create_vals = []
            for xml_id, record in data.items():
                xml_id = "account.%s" % xml_id if '.' not in xml_id else xml_id
                for translate, value in list(record.items()):
                    if '@' in translate:
                        if value:
                            field, lang = translate.split('@')
                            translate_vals[xml_id].append({
                                'type': 'model',
                                'name': f'{model},{field}',
                                'lang': lang,
                                'src': record[field],
                                'value': value,
                                'comments': None,
                                'imd_model': model,
                                'imd_name': xml_id,
                                'module': 'account',
                            })
                        del record[translate]
                create_vals.append({
                    'xml_id': xml_id,
                    'values': deref(record, self.env[model]),
                    'noupdate': True,
                })
            created = self.env[model]._load_records(create_vals)
            for vals, record in zip(create_vals, created):
                for translation in translate_vals[vals['xml_id']]:
                    irt_cursor.push({**translation, 'res_id': record.id})
        irt_cursor.finish()

    def _load_csv(self, module, file_name):
        def sanitize_csv(model, row):
            model_fields = model._fields
            return {
                key: (
                    value if '@' in key
                    else ast.literal_eval(value) if model_fields[key].type in ('boolean', 'int', 'float')
                    else (value and model.env.ref(value).id or False) if model_fields[key].type == 'many2one'
                    else (value and model.env.ref(value).ids or []) if model_fields[key].type in ('one2many', 'many2many')
                    else value
                )
                for key, value in ((key.replace('/id', ''), value) for key, value in row.items())
                if key != 'id'
            }

        cid = self.env.company.id
        try:
            with open(get_resource_path('account', 'data', 'template', module, file_name), 'r+') as fp:
                return {
                    f"{cid}_{r['id']}": sanitize_csv(self.env['.'.join(file_name.split('.')[:-1])], r)
                    for r in csv.DictReader(fp)
                }
        except OSError:
            return {}

    def _get_chart_template_data(self):
        return {
            'account.account': self._get_account_account(),
            'account.group': self._get_account_group(),
            'account.journal': self._get_account_journal(),
            'res.company': self._get_res_company(),
            'account.tax.group': self._get_tax_group(),
            'account.tax': self._get_account_tax(),
        }


    def _get_account_account(self):
        return self._load_csv(self.env.company.chart_template, 'account.account.csv')

    def _get_account_group(self):
        return self._load_csv(self.env.company.chart_template, 'account.group.csv')

    def _get_tax_group(self):
        return self._load_csv(self.env.company.chart_template, 'account.tax.group.csv')

    def _post_load_data(self):
        company = self.env.company
        ref = self.env.ref
        cid = self.env.company.id
        template_data = self._get_template_data()
        code_digits = template_data.get('code_digits', 6)
        # Set default cash difference account on company
        if not company.account_journal_suspense_account_id:
            company.account_journal_suspense_account_id = self.env['account.account'].create({
                'name': _("Bank Suspense Account"),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
                'user_type_id': self.env.ref('account.data_account_type_current_liabilities').id,
                'company_id': company.id,
            })

        account_type_current_assets = self.env.ref('account.data_account_type_current_assets')
        if not company.account_journal_payment_debit_account_id:
            company.account_journal_payment_debit_account_id = self.env['account.account'].create({
                'name': _("Outstanding Receipts"),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
                'reconcile': True,
                'user_type_id': account_type_current_assets.id,
                'company_id': company.id,
            })

        if not company.account_journal_payment_credit_account_id:
            company.account_journal_payment_credit_account_id = self.env['account.account'].create({
                'name': _("Outstanding Payments"),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
                'reconcile': True,
                'user_type_id': account_type_current_assets.id,
                'company_id': company.id,
            })

        if not company.default_cash_difference_expense_account_id:
            company.default_cash_difference_expense_account_id = self.env['account.account'].create({
                'name': _('Cash Difference Loss'),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, '999'),
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
                'company_id': company.id,
            })

        if not company.default_cash_difference_income_account_id:
            company.default_cash_difference_income_account_id = self.env['account.account'].create({
                'name': _('Cash Difference Gain'),
                'code': self.env['account.account']._search_new_account_code(company, code_digits, '999'),
                'user_type_id': self.env.ref('account.data_account_type_revenue').id,
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
                'company_id': company.id,
            })

        # Set the transfer account on the company
        transfer_account_code_prefix = template_data['transfer_account_code_prefix']
        company.transfer_account_id = self.env['account.account'].search([
            ('code', '=like', transfer_account_code_prefix + '%'), ('company_id', '=', company.id)], limit=1)

        # Create the current year earning account if it wasn't present in the CoA
        company.get_unaffected_earnings_account()

        if not company.account_sale_tax_id:
            company.account_sale_tax_id = self.env['account.tax'].search([
                ('type_tax_use', 'in', ('sale', 'all')),
                ('company_id', '=', company.id)
            ], limit=1).id
        if not company.account_purchase_tax_id:
            company.account_purchase_tax_id = self.env['account.tax'].search([
                ('type_tax_use', 'in', ('purchase', 'all')),
                ('company_id', '=', company.id)
            ], limit=1).id

        for field, model in [
            ('property_account_receivable_id', 'res.partner'),
            ('property_account_payable_id', 'res.partner'),
            ('property_account_expense_categ_id', 'product.category'),
            ('property_account_income_categ_id', 'product.category'),
            ('property_account_expense_id', 'product.template'),
            ('property_account_income_id', 'product.template'),
            ('property_tax_payable_account_id', 'account.tax.group'),
            ('property_tax_receivable_account_id', 'account.tax.group'),
            ('property_advance_tax_payment_account_id', 'account.tax.group'),
        ]:
            value = template_data.get(field)
            if value:
                self.env['ir.property']._set_default(field, model, ref(f"account.{cid}_{value}").id, company=company)

    ###############################################################################################
    # GENERIC Template                                                                            #
    ###############################################################################################

    def _get_template_data(self):
        return {
            'bank_account_code_prefix': '1014',
            'cash_account_code_prefix': '1015',
            'transfer_account_code_prefix': '1017',
            'property_account_receivable_id': 'receivable',
            'property_account_payable_id': 'payable',
            'property_account_expense_categ_id': 'expense',
            'property_account_income_categ_id': 'income',
            'property_account_expense_id': 'expense',
            'property_account_income_id': 'income',
            'property_tax_payable_account_id': 'tax_payable',
            'property_tax_receivable_account_id': 'tax_receivable',
            'property_advance_tax_payment_account_id': 'cash_diff_income',  # TODO
        }

    def _get_account_journal(self):
        cid = self.env.company.id
        return {
            f"{cid}_sale": {
                'name': _('Customer Invoices'),
                'type': 'sale',
                'code': _('INV'),
                'default_account_id': f"account.{cid}_income",
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 5,
            },
            f"{cid}_purchase": {
                'name': _('Vendor Bills'),
                'type': 'purchase',
                'code': _('BILL'),
                'default_account_id': f"account.{cid}_expense",
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 6,
            },
            f"{cid}_general": {
                'name': _('Miscellaneous Operations'),
                'type': 'general',
                'code': _('MISC'),
                'show_on_dashboard': True,
                'sequence': 7,
            },
            f"{cid}_exch": {
                'name': _('Exchange Difference'),
                'type': 'general',
                'code': _('EXCH'),
                'show_on_dashboard': False,
                'sequence': 9,
            },
            f"{cid}_caba": {
                'name': _('Cash Basis Taxes'),
                'type': 'general',
                'code': _('CABA'),
                'show_on_dashboard': False,
                'sequence': 10,
            },
            f"{cid}_cash": {
                'name': _('Cash'),
                'type': 'cash',
                'suspense_account_id': f"account.{cid}_cash_diff_income",  # TODO
            },
            f"{cid}_bank": {
                'name': _('Bank'),
                'type': 'bank',
                'suspense_account_id': f"account.{cid}_cash_diff_income",  # TODO
            },
        }

    def _get_account_tax(self):
        cid = self.env.company.id
        return {
            f"{cid}_sale_tax_template": {
                "name": _("Tax 15%"),
                "amount": 15,
                "type_tax_use": 'sale',
                "tax_group_id": f'account.{cid}_tax_group_15',
                "invoice_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
                "refund_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
            },
            f"{cid}_purchase_tax_template": {
                "name": _("Purchase Tax 15%"),
                "amount": 15,
                "type_tax_use": 'purchase',
                "tax_group_id": f'account.{cid}_tax_group_15',
                "invoice_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
                "refund_repartition_line_ids": [
                    Command.clear(),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': f'account.{cid}_tax_received',
                    }),
                ],
            },
        }

    def _get_res_company(self):
        cid = self.env.company.id
        return {
            self.env.company.get_metadata()[0]['xmlid']: {
                'currency_id': 'base.USD',
                'account_fiscal_country_id': 'base.us',
                'default_cash_difference_income_account_id': f'account.{cid}_cash_diff_income',
                'default_cash_difference_expense_account_id': f'account.{cid}_cash_diff_expense',
                'account_cash_basis_base_account_id': f'account.{cid}_cash_diff_income',  # TODO
                'account_default_pos_receivable_account_id': f'account.{cid}_cash_diff_income',  # TODO
                'income_currency_exchange_account_id': f'account.{cid}_income_currency_exchange',
                'expense_currency_exchange_account_id': f'account.{cid}_expense_currency_exchange',
            }
        }
