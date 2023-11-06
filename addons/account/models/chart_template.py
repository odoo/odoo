# -*- coding: utf-8 -*-

import ast
import csv
from collections import defaultdict
from functools import wraps
from inspect import getmembers

import logging
import re

from psycopg2.extras import Json

from odoo import Command, _, models, api
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.addons.account import SYSCOHADA_LIST
from odoo.exceptions import AccessError
from odoo.tools import file_open, groupby
from odoo.tools.translate import TranslationImporter

_logger = logging.getLogger(__name__)

TEMPLATE_MODELS = (
    'account.group',
    'account.account',
    'account.tax.group',
    'account.tax',
    'account.journal',
    'account.reconcile.model',
    'account.fiscal.position',
)

TAX_TAG_DELIMITER = '||'


def preserve_existing_tags_on_taxes(env, module):
    ''' This is a utility function used to preserve existing previous tags during upgrade of the module.'''
    xml_records = env['ir.model.data'].search([('model', '=', 'account.account.tag'), ('module', 'like', module)])
    if xml_records:
        env.cr.execute("update ir_model_data set noupdate = 't' where id in %s", [tuple(xml_records.ids)])


def template(template=None, model='template_data'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if template is not None:
                # remove the template code argument as we already know it from the decorator
                args, kwargs = args[:1], {}
            return func(*args, **kwargs)
        return api.attrsetter('_l10n_template', (template, model))(wrapper)
    return decorator


class AccountChartTemplate(models.AbstractModel):
    _name = "account.chart.template"
    _description = "Account Chart Template"

    @property
    def _template_register(self):
        def is_template(func):
            return callable(func) and hasattr(func, '_l10n_template')
        template_register = defaultdict(lambda: defaultdict(list))
        cls = type(self)
        for _attr, func in getmembers(cls, is_template):
            template, model = func._l10n_template
            template_register[template][model].append(func)
        cls._template_register = template_register
        return template_register

    def _setup_complete(self):
        super()._setup_complete()
        type(self)._template_register = AccountChartTemplate._template_register


    # --------------------------------------------------------------------------------
    # Template selection
    # --------------------------------------------------------------------------------

    def _get_chart_template_mapping(self, get_all=False):
        """Get basic information about available CoA and their modules.

        :return: a mapping between the template code and a dictionary containing the
                 name, country id, country name, module dependencies and parent template
        :rtype: dict[str, dict]
        """
        # This function is called many times. Avoid doing a search every time by using the ORM's cache.
        # We assume that the field is always computed for all the modules at once (by this function)
        field = self.env['ir.module.module']._fields['account_templates']
        modules = (
            self.env.cache.get_records(self.env['ir.module.module'], field)
            or self.env['ir.module.module'].search([])
        )

        return {
            name: template
            for mapping in modules.mapped('account_templates')
            for name, template in mapping.items()
            if get_all or template['visible']
        }

    def _select_chart_template(self, country=None):
        """Get the available templates in a format suited for Selection fields."""
        country = country if country is not None else self.env.company.country_id
        chart_template_mapping = self._get_chart_template_mapping()
        return [
            (template_code, template['name'])
            for template_code, template in sorted(chart_template_mapping.items(), key=(lambda t: (
                t[1]['name'] != 'generic_coa' if not country
                else t[1]['name'] != 'syscohada' if country.code in SYSCOHADA_LIST
                else t[1]['country_id'] != country.id
            )))
        ]

    def _guess_chart_template(self, country):
        """Guess the most appropriate template based on the country."""
        return self._select_chart_template(country)[0][0]

    # --------------------------------------------------------------------------------
    # Loading
    # --------------------------------------------------------------------------------

    def try_loading(self, template_code, company, install_demo=True):
        """Check if the chart template can be loaded then proceeds installing it.

        :param template_code: code of the chart template to be loaded.
        :type template_code: str
        :param company: the company we try to load the chart template on.
            If not provided, it is retrieved from the context.
        :type company: int, Model<res.company>
        :param install_demo: whether or not we should load demo data right after loading the
            chart template.
        :type install_demo: bool
        """
        if not company:
            company = self.env.company
        if isinstance(company, int):
            company = self.env['res.company'].browse([company])

        template_code = template_code or company and self._guess_chart_template(company.country_id)

        return self._load(template_code, company, install_demo)

    def _load(self, template_code, company, install_demo):
        """Install this chart of accounts for the current company.

        :param template_code: code of the chart template to be loaded.
        :param company: the company we try to load the chart template on.
            If not provided, it is retrieved from the context.
        :param install_demo: whether or not we should load demo data right after loading the
            chart template.
        """
        # Ensure that the context is the correct one, even if not called by try_loading
        if not self.env.is_system():
            raise AccessError(_("Only administrators can install chart templates"))

        module_name = self._get_chart_template_mapping()[template_code].get('module')
        module = self.env['ir.module.module'].search([('name', '=', module_name), ('state', '=', 'uninstalled')])
        if module:
            module.button_immediate_install()
            self.env.reset()  # clear the envs with an old registry
            self = self.env()['account.chart.template']  # create a new env with the new registry

        self = self.with_context(
            default_company_id=company.id,
            allowed_company_ids=[company.id],
            tracking_disable=True,
            delay_account_group_sync=True,
        )
        company = company.with_env(self.env)

        reload_template = template_code == company.chart_template
        company.chart_template = template_code

        if not reload_template and (not company.root_id._existing_accounting() or self.env.ref('base.module_account').demo):
            for model in ('account.move',) + TEMPLATE_MODELS[::-1]:
                if not company.parent_id:
                    self.env[model].sudo().with_context(active_test=False).search([('company_id', 'child_of', company.id)]).with_context({MODULE_UNINSTALL_FLAG: True}).unlink()

        data = self._get_chart_template_data(template_code)
        template_data = data.pop('template_data')
        if company.parent_id:
            data = {
                'res.company': data['res.company'],
            }

        if reload_template:
            self._pre_reload_data(company, template_data, data)
            install_demo = False
        data = self._pre_load_data(template_code, company, template_data, data)
        self._load_data(data)
        self._load_translations(companies=company)
        self._post_load_data(template_code, company, template_data)

        # Manual sync because disable above (delay_account_group_sync)
        AccountGroup = self.env['account.group'].with_context(delay_account_group_sync=False)
        AccountGroup._adapt_accounts_for_account_groups(self.env['account.account'].search([]))
        AccountGroup.search([])._adapt_parent_account_group()

        # Install the demo data when the first localization is instanciated on the company
        if install_demo and self.ref('base.module_account').demo and not reload_template:
            try:
                with self.env.cr.savepoint():
                    self.sudo()._load_data(self._get_demo_data(company))
                    self._post_load_demo_data(company)
            except Exception:
                # Do not rollback installation of CoA if demo data failed
                _logger.exception('Error while loading accounting demo data')
        for subsidiary in company.child_ids:
            self._load(template_code, subsidiary, install_demo)

    def _pre_reload_data(self, company, template_data, data):
        """Pre-process the data in case of reloading the chart of accounts.

        When we reload the chart of accounts, we only want to update fields that are main
        configuration, like:
        - tax tags
        - fiscal position mappings linked to new records
        """
        for prop in list(template_data):
            if prop.startswith('property_'):
                template_data.pop(prop)
        data.pop('account.reconcile.model', None)

        for xmlid, journal_data in list(data.get('account.journal', {}).items()):
            if self.ref(xmlid, raise_if_not_found=False):
                del data['account.journal'][xmlid]
            else:
                journal = None
                if 'code' in journal_data:
                    journal = self.env['account.journal'].with_context(active_test=False).search([
                        *self.env['account.journal']._check_company_domain(company),
                        ('code', '=', journal_data['code']),
                    ])
                # Try to match by journal name to avoid conflict in the unique constraint on the mail alias
                if not journal and 'name' in journal_data and 'type' in journal_data:
                    journal = self.env['account.journal'].with_context(active_test=False).search([
                        *self.env['account.journal']._check_company_domain(company),
                        ('type', '=', journal_data['type']),
                        ('name', '=', journal_data['name']),
                    ], limit=1)
                if journal:
                    del data['account.journal'][xmlid]
                    self.env['ir.model.data']._update_xmlids([{
                        'xml_id': f"account.{company.id}_{xmlid}",
                        'record': journal,
                        'noupdate': True,
                    }])

        account_group_count = self.env['account.group'].search_count([])
        if account_group_count:
            data.pop('account.group', None)

        current_taxes = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(company),
        ])
        unique_tax_name_key = lambda t: (t.name, t.type_tax_use, t.tax_scope, t.company_id)
        unique_tax_name_keys = set(current_taxes.mapped(unique_tax_name_key))
        xmlid2tax = {
            xml_id.split('.')[1].split('_', maxsplit=1)[1]: self.env['account.tax'].browse(record)
            for record, xml_id in current_taxes.get_external_id().items() if xml_id
        }
        def tax_template_changed(tax, template):
            return (
                tax.amount_type != template.get('amount_type', 'percent')
                or tax.amount != template.get('amount', 0)
            )

        obsolete_xmlid = set()
        skip_update = set()
        for model_name, records in data.items():
            for xmlid, values in records.items():
                if model_name == 'account.fiscal.position':
                    # Only add tax mappings containing new taxes
                    values['tax_ids'] = [
                        (command, id, vals)
                        for command, id, vals in values.get('tax_ids', [])
                        if (
                            command not in (Command.UPDATE, Command.CREATE)
                            or not self.ref(vals['tax_src_id'], raise_if_not_found=False)
                            or (vals.get('tax_dest_id') and not self.ref(vals['tax_dest_id'], raise_if_not_found=False))
                        )
                    ]
                    if not values['tax_ids']:
                        del values['tax_ids']
                elif model_name == 'account.tax':
                    # Only update the tags of existing taxes
                    if xmlid not in xmlid2tax or tax_template_changed(xmlid2tax[xmlid], values):
                        if self._context.get('force_new_tax_active'):
                            values['active'] = True
                        if xmlid in xmlid2tax:
                            obsolete_xmlid.add(xmlid)
                            oldtax = xmlid2tax[xmlid]
                            if unique_tax_name_key(oldtax) in unique_tax_name_keys:
                                oldtax.name = f"[old] {oldtax.name}"
                    else:
                        repartition_lines = values.get('repartition_line_ids')
                        values.clear()
                        if repartition_lines:
                            values['repartition_line_ids'] = repartition_lines
                            for _c, _id, repartition_line in values.get('repartition_line_ids', []):
                                tags = repartition_line.get('tag_ids')
                                repartition_line.clear()
                                if tags:
                                    repartition_line['tag_ids'] = tags
                elif model_name == 'account.account':
                    # Point or create xmlid to existing record to avoid duplicate code
                    account = self.ref(xmlid, raise_if_not_found=False)
                    if not account or (account and account.code != values['code']):
                        existing_account = self.env['account.account'].search([
                            *self.env['account.account']._check_company_domain(company),
                            ('code', '=', values['code']),
                        ])
                        if existing_account:
                            self.env['ir.model.data']._update_xmlids([{
                                'xml_id': f"account.{company.id}_{xmlid}",
                                'record': existing_account,
                                'noupdate': True,
                            }])
                            account = existing_account
                    # on existing accounts, only tag_ids are to be updated using default data
                    if account and 'tag_ids' in data[model_name][xmlid]:
                        data[model_name][xmlid] = {'tag_ids': data[model_name][xmlid]['tag_ids']}
                    elif account:
                        skip_update.add((model_name, xmlid))

        for skip_model, skip_xmlid in skip_update:
            data[skip_model].pop(skip_xmlid, None)

        if obsolete_xmlid:
            self.env['ir.model.data'].search([
                ('name', 'in', [f"{company.id}_{xmlid}" for xmlid in obsolete_xmlid]),
                ('module', '=', 'account'),
            ]).unlink()

        custom_fields = {  # Don't alter values that can be changed by the users
            'account.fiscal.position.tax_ids',
        }
        for model_name, records in data.items():
            _fields = self.env[model_name]._fields
            for xmlid, values in records.items():
                x2manyfields = [
                    fname
                    for fname in values
                    if fname in _fields
                    and f"{model_name}.{fname}" not in custom_fields
                    and _fields[fname].type in ('one2many', 'many2many')
                    and isinstance(values[fname], (list, tuple))
                ]
                if x2manyfields:
                    rec = self.ref(xmlid, raise_if_not_found=False)
                    if rec:
                        for fname in x2manyfields:
                            for i, (line, (command, _id, vals)) in enumerate(zip(rec[fname], values[fname])):
                                if command == Command.CREATE:  # converts ORM command `create` into `update`
                                    values[fname][i] = Command.update(line.id, vals)

    def _pre_load_data(self, template_code, company, template_data, data):
        """Pre-process the data and preload some values.

        Some of the data needs special pre_process before being fed to the database.
        e.g. the account codes' width must be standardized to the code_digits applied.
        The fiscal country code must be put in place before taxes are generated.
        """
        if 'account_fiscal_country_id' in data['res.company'][company.id]:
            fiscal_country = self.ref(data['res.company'][company.id]['account_fiscal_country_id'])
        else:
            fiscal_country = company.account_fiscal_country_id

        # Apply template data to the company
        filter_properties = lambda key: (
            (not key.startswith("property_") or key.startswith("property_stock_") or key == "additional_properties")
            and key != 'name'
            and key in company._fields
        )

        # Set the currency to the fiscal country's currency
        vals = {key: val for key, val in template_data.items() if filter_properties(key)}
        if not company.root_id._existing_accounting():
            if company.parent_id:
                vals['currency_id'] = company.parent_id.currency_id.id
            else:
                vals['currency_id'] = fiscal_country.currency_id.id
        if not company.country_id:
            vals['country_id'] = fiscal_country.id

        # This write method is important because it's overridden and has additional triggers
        # e.g it activates the currency
        company.write(vals)

        # Normalize the code_digits of the accounts
        code_digits = int(template_data.get('code_digits', 6))
        for key, account_data in data.get('account.account', {}).items():
            if 'code' in account_data:
                data['account.account'][key]['code'] = f'{account_data["code"]:<0{code_digits}}'

        for model in ('account.fiscal.position', 'account.reconcile.model'):
            if model in data:
                data[model] = data.pop(model)

        return data

    def _load_data(self, data):
        """Load all the data linked to the template into the database.

        The data can contain translation values (i.e. `name@fr_FR` to translate the name in French)
        An xml_id that doesn't contain a `.` will be treated as being linked to `account` and prefixed
        with the company's id (i.e. `cash` is interpreted as `account.1_cash` if the company's id is 1)

        :param data: Basically all the final data of records to create/update for the chart
                     of accounts. It is a mapping {model: {xml_id: values}}.
        :type data: dict[str, dict[(str, int), dict]]
        """
        def deref(values, model):
            """Replace xml_id references by database ids.

            This allows to define all the data before the records even exist in the database.
            """
            fields = ((model._fields[k], k, v) for k, v in values.items() if k in model._fields)
            for field, fname, value in fields:
                if not value:
                    values[fname] = False
                elif isinstance(value, str) and (
                    field.type == 'many2one'
                    or (field.type in ('integer', 'many2one_reference') and not value.isdigit())
                ):
                    try:
                        values[fname] = self.ref(value).id if value not in ('', 'False', 'None') else False
                    except ValueError as e:
                        _logger.warning("Failed when trying to recover %s for field=%s", value, field)
                        raise e
                elif field.type in ('one2many', 'many2many') and isinstance(value[0], (list, tuple)):
                    for i, (command, _id, *last_part) in enumerate(value):
                        if last_part:
                            last_part = last_part[0]
                        # (0, 0, {'test': 'account.ref_name'}) -> Command.Create({'test': 13})
                        if command in (Command.CREATE, Command.UPDATE):
                            deref(last_part, self.env[field.comodel_name])
                        # (6, 0, ['account.ref_name']) -> Command.Set([13])
                        elif command == Command.SET:
                            for subvalue_idx, subvalue in enumerate(last_part):
                                if isinstance(subvalue, str):
                                    last_part[subvalue_idx] = self.ref(subvalue).id
                        elif command == Command.LINK and isinstance(_id, str):
                            value[i] = Command.link(self.ref(_id).id)
                elif field.type in ('one2many', 'many2many') and isinstance(value, str):
                    values[fname] = [Command.set([
                        self.ref(v).id
                        for v in value.split(',')
                        if v
                    ])]
            return values

        def defer(all_data):
            """Defer writing some relations if the related records don't exist yet."""
            created_models = set()
            while all_data:
                (model, data), *all_data = all_data
                to_delay = defaultdict(dict)
                for xml_id, vals in data.items():
                    to_be_removed = []
                    for field_name, field_val in vals.items():
                        field = self.env[model]._fields.get(field_name, None)
                        if (
                            field
                            and field.relational
                            and field_val
                            and (  # allow create commands but delay all other related fields
                                not isinstance(field_val, (list, tuple))
                                or (
                                    isinstance(field_val[0], (list, tuple))
                                    and {command for command, *dummy in field_val} != {Command.CREATE}
                                )
                            )
                            and field.comodel_name not in created_models
                            and (
                                field.comodel_name in dict(all_data)
                                or field.comodel_name == model
                            )
                        ):
                            to_be_removed.append(field_name)
                            to_delay[xml_id][field_name] = field_val
                    for field_name in to_be_removed:
                        del vals[field_name]
                if any(to_delay.values()):
                    all_data.append((model, to_delay))
                yield model, data
                created_models.add(model)

        created_vals = {}
        for model, data in defer(list(data.items())):
            create_vals = []
            for xml_id, record in data.items():
                # Extract the translations from the values
                for key in list(record):
                    if '@' in key:
                        del record[key]

                # Manage ids given as database id or xml_id
                if isinstance(xml_id, int):
                    record['id'] = xml_id
                    xml_id = False
                else:
                    xml_id = f"{('account.' + str(self.env.company.id) + '_') if '.' not in xml_id else ''}{xml_id}"

                create_vals.append({
                    'xml_id': xml_id,
                    'values': deref(record, self.env[model]),
                    'noupdate': True,
                })
            created_vals[model] = self.with_context(lang='en_US').env[model]._load_records(create_vals)
        return created_vals

    def _post_load_data(self, template_code, company, template_data):
        company = (company or self.env.company)
        additional_properties = template_data.pop('additional_properties', {})

        self._setup_utility_bank_accounts(template_code, company, template_data)

        # Unaffected earnings account on the company (if not present yet)
        company.get_unaffected_earnings_account()

        # Set newly created Cash difference and Suspense accounts to the Cash and Bank journals
        for journal in [self.ref(kind, raise_if_not_found=False) for kind in ('bank', 'cash')]:
            if journal:
                journal.suspense_account_id = journal.suspense_account_id or company.account_journal_suspense_account_id
                journal.profit_account_id = journal.profit_account_id or company.default_cash_difference_income_account_id
                journal.loss_account_id = journal.loss_account_id or company.default_cash_difference_expense_account_id

        # Set newly created journals as defaults for the company
        if not company.tax_cash_basis_journal_id:
            company.tax_cash_basis_journal_id = self.ref('caba')
        if not company.currency_exchange_journal_id:
            company.currency_exchange_journal_id = self.ref('exch')

        # Setup default Income/Expense Accounts on Sale/Purchase journals
        sale_journal = self.ref("sale", raise_if_not_found=False)
        if sale_journal and template_data.get('property_account_income_categ_id'):
            sale_journal.default_account_id = self.ref(template_data.get('property_account_income_categ_id'))
        purchase_journal = self.ref("purchase", raise_if_not_found=False)
        if purchase_journal and template_data.get('property_account_expense_categ_id'):
            purchase_journal.default_account_id = self.ref(template_data.get('property_account_expense_categ_id'))

        # Set default Purchase and Sale taxes on the company
        if not company.account_sale_tax_id:
            company.account_sale_tax_id = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('type_tax_use', 'in', ('sale', 'all'))], limit=1).id
        if not company.account_purchase_tax_id:
            company.account_purchase_tax_id = self.env['account.tax'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('type_tax_use', 'in', ('purchase', 'all'))], limit=1).id
        # Display caba fields if there are caba taxes
        if not company.parent_id and self.env['account.tax'].search([('tax_exigibility', '=', 'on_payment')]):
            company.tax_exigibility = True

        for field, model in {
            **additional_properties,
            'property_account_receivable_id': 'res.partner',
            'property_account_payable_id': 'res.partner',
            'property_account_expense_categ_id': 'product.category',
            'property_account_income_categ_id': 'product.category',
            'property_stock_journal': 'product.category',
        }.items():
            value = template_data.get(field)
            if value and field in self.env[model]._fields:
                self.env['ir.property']._set_default(field, model, self.ref(value).id, company=company)

    def _get_chart_template_data(self, template_code):
        template_data = defaultdict(lambda: defaultdict(dict))
        template_data['res.company']  # ensure it's the first property when iterating
        for code in [None] + self._get_parent_template(template_code):
            for model, funcs in sorted(
                self._template_register[code].items(),
                key=lambda i: TEMPLATE_MODELS.index(i[0]) if i[0] in TEMPLATE_MODELS else 1000
            ):
                for func in funcs:
                    data = func(self, template_code)
                    if data is not None:
                        if model == 'template_data':
                            template_data[model].update(data)
                        else:
                            for xmlid, record in data.items():
                                template_data[model][xmlid].update(record)
        return template_data

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        """Define basic bank accounts for the company.

        - Suspense Account
        - Outstanding Receipts/Payments Accounts
        - Cash Difference Gain/Loss Accounts
        - Liquidity Transfer Account
        """
        # Create utility bank_accounts
        bank_prefix = company.bank_account_code_prefix
        code_digits = int(template_data.get('code_digits', 6))
        accounts_data = {
            'account_journal_suspense_account_id': {
                'name': _("Bank Suspense Account"),
                'prefix': bank_prefix,
                'code_digits': code_digits,
                'account_type': 'asset_current',
            },
            'account_journal_payment_debit_account_id': {
                'name': _("Outstanding Receipts"),
                'prefix': bank_prefix,
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': True,
            },
            'account_journal_payment_credit_account_id': {
                'name': _("Outstanding Payments"),
                'prefix': bank_prefix,
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': True,
            },
            'account_journal_early_pay_discount_loss_account_id': {
                'name': _("Cash Discount Loss"),
                'code': '999998',
                'account_type': 'expense',
            },
            'account_journal_early_pay_discount_gain_account_id': {
                'name': _("Cash Discount Gain"),
                'code': '999997',
                'account_type': 'income_other',
            },
            'default_cash_difference_income_account_id': {
                'name': _("Cash Difference Gain"),
                'prefix': '999',
                'code_digits': code_digits,
                'account_type': 'income_other',
                'tag_ids': [(6, 0, self.ref('account.account_tag_investing').ids)],
            },
            'default_cash_difference_expense_account_id': {
                'name': _("Cash Difference Loss"),
                'prefix': '999',
                'code_digits': code_digits,
                'account_type': 'expense',
                'tag_ids': [(6, 0, self.ref('account.account_tag_investing').ids)],
            },
            'transfer_account_id': {
                'name': _("Liquidity Transfer"),
                'prefix': company.transfer_account_code_prefix,
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': True,
            },
        }

        for fname in list(accounts_data):
            if company[fname]:
                del accounts_data[fname]
        if company.parent_id:
            for company_attr_name in accounts_data:
                company[company_attr_name] = company.parent_ids[0][company_attr_name]
        else:
            accounts = self.env['account.account'].create(accounts_data.values())
            for company_attr_name, account in zip(accounts_data.keys(), accounts):
                company[company_attr_name] = account

    @api.model
    def _instantiate_foreign_taxes(self, country, company):
        """Create and configure foreign taxes from the provided country.

        Instantiate the taxes as they would be for the foreign localization only replacing the accounts used by the most
        probable account we can retrieve from the company's localization.
        This method is intended as a shortcut for instantiation, accelerating it, not as an out-of-the-box solution 100%
        correct solution.
        """
        # Implementation:
        # - Check if there is any tax for this country and stop the process if yes
        # - Retrieve the tax group and tax template data
        # - Try to create accounts at most probable location in the CoA
        # - Assign those accounts to the data
        # - Creates tax group and taxes with their ir.model.data

        taxes_in_country = self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(company),
            ('country_id', '=', country.id),
        ])
        if taxes_in_country:
            return

        def create_foreign_tax_account(existing_account, additional_label):
            new_code = self.env['account.account']._search_new_account_code(
                existing_account.company_id,
                len(existing_account.code),
                existing_account.code[:-2]
            )
            return self.env['account.account'].create({
                'name': f"{existing_account.name} - {additional_label}",
                'code': new_code,
                'account_type': existing_account.account_type,
                'company_id': existing_account.company_id.id,
            })

        existing_accounts = {'': None, None: None}  # keeps tracks of the created account by foreign xml_id
        default_company_taxes = company.account_sale_tax_id + company.account_purchase_tax_id
        chart_template_code = self._guess_chart_template(country=country)
        tax_group_data = self._get_chart_template_data(chart_template_code)['account.tax.group']
        tax_data = self._get_chart_template_data(chart_template_code)['account.tax']

        # Populate foreign accounts mapping
        # Try to create tax group accounts if not mapped
        field_and_names = (
            ('tax_payable_account_id', _("Foreign tax account payable (%s)", country.code)),
            ('tax_receivable_account_id', _("Foreign tax account receivable (%s)", country.code)),
            ('advance_tax_payment_account_id', _("Foreign tax account advance payment (%s)", country.code)),
        )
        for field, account_name in field_and_names:
            for tax_group in tax_group_data.values():
                account_template_xml_id = tax_group.get(field)
                if account_template_xml_id in existing_accounts:
                    continue
                local_tax_group = self.env["account.tax.group"].search([
                    *self.env['account.tax.group']._check_company_domain(company),
                    ('country_id', '=', company.account_fiscal_country_id.id),
                    (field, '!=', False),
                ], limit=1)
                if local_tax_group:
                    existing_accounts[account_template_xml_id] = create_foreign_tax_account(local_tax_group[field], account_name).id

        # Try to create repartition lines account if not mapped
        for tax_template in tax_data.values():
            for _command, _id, rep_line in tax_template.get('repartition_line_ids', []):
                if 'account_id' in rep_line and rep_line['repartition_type'] == 'tax':
                    type_tax_use, foreign_tax_rep_line = tax_template['type_tax_use'], rep_line
                    account_template_xml_id = foreign_tax_rep_line['account_id']
                    if account_template_xml_id in existing_accounts:
                        continue

                    sign_comparator = '<' if float(foreign_tax_rep_line.get('factor_percent', 100)) < 0 else '>'
                    minimal_domain = [
                        *self.env['account.tax.repartition.line']._check_company_domain(company),
                        ('account_id', '!=', False),
                        ('factor_percent', sign_comparator, 0),
                    ]
                    additional_domain = [
                        ('tax_id.type_tax_use', '=', type_tax_use),
                        ('tax_id.country_id', '=', company.account_fiscal_country_id.id),
                        ('tax_id', 'in', default_company_taxes.ids),
                    ]

                    # Trying to find an account being less restrictive on each iteration until the minimum acceptable is
                    # reached. If nothing is found, don't fill it to avoid setting a wrong account
                    similar_repartition_line = None
                    while not similar_repartition_line and additional_domain:
                        search_domain = minimal_domain + additional_domain
                        similar_repartition_line = self.env['account.tax.repartition.line'].search(search_domain, limit=1)
                        additional_domain.pop()

                    if similar_repartition_line:
                        local_tax_account = similar_repartition_line.account_id
                        similar_account_id = create_foreign_tax_account(local_tax_account, _("Foreign tax account (%s)", country.code))
                        existing_accounts[account_template_xml_id] = similar_account_id.id

        # Try to create cash basis account if not mapped
        local_cash_basis_tax = self.env["account.tax"].search([
            *self.env['account.tax']._check_company_domain(company),
            ('country_id', '=', company.account_fiscal_country_id.id),
            ('cash_basis_transition_account_id', '!=', False)
        ], limit=1)
        for tax_template in tax_data.values():
            account_xml_id = tax_template.get('cash_basis_transition_account_id')
            if account_xml_id in existing_accounts:
                continue

            if local_cash_basis_tax:
                existing_accounts[account_xml_id] = create_foreign_tax_account(
                    local_cash_basis_tax.cash_basis_transition_account_id,
                    _("Cash basis transition account")
                ).id
                continue

            account_id = [rep_line['account_id'] for _command, _id, rep_line in tax_template['repartition_line_ids'] if rep_line.get('account_id')]
            if account_id:
                local_account = self.env['account.account'].browse(existing_accounts[account_id[0]])
                existing_accounts[account_xml_id] = create_foreign_tax_account(local_account, _("Cash basis transition account")).id
                continue
            existing_accounts[account_xml_id] = None

        # Assign the account based on the map
        for field, account_name in field_and_names:
            for tax_group in tax_group_data.values():
                tax_group[field] = existing_accounts.get(account_template_xml_id)

        for tax_template in tax_data.values():
            # This is required because the country isn't provided directly by the template
            tax_template['country_id'] = country.id

            if tax_template.get('tax_group_id'):
                tax_template['tax_group_id'] = f"{chart_template_code}_{tax_template['tax_group_id']}"

            for _command, _id, rep_line in tax_template.get('repartition_line_ids', []):
                rep_line['account_id'] = existing_accounts.get(rep_line.get('account_id'))

            account_xml_id = tax_template.get('cash_basis_transition_account_id')
            tax_template['cash_basis_transition_account_id'] = existing_accounts[account_xml_id]

        data = {
            'account.tax.group': tax_group_data,
            'account.tax': tax_data,
        }
        # prefix the xml_id with the chart template code to avoid collision
        # because since 16.2 xml_ids are regrouped under module account
        data = {
            model: {
                f"{chart_template_code}_{xml_id}": template
                for xml_id, template in templates.items()
            }
            for model, templates in data.items()
        }
        # add the prefix to the "children_tax_ids" value for group-type taxes
        for tax_data in data['account.tax'].values():
            if tax_data.get('amount_type') == 'group':
                children_taxes = tax_data['children_tax_ids'].split(',')
                for idx, child_tax in enumerate(children_taxes):
                    children_taxes[idx] = f"{chart_template_code}_{child_tax}"
                tax_data['children_tax_ids'] = ','.join(children_taxes)
        self._load_data(data)

    # --------------------------------------------------------------------------------
    # Root template functions
    # --------------------------------------------------------------------------------

    @template(model='account.account')
    def _get_account_account(self, template_code):
        return self._parse_csv(template_code, 'account.account')

    @template(model='account.group')
    def _get_account_group(self, template_code):
        return self._parse_csv(template_code, 'account.group')

    @template(model='account.tax.group')
    def _get_account_tax_group(self, template_code):
        return self._parse_csv(template_code, 'account.tax.group')

    @template(model='account.tax')
    def _get_account_tax(self, template_code):
        tax_data = self._parse_csv(template_code, 'account.tax')
        self._deref_account_tags(template_code, tax_data)
        return tax_data

    @template(model='account.fiscal.position')
    def _get_account_fiscal_position(self, template_code):
        return self._parse_csv(template_code, 'account.fiscal.position')

    @template(model='account.journal')
    def _get_account_journal(self, template_code):
        return {
            "sale": {
                'name': _('Customer Invoices'),
                'type': 'sale',
                'code': _('INV'),
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 5,
            },
            "purchase": {
                'name': _('Vendor Bills'),
                'type': 'purchase',
                'code': _('BILL'),
                'show_on_dashboard': True,
                'color': 11,
                'sequence': 6,
            },
            "general": {
                'name': _('Miscellaneous Operations'),
                'type': 'general',
                'code': _('MISC'),
                'show_on_dashboard': True,
                'sequence': 7,
            },
            "exch": {
                'name': _('Exchange Difference'),
                'type': 'general',
                'code': _('EXCH'),
                'show_on_dashboard': False,
                'sequence': 9,
            },
            "caba": {
                'name': _('Cash Basis Taxes'),
                'type': 'general',
                'code': _('CABA'),
                'show_on_dashboard': False,
                'sequence': 10,
            },
            "bank": {
                'name': _('Bank'),
                'type': 'bank',
                'show_on_dashboard': True,
            },
            "cash": {
                'name': _('Cash'),
                'type': 'cash',
                'show_on_dashboard': True,
            },
        }

    @template(model='account.reconcile.model')
    def _get_account_reconcile_model(self, template_code):
        return {
            "reconcile_perfect_match": {
                "name": _('Invoices/Bills Perfect Match'),
                "sequence": 1,
                "rule_type": 'invoice_matching',
                "auto_reconcile": True,
                "match_nature": 'both',
                "match_same_currency": True,
                "allow_payment_tolerance": True,
                "payment_tolerance_type": 'percentage',
                "payment_tolerance_param": 0,
                "match_partner": True,
            },
            "reconcile_partial_underpaid": {
                "name": _('Invoices/Bills Partial Match if Underpaid'),
                "sequence": 2,
                "rule_type": 'invoice_matching',
                "auto_reconcile": False,
                "match_nature": 'both',
                "match_same_currency": True,
                "allow_payment_tolerance": False,
                "match_partner": True,
            }
        }

    # --------------------------------------------------------------------------------
    # Tooling
    # --------------------------------------------------------------------------------

    def ref(self, xmlid, raise_if_not_found=True):
        if '.' in xmlid:
            return self.env.ref(xmlid, raise_if_not_found)
        return (
            self.env.ref(f"account.{self.env.company.id}_{xmlid}", raise_if_not_found=False)
            or self.env.ref(f"account.{self.env.company.parent_ids[0].id}_{xmlid}", raise_if_not_found)
        )

    def _get_parent_template(self, code):
        parents = []
        template_mapping = self._get_chart_template_mapping(get_all=True)
        while template_mapping.get(code):
            parents.append(code)
            code = template_mapping.get(code).get('parent')
        return parents

    def _get_tag_mapper(self, template_code):
        tags = {x.name: x.id for x in self.env['account.account.tag'].search([
            ('applicability', '=', 'taxes'),
            ('country_id', '=', self._get_chart_template_mapping()[template_code]['country_id']),
        ])}
        return lambda *args: [tags[re.sub(r'\s+', ' ', x.strip())] if not re.match(r"^\w+\.\w+$", x) else x for x in args]

    def _deref_account_tags(self, template_code, tax_data):
        mapper = self._get_tag_mapper(template_code)
        for tax in tax_data.values():
            for fname in ('invoice_repartition_line_ids', 'refund_repartition_line_ids', 'repartition_line_ids'):
                if tax.get(fname):
                    for _command, _id, repartition in tax[fname]:
                        tags = repartition.get('tag_ids')
                        if isinstance(tags, str):
                            repartition['tag_ids'] = [Command.set(mapper(*tags.split(TAX_TAG_DELIMITER)))]

    def _parse_csv(self, template_code, model, module=None):
        Model = self.env[model]
        model_fields = Model._fields

        if module is None:
            module = self._get_chart_template_mapping().get(template_code)['module']
        assert re.fullmatch(r"[a-z0-9_]+", module)

        res = {}
        for template in self._get_parent_template(template_code)[::-1] or ['']:
            try:
                with file_open(f"{module}/data/template/{model}{f'-{template}' if template else ''}.csv", 'r') as csv_file:
                    for row in csv.DictReader(csv_file):
                        if row['id']:
                            last_id = row['id']
                            res[row['id']] = {
                                key.split('/')[0]: (
                                    value if '@' in key
                                    else [] if '/' in key
                                    else (value and ast.literal_eval(value) or False) if model_fields[key].type in ('boolean', 'int', 'float')
                                    else value
                                )
                                for key, value in row.items()
                                if key != 'id' and value != "" and ('@' in key or '/' in key or key in model_fields)
                            }
                        create_added = set()
                        for key, value in row.items():
                            if '/' in key and value:
                                sub = [Command.create(res[last_id])]
                                path = key.split('/')
                                for p in path[:-1]:
                                    if p not in create_added:
                                        create_added.add(p)
                                        sub[-1][2].setdefault(p, [])
                                        sub[-1][2][p].append(Command.create({}))
                                    sub = sub[-1][2][p]
                                sub[-1][2][path[-1]] = value
            except FileNotFoundError:
                _logger.debug("No file %s found for template '%s'", model, module)
        return res

    def _load_translations(self, langs=None, companies=None):
        """Load the translations of the chart template.

        :param langs: the lang code to load the translations for. If one of the codes is not present,
                      we are looking for it more generic locale (i.e. `en` instead of `en_US`)
        :type langs: list[str]
        :param companies: the companies to load the translations for
        :type companies: Model<res.company>
        """
        langs = langs or [code for code, _name in self.env['res.lang'].get_installed()]
        available_template_codes = list(self._get_chart_template_mapping(get_all=True))
        companies = companies or self.env['res.company'].search([('chart_template', 'in', available_template_codes)])

        translation_importer = TranslationImporter(self.env.cr, verbose=False)
        for chart_template, chart_companies in groupby(companies, lambda c: c.chart_template):
            template_data = self.env['account.chart.template']._get_chart_template_data(chart_template)
            template_data.pop('template_data', None)
            for mname, data in template_data.items():
                for _xml_id, record in data.items():
                    fnames = {fname.split('@')[0] for fname in record}
                    for lang in langs:
                        for fname in fnames:
                            value = record.get(f"{fname}@{lang}")
                            if not value:  # manage generic locale (i.e. `fr` instead of `fr_BE`)
                                value = record.get(f"{fname}@{lang.split('_')[0]}")
                            if value:
                                for company in chart_companies:
                                    xml_id = f"account.{company.id}_{_xml_id}"
                                    translation_importer.model_translations[mname][fname][xml_id][lang] = value
        translation_importer.save(overwrite=False)
