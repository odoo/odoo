# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
from collections import defaultdict
from lxml import etree

from odoo import Command, fields, models, _
from odoo.exceptions import RedirectWarning


class SaftImportWizard(models.TransientModel):
    """ SAF-T import wizard is the main class to import SAF-T files.  """

    _name = "account.saft.import.wizard"
    _description = "Account SAF-T import wizard"

    attachment_name = fields.Char(string="Filename")
    attachment_id = fields.Binary(string="File", required=True, help="Accounting SAF-T data file to be imported")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", help="Company used for the import", default=lambda self: self.env.company, required=True, readonly=True)
    import_opening_balance = fields.Boolean(string="Import account opening balances")

    # ------------------------------------
    # Utility
    # ------------------------------------

    def _get_account_types(self):
        """ Returns a mapping between the account types accepted for the SAF-T and the types in Odoo """
        # To be overriden
        return {}

    def _make_xml_id(self, prefix, key):
        # To be overriden
        if '_' in prefix:
            raise ValueError('`prefix` cannot contain an underscore')
        key = key.replace(' ', '_')
        return f"l10n_{self.company_id.country_code.lower()}_saft_import.{self.company_id.id}_{prefix}_{key}"

    def _get_cleaned_namespace(self, saft):
        """ Helper that returns the cleaned version of tha namespace. As-is, aft.nsmap cannot be used as there is
        a None key that raises an error (lxml is XPATH 1.0 only)
        """
        nsmap = dict(saft.nsmap)
        nsmap_key = None
        for key, ns in nsmap.items():
            if ns.startswith('urn:StandardAuditFile-Taxation-Financial'):
                nsmap_key = key
                break
        nsmap['saft'] = nsmap[nsmap_key]
        del nsmap[nsmap_key]
        return nsmap

    # ------------------------------------
    # Reading
    # ------------------------------------

    def _prepare_account_data(self, tree):
        """ Extracts the data on accounts to create missing ones and give the mappings used for transactions

        :param tree: tree of the xml file
        :returns: accounts_to_create: values for the accounts to create
        :returns: account_mapping_ids: mapping between ids coming from the SAF-T with the ones from Odoo and the balance
        """
        nsmap = self._get_cleaned_namespace(tree)
        template_data = self.env['account.chart.template']._get_chart_template_data(self.company_id.chart_template).get('template_data')
        digits = int(template_data.get('code_digits', 6))

        existing_accounts = self.env['account.account'].with_company(self.company_id).search_fetch(
            self.env['account.account']._check_company_domain(self.company_id),
            field_names=['id', 'code'],
        )
        existing_accounts_code = {account.code: account.id for account in existing_accounts}
        account_types = self._get_account_types()
        accounts_to_create = {}
        account_mapping_ids = {}
        for element_account in tree.findall('.//saft:Account', namespaces=nsmap):
            account_id = element_account.find('saft:AccountID', namespaces=nsmap).text
            account_code = element_account.find('saft:StandardAccountID', namespaces=nsmap).text
            account_code = account_code[:digits] + account_code[digits:].rstrip('0')
            account_opening_debit = element_account.find('saft:OpeningDebitBalance', namespaces=nsmap)
            account_opening_credit = element_account.find('saft:OpeningCreditBalance', namespaces=nsmap)
            account_mapping_ids[account_id] = {
                'balance': float(account_opening_debit.text) if account_opening_debit is not None else - float(account_opening_credit.text),
            }
            if account_code in existing_accounts_code:
                account_mapping_ids[account_id].update({'id': existing_accounts_code[account_code]})
            else:
                account_type = element_account.find('saft:AccountType', namespaces=nsmap)
                name = element_account.find('saft:AccountDescription', namespaces=nsmap).text
                xml_id = self._make_xml_id('account', account_code)
                accounts_to_create[xml_id] = {
                    'company_ids': [Command.link(self.company_id.id)],
                    'code': account_code,
                    'account_type': account_types.get(account_type, 'asset_current'),
                    'name': name,
                }

                existing_accounts_code[account_code] = xml_id
                account_mapping_ids[account_id].update({'id': xml_id})
        return accounts_to_create, account_mapping_ids

    def _prepare_opening_balance_move(self, tree, map_accounts):
        """ Create a move if there is inconsistency between opening balance for each account and amls in Odoo

        :param tree: tree of the xml file
        :param map_accounts: dict containing balance and id values for each code
        :returns: dict values for the creation of the opening balance move
        """
        nsmap = self._get_cleaned_namespace(tree)
        selection_start_node = tree.find('.//saft:SelectionStartDate', namespaces=nsmap)
        if selection_start_node is not None:
            start_date = fields.Date.to_date(selection_start_node.text)
        else:
            period_start_node = tree.find('.//saft:PeriodStart', namespaces=nsmap)
            period_start_year_node = tree.find('.//saft:PeriodStartYear', namespaces=nsmap)
            start_date = datetime.date(int(period_start_year_node.text), int(period_start_node.text), 1)

        default_currency_code = tree.find('.//saft:DefaultCurrencyCode', namespaces=nsmap)
        currency = self.env['res.currency'].with_context(active_test=False).search([('name', '=', default_currency_code.text)])

        account_diff_balance = {}
        self._cr.execute("""
                    SELECT account.id,
                           SUM(aml.balance) AS balance
                      FROM account_move_line AS aml
                 LEFT JOIN account_account AS account
                        ON aml.account_id = account.id
                     WHERE aml.company_id = %s
                       AND aml.date < %s
                       and aml.parent_state != 'cancel'
                  GROUP BY account.id
                """, [self.company_id.id, start_date])
        existing_balances = defaultdict(dict)
        for balance_row in self._cr.dictfetchall():
            existing_balances[balance_row['id']] = balance_row['balance']

        for account_dict in map_accounts.values():
            if currency.compare_amounts(account_dict['balance'], existing_account_balance := existing_balances.get(account_dict['id'], 0)) != 0:
                account_diff_balance[account_dict['id']] = account_dict['balance'] - existing_account_balance

        journal_misc = self.env['account.journal'].search([*self.env['account.journal']._check_company_domain(self.company_id), ('type', '=', 'general')], limit=1)

        lines_data = []
        for account_id, balance in account_diff_balance.items():
            lines_data.append(
                Command.create({
                    'account_id': account_id,
                    'currency_id': currency.id,
                    'amount_currency': balance,
                    'date': fields.Date.today(),
                    'journal_id': journal_misc.id,
                })
            )
        if lines_data:
            xml_id = self._make_xml_id('move', f'opening_balance{start_date}')
            return {
                xml_id: {
                    'date': fields.Date.today(),
                    'ref': _('SAF-T opening balance move'),
                    'journal_id': journal_misc.id,
                    'partner_id': None,
                    'company_id': self.company_id.id,
                    'currency_id': currency.id,
                    'move_type': 'entry',
                    'line_ids': lines_data,
                }
            }

    def _prepare_partner_data(self, tree):
        """ Extracts the data on partners to create them. Those with the same name and saft_id won't be re-imported

        :param tree: tree of the xml file
        :returns: partners_to_create: values for the partners to create
        :returns: partner_mapping_ids: mapping between ids coming from the SAF-T with the ones from Odoo
        """
        nsmap = self._get_cleaned_namespace(tree)
        partners_to_create = {}
        existing_partners = self.env['res.partner'].search_fetch(
            self.env['res.partner']._check_company_domain(self.company_id),
            field_names=['id', 'name', 'vat'],
        )
        existing_partners_mapping = {(part.name, part.vat): part.id for part in existing_partners}
        partner_mapping_ids = {}

        element_customers_node = tree.find('.//saft:Customers', namespaces=nsmap)
        customers_node = element_customers_node.findall('.//saft:Customer', namespaces=nsmap) if element_customers_node is not None else []
        element_suppliers_node = tree.find('.//saft:Suppliers', namespaces=nsmap)
        suppliers_node = element_suppliers_node.findall('.//saft:Supplier', namespaces=nsmap) if element_suppliers_node is not None else []

        for element_partner in customers_node + suppliers_node:
            partner_name = element_partner.find('saft:Name', namespaces=nsmap).text
            partner_vat = element_partner.find('.//saft:TaxRegistrationNumber', namespaces=nsmap)
            partner_vat = partner_vat.text if partner_vat is not None else False
            partner_id = element_partner.find('saft:CustomerID', namespaces=nsmap).text if element_partner.tag == ('{%s}Customer' % nsmap['saft']) else element_partner.find('saft:SupplierID', namespaces=nsmap).text

            if (partner_name, partner_vat) in existing_partners_mapping:
                partner_mapping_ids[partner_id] = existing_partners_mapping.get((partner_name, partner_vat))
                continue

            child_partners = []
            for contact_node in element_partner.findall('saft:Contact', namespaces=nsmap):
                first_name = contact_node.find('.//saft:FirstName', namespaces=nsmap)
                last_name = contact_node.find('.//saft:LastName', namespaces=nsmap)
                telephone = contact_node.find('.//saft:Telephone', namespaces=nsmap)
                email = contact_node.find('.//saft:Email', namespaces=nsmap)
                mobile = contact_node.find('.//saft:MobilePhone', namespaces=nsmap)

                child_partner_name = last_name.text if last_name is not None else ''
                if first_name is not None and first_name.text != 'NotUsed':
                    child_partner_name = f'{first_name.text} {child_partner_name}'.strip()

                child_partners.append(
                    Command.create({
                        'name': child_partner_name,
                        'type': 'contact',
                        **({'phone': telephone.text} if telephone is not None else {}),
                        **({'email': email.text} if email is not None else {}),
                        **({'mobile': mobile.text} if mobile is not None else {}),
                        'company_id': self.company_id.id,
                    })
                )

            address_node = element_partner.find('saft:Address', namespaces=nsmap)
            partner_street = address_node.find('saft:StreetName', namespaces=nsmap)
            partner_street2 = address_node.find('saft:AdditionalAddressDetail', namespaces=nsmap)
            partner_city = address_node.find('saft:City', namespaces=nsmap)
            partner_zip = address_node.find('saft:PostalCode', namespaces=nsmap)
            partner_country_code = address_node.find('saft:Country', namespaces=nsmap)

            xml_id = self._make_xml_id('partner', f'{partner_name}_{partner_vat}')
            partners_to_create[xml_id] = {
                'company_id': self.company_id.id,
                'vat': partner_vat,
                'name': partner_name,
                **({'street': partner_street.text} if partner_street is not None else {}),
                **({'street2': partner_street2.text} if partner_street2 is not None else {}),
                **({'city': partner_city.text} if partner_city is not None else {}),
                **({'zip': partner_zip.text} if partner_zip is not None else {}),
                **({'country_code': partner_country_code.text} if partner_country_code is not None else {}),
                'child_ids': child_partners,
            }
            existing_partners_mapping[(partner_name, partner_vat)] = xml_id
            partner_mapping_ids[partner_id] = xml_id

        return partners_to_create, partner_mapping_ids

    def _prepare_tax_data(self, tree):
        """ Extracts the data on taxes to create them.
        Those with the same name, amount_type and amount won't be imported

        :param tree: tree of the xml file
        :returns: taxes_to_create: values for the taxes to create
        :returns: tax_mapping_ids: mapping between ids coming from the SAF-T with the ones used in Odoo
        """
        nsmap = self._get_cleaned_namespace(tree)
        existing_taxes = self.env['account.tax'].search_fetch(
            self.env['account.tax']._check_company_domain(self.company_id),
            field_names=['name', 'amount_type', 'amount', 'id'],
        )
        # map between name+amount_type+amount and id of a tax that corresponds
        existing_taxes_mapping = {(tax.name, tax.amount_type, tax.amount): tax.id for tax in existing_taxes}

        default_tax_group = self.env['account.tax.group'].search(
            [*self.env['account.tax.group']._check_company_domain(self.company_id), ('name', '=', 'SAF-T taxes')],
        )
        tax_mapping_ids = {}
        tax_to_create = {}
        for tax_node in tree.findall('.//saft:TaxCodeDetails', namespaces=nsmap):
            tax_code = tax_node.find('.//saft:TaxCode', namespaces=nsmap)
            tax_description = tax_node.find('.//saft:Description', namespaces=nsmap)
            tax_description = tax_description.text if tax_description is not None else False
            tax_percentage = tax_node.find('.//saft:TaxPercentage', namespaces=nsmap)
            tax_percentage = tax_percentage.text if tax_percentage is not None else 0
            tax_flat_rate = tax_node.find('.//saft:TaxFlatRate', namespaces=nsmap)
            tax_flat_rate = tax_flat_rate.text if tax_flat_rate is not None else 0
            tax_mapping_key = (
                tax_description,
                ('fixed' if tax_flat_rate else 'percent'),
                float(tax_percentage) or float(tax_flat_rate),
            )

            if tax_mapping_key in existing_taxes_mapping:
                tax_mapping_ids[tax_code.text] = existing_taxes_mapping[tax_mapping_key]
            else:
                if not default_tax_group:
                    # We only want to create it if it does not exist and if we have taxes to create
                    default_tax_group = self.env['account.tax.group'].create({
                        'name': 'SAF-T taxes',
                        'country_id': self.company_id.account_fiscal_country_id.id,
                    })
                xml_id = self._make_xml_id('tax', '_'.join(str(elem) for elem in tax_mapping_key))
                tax_to_create[xml_id] = {
                    'company_id': self.company_id.id,
                    'name': tax_mapping_key[0],
                    'amount_type': tax_mapping_key[1],
                    'amount': tax_mapping_key[2],
                    'country_id': self.company_id.account_fiscal_country_id.id,
                    'tax_group_id': default_tax_group.id,
                }
                tax_mapping_ids[tax_code.text] = xml_id
                existing_taxes_mapping[(tax_mapping_key[0], tax_mapping_key[1], tax_mapping_key[2])] = xml_id

        return tax_to_create, tax_mapping_ids

    def _prepare_journal_data(self, tree, default_currency, map_accounts, map_taxes, map_currencies, map_partners):
        """ Extracts the data on journals to create those missing (based on the code).
            Then, for each journal, extract the moves associated

        :param tree: tree of the xml file
        :param default_currency: base currency defined in the SAF-T file
        :param map_accounts: mapping between saft and odoo ids (and balance) for accounts
        :param map_taxes: mapping between saft and odoo ids for taxes
        :param map_currencies: mapping between saft and odoo ids for taxes
        :param map_partners: mapping between saft and odoo ids for partners

        :returns: journals_to_create: values for the journals to create
        :returns: moves_to_create: values for the moves to create
        """

        nsmap = self._get_cleaned_namespace(tree)
        journals_to_create = {}
        moves_to_create = {}
        existing_journal_xml_ids = self.env['account.journal'].search(self.env['account.journal']._check_company_domain(self.company_id))._get_external_ids()
        existing_journal_xml_ids = {xml_id[0]: journal_id for journal_id, xml_id in existing_journal_xml_ids.items() if xml_id}
        possible_journal_types = self.env['account.journal']._fields['type'].get_values(self.env)

        for element_journal in tree.findall('.//saft:Journal', namespaces=nsmap):
            saft_journal_code = element_journal.find('saft:JournalID', namespaces=nsmap).text
            name = element_journal.find('saft:Description', namespaces=nsmap).text
            journal_type = element_journal.find('saft:Type', namespaces=nsmap)
            journal_type = journal_type.text if journal_type is not None and journal_type.text in possible_journal_types else 'general'
            xml_id = self._make_xml_id('journal', saft_journal_code)
            journal_id = existing_journal_xml_ids.get(xml_id) or xml_id
            if xml_id not in existing_journal_xml_ids:
                journal_code = saft_journal_code
                journals_to_create[xml_id] = {
                    'company_id': self.company_id.id,
                    'name': name,
                    'code': journal_code,
                    'type': journal_type,
                    'alias_name': f"{name}-{journal_code}-{self.company_id.name}",
                }
            moves_to_create.update(self._prepare_move_data(element_journal, default_currency, saft_journal_code, journal_id, map_accounts, map_taxes, map_currencies, map_partners))

        return journals_to_create, moves_to_create

    def _prepare_move_data(self, journal_tree, default_currency, saft_journal_code, journal_id, map_accounts, map_taxes, map_currencies, map_partners):
        """ Extracts the data on moves to be created. Those with the same name and journal won't be re-imported.

        :param journal_tree: tree of the xml hierarchy for the journal concerned
        :param default_currency: base currency defined in the SAF-T file
        :param saft_journal_code: saft code of the journal
        :param journal_id: odoo id of the journal
        :param map_accounts: mapping between saft and odoo ids (and balance) for accounts
        :param map_taxes: mapping between saft and odoo ids for taxes
        :param map_currencies: mapping between saft and odoo ids for taxes
        :param map_partners: mapping between saft and odoo ids for partners

        :returns: moves_to_create: values for the moves to create
        """
        nsmap = self._get_cleaned_namespace(journal_tree)
        moves_to_create = {}
        already_imported_move_xmlids = self.env['ir.model.data'].sudo().search_fetch(
            [('name', 'like', f'{self.company_id.id}_move_{saft_journal_code}_'), ('model', '=', 'account.move')],
            field_names=['module', 'name'],
        )
        already_imported_move_xmlids = [f'{move_data.module}.{move_data.name}' for move_data in already_imported_move_xmlids]

        for move_node in journal_tree.findall('saft:Transaction', namespaces=nsmap):
            move_date = move_node.find('./saft:TransactionDate', namespaces=nsmap)
            move_name = move_node.find('./saft:TransactionID', namespaces=nsmap)
            move_customer = move_node.find('./saft:CustomerID', namespaces=nsmap)
            move_supplier = move_node.find('./saft:SupplierID', namespaces=nsmap)
            move_partner = move_customer.text if move_customer is not None else move_supplier.text if move_supplier is not None else None
            xml_id = self._make_xml_id('move', f'{saft_journal_code}_{move_name.text}')
            if xml_id in already_imported_move_xmlids:
                continue
            line_data = []
            for line_node in move_node.findall('.//saft:Line', namespaces=nsmap):
                line_account = line_node.find('saft:AccountID', namespaces=nsmap)
                line_name = line_node.find('saft:Description', namespaces=nsmap)
                line_debit = line_node.find('saft:DebitAmount', namespaces=nsmap)
                line_credit = line_node.find('saft:CreditAmount', namespaces=nsmap)
                line_amount = line_node.find('.//saft:Amount', namespaces=nsmap)
                line_currency_code = line_node.find('.//saft:CurrencyCode', namespaces=nsmap)
                line_currency_amount = line_node.find('.//saft:CurrencyAmount', namespaces=nsmap)
                debit = float(line_amount.text) if line_debit is not None else 0
                credit = float(line_amount.text) if line_credit is not None else 0
                sign = 1 if debit - credit > 0 else -1

                tax_ids = []
                for tax_node in line_node.findall('saft:TaxInformation', namespaces=nsmap):
                    tax_code = tax_node.find('./saft:TaxCode', namespaces=nsmap)
                    tax_ids.append(map_taxes[tax_code.text])

                line_data.append(
                    Command.create({
                        'account_id': map_accounts[line_account.text]['id'],
                        'debit': float(line_amount.text) if line_debit is not None else 0,
                        'credit': float(line_amount.text) if line_credit is not None else 0,
                        'name': line_name.text,
                        'currency_id': map_currencies[line_currency_code.text] if line_currency_code is not None else default_currency.id,
                        **({'amount_currency': float(line_currency_amount.text) * sign} if line_currency_amount is not None else {}),
                        'tax_ids': [Command.set(tax_ids)],
                    })
                )

            moves_to_create[xml_id] = {
                'company_id': self.company_id.id,
                'journal_id': journal_id,
                'date': move_date.text,
                **({'partner_id': map_partners[move_partner]} if move_partner else {}),
                'name': move_name.text,
                'line_ids': line_data,
            }
        return moves_to_create

    def _get_data(self):
        """ Returns the data that is stored inside the XML SAF-T attachment, for each model, to be loaded. """
        import_data = base64.b64decode(self.attachment_id)
        tree = etree.fromstring(import_data)
        data = {}
        account_data, map_accounts = self._prepare_account_data(tree)
        data['account.account'] = account_data

        tax_to_create, map_taxes = self._prepare_tax_data(tree)
        data['account.tax'] = tax_to_create

        partner_data, map_partners = self._prepare_partner_data(tree)
        data['res.partner'] = partner_data

        data['account.journal'] = {}  # so journals are loaded before moves
        if self.import_opening_balance:
            data['account.move'] = self._prepare_opening_balance_move(tree, map_accounts)
        else:
            data['account.move'] = {}

        nsmap = self._get_cleaned_namespace(tree)
        default_currency_code = tree.find('.//saft:DefaultCurrencyCode', namespaces=nsmap)
        default_currency = self.env['res.currency'].with_context(active_test=False).search([('name', '=', default_currency_code.text)])

        all_currency_codes = tree.findall('.//saft:CurrencyCode', namespaces=nsmap)
        currency_codes_to_look_for = {currency_code_node.text for currency_code_node in all_currency_codes}
        currencies = self.env['res.currency'].with_context(active_test=False)._read_group(
            domain=[('name', 'in', list(currency_codes_to_look_for))],
            aggregates=['id:array_agg'],
            groupby=['name'],
        )
        map_currencies = {curr[0]: curr[1][0] for curr in currencies}

        journal_data, moves_data = self._prepare_journal_data(tree, default_currency, map_accounts, map_taxes, map_currencies, map_partners)

        data['account.journal'] = journal_data
        data['account.move'].update(moves_data)

        return data

    # -----------------------------------
    # Main method
    # -----------------------------------

    def action_import(self):
        """ Start the import by gathering generators and templates and applying them to attached files. """

        # Basic checks to start
        if not self.company_id.chart_template:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(_('You should install a Fiscal Localization first.'), action.id, _('Accounting Settings'))

        # In Odoo, move names follow sequences based on the year, so the checks complain
        # if the year present in the move's name doesn't match with the move's date.
        # This is unimportant here since we are importing existing moves from external data.
        # The workaround is to set the sequence.mixin.constraint_start_date parameter
        # to the date of the oldest move (defaulting to today if there is no move at all).
        domain = self.env['account.move']._check_company_domain(self.company_id)
        start_date = self.env['account.move'].search(domain, limit=1, order='date asc').date or fields.Date.today()
        self.env['ir.config_parameter'].sudo().set_param('sequence.mixin.constraint_start_date', start_date.strftime("%Y-%m-%d"))

        data = self._get_data()

        # skip_invoice_sync to avoid creating twice the tax lines
        created_vals = self.env['account.chart.template'].with_context(skip_invoice_sync=True)._load_data(data)

        import_summary = self.env['account.import.summary'].create({
            'import_summary_account_ids': created_vals.get("account.account"),
            'import_summary_journal_ids': created_vals.get("account.journal"),
            'import_summary_move_ids': created_vals.get("account.move"),
            'import_summary_partner_ids': created_vals.get("res.partner"),
            'import_summary_tax_ids': created_vals.get("account.tax"),
        })
        return import_summary.action_open_summary_view()
