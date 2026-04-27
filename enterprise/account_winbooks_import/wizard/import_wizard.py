# -*- coding: utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections
import io
import itertools
import logging
import os
import zipfile
import re
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory

from dbfread import DBF

from odoo import models, fields, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import frozendict

_logger = logging.getLogger(__name__)


PURCHASE_CODE = '0'
SALE_CODE = '2'
CREDIT_NOTE_PURCHASE_CODE = '1'
CREDIT_NOTE_SALE_CODE = '3'

class WinbooksImportWizard(models.TransientModel):
    _name = "account.winbooks.import.wizard"
    _description = 'Account Winbooks import wizard'

    zip_file = fields.Binary('File', required=True)
    only_open = fields.Boolean('Import only open years', help="Years closed in Winbooks are likely to have incomplete data. The counter part of incomplete entries will be set in a suspense account", default=True)
    suspense_code = fields.Char(string="Suspense Account Code", help="This is the code of the account in which you want to put the counterpart of unbalanced moves. This might be an account from your Winbooks data, or an account that you created in Odoo before the import.")

    def _import_partner_info(self, dbf_records):
        """Import information related to partner from *_table*.dbf files.
        The data in those files is the title, language, payment term and partner
        category.
        :return: (civility_data, category_data)
            civility_data is a dictionary whose keys are the Winbooks references
                and the values the civility title
            category_data is a dictionary whose keys are the Winbooks category
                references and the values the partner categories
        """
        _logger.info("Import Partner Infos")
        civility_data = {}
        category_data = {}
        ResPartnerTitle = self.env['res.partner.title']
        ResPartnerCategory = self.env['res.partner.category']
        for rec in dbf_records:
            if rec.get('TTYPE') == 'CIVILITY':
                shortcut = rec.get('TID')
                title = ResPartnerTitle.search([('shortcut', '=', shortcut)], limit=1)
                if not title:
                    title = ResPartnerTitle.create({'shortcut': shortcut, 'name': rec.get('TDESC')})
                civility_data[shortcut] = title.id
            elif rec.get('TTYPE').startswith('CAT'):
                category = ResPartnerCategory.search([('name', '=', rec.get('TDESC'))], limit=1)
                if not category:
                    category = ResPartnerCategory.create({'name': rec.get('TDESC')})
                category_data[rec.get('TID')] = category.id
        return civility_data, category_data

    def _import_partner(self, dbf_records, civility_data, category_data, account_data):
        """Import partners from *_csf*.dbf files.
        The data in those files is the partner details, its type, its category,
        bank informations, and central accounts.
        :return: a dictionary whose keys are the Winbooks partner references and
            the values are the partner ids in Odoo.
        """
        _logger.info("Import Partners")
        partner_data = {}
        ResBank = self.env['res.bank']
        ResCountry = self.env['res.country']
        ResPartner = self.env['res.partner']
        ResPartnerBank = self.env['res.partner.bank']
        partner_data_dict = {}
        for rec in dbf_records:
            if not rec.get('NUMBER'):
                continue
            partner = ResPartner.search([('ref', '=', rec.get('NUMBER'))], limit=1)
            if partner:
                partner_data[rec.get('NUMBER')] = partner.id
            if not partner:
                vatcode = rec.get('VATNUMBER') and rec.get('COUNTRY') and (rec.get('COUNTRY') + rec.get('VATNUMBER').replace('.', ''))
                if not rec.get('VATNUMBER') or not rec.get('COUNTRY') or not ResPartner.simple_vat_check(rec.get('COUNTRY').lower(), vatcode):
                    vatcode = ''
                data = {
                    'ref': rec.get('NUMBER'),
                    'name': rec.get('NAME1'),
                    'street': rec.get('ADRESS1'),
                    'country_id': ResCountry.search([('code', '=', rec.get('COUNTRY'))], limit=1).id,
                    'city': rec.get('CITY'),
                    'street2': rec.get('ADRESS2'),
                    'vat': vatcode,
                    'phone': rec.get('TELNUMBER'),
                    'zip': rec.get('ZIPCODE') and ''.join([n for n in rec.get('ZIPCODE') if n.isdigit()]),
                    'email': rec.get('EMAIL'),
                    'active': not rec.get('ISLOCKED'),
                    'title': civility_data.get(rec.get('CIVNAME1'), False),
                    'category_id': [(6, 0, [category_data.get(rec.get('CATEGORY'))])] if category_data.get(rec.get('CATEGORY')) else False
                }
                if partner_data_dict.get(rec.get('NUMBER')):
                    for key, value in partner_data_dict[rec.get('NUMBER')].items():
                        if value:  # Winbooks has different partners for customer/supplier. Here we merge the data of the 2
                            data[key] = value
                if rec.get('NAME2'):
                    data.update({
                        'child_ids': [(0, 0, {'name': rec.get('NAME2'), 'title': civility_data.get(rec.get('CIVNAME2'), False)})]
                    })
                # manage the bank account of the partner
                if rec.get('IBANAUTO'):
                    partner_bank = ResPartnerBank.search([('acc_number', '=', rec.get('IBANAUTO'))], limit=1)
                    if partner_bank:
                        data['bank_ids'] = [(4, partner_bank.id)]
                    else:
                        bank = ResBank.search([('name', '=', rec.get('BICAUTO'))], limit=1)
                        if not bank:
                            bank = ResBank.create({'name': rec.get('BICAUTO')})
                        data.update({
                            'bank_ids': [(0, 0, {
                                'acc_number': rec.get('IBANAUTO'),
                                'bank_id': bank.id
                            })],
                        })
                # manage the default payable/receivable accounts for the partner
                if rec.get('CENTRAL'):
                    if rec.get('TYPE') == '1':
                        data['property_account_receivable_id'] = account_data[rec.get('CENTRAL')]
                    else:
                        data['property_account_payable_id'] = account_data[rec.get('CENTRAL')]

                partner_data_dict[rec.get('NUMBER')] = data
                if len(partner_data_dict) % 100 == 0:
                    _logger.info("Advancement: %s", len(partner_data_dict))

        partner_ids = ResPartner.create(partner_data_dict.values())
        for partner in partner_ids:
            partner_data[partner.ref] = partner.id
        return partner_data, partner_ids

    def _import_account(self, dbf_records):
        """Import accounts from *_acf*.dbf files.
        The data in those files are the type, name, code and currency of the
        account as well as wether it is used as a default central account for
        partners or taxes.
        :return: (account_data, account_central, account_deprecated_ids, account_tax)
            account_data is a dictionary whose keys are the Winbooks account
                references and the values are the account ids in Odoo.
            account_central is a dictionary whose keys are the Winbooks central
                account references and the values are the account ids in Odoo.
            account_deprecated_ids is a recordset of account that need to be
                deprecated after the import.
            account_tax is a dictionary whose keys are the Winbooks account
                references and the values are the Winbooks tax references.
        """
        def manage_centralid(account, centralid, skip_constraints_check=False):
            "Set account to being a central account"
            property_name = None
            account_central[centralid] = account.id
            tax_group_name = None
            if centralid == 'S1':
                property_name = 'property_account_payable_id'
                model_name = 'res.partner'
            if centralid == 'C1':
                property_name = 'property_account_receivable_id'
                model_name = 'res.partner'
            if centralid == 'V01':
                tax_group_name = 'tax_receivable_account_id'
            if centralid == 'V03':
                tax_group_name = 'tax_payable_account_id'
            if property_name:
                self.env['ir.default'].set(model_name, property_name, account.id, company_id=self.env.company.id)
            if tax_group_name:
                self.env['account.tax.group'].search(self.env['account.tax.group']._check_company_domain(self.env.company)).with_context(skip_constraints_check=skip_constraints_check)[tax_group_name] = account

        _logger.info("Import Accounts")
        account_data = {}
        account_central = {}
        account_tax = {}
        grouped = collections.defaultdict(list)
        AccountAccount = self.env['account.account']
        ResCurrency = self.env['res.currency']
        AccountGroup = self.env['account.group']
        account_types = [
            {'min': 100, 'max': 160, 'id': 'equity'},
            {'min': 160, 'max': 200, 'id': 'liability_non_current'},
            {'min': 200, 'max': 280, 'id': 'asset_non_current'},
            {'min': 280, 'max': 290, 'id': 'asset_fixed'},
            {'min': 290, 'max': 420, 'id': 'asset_current'},
            {'min': 420, 'max': 490, 'id': 'liability_current'},
            {'min': 490, 'max': 492, 'id': 'asset_current'},
            {'min': 492, 'max': 500, 'id': 'liability_current'},
            {'min': 500, 'max': 600, 'id': 'asset_cash'},
            {'min': 600, 'max': 700, 'id': 'expense'},
            {'min': 700, 'max': 822, 'id': 'income'},
            {'min': 822, 'max': 860, 'id': 'expense'},
        ]
        for rec in dbf_records:
            grouped[rec.get('TYPE')].append(rec)
        rec_number_list = []
        account_data_list = []
        journal_centered_list = []
        is_deprecated_list = []
        account_deprecated_ids = self.env['account.account']
        for key, val in grouped.items():
            if key == '3':  # 3=general account, 9=title account
                for rec in val:
                    account = AccountAccount.search([
                        *AccountAccount._check_company_domain(self.env.company),
                        ('code', '=', rec.get('NUMBER')),
                    ], limit=1)
                    if account:
                        account_data[rec.get('NUMBER')] = account.id
                        rec['CENTRALID'] and manage_centralid(account, rec['CENTRALID'], skip_constraints_check=True)
                    if not account and rec.get('NUMBER') not in rec_number_list:
                        data = {
                            'code': rec.get('NUMBER'),
                            'name': rec.get('NAME11'),
                            'group_id': AccountGroup.search([('code_prefix_start', '=', rec.get('CATEGORY'))], limit=1).id,
                            'currency_id': ResCurrency.search([('name', '=', rec.get('CURRENCY'))], limit=1).id
                        }
                        if rec.get('VATCODE'):
                            account_tax[rec.get('NUMBER')] = rec.get('VATCODE')
                        try:
                            account_code = int(rec.get('NUMBER')[:3])
                        except Exception:
                            _logger.warning('%s is not a valid account number for %s.', rec.get('NUMBER'), rec.get('NAME11'))
                            account_code = 300  # set Current Asset by default for deprecated accounts
                        for account_type in account_types:
                            if account_code in range(account_type['min'], account_type['max']):
                                if rec.get('CENTRALID', '').startswith('C') or rec.get('CENTRALID', '').startswith('V01'):
                                    data['account_type'] = 'asset_receivable'
                                    data['reconcile'] = True
                                    data['non_trade'] = True
                                elif rec.get('CENTRALID', '').startswith('S') or rec.get('CENTRALID', '').startswith('V03'):
                                    data['account_type'] = 'liability_payable'
                                    data['reconcile'] = True
                                    data['non_trade'] = True
                                else:
                                    data['account_type'] = account_type['id']
                                    data['reconcile'] = False
                                break
                        # fallback for accounts not in range(100000,860000)
                        if not data.get('account_type'):
                            data['account_type'] = 'income_other'
                        account_data_list.append(data)
                        rec_number_list.append(rec.get('NUMBER'))
                        journal_centered_list.append(rec.get('CENTRALID'))
                        is_deprecated_list.append(rec.get('ISLOCKED'))

                        if len(account_data_list) % 100 == 0:
                            _logger.info("Advancement: %s", len(account_data_list))
        account_ids = AccountAccount.create(account_data_list)
        for account, rec_number, journal_centred, is_deprecated in zip(account_ids, rec_number_list, journal_centered_list, is_deprecated_list):
            account_data[rec_number] = account.id
            # create the ir.default if this is marked as a default account for something
            journal_centred and manage_centralid(account, journal_centred)
            # we can't deprecate the account now as we still need to add lines with this account
            # keep the list in memory so that we can deprecate later
            if is_deprecated:
                account_deprecated_ids += account
        return account_data, account_central, account_deprecated_ids, account_tax, account_ids

    def _post_process_account(self, account_data, vatcode_data, account_tax):
        """Post process the accounts after the taxes creation to add the taxes
        on the accounts"""
        for account, vat in account_tax.items():
            if vat in vatcode_data:
                self.env['account.account'].browse(account_data[account]).write({'tax_ids': [(4, vatcode_data[vat])]})

    def _post_process_tax(self, tax_ids, account_deprecated_ids):
        """Post process the tax data in order to avoid deprecating accounts
           used in repartition lines
        """
        account_deprecated_ids -= tax_ids.repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax').account_id
        return account_deprecated_ids

    def _import_journal(self, dbf_records):
        """Import journals from *_dbk*.dbf files.
        The data in those files are the name, code and type of the journal.
        :return: a dictionary whose keys are the Winbooks journal references and
            the values the journal ids in Odoo
        """
        _logger.info("Import Journals")
        journal_types = {
            '0': 'purchase',
            '1': 'purchase',
            '2': 'sale',
            '3': 'sale',
            '5': 'general',
        }
        journal_data = {}
        journals = self.env['account.journal']
        AccountJournal = self.env['account.journal']
        existing_journals = AccountJournal.search(AccountJournal._check_company_domain(self.env.company))
        used_codes = set(existing_journals.mapped('code'))
        processed_records = set()   # used to filter out duplicate records
        code_inc = 0
        for rec in dbf_records:
            if not rec.get('DBKID') or rec.get('DBKID') in processed_records:
                continue
            journal = existing_journals.filtered(lambda j: j.code == rec.get('DBKID'))
            if not journal:
                if rec.get('DBKTYPE') == '4':
                    journal_type = 'bank' if 'IBAN' in rec.get('DBKOPT') else 'cash'
                else:
                    journal_type = journal_types.get(rec.get('DBKTYPE'), 'general')
                # The code of a journal is limited to a size of 5 characters.
                # The following process is applied to the received code:
                # 1) Check if the 5 first characters is used.
                # 2) Check if the 5 last characters is used.
                # 3) Fall back on a generic code.
                # The format of this code will be the "*" character followed by an incremented number.
                # The possible values will range from "*1" to "*9999".
                # There are only 9999 possibilities, but it should be more than enough to handle the duplicate codes.
                # The purpose of this generic code is to not prevent the jounal creation and to be able
                # to quickly find it once created if we want to change it manually.
                code = rec.get('DBKID')[:5]
                if code in used_codes:
                    code = rec.get('DBKID')[-5:]
                while code in used_codes and code_inc < 10000:
                    code_inc += 1
                    code = '*%s' % code_inc
                used_codes.add(code)
                data = {
                    'name': rec.get('DBKDESC'),
                    'code': code,
                    'type': journal_type,
                }
                if data['type'] == 'sale':
                    data['default_account_id'] = self.env['product.category']._fields['property_account_income_categ_id'].get_company_dependent_fallback(self.env['product.category']).id
                if data['type'] == 'purchase':
                    data['default_account_id'] = self.env['product.category']._fields['property_account_expense_categ_id'].get_company_dependent_fallback(self.env['product.category']).id
                journal = AccountJournal.create(data)
            journal_data[rec.get('DBKID')] = journal.id
            journals += journal
            processed_records.add(rec.get('DBKID'))
        return journal_data, journals

    def _import_move(self, dbf_records, pdffiles, account_data, account_central, journal_data, partner_data, vatcode_data, param_data):
        """Import the journal entries from *_act*.dfb and @scandbk.zip files.
        The data in *_act*.dfb files are related to the moves and the data in
        @scandbk.zip files are the attachments.
        """
        _logger.info("Import Moves")
        ResCurrency = self.env['res.currency']
        IrAttachment = self.env['ir.attachment']
        suspense_account = self.env['account.account'].search([('code', '=', self.suspense_code)], limit=1)
        if not self.only_open and not suspense_account:
            raise UserError(_("The code for the Suspense Account you entered doesn't match any account"))
        counter_part_created = False
        result = [
            tupleized
            for tupleized in set(
                item
                for item in dbf_records
                if item.get("BOOKYEAR") and item.get("DOCNUMBER") != "99999999"
            )
        ]
        grouped = collections.defaultdict(list)
        currency_codes = set()
        for item in result:
            # Group by number/year/period
            grouped[item['DOCNUMBER'], item['DBKCODE'], item['DBKTYPE'], item['BOOKYEAR'], item['PERIOD']] += [item]

            # Get all currencies to search them in batch
            currency_codes.add(item.get('CURRCODE'))
        currencies = ResCurrency.with_context(active_test=False).search([('name', 'in', list(currency_codes))])
        if currencies:
            currencies.active = True
        currency_map = {currency.name: currency for currency in currencies}

        move_data_list = []
        pdf_file_list = []
        for key, val in grouped.items():
            journal_id = self.env['account.journal'].browse(journal_data.get(key[1]))
            if not journal_id:
                continue
            bookyear = int(key[3], 36)
            if not bookyear or (self.only_open and bookyear not in param_data['openyears']):
                continue
            perdiod_number = len(param_data['period_date'][bookyear]) - 2
            period = min(int(key[4]), perdiod_number + 1)  # closing is 99 in winbooks, not 13
            start_period_date = param_data['period_date'][bookyear][period]
            if 1 <= period < perdiod_number:
                end_period_date = param_data['period_date'][bookyear][period + 1] + timedelta(days=-1)
            elif period == perdiod_number:  # take the last day of the year = day of closing
                end_period_date = param_data['period_date'][bookyear][period + 1]
            else:  # opening (0) or closing (99) are at a fixed date
                end_period_date = start_period_date
            move_date = val[0].get('DATEDOC')
            move_data_dict = {
                'journal_id': journal_id.id,
                'move_type': 'out_invoice' if journal_id.type == 'sale' else 'in_invoice' if journal_id.type == 'purchase' else 'entry',
                'ref': '%s_%s' % (key[1], key[0]),
                'company_id': self.env.company.id,
                'date': min(max(start_period_date, move_date), end_period_date),
                'payment_state': 'not_paid',
            }
            if not move_data_dict.get('journal_id') and key[1] == 'MATCHG':
                continue
            move_line_data_list = []
            move_amount_total = 0
            move_total_receivable_payable = 0

            # Split lines having a different sign on the balance in company currency and foreign currency
            tmp_val = []
            for rec in val:
                tmp_val += [rec.copy()]
                if (rec['AMOUNTEUR'] or 0) * (rec['CURRAMOUNT'] or 0) < 0:
                    tmp_val[-1]['CURRAMOUNT'] = 0
                    tmp_val += [rec.copy()]
                    tmp_val[-1]['AMOUNTEUR'] = 0
            val = tmp_val

            # Basic line info
            for rec in val:
                currency = currency_map.get(rec.get('CURRCODE'))
                partner_id = self.env['res.partner'].browse(partner_data.get(rec.get('ACCOUNTRP'), False))
                account_id = self.env['account.account'].browse(account_data.get(rec.get('ACCOUNTGL')))
                matching_number = rec.get('MATCHNO') and '%s-%s' % (rec.get('ACCOUNTGL'), rec.get('MATCHNO')) or False
                balance = rec.get('AMOUNTEUR', 0.0)
                amount_currency = rec.get('CURRAMOUNT') if currency and rec.get('CURRAMOUNT') else balance
                if balance and not account_id:
                    account_id = suspense_account
                line_data = {
                    'date': rec.get('DATE', False),
                    'account_id': account_id.id,
                    'partner_id': partner_id.id,
                    'date_maturity': rec.get('DUEDATE', False),
                    'name': rec.get('COMMENT'),
                    'balance': balance,
                    'amount_currency': amount_currency,
                    'amount_residual_currency': amount_currency,
                    'matching_number': balance != 0.0 and matching_number and f"I{matching_number}",
                    'winbooks_line_id': rec['DOCORDER'],
                }
                if currency:
                    line_data['currency_id'] = currency.id

                if move_data_dict['move_type'] != 'entry':
                    if rec.get('DOCORDER') == 'VAT':
                        line_data['display_type'] = 'tax'
                    elif account_id and account_id.account_type in ('asset_receivable', 'liability_payable'):
                        line_data['display_type'] = 'payment_term'
                    elif rec.get('DBKTYPE') in (CREDIT_NOTE_PURCHASE_CODE, SALE_CODE):
                        line_data['price_unit'] = -amount_currency
                    elif rec.get('DBKTYPE') in (PURCHASE_CODE, CREDIT_NOTE_SALE_CODE):
                        line_data['price_unit'] = amount_currency

                if rec.get('AMOUNTEUR'):
                    move_amount_total = round(move_amount_total, 2) + round(rec.get('AMOUNTEUR'), 2)
                move_line_data_list.append((0, 0, line_data))
                if account_id.account_type in ('asset_receivable', 'liability_payable'):
                    move_total_receivable_payable += rec.get('AMOUNTEUR')

            # Compute refund value
            if journal_id.type in ('sale', 'purchase'):
                is_refund = move_total_receivable_payable < 0 if journal_id.type == 'sale' else move_total_receivable_payable > 0
                if is_refund and key[2] in (PURCHASE_CODE, SALE_CODE):
                    # We are importing a negative invoice or purchase, so we need to change it to a credit note and inverse the price_units
                    for move_line_data in move_line_data_list:
                        if move_line_data[2].get('price_unit'):
                            move_line_data[2]['price_unit'] = -move_line_data[2]['price_unit']
            else:
                is_refund = False

            # Add tax information
            for line_data, rec in zip(move_line_data_list, val):
                if self.env['account.account'].browse(account_data.get(rec.get('ACCOUNTGL'))).account_type in ('asset_receivable', 'liability_payable'):
                    continue
                tax_line = self.env['account.tax'].browse(vatcode_data.get(rec.get('VATCODE') or rec.get('VATIMPUT', [])))
                if not tax_line and line_data[2]['account_id'] in account_central.values():
                    # this line is on a centralised account, most likely a tax account, but is not linked to a tax
                    # this is because the counterpart (second repartion line) line of a tax is not flagged in Winbooks
                    try:
                        counterpart = next(r for r in val if r['AMOUNTEUR'] == -rec['AMOUNTEUR'] and r['DOCORDER'] == 'VAT' and r['VATCODE'])
                        tax_line = self.env['account.tax'].browse(vatcode_data.get(counterpart['VATCODE']))
                    except StopIteration:
                        pass  # We didn't find a tax line that is counterpart with same amount
                is_vat_account = (
                    self.env.company.country_id.code == 'BE' and rec.get('ACCOUNTGL')[:3] in ('411', '451')
                    or self.env.company.country_id.code == 'LU' and rec.get('ACCOUNTGL')[:4] in ('4614', '4216')
                )
                is_vat = (
                    rec.get('DOCORDER') == 'VAT'
                    or move_data_dict['move_type'] == 'entry' and is_vat_account
                )
                repartition_line = is_refund and tax_line.refund_repartition_line_ids or tax_line.invoice_repartition_line_ids
                repartition_type = 'tax' if is_vat else 'base'
                line_data[2].update({
                    'tax_ids': tax_line and not is_vat and [(4, tax_line.id)] or [],
                    'tax_tag_ids': [(6, 0, tax_line.get_tax_tags(is_refund, repartition_type).ids)],
                    'tax_repartition_line_id': is_vat and repartition_line.filtered(lambda x: x.repartition_type == repartition_type and x.account_id.id == line_data[2]['account_id']).id or False,
                })
            move_line_data_list = [line for line in move_line_data_list if line[2]['account_id']]  # Remove empty lines

            # Adapt invoice specific informations
            if move_data_dict['move_type'] != 'entry':
                # In Winbooks, invoice lines have the same currency, so we take the currency of the first line
                move_data_dict['currency_id'] = currency_map.get(val[0].get('CURRCODE'), self.env.company.currency_id).id
                move_data_dict['partner_id'] = move_line_data_list[0][2]['partner_id']
                move_data_dict['invoice_date_due'] = move_line_data_list[0][2]['date_maturity']
                move_data_dict['invoice_date'] = move_line_data_list[0][2]['date']
                if is_refund:
                    move_data_dict['move_type'] = move_data_dict['move_type'].replace('invoice', 'refund')

            # Balance move, should not happen in an import from a complete db
            if move_amount_total:
                if not counter_part_created:
                    _logger.warning(_('At least one automatic counterpart has been created at import. This is probably an error. Please check entry lines with reference: Counterpart (generated at import from Winbooks)'))
                counter_part_created = True
                account_id = journal_id.default_account_id
                account_id = account_id or (partner_id.property_account_payable_id if rec.get('DOCTYPE') in ['0', '1'] else partner_id.property_account_receivable_id)
                account_id = account_id or suspense_account  # Use suspense account as fallback
                line_data = {
                    'account_id': account_id.id,
                    'date_maturity': rec.get('DUEDATE', False),
                    'name': _('Counterpart (generated at import from Winbooks)'),
                    'balance': -move_amount_total,
                    'amount_currency': -move_amount_total,
                    'price_unit': abs(move_amount_total),
                }
                move_line_data_list.append((0, 0, line_data))

            if (
                move_data_dict['move_type'] != 'entry'
                and len(move_line_data_list) == 1
                and move_line_data_list[0][2].get('display_type') == 'payment_term'
                and move_line_data_list[0][2]['balance'] == 0
            ):
                # add a line so that the payment terms are not deleted during sync
                line_data = {
                    'account_id': journal_id.default_account_id.id,
                    'name': _('Counterpart (generated at import from Winbooks)'),
                    'balance': 0,
                }
                move_line_data_list.append((0, 0, line_data))

            # Link all to the move
            move_data_dict['line_ids'] = move_line_data_list
            attachment_key = '%s_%s_%s' % (key[1], key[4], key[0])
            pdf_files = {name: fd for name, fd in pdffiles.items() if attachment_key in name}
            pdf_file_list.append(pdf_files)
            move_data_list.append(move_data_dict)

            if len(move_data_list) % 100 == 0:
                _logger.info("Advancement: %s", len(move_data_list))

        _logger.info("Creating moves")
        move_ids = self.env['account.move'].with_context(skip_invoice_sync=True).create(move_data_list)
        _logger.info("Creating attachments")
        attachment_data_list = []
        for move, pdf_files in zip(move_ids, pdf_file_list):
            if pdf_files:
                for name, fd in pdf_files.items():
                    attachment_data = {
                        'name': name.split('/')[-1],
                        'type': 'binary',
                        'datas': base64.b64encode(fd.read()),
                        'res_model': move._name,
                        'res_id': move.id,
                        'res_name': move.name
                    }
                    attachment_data_list.append(attachment_data)
        self.env['ir.attachment'].create(attachment_data_list)
        return {f"{m.date.year}_{m.ref}" : m for m in move_ids}, move_ids

    def _import_analytic_account(self, dbf_records, param_data):
        """Import the analytic accounts from *_anf*.dbf files.
        :return: a dictionary whose keys are the Winbooks analytic account
        references and the values the analytic account ids in Odoo.
        """
        _logger.info("Import Analytic Accounts")
        analytic_account_data = {}
        analytic_plan_dict = {}
        analytic_accounts = self.env['account.analytic.account']
        AccountAnalyticAccount = self.env['account.analytic.account']
        AccountAnalyticPlan = self.env['account.analytic.plan']
        for rec in dbf_records:
            if not rec.get('NUMBER'):
                continue
            analytic_account = AccountAnalyticAccount.search(
                [('code', '=', rec.get('NUMBER')), ('company_id', '=', self.env.company.id)], limit=1)
            plan_name = param_data['ZONANA' + rec['TYPE']]
            if not analytic_plan_dict.get(plan_name):
                analytic_plan_dict[plan_name] = (
                    AccountAnalyticPlan.search([('name', '=', plan_name)], limit=1)
                    or AccountAnalyticPlan.create({'name': plan_name})
                )
            if not analytic_account:
                data = {
                    'code': rec.get('NUMBER'),
                    'name': rec.get('NAME1'),
                    'active': not rec.get('INVISIBLE'),
                    'plan_id': analytic_plan_dict[plan_name].id,
                }
                analytic_account = AccountAnalyticAccount.create(data)
            analytic_accounts += analytic_account
            analytic_account_data[rec['NUMBER']] = analytic_account
        return analytic_account_data, analytic_accounts

    def _import_analytic_account_line(self, dbf_records, analytic_account_data, account_data, move_data, param_data):
        """Import the analytic lines from the *_ant*.dbf files.
        """
        _logger.info("Import Analytic Account Lines")
        analytic_line_data_list = []
        analytic_list = None
        line2analytics2amount = collections.defaultdict(lambda: collections.defaultdict(float))  # {account.move.line: {analytic_ids: amount}}
        for rec in dbf_records:
            bookyear = int(rec['BOOKYEAR'] or '0', 36)
            if not bookyear or (self.only_open and bookyear not in param_data['openyears']):
                continue
            if not analytic_list:
                # In this winbooks file, there is one column for each analytic plan, named 'ZONANA' + [number of the plan].
                # These columns contain the analytic account number associated to that plan.
                # We thus need to create an analytic line for each of these accounts.
                analytic_list = [k for k in rec.keys() if 'ZONANA' in k]
            bookyear_first_year = param_data['period_date'][int(rec['BOOKYEAR'], 36)][0].year
            bookyear_last_year = param_data['period_date'][int(rec['BOOKYEAR'], 36)][-1].year
            journal_code, move_number = rec['DBKCODE'], rec['DOCNUMBER']
            account_id = account_data.get(rec.get('ACCOUNTGL'))
            analytic_accounts = [
                analytic_account_data.get(rec[analytic])
                for analytic in analytic_list
                if analytic_account_data.get(rec.get(analytic))
            ]
            move = move_data.get(f"{bookyear_first_year}_{journal_code}_{move_number}") or move_data.get(f"{bookyear_last_year}_{journal_code}_{move_number}")
            if move:
                # Since the moves are in draft, the analytic lines can't exist yet
                move_line = move.line_ids.filtered(lambda l:
                    l.winbooks_line_id == rec['DOCORDER']
                    and l.account_id.id == account_id
                    and round(l.balance, 1) == round(rec.get('AMOUNTGL'), 1)
                )[:1]
                line2analytics2amount[move_line][','.join(str(a.id) for a in analytic_accounts)] += rec.get('AMOUNTEUR')
            else:
                analytic_line_data_list.append({
                    'date': rec.get('DATE', False),
                    'name': rec.get('COMMENT'),
                    'amount': -rec.get('AMOUNTEUR'),
                    'general_account_id': account_id,
                    **{account.plan_id._column_name(): account.id for account in analytic_accounts},
                })
                if len(analytic_line_data_list) % 100 == 0:
                    _logger.info("Advancement: %s", len(analytic_line_data_list))
        if line2analytics2amount or analytic_line_data_list:
            group_user = self.env.ref('base.group_user', raise_if_not_found=False)
            group_analytic = self.env.ref('analytic.group_analytic_accounting', raise_if_not_found=False)
            if group_user and group_analytic:
                group_user.sudo()._apply_group(group_analytic)
        if line2analytics2amount:
            _logger.info("Updating Analytic Distributions on %s lines", len(line2analytics2amount))
            self.env['decimal.precision'].search([('name', '=', 'Percentage Analytic')]).digits = 6
            for line, analytics2amount in line2analytics2amount.items():
                line.analytic_distribution = {
                    analytics: 100 * (amount / line.balance if amount and line.balance else 1)
                    for analytics, amount in analytics2amount.items()
                }
        if analytic_line_data_list:
            _logger.info("Creating Analytic Lines")
        return self.env['account.analytic.line'].create(analytic_line_data_list)

    def _import_vat(self, dbf_records, account_central):
        """Import the taxes from *codevat.dbf files.
        The data in thos files are the amount, type, including, account and tags
        of the taxes.
        :return: a dictionary whose keys are the Winbooks taxes references and
        the values are the taxes ids in Odoo.
        """
        _logger.info("Import VAT")
        vatcode_data = {}
        treelib = {}
        AccountTax = self.env['account.tax']
        tags_cache = {}

        def get_tags(string):
            "Split the tags, create if it doesn't exist and return m2m command for creation"
            tag_ids = self.env['account.account.tag']
            if not string:
                return tag_ids
            indexes = [i for i, x in enumerate(string) if x in ('+', '-')] + [len(string)]
            for i in range(len(indexes) - 1):
                tag_name = string[indexes[i]: indexes[i + 1]]
                tag_id = tags_cache.get(tag_name, False)
                if not tag_id:
                    tag_id = self.env['account.account.tag'].with_context(lang='en_US').search([('name', '=', tag_name), ('applicability', '=', 'taxes')])
                    tags_cache[tag_name] = tag_id
                if not tag_id:
                    tag_id = self.env['account.account.tag'].create({'name': tag_name, 'applicability': 'taxes', 'country_id': self.env.company.account_fiscal_country_id.id})
                tag_ids += tag_id
            return [(4, id, 0) for id in tag_ids.ids]

        data_list = []
        code_list = []
        for rec in sorted(dbf_records, key=lambda rec: len(rec.get('TREELEVEL'))):
            treelib[rec.get('TREELEVEL')] = rec.get('TREELIB1')
            if not rec.get('USRCODE1'):
                continue
            tax_name = " ".join([treelib[x] for x in [rec.get('TREELEVEL')[:i] for i in range(2, len(rec.get('TREELEVEL')) + 1, 2)]])
            tax = AccountTax.search([('company_id', '=', self.env.company.id), ('name', '=', tax_name),
                                        ('type_tax_use', '=', 'sale' if rec.get('CODE')[0] == '2' else 'purchase')], limit=1)
            if tax.amount != rec.get('RATE') if rec.get('TAXFORM') else 0.0:
                tax.amount = rec.get('RATE') if rec.get('TAXFORM') else 0.0
            if tax:
                vatcode_data[rec.get('CODE')] = tax.id
            else:
                data = {
                    'amount_type': 'percent',
                    'name': tax_name,
                    'company_id': self.env.company.id,
                    'amount': rec.get('RATE') if rec.get('TAXFORM') else 0.0,
                    'type_tax_use': 'sale' if rec.get('CODE')[0] == '2' else 'purchase',
                    'price_include_override': 'tax_excluded' if rec.get('TAXFORM') or rec.get('BASFORM') == 'BAL' else 'tax_included',
                    'refund_repartition_line_ids': [
                        (0, 0, {'repartition_type': 'base', 'tag_ids': get_tags(rec.get('BASE_CN')), 'company_id': self.env.company.id}),
                        (0, 0, {'repartition_type': 'tax', 'tag_ids': get_tags(rec.get('TAX_CN')), 'company_id': self.env.company.id, 'account_id': account_central.get(rec.get('ACCCN1'), False)}),
                    ],
                    'invoice_repartition_line_ids': [
                        (0, 0, {'repartition_type': 'base', 'tag_ids': get_tags(rec.get('BASE_INV')), 'company_id': self.env.company.id}),
                        (0, 0, {'repartition_type': 'tax', 'tag_ids': get_tags(rec.get('TAX_INV')), 'company_id': self.env.company.id, 'account_id': account_central.get(rec.get('ACCINV1'), False)}),
                    ],
                }
                if rec.get('ACCCN2'):
                    data['refund_repartition_line_ids'] += [(0, 0, {'repartition_type': 'tax', 'factor_percent': -100.0, 'tag_ids': [], 'company_id': self.env.company.id, 'account_id': account_central.get(rec.get('ACCCN2'), False)})]
                if rec.get('ACCINV2'):
                    data['invoice_repartition_line_ids'] += [(0, 0, {'repartition_type': 'tax', 'factor_percent': -100.0, 'tag_ids': [], 'company_id': self.env.company.id, 'account_id': account_central.get(rec.get('ACCINV2'), False)})]
                data_list.append(data)
                code_list.append(rec.get('CODE'))

                if len(data_list) % 100 == 0:
                    _logger.info("Advancement: %s", len(data_list))
        tax_ids = AccountTax.create(data_list)
        for tax_id, code in zip(tax_ids, code_list):
            vatcode_data[code] = tax_id.id
        return vatcode_data, tax_ids

    def _import_param(self, dbf_records):
        """Import parameters from *_param.dbf files.
        The data in those files is the open or closed state of financial years
        in Winbooks.
        :return: a dictionary with the parameters extracted.
        """
        def parse_csv_value(csv_values):
            return dict(pair.split('=') for pair in csv_values.split(','))

        param_data = {}
        param_data['openyears'] = []
        param_data['period_date'] = {}
        for rec in dbf_records:
            if not rec.get('ID'):
                continue
            rec_id = rec.get('ID')
            value = rec.get('VALUE')
            # only the lines with status 'open' are known to be complete/without unbalanced entries
            search = re.search(r'BOOKYEAR(\d+).STATUS', rec_id)
            if search and search.group(1) and value.lower() == 'open':
                param_data['openyears'].append(int(search.group(1)))
            # winbooks has 3 different dates on a line : the move date, the move line date, and the period
            # here we get the different periods as it is what matters for the reports
            search = re.search(r'BOOKYEAR(\d+).PERDATE', rec_id)
            if search and search.group(1):
                param_data['period_date'][int(search.group(1))] = [datetime.strptime(value[i*8:(i+1)*8], '%d%m%Y').date() for i in range(int(len(value)/8))]
            try:
                csv_values = parse_csv_value(value + rec.get('VALUEEXT'))
            except ValueError:
                csv_values = {}
            if csv_values.get('NAME', '').startswith('ZONANA'):  # get the names of analytic plans
                param_data[csv_values['NAME']] = csv_values['TIT1']
        return param_data

    def _post_import(self, account_deprecated_ids):
        account_deprecated_ids.write({'deprecated': True})  # We can't set it before because of a constraint in aml's create

    def import_winbooks_file(self):
        """Import all the data from a Winbooks database dump. The imported
        models are the journals, the accounts, the taxes, the journal entries,
        and the analytic account and lines.
        """
        if not self.env.company.country_id:
            action = self.env.ref('base.action_res_company_form')
            raise RedirectWarning(_('Please define the country on your company.'), action.id, _('Company Settings'))
        if not self.env.company.chart_template:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(_('You should install a Fiscal Localization first.'), action.id,  _('Accounting Settings'))
        self = self.with_context(active_test=False)
        with TemporaryDirectory() as file_dir:
            def get_dbfrecords(filterfunc):
                return itertools.chain.from_iterable(
                    DBF(os.path.join(file_dir, file), encoding='latin', recfactory=frozendict).records
                    for file in [s for s in dbffiles if filterfunc(s)]
                )

            # the main zip is only a container for other sub zips
            with zipfile.ZipFile(io.BytesIO(base64.decodebytes(self.zip_file))) as zip_ref:
                sub_zips = [
                    filename
                    for filename in zip_ref.namelist()
                    if filename.lower().endswith('.zip')
                ]
                zip_ref.extractall(file_dir, members=sub_zips)

            # @cie@ sub zip file contains all the data
            try:
                cie_zip_name = next(filename for filename in sub_zips if "@cie@" in filename.lower())
            except StopIteration:
                raise UserError(_("No data zip in the main archive. Please use the complete Winbooks export."))
            with zipfile.ZipFile(os.path.join(file_dir, cie_zip_name), 'r') as child_zip_ref:
                dbffiles = [
                    filename
                    for filename in child_zip_ref.namelist()
                    if filename.lower().endswith('.dbf')
                ]
                child_zip_ref.extractall(file_dir, members=dbffiles)

            # @scandbk@ zip file contains all the attachments
            pdffiles = {}
            scan_zip_names = [filename for filename in sub_zips if "@scandbk" in filename.lower()]
            try:
                for scan_zip_name in scan_zip_names:
                    with zipfile.ZipFile(os.path.join(file_dir, scan_zip_name), 'r') as scan_zip:
                        _pdffiles = [
                            filename
                            for filename in scan_zip.namelist()
                            if filename.lower().endswith('.pdf')
                        ]
                        scan_zip.extractall(file_dir, members=_pdffiles)
                        for filename in _pdffiles:
                            pdffiles[filename] = open(os.path.join(file_dir, filename), "rb")

                # load all the records
                param_recs = get_dbfrecords(lambda file: file.lower().endswith("_param.dbf"))
                param_data = self._import_param(param_recs)

                dbk_recs = get_dbfrecords(lambda file: "dbk" in file.lower() and file.lower().endswith('.dbf'))
                journal_data, journal_ids = self._import_journal(dbk_recs)

                acf_recs = get_dbfrecords(lambda file: file.lower().endswith("_acf.dbf"))
                account_data, account_central, account_deprecated_ids, account_tax, account_ids = self._import_account(acf_recs)

                vat_recs = get_dbfrecords(lambda file: file.lower().endswith("_codevat.dbf"))
                vatcode_data, tax_ids = self._import_vat(vat_recs, account_central)

                account_deprecated_ids = self._post_process_tax(tax_ids, account_deprecated_ids)
                self._post_process_account(account_data, vatcode_data, account_tax)

                table_recs = get_dbfrecords(lambda file: file.lower().endswith("_table.dbf"))
                civility_data, category_data = self._import_partner_info(table_recs)

                csf_recs = get_dbfrecords(lambda file: file.lower().endswith("_csf.dbf"))
                partner_data, partner_ids = self._import_partner(csf_recs, civility_data, category_data, account_data)

                act_recs = get_dbfrecords(lambda file: file.lower().endswith("_act.dbf"))
                move_data, move_ids = self._import_move(act_recs, pdffiles, account_data, account_central, journal_data, partner_data, vatcode_data, param_data)

                anf_recs = get_dbfrecords(lambda file: file.lower().endswith("_anf.dbf"))
                analytic_account_data, analytic_account_ids = self._import_analytic_account(anf_recs, param_data)

                ant_recs = get_dbfrecords(lambda file: file.lower().endswith("_ant.dbf"))
                analytic_account_line_ids = self._import_analytic_account_line(ant_recs, analytic_account_data, account_data, move_data, param_data)

                self._post_import(account_deprecated_ids)
                _logger.info("Completed")
                self.env['onboarding.onboarding.step'].sudo().action_validate_step('account.onboarding_onboarding_step_chart_of_accounts')

                import_summary = self.env['account.import.summary'].create({
                    'import_summary_account_ids': account_ids,
                    'import_summary_journal_ids': journal_ids,
                    'import_summary_move_ids': move_ids,
                    'import_summary_partner_ids': partner_ids,
                    'import_summary_tax_ids': tax_ids,
                    'import_summary_analytic_ids': analytic_account_ids,
                    'import_summary_analytic_line_ids': analytic_account_line_ids,
                })
            finally:
                for fd in pdffiles.values():
                    fd.close()
        return import_summary.action_open_summary_view()
