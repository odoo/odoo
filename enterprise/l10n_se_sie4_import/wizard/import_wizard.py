import base64
import csv
import re

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, Command, fields, models, modules, tools
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

DATEFORMAT_SIE4 = '%Y%m%d'
DATEFORMAT_MAIN = DEFAULT_SERVER_DATE_FORMAT


class SIE4ImportWizard(models.TransientModel):
    _name = 'l10n_se_sie4_import.wizard'
    _description = "Accounting SIE 4 import wizard"

    attachment_name = fields.Char(string="Filename")
    attachment_file = fields.Binary(string="SIE 4 File", required=True)
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company)
    update_account_data = fields.Boolean(
        string="Update Chart of Account data",
        help="Update existing accounts information with the file's information.",
    )
    import_opening_balance = fields.Boolean(
        string="Import account opening balances",
        help="Compare opening balance information from Odoo with the file and create a move with the difference found.",
    )

    # --------------------------------------------------------------------------
    # IMPORT KEY HANDLERS (in order)
    # --------------------------------------------------------------------------
    # 1. Identification items
    # --------------------------------------------------------------------------

    def _import_key_orgnr(self, data_map, org_number):
        """
        Handles the #ORGNR item.
        Specifies the swedish organization number of the imported company.
        :param str org_number:
        """
        data_map['res.company'][self.company_id.id].update({
            'vat': f"SE{org_number.replace('-', '')}01",
        })

    def _import_key_adress(self, data_map, addr_detail, addr_main, telephone):
        """
        Handles the #ADRESS item.
        Specifies the address information of the imported company.
        :param str addr_detail:
        :param str addr_main:
        :param str telephone:
        """
        data_map['res.company'][self.company_id.id].update({
            'street': addr_main,
            'street2': addr_detail,
            'phone': telephone,
        })

    def _import_key_fnamn(self, data_map, company_name):
        """
        Handles the #FNAMN item.
        Specifies the imported company name.
        :param str company_name:
        """
        data_map['res.company'][self.company_id.id].update({
            'name': company_name,
        })

    def _import_key_rar(self, data_map, year_idx, date_from, date_to):
        """
        Handles all #RAR items.
        Specifies the financial year dates of the exported data.
        :param str year_idx: '0' for current year, '-1' for previous year.
        :param str date_from: start date string in the main format
        :param str date_to: end date string in the main format
        """
        date_from = self._get_standard_date_str(date_from)
        date_to = self._get_standard_date_str(date_to)
        data_map['dates'][year_idx] = {
            'date_from': date_from,
            'date_to': date_to,
        }
        if year_idx == '0':  # also add info for next year
            data_map['dates']['1'] = {
                'date_from': (datetime.strptime(date_from, DATEFORMAT_MAIN) + relativedelta(years=1)).strftime(DATEFORMAT_MAIN),
                'date_to': (datetime.strptime(date_to, DATEFORMAT_MAIN) + relativedelta(years=1)).strftime(DATEFORMAT_MAIN),
            }

    # --------------------------------------------------------------------------
    # 2. Chart of accounts information items
    # --------------------------------------------------------------------------

    def _import_key_konto(self, data_map, account_code, account_name):
        """
        Handles all #KONTO items.
        Specifies the name of the account related to the mentioned code.
        :param str account_code:
        :param str account_name:
        """
        if account_code in data_map['existing_accounts_map']:
            if self.update_account_data:
                account_id = data_map['existing_accounts_map'][account_code]
                matching_account = self.env['account.account'].browse(account_id)
                if matching_account.name != account_name:
                    data_map['account.account'].setdefault(matching_account.id, {})
                    data_map['account.account'][matching_account.id].update({'name': account_name})
        else:
            account_xml_id = self._make_xml_id('account', account_code)
            data_map['account.account'].setdefault(account_xml_id, {'company_ids': self.company_id.ids, 'code': account_code})
            data_map['account.account'][account_xml_id].update({'name': account_name})

    def _import_key_ktyp(self, data_map, account_code, sie4_type_code):
        """
        Handles all #KTYP items.
        :param str account_code:
        :param str sie4_type_code: Can be one of the following: "T" (asset), "S" (debt), "K" (expense), or "I" (income)
        """
        match sie4_type_code:
            case "T":
                account_type = "asset_receivable"
            case "S":
                account_type = "liability_current"
            case "K":
                account_type = "expense"
            case _:  # "I"
                account_type = "income"

        if account_code in data_map['existing_accounts_map']:
            if self.update_account_data:
                account_id = data_map['existing_accounts_map'][account_code]
                matching_account = self.env['account.account'].browse(account_id)
                if matching_account.account_type != account_type:
                    data_map['account.account'].setdefault(matching_account.id, {})
                    data_map['account.account'][matching_account.id].update({'account_type': account_type})
        else:
            account_xml_id = self._make_xml_id('account', account_code)
            data_map['account.account'].setdefault(account_xml_id, {'company_ids': self.company_id.ids, 'code': account_code})
            data_map['account.account'][account_xml_id].update({'account_type': account_type})

    # --------------------------------------------------------------------------
    # 3. Balance items / Verification items
    # --------------------------------------------------------------------------

    def _import_key_ib(self, data_map, year_idx, account_code, balance):
        """
        Handles all #IB (opening balance) items.
        #IB will only be imported when the import balance preference is checked.
        For the first SIE 4 import implementation, we will only import #IB 0 and ignore everything else as their purpose are still unclear.
        This method gathers all the mentioned account codes and its balance into the data_map, to be processed as a batch later.
        :param str year_idx:
        :param str account_code:
        :param str balance:
        """
        if not self.import_opening_balance or year_idx != '0':
            return
        data_map['opening_balance_map'][account_code] = float(balance)

    def _import_key_ub(self, data_map, year_idx, account_code, balance):
        """
        Handles all #UB (closing balance) items.
        #UB is the exact same as the opening balance (#IB) of the next year.
        In Odoo, we only save the opening balance move, so we don't really need this item.
        However, in SIE 4, the file also provides closing balance for the current year.
        In that scenario, we should treat them as an opening balance for the next year.
        :param str year_idx:
        :param str account_code:
        :param str balance:
        """
        if year_idx == '0':  # current year's closing balance
            year_idx = '1'
            self._import_key_ib(data_map, year_idx, account_code, balance)

    def _import_special_key_ver(self, data_map, verification_str, verification_date, verification_text, transactions):
        """
        #VER (short for "verification") is a special key; it's always comes with list of transactions to verify.
        In Odoo, they are specified as ``account.move``, where each transaction is an ``account.move.line``

        :param str verification_str: the unique XML id based on the SIE4 move
        :param str verification_date: the date of the move in SIE 4 format
        :param str verification_text: the additional detail text of the move. By default, they should be an empty string
        :param list[dict] transactions: [{'account_code': <str>, 'balance': <float>}, ...]
        """
        move_xml_id = self._make_xml_id('move', verification_str)
        line_ids = []

        for transaction in transactions:
            code = transaction['account_code']
            account_id = data_map['existing_accounts_map'].get(code, self._make_xml_id('account', code))
            line_ids.append(Command.create({
                'account_id': account_id,
                'amount_currency': transaction['balance'],
                'currency_id': self.company_id.currency_id.id,
            }))

        move_ref = _("Imported from SIE4")
        if verification_text:
            move_ref += f" - {verification_text}"

        data_map['account.move'][move_xml_id] = {
            'company_id': self.company_id.id,
            'journal_id': data_map['journal_misc_id'],
            'date': self._get_standard_date_str(verification_date),
            'line_ids': line_ids,
            'ref': move_ref,
        }

    # --------------------------------------------------------------------------
    # UTILITIES
    # --------------------------------------------------------------------------

    def _make_xml_id(self, prefix, key):
        if tools.config['test_enable'] or modules.module.current_test:
            return f'test.{prefix}_{key}'
        if '_' in prefix:
            raise ValueError('`prefix` cannot contain an underscore')
        key = key.replace(' ', '_').replace('-', '_')
        return f"l10n_se_sie4_import.{self.company_id.id}_{prefix}_{key}"

    @api.model
    def _get_standard_date_str(self, sie_date):
        """
        Convert the SIE 4 date format (ex: '20240131') to the standard format (ex: '2024-01-31')
        :param str sie_date: the date string in SIE 4 format
        :rtype: str
        """
        return datetime.strptime(sie_date, DATEFORMAT_SIE4).strftime(DATEFORMAT_MAIN)

    @api.model
    def _get_sie4_line_items(self, sie4_line):
        """
        The SIE 4 file line general format is designed similarly to how a space-separated CSV works.
        All words are its own items, but if double quotes (`""`) or curly braces (`{}`) is used, everything inside it is grouped.
        This method converts the sie4 line to the parsed list of items.
        :param str sie4_line: a string of a line in the SIE 4 file
        :rtype: list[str]
        """
        sie4_line = sie4_line.replace('{', '"').replace('}', '"').replace('\t', ' ').strip()
        sie4_line = re.sub(r' +', ' ', sie4_line)  # filter double spaces between words
        reader = csv.reader([sie4_line], delimiter=' ')
        return next(reader)

    @api.model
    def _prepare_line_data(self, line_items):
        """
        :param list[str] line_items:
        :rtype: dict[str, str]
        """
        label = line_items[0]
        args = line_items[1:]
        match label:
            case '#ORGNR':
                return {'org_number': args[0]}
            case '#ADRESS':
                if len(args) < 4:
                    raise UserError(_(
                        'Missing element in #ADRESS line.\n'
                        'Expected format: "contact" "distribution address" "postal address" "telephone".\n'
                        'Received data: %(data)s.',
                        data=" ".join(args),
                    ))
                return {'addr_detail': args[1], 'addr_main': args[2], 'telephone': args[3]}
            case '#FNAMN':
                return {'company_name': args[0]}
            case '#RAR':
                return {'year_idx': args[0], 'date_from': args[1], 'date_to': args[2]}
            case '#KONTO':
                return {'account_code': args[0], 'account_name': args[1]}
            case '#KTYP':
                return {'account_code': args[0], 'sie4_type_code': args[1]}
            case '#IB' | '#UB':
                return {'year_idx': args[0], 'account_code': args[1], 'balance': args[2]}

    # --------------------------------------------------------------------------
    # ACTION LOGICS
    # --------------------------------------------------------------------------

    def _generate_sie4_data(self):
        """
        Generate sie4_data from the attachment.
        The sie4_data will be returned as a list of dictionaries, where each dictionary can be either:

        - {'label': <str>, 'args_map': <dict>} for normal items
        - {'label': "#VER", 'verification_str': <str>, 'verification_date': <str>, 'transactions': <list[dict]>} for #VER items.

        The dictionary fields other than the label are to be used as the parameter for its respective label methods.
        """
        sie4_bytes = base64.b64decode(self.attachment_file)
        try:
            sie4_lines = sie4_bytes.decode('UTF-8').split('\n')
        except UnicodeDecodeError:
            sie4_lines = sie4_bytes.decode('ISO-8859-1').split('\n')
        sie4_data = []
        idx = 0

        # Use `while` loop instead of `for` because some lines must be grouped together and processed as one item.
        # We need to be able to skip several lines at once by modifying the `while`'s index
        while idx < len(sie4_lines):
            line_items = self._get_sie4_line_items(sie4_lines[idx])
            label = line_items[0] if line_items else None

            # Handle related contiguous lines from the #VER special item (for generating `account.move`).
            # Verification items are always followed with a "\n{\n<lines-of-transaction>\n}\n",
            # Where every line of transaction ("#TRANS") corresponds to the `account.move.line` of the move
            if label and label == '#VER':
                transactions = []
                idx += 2  # skips `{` line and read the transaction items immediately
                # We don't need the object list for transactions, to keep the same order,
                # we delete this part which can have more than one element
                inner_line_items = self._get_sie4_line_items(re.sub(r'\{.*}', ' "" ', sie4_lines[idx]))

                while sie4_lines[idx].strip() != '}':
                    if inner_line_items and inner_line_items[0] == '#TRANS':  # only accept #TRANS key; ignore #RTRANS and #BTRANS if it exists
                        transactions.append({
                            'account_code': inner_line_items[1],
                            'balance': float(inner_line_items[3]),
                        })
                    idx += 1
                    inner_line_items = self._get_sie4_line_items(re.sub(r"\{.*}", ' "" ', sie4_lines[idx]))

                if transactions:
                    ver_series, ver_nb, ver_date = line_items[1:4]
                    ver_text = line_items[4] if len(line_items) > 4 else ''
                    sie4_data.append({
                        'label': label,
                        'verification_str': f"sie4_{ver_date}{ver_series}{ver_nb}",
                        'verification_date': ver_date,
                        'verification_text': ver_text,
                        'transactions': transactions,
                    })

            elif label:  # normal items (ex: "#KONTO", "#FNAMN", "#IB", etc.)
                sie4_data.append({
                    'label': label,
                    'data': self._prepare_line_data(line_items),
                })

            idx += 1

        return sie4_data

    def _read_sie4_data(self, data_map):
        """
        Reads sie4_data and process each recognized label line by line.
        Create/Update values are collected to ``data_map`` and will be created after processing the whole file.
        """
        sie4_method_map = {
            '#ORGNR': self._import_key_orgnr,
            '#ADRESS': self._import_key_adress,
            '#FNAMN': self._import_key_fnamn,
            '#RAR': self._import_key_rar,
            '#KONTO': self._import_key_konto,
            '#KTYP': self._import_key_ktyp,
            '#IB': self._import_key_ib,
            '#UB': self._import_key_ub,
        }
        sie4_data = data_map['sie4_data']

        for line_data in sie4_data:
            if line_data['label'] == '#VER':
                self._import_special_key_ver(
                    data_map=data_map,
                    verification_str=line_data['verification_str'],
                    verification_date=line_data['verification_date'],
                    verification_text=line_data['verification_text'],
                    transactions=line_data['transactions'],
                )
            elif line_data['label'] in sie4_method_map:
                import_key_method = sie4_method_map[line_data['label']]
                import_key_method(data_map, **line_data['data'])

    def _prepare_sie4_opening_balance_move(self, data_map):
        """
        This method processes all the gathered account_code-balance map in data_map.
        It then compares the difference of the opening balance found in Odoo with the file.
        If any difference is found, it will then create an opening balance move with that sum difference.
        """
        if '-1' in data_map['dates']:
            prev_date_to = data_map['dates']['-1']['date_to']
        else:
            # Fallback: one day before the IB year start
            ib_date_from = data_map['dates']['0']['date_from']
            dt = datetime.strptime(ib_date_from, "%Y-%m-%d")
            prev_date_to = (dt - timedelta(days=1)).strftime("%Y-%m-%d")

        account_codes = list(data_map['opening_balance_map'].keys())
        currency = self.company_id.currency_id

        account_sum_group = self.env['account.move.line'].with_company(self.company_id)._read_group(
            domain=[
                ('account_id.code', 'in', account_codes),
                ('date', '<=', prev_date_to),
                ('display_type', 'not in', ('line_note', 'line_section')),
            ],
            groupby=['account_id'],
            aggregates=['balance:sum'],
        )

        # If some account codes are not found in the searched group, add them manually with a 0 balance
        # to make sure all found accounts from the file's opening balance items have a counterpart to compare
        if unseen_account_codes := set(account_codes).difference(group_account.code for group_account, _account_sum in account_sum_group):
            unseen_accounts = self.env['account.account'].with_company(self.company_id).search_fetch(
                domain=[('code', 'in', tuple(unseen_account_codes))],
                field_names=['id', 'code'],
            )
            for account in unseen_accounts:
                account_sum_group.append((account, 0))

        line_ids = []
        total_diff = 0.0
        for account, account_sum in account_sum_group:
            if currency.compare_amounts(account_sum, data_map['opening_balance_map'][account.code]) != 0:
                diff_balance = data_map['opening_balance_map'][account.code] - account_sum
                total_diff += diff_balance
                line_ids.append(Command.create({
                    'date': prev_date_to,
                    'account_id': account.id,
                    'amount_currency': diff_balance,
                    'currency_id': currency.id,
                    'journal_id': data_map['journal_misc_id'],
                }))

        if not currency.is_zero(total_diff):
            off_balance_account = self.env['account.account'].with_company(self.company_id).search_fetch(
                domain=[('account_type', '=', 'equity_unaffected')],
                field_names=['id'],
            )
            line_ids.append(Command.create({
                'date': prev_date_to,
                'account_id': off_balance_account.id,
                'amount_currency': -total_diff,
                'currency_id': currency.id,
                'journal_id': data_map['journal_misc_id'],
            }))

        if line_ids:
            move_xml_id = self._make_xml_id('move', f'opening_balance_{prev_date_to.replace("-", "_")}')
            data_map['account.move'][move_xml_id] = {
                'date': prev_date_to,
                'ref': _('SIE opening balance move %(date)s', date=prev_date_to),
                'journal_id': data_map['journal_misc_id'],
                'company_id': self.company_id.id,
                'move_type': 'entry',
                'line_ids': line_ids,
            }

    def action_import_sie4(self):
        self.ensure_one()
        existing_accounts_map = {
            account['code']: account['id']
            for account in self.env['account.account'].with_company(self.company_id).search_read(fields=['id', 'code'])
        }
        journal_misc = self.env['account.journal'].search_fetch(
            domain=[*self.env['account.journal']._check_company_domain(self.company_id), ('type', '=', 'general')],
            field_names=['id'],
            limit=1,
        )
        journal_misc_id = journal_misc.id or self._make_xml_id('journal', f"sie4_misc_{self.id}")
        data_map = {
            'opening_balance_map': {},  # { <account_code(str)> : <account_opening_balance(float)> } for <#IB 0> only
            'existing_accounts_map': existing_accounts_map,
            'journal_misc_id': journal_misc_id,
            'dates': {},  # { <rar_year(str)> : {'date_from': <str>, 'date_to': <str>} }
            'sie4_data': self._generate_sie4_data(),
            'account.account': {},
            'res.company': {self.company_id.id: {}},
            'account.fiscal.year': {},
            'account.move': {},
        }

        self._read_sie4_data(data_map)
        if data_map['opening_balance_map']:
            self._prepare_sie4_opening_balance_move(data_map)

        create_keys = ('res.company', 'account.account', 'account.fiscal.year', 'account.move')
        if isinstance(journal_misc_id, str):  # No MISC journal found; create the MISC journal for the moves to create
            create_keys = ('res.company', 'account.account', 'account.journal', 'account.fiscal.year', 'account.move')
            data_map['account.journal'] = {
                journal_misc_id: {
                    'name': "SIE4 Miscellaneous",
                    'type': 'general',
                    'code': 'MISCSIE4',
                }
            }

        create_data = {key: data_map[key] for key in create_keys if data_map[key]}
        created_vals = self.env['account.chart.template']._load_data(create_data)

        # Set the sequence of the newly imported moves
        if moves := created_vals.get('account.move'):
            moves = moves.sorted(lambda m: (m.date, m.ref or '', m._origin.id))
            for move in moves:
                if not move.name or move.name == '/':
                    move._set_next_sequence()

        import_summary = self.env['account.import.summary'].create({
            'import_summary_account_ids': created_vals.get("account.account"),
            'import_summary_journal_ids': created_vals.get("account.journal"),
            'import_summary_move_ids': created_vals.get("account.move"),
        })
        return import_summary.action_open_summary_view()
