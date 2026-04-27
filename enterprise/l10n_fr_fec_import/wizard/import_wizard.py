# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import codecs
from collections import defaultdict
import csv
import datetime
import io
import logging
import copy

from odoo import _, fields, models, Command
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import float_repr, float_is_zero, SQL

_logger = logging.getLogger(__name__)


class UnbalancedMovesError(UserError):
    pass


class FecImportWizard(models.TransientModel):
    """ FEC import wizard is the main class to import FEC files.  """

    _name = "account.fec.import.wizard"
    _description = "Account FEC import wizard"

    attachment_name = fields.Char(string="Filename")
    attachment_id = fields.Binary(string="File", required=True, help="Accounting FEC data file to be imported")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", help="Company used for the import", default=lambda self: self.env.company, required=True, readonly=True)
    document_prefix = fields.Char(string="Document prefix")
    duplicate_documents_handling = fields.Selection(
        selection=[
            ('ignore', "Ignore"),
            ('update', "Update"),
        ],
        string="Duplicate documents handling",
        default='update',
    )

    # ------------------------------------
    # Reading
    # ------------------------------------

    def _get_rows(self, attachment, attachment_name):
        """ Returns the rows that are stored inside the CSV FEC attachment.

            If the file starts with a BOM_UTF8, it's considered utf-8 w/BOM.
            'utf-8' and 'iso8859_15' are the only other allowed encodings.
            Allowed delimiters are ';|,\t', as in the official FEC testing tooling.

            Record fields are stripped of spaces after being read from the file.
        """

        # Determine the encoding
        bytes_data = base64.b64decode(attachment)
        if bytes_data.startswith(codecs.BOM_UTF8):
            string_data = bytes_data.decode('utf-8-sig')
        else:
            for encoding in ['utf-8', 'iso8859_15']:
                try:
                    string_data = bytes_data.decode(encoding)
                    if string_data:
                        break
                except ValueError:
                    pass
            if not string_data:
                raise UserError(_("Cannot determine the encoding for the attached file."))

        # Find the CSV dialect
        try:
            dialect = csv.Sniffer().sniff(string_data, delimiters=";|,\t")
        except csv.Error:
            raise UserError(_("Cannot determine the file format for the attached file."))

        # Return the spaces-stripped rows
        rows = []
        try:
            incomplete_lines = []
            reader = csv.reader(io.StringIO(string_data), dialect=dialect)

            for line_no, record in enumerate(reader, 1):
                # Deal with the header
                if line_no == 1:
                    header = [x.strip() for x in record]
                    while header and not header[-1]:
                        header.pop()
                else:
                    # Read the rows, skipping the empty ones
                    # Then put it in the rows basket, or flag it if it's incomplete
                    row = [x.strip() if isinstance(x, str) else x for x in record]
                    if row:
                        if len(row) >= len(header):
                            rows.append(dict(zip(header, row)))
                        else:
                            incomplete_lines.append(line_no)

        # Print a friendly message to the user
        except csv.Error as e:
            _logger.warning("csv.Error: %s", e)
            raise UserError(_("This file could not be recognised.\n"
                              "Please check that it is encoded in utf-8 or iso8859_15"))

        # Block the processing if there are incomplete lines
        if incomplete_lines:
            raise UserError(_("Some lines do not have the same number of fields as the header.\n"
                              "Please check the following line numbers:\n"
                              "%s", incomplete_lines))

        return rows

    # ------------------------------------
    # Generators
    # -----------------------------------
    def _make_xml_id(self, prefix, key):
        if '_' in prefix:
            raise ValueError(_('`prefix` cannot contain an underscore'))

        if not key:
            raise UserError(_("%s not found", prefix))
        key = key.replace(' ', '_')
        return f"l10n_fr_fec_import.{self.company_id.id}_{prefix}_{key}"

    def _parse_xml_id(self, xml_id):
        components = xml_id.split('.', 1)[1].split('_', 2)
        components[0] = int(components[0])
        return components

    def _generator_fec_account_account(self, rows, cache):
        """ Import the accounts from the FEC file """
        data = self.env['account.chart.template']._get_chart_template_data('fr')
        template_data = data.pop('template_data')
        accounts = cache['account.account'].copy()
        new_ids = {}

        digits = template_data['code_digits']
        for record in rows:
            account_code_orig = record.get("CompteNum", "")
            account_name = record.get("CompteLib", "")
            account_code = account_code_orig[:digits] + account_code_orig[digits:].rstrip('0')
            account_code_stripped = account_code.rstrip('0')
            account_xml_id = self._make_xml_id('account', account_code)
            if account_code_stripped in accounts.keys():
                account = accounts[account_code_stripped]
                if account_code not in new_ids:
                    new_ids[account_code] = {
                        'xml_id': account_xml_id,
                        'record': account,
                        'noupdate': True,
                    }
            else:
                data = {
                    "company_ids": [Command.link(self.company_id.id)],
                    "code": account_code,
                    "name": account_name,
                    "account_type": 'asset_current',
                }
                cache['account.account'][account_code_stripped] = data
                yield account_xml_id, data
        self.env['ir.model.data']._update_xmlids(new_ids.values())


    def _shorten_code(self, value, max_len, cache, reserved_digits=2):
        """ In case that given value is too long, this function shortens it like this:

            PACMAN, max_len=5, reserved_digits = 2 -> PAC01
            if PAC01 already exists                -> PAC02
            ...

            If all PACnn exist until PAC99, False is returned.
            If a value is found, or the code isn't too long to begin with,
            then the shortened value is returned.

            If a value is found, a cache entry "mapping_<field_name>"
            is created/updated with the mapping old_value->new_value
        """

        if len(value) <= max_len:
            return value

        code_cache = cache.setdefault("mapping_journal_code", {})

        if value in code_cache:
            return code_cache[value]

        prefix = value[0:(max_len - reserved_digits)]
        for idx in range(1, 10 ** reserved_digits):
            new_value = ("%%s%%0%dd" % reserved_digits) % (prefix, idx)
            if new_value not in code_cache.values():
                code_cache[value] = new_value
                return new_value

        return False

    def _generator_fec_account_journal(self, rows, cache):
        """ Import the journals from fec data files """
        journals = {journal.code: journal for journal in self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.company_id),
        ])}
        new_ids = {}
        for record in rows:
            journal_code = record.get("JournalCode")
            journal_name = record.get("JournalLib")
            journal_xml_id = self._make_xml_id('journal', journal_code)
            if journal_code in journals.keys():
                journal = journals[journal_code]
                if journal_code not in new_ids:
                    new_ids[journal_code] = {
                        'xml_id': journal_xml_id,
                        'record': journal,
                        'noupdate': True,
                    }
            else:
                data = {
                    "company_id": self.company_id.id,
                    "code": self._shorten_code(journal_code, 5, cache),
                    "name": "FEC-%s" % (journal_name or journal_code),
                    "type": "general"
                }
                yield journal_xml_id, data

        self.env['ir.model.data']._update_xmlids(new_ids.values())

    def _generator_fec_res_partner(self, rows, cache):
        """ Import the partners from FEC data files """
        template_data = self.env['account.chart.template']._get_chart_template_data('fr').get('template_data')
        partners_set = set()
        for record in rows:
            partner_ref = record.get("CompAuxNum", "")
            partner_name = record.get("CompAuxLib", "")
            account_code = record.get("CompteNum", "")
            if partner_ref:
                partner_ref = partner_ref.replace(' ', '_')
                # Check for an existing partner with the same name or ref
                partner_key = partner_ref or partner_name
                if not partner_key or partner_key in partners_set:
                    continue
                partners_set.add(partner_key)

                # Check if the partner is already existing
                existing_partner = cache["res.partner.ref"].get(partner_ref, None)
                if existing_partner:
                    partner_xml_id = self._make_xml_id('partner', partner_ref)
                    self.env['ir.model.data']._update_xmlids([{'xml_id': partner_xml_id, 'record': existing_partner}])
                    continue

                data = {
                    "company_id": self.company_id.id,
                    "name": partner_name or partner_ref,
                    "ref": partner_ref,
                }

                # Setup account properties
                if account_code:
                    digits = template_data['code_digits']
                    account_code = account_code[:digits] + account_code[digits:].rstrip('0')
                    account = cache['account.account'].get(account_code.rstrip('0'))
                    account_xml_id = self._make_xml_id('account', account_code)
                    if account['account_type'] == 'asset_receivable':
                        data["property_account_receivable_id"] = account_xml_id
                    elif account['account_type'] == 'liability_payable':
                        data["property_account_payable_id"] = account_xml_id

                yield self._make_xml_id('partner', partner_ref), data

    def _check_rounding_issues(self, moves_dict, balance_dict):
        """ If journals are unbalanced, check if they can be balanced by adding some counterpart line
            when a rounding issue is found. """

        # Get the accounts for the debit and credit differences
        debit_account, credit_account = (
            self.env["account.account"].with_company(self.company_id).search([
                *self.env['account.account']._check_company_domain(self.company_id),
                ('code', '=like', code),
            ], order='code', limit=1)
            for code in ('658%', '7580%')
        )

        # Check the moves for rounding issues
        currency = self.company_id.currency_id
        imbalanced_journals = set()
        for key, move in moves_dict.items():
            balance_data = balance_dict[key]
            balance, matching = balance_data["balance"], balance_data["matching"]

            # If it's tolerable, create a counterpart line
            if 0 < abs(balance) <= currency.rounding:
                data = {
                    "name": _("Import rounding difference"),
                    "account_id": debit_account.id if balance > 0 else credit_account.id,
                    "credit": 0.0 if balance > 0 else abs(balance),
                    "debit": balance if balance > 0 else 0.0,
                    "matching_number": matching and f"I{matching}" or False,
                }
                move["line_ids"].append(fields.Command.create(data))

            # If it's not tolerable, mark the journal and the date as incorrect
            elif abs(balance) > currency.rounding:
                imbalanced_journals.add(move["journal_id"])

        return imbalanced_journals

    def _try_balance_moves(self, key_function, currency, journal_id, lines_grouped_by_date):
        """ Try to balance moves by grouping them by date.
            The key_function is applied on the date to group lines toghether.
            Throws UnbalancedMovesError if the grouping cannot produce zero-balanced moves,
            Returns {date_key: list_of_lines}"""

        # Compute the balance, using the key_function to group the lines
        groups = {}
        for lines_date, lines in lines_grouped_by_date.items():
            key = key_function(lines_date)
            balance = sum([line["debit"] - line["credit"] for line in lines])
            old_balance, old_lines = groups.get(key, (0.0, []))
            groups[key] = [old_balance + balance, old_lines + lines]

        # Check if there's any group with a non-zero balance
        rebalanced_moves = {}
        for key, (balance, lines) in groups.items():

            # If there is a non-zero balance, rebalanced_moves is invalid
            # Exit the function indicating failure.
            if not float_is_zero(balance, precision_rounding=currency.rounding):
                raise UnbalancedMovesError("Cannot group moves")

            # Build the keys with the same format that was used in moves_dict
            _cid, _prefix, journal_code = self._parse_xml_id(journal_id)
            if len(key) == 2:
                move_key = "%s/%04d%02d" % (journal_code, *key)
                move_date = datetime.date(*key, 1)
            else:
                move_key = "%s/%04d%02d%02d" % (journal_code, *key)
                move_date = datetime.date(*key)

            # Store the valid move in a dictionary
            rebalanced_moves[move_key] = {
                "company_id": self.company_id.id,
                "name": move_key,
                "date": move_date,
                "journal_id": journal_id,
                "line_ids": [fields.Command.create(line) for line in lines]
            }

        return rebalanced_moves

    def _check_imbalanced_journals(self, cache, moves_dict, balance_dict, imbalanced_journals, imbalances):
        """ If there are still imbalanced moves, try to re-group the lines by journal/date
            for the imbalanced journals, to see if now they balance altogether. """
        currency = self.company_id.currency_id

        # If there still are imbalanced journals, clear the moves_dict
        # of all the moves with the imbalanced journal_id and put them aside
        imbalanced_moves = []
        for move_key in list(moves_dict.keys()):
            if moves_dict[move_key]["journal_id"] in imbalanced_journals:
                imbalanced_moves.append((move_key, moves_dict.pop(move_key)))

        # For each journal, try to group it with different key functions
        # until you find one that produces groups of lines which are zero-balanced
        for journal_id in imbalanced_journals:
            lines_grouped_by_date = imbalances[journal_id]
            for _grouping, key_function in [
                ("day", lambda x: (x.year, x.month, x.day)),
                ("month", lambda x: (x.year, x.month))
            ]:
                # If a grouping that makes all moves have a zero-balance has been found,
                # we save the moves and stop looking for other ways of grouping them.
                try:
                    rebalanced_moves = self._try_balance_moves(
                        key_function, currency, journal_id, lines_grouped_by_date)
                    moves_dict.update(rebalanced_moves)
                    break
                except UnbalancedMovesError:
                    pass

            # If no grouping (day/month) can make all moves be balanced,
            # then alert the user that the file cannot be understood
            else:
                balance_issues = ""
                for key, move in imbalanced_moves:
                    balance = balance_dict[key]["balance"]
                    if not float_is_zero(balance, precision_rounding=currency.rounding):
                        balance_issues += _("Move with name '%(name)s' has a balance of %(balance)s\n",
                                            name=move["name"], balance=float_repr(balance, currency.decimal_places))
                raise UserError(_("Moves report incorrect balances:\n%s", balance_issues))

    def _normalize_float_value(self, record, key):
        """ Normalize a float string value inside a dictionary """
        return float((record.get(key, "") or "0.0").replace(",", "."))

    def _get_credit_debit_balance(self, record, currency):
        """ The credit/debit may be specified as Montant/Sens
            Sens must be in ['C', 'D'] which mean Credit/Debit) """

        if "Montant" in record and "Sens" in record:
            sens = record.get("Sens", "").upper()
            montant = self._normalize_float_value(record, "Montant")
            credit = montant if sens == "C" else 0.0
            debit = montant if sens == "D" else 0.0
        else:
            credit = self._normalize_float_value(record, "Credit")
            debit = self._normalize_float_value(record, "Debit")

        credit = currency.round(credit)
        debit = currency.round(debit)

        # Negative values must be inverted
        if credit < 0 or debit < 0:
            debit, credit = -credit, -debit

        balance = currency.round(debit - credit)

        return credit, debit, balance

    def _generator_fec_account_move(self, rows, cache):
        """ Import the moves from the FEC files.
            The first loop collects informations, then in a second loop, move_line level information is assembled and the data can be yielded.

            If partner information is found on a line, it has to be brought from move_line level to move level.

            The credit/debit may be specified as Montant/Sens.
            Sens must be in ['C', 'D'] which mean Credit/Debit).
        """

        template_data = self.env['account.chart.template']._get_chart_template_data('fr').get('template_data')
        moves_dict = {}

        # Keeps track of moves grouped by journal_id and move_date, it helps with imbalances
        imbalances = defaultdict(lambda: defaultdict(list))

        # Keeps the move's balance after summing each line's debit and credit
        balance_dict = {}

        for idx, record in enumerate(rows):

            # Move data -----------------------------------------

            # The move_name sometimes may be not provided, use the piece_ref instead
            piece_ref = record.get("PieceRef", "")
            ecriture_num = record.get("EcritureNum", "")
            move_name = ecriture_num or piece_ref
            if not move_name:
                raise UserError(_("Line %s has an invalid move name", idx))

            if self.document_prefix:
                move_name = self.document_prefix.strip() + ' ' + move_name

            # The move_date sometimes is not provided, use the piece_date instead
            piece_date = record.get("PieceDate", "")
            piece_date = piece_date and datetime.datetime.strptime(piece_date, "%Y%m%d")
            move_date = record.get("EcritureDate", "")
            move_date = (move_date and datetime.datetime.strptime(move_date, "%Y%m%d")) or piece_date
            partner_ref = record.get("CompAuxNum", "")
            journal_code = record.get("JournalCode", "")

            # Move line data ------------------------------------
            digits = template_data['code_digits']
            move_line_name = record.get("EcritureLib", "")
            account_code_orig = record.get("CompteNum", "")
            account_code = account_code_orig[:digits] + account_code_orig[digits:].rstrip('0')

            currency_name = record.get("Idevise", "")
            amount_currency = self._normalize_float_value(record, "Montantdevise")
            matching = record.get("EcritureLet", "")

            # Move import --------------------------------------

            # Use the journal and the move_name as key for the move in the moves_dict
            move_key = self._make_xml_id('move', f"{journal_code}_{move_name}")

            # Many move_lines may belong to the same move, the move info gets saved in the moves_dict
            data = moves_dict.setdefault(move_key, {
                "company_id": self.company_id.id,
                "name": move_name,
                "date": move_date,
                "ref": piece_ref,
                "journal_id": self._make_xml_id('journal', journal_code),
                "line_ids": [],
            })
            balance_data = balance_dict.setdefault(move_key, {"balance": 0.0, "matching": False})

            # Move line import ----------------------------------

            # Build the basic data
            line_data = {
                "company_id": self.company_id.id,
                "name": move_line_name,
                "ref": piece_ref,
                "account_id": self._make_xml_id('account', account_code),
                "matching_number": matching and f"I{matching}" or False,
                "tax_ids": [],  # Avoid default taxes on the accounts to be set
            }

            # Save the matching number for eventual balance issues
            balance_data["matching"] = balance_data["matching"] or matching or False

            # Partner. As we are creating Journal Entries and not invoices/vendor bills,
            # the partner information will stay just on the line.
            # It may be updated in the post-processing after all the imports are done.
            if partner_ref:
                line_data["partner_id"] = self._make_xml_id('partner', partner_ref)

            if currency_name in cache["res.currency"] and amount_currency:
                line_data.update({
                    "currency_id": cache["res.currency"][currency_name].id,
                    "amount_currency": amount_currency,
                })

            # Round the values, save the total balance to detect issues
            credit, debit, balance = self._get_credit_debit_balance(record, self.company_id.currency_id)
            line_data["credit"] = credit
            line_data["debit"] = debit
            balance_data["balance"] = self.company_id.currency_id.round(balance_data["balance"] + balance)

            # Montantdevise can be positive while the line is credited:
            # => amount_currency and balance (debit - credit) should always have the same sign
            if currency_name in cache["res.currency"] and amount_currency and line_data['amount_currency'] * balance < 0:
                line_data["amount_currency"] *= -1

            # Append the move_line data to the move
            data["line_ids"].append(fields.Command.create(line_data))

            # Update the data in the moves_dict
            imbalances[data['journal_id']][move_date].append(line_data)

        # Check for imbalanced journals, fix rounding issues
        imbalanced_journals = self._check_rounding_issues(moves_dict, balance_dict)

        # If there are still imbalanced, journals, try to re-group the lines by journal/date,
        # to see if now they balance altogether
        if imbalanced_journals:
            self._check_imbalanced_journals(cache, moves_dict, balance_dict, imbalanced_journals, imbalances)

        yield from moves_dict.items()

    # -----------------------------------
    # Templates
    # -----------------------------------

    def _gather_templates(self):
        """ Find all the templates for the considered entities.
            These templates will be used to fill out missing information coming from the records.
            For accounts, account_type and reconcile flags are used.  """
        account_data = self.env['account.chart.template']._get_account_account('fr')
        all_templates = {"account.account": {x['code']: x for x in account_data.values()}}
        return all_templates

    def _apply_template(self, templates, model, record):
        """ Given a template, apply its fields to the record, overwriting existing ones.
            As for accounts, it matches the significant digits (right zeros are stripped) of the code with those of the template's code.
        """
        if model == "account.account":
            for limit in [999, 3, 2]:
                def normalize_code(x):
                    return x[:limit].rstrip('0')
                template = next((v for k, v in templates.items() if normalize_code(k) == normalize_code(record['code'])), {})
                if template:
                    for key, value in template.items():
                        if key not in ['id', 'code', 'name']:
                            record[key] = value
                    break

    # ------------------------------------
    # Utility functions
    # ------------------------------------

    def _get_journal_type(self, journals, ratio, min_moves):
        """
            Determine the type of journal given the current situation with moves and accounts.

            'bank'      Moves in these journals will always have a line (debit or credit) impacting a liquidity account.
                        ('cash' / 'bank' can be interchanged, so 'bank' is set everywhere when this condition is met)
            'sale'      Moves in these journals will mostly have debit lines on receivable accounts and credit lines on tax income accounts.
                        Sale refund journal items will be debit/credit inverted.
            'purchase'  Moves in these journals will mostly have credit lines on payable accounts and debit lines on expense accounts.
                        Purchase refund journal items will be debit/credit inverted.
            'general'   For everything else.

            A minimum of 3 moves is necessary for journal_type identification.
            A threshold of 70% of moves must correspond to a criteria for a journal_type to be determined.

            Example:
                Journal id=5
                Moves: total=4
                    has a sale account line and no purchase account line=0     ratio=0
                    has a purchase account line and no sale account line=1     ratio=0.25
                    has a liquidity account line                        =3     ratio=0.75

            The journal type is "bank", because the bank moves ratio 3/4 (0.75) exceeds the threshold (0.7)

        """

        # Ensure data consistency
        self.env.flush_all()

        # Query the database to determine the journal type
        # The sum_move_lines_per_move query determines the type of the account of the lines
        # The sum_moves_per_journal query counts the account types on the lines for each move
        # The main query compares the sums with the threshold and determines the type
        aj_name = self.env['account.journal']._field_to_sql('aj', 'name')
        sql = SQL("""
            WITH sum_move_lines_per_move as (
                SELECT aml.journal_id as journal_id,
                       %(aj_name)s as journal_name,
                       aml.move_id,
                       SUM(CASE WHEN aa.account_type IN ('asset_cash','liability_credit_card') THEN 1 ELSE 0 END) as bank,
                       SUM(CASE aa.account_type WHEN 'asset_receivable' THEN 1 ELSE 0 END) as sale,
                       SUM(CASE aa.account_type WHEN 'liability_payable' THEN 1 ELSE 0 END) as purchase
                  FROM account_move_line aml
                       JOIN account_account aa on aa.id = aml.account_id
                       JOIN account_journal aj on aj.id = aml.journal_id
                 WHERE aj.id in %(journals_ids)s
              GROUP BY journal_id, journal_name, move_id),

            sum_moves_per_journal as (
                SELECT journal_id,
                       journal_name,
                       SUM(CASE WHEN bank > 0 THEN 1 ELSE 0 END) as bank_sum,
                       SUM(CASE WHEN sale > 0 THEN 1 ELSE 0 END) as sale_sum,
                       SUM(CASE WHEN purchase > 0 THEN 1 ELSE 0 END) as purchase_sum,
                       COUNT(*) as moves,
                       CAST(COUNT(*) * %(ratio)s as integer) as threshold
                  FROM sum_move_lines_per_move
              GROUP BY journal_id, journal_name)

            SELECT journal_id,
                   CASE WHEN moves < %(min_moves)s THEN 'general'
                        WHEN bank_sum >= threshold THEN 'bank'
                        WHEN sale_sum >= threshold and purchase_sum = 0 THEN 'sale'
                        WHEN purchase_sum >= threshold and sale_sum = 0 THEN 'purchase'
                        ELSE 'general'
                    END as journal_type
              FROM sum_moves_per_journal
          ORDER BY journal_id
        """, aj_name=aj_name, journals_ids=tuple(journals.ids), ratio=ratio, min_moves=min_moves)

        # Yield the records
        self.env.cr.execute(sql)
        yield from self.env.cr.fetchall()

    def _setup_bank_journal(self, journal):
        """ The bank journal needs a default liquidity account and outstanding payments accounts to be set """

        # Determine the most used liquidity account on the journal and set it as default on the Bank Journal
        sql = """
            SELECT aa.id,
                   COUNT(*) as frequency
              FROM account_move_line aml
                   JOIN account_account aa on aa.id = aml.account_id
                   JOIN account_journal aj on aj.id = aml.journal_id
              WHERE aj.id = %s
                    and (aa.account_type = 'asset_cash' OR aa.account_type = 'liability_credit_card')
           GROUP BY aa.id
           ORDER BY frequency DESC
        """
        self.env.cr.execute(sql, (journal.id, ))
        record = self.env.cr.fetchone()
        if record:
            journal.default_account_id = record[0]

        # Set default suspense account on the Bank Journal
        journal.suspense_account_id = self.company_id.account_journal_suspense_account_id

    def _build_import_cache(self):
        """ Build a cache with all the data needed by the generators, so that the query is done just one time """

        # Retrieve all the data from the database
        accounts = self.env["account.account"].search(self.env['account.account']._check_company_domain(self.company_id))
        journals = self.env["account.journal"].search(self.env['account.journal']._check_company_domain(self.company_id))
        partners = self.env["res.partner"].search_fetch(domain=self.env['res.partner']._check_company_domain(self.company_id), field_names=['name', 'ref'])
        currencies = self.env["res.currency"].search([])

        # Build the cache dictionary
        return {
            "account.account": {x["code"].rstrip('0'): x for x in accounts},
            "account.journal": {x["code"]: x for x in journals},
            "res.currency": {x["name"]: x for x in currencies},
            "res.partner": {x["name"]: x for x in partners},
            "res.partner.ref": {x["ref"]: x for x in partners},
        }

    def _update_import_cache(self, cache, model, records):
        """ Update the cache with all the records created the generators.
            Each model can have a different key, and the update handles it."""

        get_key = {
            "account.account": lambda x: x.code.rstrip('0'),
            "account.journal": lambda x: x.code,
            "res.currency": lambda x: x.name,
            "res.partner": lambda x: x.name
        }.get(model, None)
        if get_key:
            cache[model].update({get_key(x): x for x in records})

        if model == "res.partner":
            cache["res.partner.ref"].update({x["ref"]: x for x in records})

    # -----------------------------------
    # Main methods
    # -----------------------------------

    def action_import(self):
        """ Action called by the Import button """
        return self._import_files()

    def _import_files(self, models=None):
        """ Start the import by gathering generators and templates and applying them to attached files. """

        # Basic checks to start
        if not self.company_id.account_fiscal_country_id or not self.company_id.chart_template:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(_('You should install a Fiscal Localization first.'), action.id, _('Accounting Settings'))

        # Models list can be injected for testing purposes
        if not models:
            models = ["account.account", "account.journal", "res.partner", "account.move"]

        # In Odoo, move names follow sequences based on the year, so the checks complain
        # if the year present in the move's name doesn't match with the move's date.
        # This is unimportant here since we are importing existing moves from external data.
        # The workaround is to set the sequence.mixin.constraint_start_date parameter
        # to the date of the oldest move (defaulting to today if there is no move at all).
        if "account.move" in models:
            domain = [("company_id", "=", self.company_id.id)]
            start_date = self.env["account.move"].search(domain, limit=1, order="date asc").date or fields.Date.today()
            start_date_str = start_date.strftime("%Y-%m-%d")
            self.env["ir.config_parameter"].sudo().set_param("sequence.mixin.constraint_start_date", start_date_str)

        # Build a cache with all the cache needed by the generators, so that the query is done just one time
        cache = self._build_import_cache()

        data = defaultdict(dict)
        all_templates = self._gather_templates()
        rows = self._get_rows(self.attachment_id, self.attachment_name)

        # For each file provided, cycle over each model
        for model in models:

            _logger.info("%s FEC import started", model)

            # Retrieve the templates
            model_templates = all_templates.get(model, {})

            # Generate the records for the model
            records = defaultdict(dict)
            generator_name = "_generator_fec_%s" % model.replace(".", "_")
            generator = getattr(self, generator_name)

            # Loop over generated records and apply a template if a matching one is found
            for xml_id, record in generator(rows, cache):
                self._apply_template(model_templates, model, record)
                records[xml_id].update(record)

            data[model] = dict(records)

        AccountChartTemplate = self.env['account.chart.template']
        created_vals = self.env['account.chart.template']._load_data(copy.deepcopy(data), ignore_duplicates=self.duplicate_documents_handling == 'ignore')
        AccountChartTemplate._load_translations(companies=self.company_id, template_data=data)

        moves = created_vals.get("account.move", [])
        for move in moves:
            move.partner_id = move.line_ids.partner_id[:1]

        journals = created_vals.get("account.journal", [])
        if journals:
            for journal_id, journal_type in self._get_journal_type(journals, ratio=0.7, min_moves=3):
                journal = self.env['account.journal'].browse(journal_id).with_context(account_journal_skip_alias_sync=True)
                # The bank journal needs a default liquidity account and outstanding payments accounts to be set
                if journal_type == 'bank':
                    self._setup_bank_journal(journal)
                journal.type = journal_type

        import_summary = self.env['account.import.summary'].create({
            'import_summary_account_ids': created_vals.get("account.account"),
            'import_summary_journal_ids': created_vals.get("account.journal"),
            'import_summary_move_ids': created_vals.get("account.move"),
            'import_summary_partner_ids': created_vals.get("res.partner"),
            'import_summary_tax_ids': created_vals.get("account.tax"),
        })
        return import_summary.action_open_summary_view()
