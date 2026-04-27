import base64
import logging
from collections import defaultdict

from lxml import etree

from odoo import Command, _, api, fields, models
from odoo.addons.l10n_se_sie_import.xml_utils import validate_xmldsig_signature
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import date_utils, file_open, mimetypes, float_is_zero, Query, SQL
from odoo.tools.safe_eval import datetime

_logger = logging.getLogger(__name__)

MOVE_TYPE_DATA = (
    {
        'main_tree': 'sie:CustomerInvoices',
        'element': 'sie:CustomerInvoice',
        'id': 'customerId',
        'partner_type': 'customer',
    }, {
        'main_tree': 'sie:SupplierInvoices',
        'element': 'sie:SupplierInvoice',
        'id': 'supplierId',
        'partner_type': 'supplier',
    }, {
        'main_tree': 'sie:FixedAssets',
        'element': 'sie:FixedAsset',
    }, {
        'main_tree': 'sie:GeneralSubdividedAccount',
        'element': 'sie:GeneralObject',
    },
)


def _get_next_journal_code(previous_code):
    """ Helper to generate new journal codes """
    next_code_id = int(previous_code.replace('SIE', '0')) + 1
    return f'SIE{next_code_id}'


def _get_cleaned_namespace(sie):
    """ Helper that returns the cleaned version of tha namespace. As-is, sie.nsmap cannot be used as there is
    a None key that raises an error (lxml is XPATH 1.0 only)
    """
    nsmap = dict(sie.nsmap)
    nsmap['sie'] = nsmap[None]
    del nsmap[None]
    return nsmap


def _get_partner_id(partners_map, name, vatno=None):
    return partners_map["vat"].get(vatno) if vatno else partners_map["name"].get(name)


def _get_partner_data_from_id(partners_map, partner_id):
    return partners_map["id"].get(partner_id)


class SIEExportWizard(models.TransientModel):
    """ SIE import wizard is the main class to import SIE files. """

    _name = "l10n_se.sie.import.wizard"
    _description = "Accounting SIE import wizard"

    attachment_id = fields.Binary(string="SIE File", required=True)
    # Importing referenced documents is a security death-wish
    include_embedded_documents = fields.Boolean(help='Should document files embedded in the SIE file be imported as well (if any), and linked to related entries?')

    ###############################
    #       PRIVATE METHODS       #
    ###############################

    @api.model
    def _check_company_data(self, sie_tree):
        """ Extract company data and check current company accordingly

        :param etree._Element sie_tree: main file element
        """
        nsmap = _get_cleaned_namespace(sie_tree)
        file_info = sie_tree.find('sie:FileInfo', namespaces=nsmap)
        file_info_company_id = file_info.find('sie:Company', namespaces=nsmap).get('organizationId')

        file_info_currency = file_info.find('sie:AccountingCurrency', namespaces=nsmap)
        company = self.env.company
        if file_info_currency is not None:  # lxml future requirements, avoids a FutureWarning
            currency_name = file_info_currency.get('currency').upper()
        else:
            currency = company.currency_id
            currency_name = currency.name

        if not company.company_registry:
            raise UserError(_("The company's Company ID must be set with the company's organisation ID (10/12 digits in XXXXXXXXXXxx-YYYYY format"))
        if company.company_registry != file_info_company_id:
            raise UserError(_("Company ID '%(company_id)s' does not match the file organisation ID '%(organisation_id)s'", company_id=company.company_registry, organisation_id=file_info_company_id))
        if company.currency_id.name != currency_name:
            raise UserError(_("Company currency '%(company_currency)s' doesn't match the file's main currency '%(main_currency)s'", company_currency=company.currency_id.name, main_currency=currency_name))

    @api.model
    def _verify_file_integrity(self, sie, is_entry=False):
        """ Verify if the file is compliant to the SIE 5 xsd schema. If the module xmlsig is installed, it also checks the signature of the file

        :param lxml._Element sie: sie lxml tree
        :param bool is_entry: SIE Entry files don't need to be signed, regular SIE do
        :raise ValidationError: If the file isn't compliant (nor signed if xmlsig is available)
        """
        with file_open('l10n_se_sie_import/data/sie5.xsd') as xsd:
            # Note that the "invoiceNumber" nodes in the schema had the "use='required'" attribute removed from the
            # sourcefile, because no such attributes are documented anywhere
            # (and it breaks the validation of even the test files)
            schema = etree.XMLSchema(file=xsd)

        if not schema.validate(sie):
            raise UserError(_("The file doesn't conform with xsd schema"))
        if not is_entry:
            signature = sie.find('{http://www.w3.org/2000/09/xmldsig#}Signature')
            with file_open('l10n_se_sie_import/data/xmldsig-core-schema.xsd') as xsd:
                schema = etree.XMLSchema(file=xsd)
            if not validate_xmldsig_signature(signature, schema):
                raise UserError(_('File signature is invalid, the file may have been modified'))

    @api.model
    def _get_file_main_year(self, sie):
        nsmap = _get_cleaned_namespace(sie)
        file_info_years = sie.find('sie:FileInfo/sie:FiscalYears', namespaces=nsmap)
        if file_info_years is not None:  # lxml future requirements, avoids a FutureWarning
            main_year = file_info_years.findall('sie:FiscalYear', namespaces=nsmap)
            if len(main_year) > 1:
                main_year = file_info_years.xpath("./sie:FiscalYear[@primary='true']", namespaces=nsmap)
            # We only have the month and the year 'yyyy-mm', so we'll start at the beginning of the month
            main_year_start = f"{main_year[0].get('start')}-01"
        else:
            main_year_start = None
        return main_year_start

    @api.model
    def _get_sie_default_journal(self):
        company_id = self.env.company.id
        default_journal = self.env['account.journal'].search([('company_id', '=', company_id), ('code', '=', 'SIE')])
        if not default_journal:
            default_journal = self.env['account.journal'].create({
                'name': _('SIE import default journal'),
                'type': 'general',
                'code': 'SIE',
                'company_id': company_id,
            })
        return default_journal

    def _get_partners_map(self, sie_tree, existing_partners_map=None):
        """
        Helper construct to find a partner in the database searching through vat number, then name
        Structure for partners_map is as followed:

        .. code-block:: python

            {
                "id": {
                    101: {
                        "name": "xx",
                        "vat": "00",
                        "active": True,
                        "file_id" : {"customer": "5555", "supplier": "5574"},
                    },
                    ...
                },
                "file_id": {
                    "customer": {"5555": 101, ...},
                    "supplier": {"5574": 101, ...}},
                ...
            }
        """
        nsmap = _get_cleaned_namespace(sie_tree)
        customers = sie_tree.find('sie:Customers', nsmap)  # Cannot or None because of lxml
        suppliers = sie_tree.find('sie:Suppliers', nsmap)  # Cannot or None because of lxml

        if not existing_partners_map:
            domain = []
            partners_map = {'id': {}, 'name': {}, 'vat': {}, "file_id": {"customer": {}, "supplier": {}}}
        else:
            existing_ids = list(existing_partners_map["id"])
            domain = [('id', 'not in', existing_ids)]
            partners_map = existing_partners_map
        self.env['res.partner'].flush_model(['name', 'vat', 'active'])
        partners_res = self.env['res.partner'].with_context(active_test=False).search_read(domain, ('id', 'name', 'vat', 'active'))
        for partner in partners_res:
            partner_id = partner.pop('id')
            partners_map['id'][partner_id] = partner
            for partner_field, field_value in partner.items():
                if partner_field == 'active':
                    continue
                if field_value:
                    partners_map[partner_field].update({field_value: partner_id})

            # lxml compliant syntax
            # pylint: disable=len-as-condition
            supplier = suppliers.xpath(f'./sie:Supplier[@name="{partner["name"]}"]', namespaces=nsmap) if suppliers is not None and len(suppliers) else None
            customer = customers.xpath(f'./sie:Customer[@name="{partner["name"]}"]', namespaces=nsmap) if customers is not None and len(customers) else None
            if supplier or customer:
                file_ids = {}
                if supplier:
                    partners_map['file_id']['supplier'].update({supplier[0].get('id'): partner_id})
                    file_ids.update({'supplier': supplier[0].get('id')})
                if customer:
                    partners_map['file_id']['customer'].update({customer[0].get('id'): partner_id})
                    file_ids.update({'customer': customer[0].get('id')})
                partners_map['id'][partner_id].update({'file_id': file_ids})
        return partners_map

    @api.model
    def _get_documents_data(self, sie_tree):
        """ Extract Embedded documents (not referenced ones) from file and prepare 'ir.attachment' data accordingly

        :param etree._Element sie_tree: main file element
        :return: list of dict data for moves to create, to update
        :rtype: tuple
        """
        doc_data = {}
        nsmap = _get_cleaned_namespace(sie_tree)
        sie_documents = sie_tree.find('sie:Documents', namespaces=nsmap)
        if not self.include_embedded_documents or len(sie_documents) == 0:
            return doc_data
        domain = [('res_model', '=', 'account.move'), ('name', '=like', 'SIE_%'), ('company_id', '=', self.env.company.id)]
        existing_documents = defaultdict(list)
        for attachment in self.env['ir.attachment'].search_read(domain, ('id', 'name')):
            existing_documents[attachment['name']].append(attachment['id'])
        for document in sie_documents.findall('sie:EmbeddedFile', namespaces=nsmap):
            content = base64.b64decode(document.text)

            # To avoid importing multiple times the same document, we check if they already exist in the database, else we create it
            doc_id = document.get('id')
            name = f"SIE_{document.get('fileName') or doc_id}"
            doc = existing_documents[name]
            if doc:
                doc_data[doc_id] = doc[0]
            else:
                doc_data[doc_id] = Command.create({
                    'name': name,
                    'type': 'binary',
                    'mimetype': mimetypes.guess_mimetype(content),
                    'raw': content,
                    'res_model': 'account.move',
                    'description': _("SIE imported file"),
                })
        return doc_data

    @api.model
    def _get_accounts_data(self, sie_tree):
        """ Extract account accounts and update coa accordingly (only the 'account.account' records)

        :param etree._Element sie_tree: main file element
        :return: Dictionary mapping the account codes to account.account.id and account types (Dict[str, Tuple[int, str]])
        :rtype: dict[str, tuple]
        """
        company_id = self.env.company.id
        nsmap = _get_cleaned_namespace(sie_tree)
        accounts = sie_tree.find('sie:Accounts', nsmap)

        accounts_map = {
            account['code']: (account['id'], account['account_type'])
            for account in self.env['account.account'].search_read([('company_ids', '=', company_id)], ('id', 'code', 'account_type'))
        }
        accounts_creation = []
        for account in accounts:
            if account.get('id') not in accounts_map:
                accounts_creation.append({
                    'name': account.get('name'),
                    'code': account.get('id'),
                    'company_ids': [Command.link(company_id)],
                })

        if accounts_creation:
            accounts = self.env['account.account'].create(accounts_creation)
            accounts_map.update({account.code: (account.id, account.account_type) for account in accounts})
        return accounts_map

    @api.model
    def _get_accounts_balances_data(self, sie_tree):
        """ Extract the account balances data

        :param etree._Element sie_tree: main file element
        :return: Dictionary containing the account balances at specific dates
        :rtype: dict[str, dict[str, int]]
        """
        nsmap = _get_cleaned_namespace(sie_tree)
        accounts = sie_tree.find('sie:Accounts', nsmap)
        balances_check = {}
        for account in accounts:
            code = account.get('id')
            balances = {
                'opening': account.xpath('sie:OpeningBalance', namespaces=nsmap) or [],
                'closing': account.xpath('sie:ClosingBalance', namespaces=nsmap) or [],
            }
            if balances['opening'] or balances['closing']:
                for balance_type, balance_values in balances.items():
                    account_data = {}
                    for balance in balance_values:
                        # The "month" attribute is a yyyy-mm date string
                        date = datetime.datetime.strptime(balance.get('month'), '%Y-%m').date()
                        date = date_utils.start_of(date, 'month') if balance_type == 'opening' else date_utils.end_of(date, 'month')
                        account_data[date] = balances_check.get(code, {}).get(balance_type, {}).get(date, 0.) + float(balance.get('amount'))
                    balances_check.setdefault(code, {})[balance_type] = account_data
        return balances_check

    @api.model
    def _get_journals_data(self, sie_tree, accounts_map, is_entry):
        """ Extract journals verification data from file if the option is selected

        :param etree._Element sie_tree: main file element
        :param book is_entry: If True, no journal will be created and the names in the file will not be formatted
        :return: dictionary mapping journal names to records, dictionary containing the journal data
        :rtype: tuple
        """
        def _extract_line_data(line, is_reversed=False):
            """
            Extract all the required data for an account.move.line from a file 'sie:LedgerEntry' element, also handles
            the fact that those lines may have been deleted/corrected so a reversed line may be created later

            :param lxml.etree._Element line: File element containing account.move.line data
            :param bool is_reversed: Do the line amounts need to be reversed
            :return: Dictionary containing required data to create an account.move.line
            :return: dict[str, any]
            """
            file_object_ref = line.find('sie:SubdividedAccountObjectReference', namespaces=nsmap)
            account_code = line.get('accountId')
            account_id, account_type = accounts_map[account_code]
            amount_sign = -1 if is_reversed else 1
            line_data = {
                "account": account_code,
                "account_id": account_id,
                "account_type": account_type,
                "text": line.get('text'),
                "balance": float(line.get('amount')) * amount_sign,
                "file_object_ref": file_object_ref,
            }

            if file_object_ref is not None:  # lxml future requirements, avoids a FutureWarning
                file_object_refs.add(f"{account_code}|{file_object_ref.get('objectId')}")
            foreign_currency = line.find('sie:ForeignCurrencyAmount', namespaces=nsmap)
            if foreign_currency is not None:  # lxml future requirements, avoids a FutureWarning
                line_data['other_currency'] = {
                    'currency': foreign_currency.get('currency'),
                    'balance': float(foreign_currency.get('amount')) * amount_sign,
                }
            return line_data

        def _extract_move_data(entry, journal_name, is_reversed=False):
            """ Extract all the required data for an account.move from a file 'sie:LedgerEntry' element, also handles
            the fact that those lines may have been deleted/corrected so a reversed line may be created later

            :param lxml.etree._Element entry: File element containing account.move.line data
            :param str journal_name: File journal element name
            :param bool is_reversed: Do the line amounts need to be reversed
            :return: Dictionary containing required data to create an account.move.line
            :rtype: dict[str, any]
            """
            file_entry_data = {
                # To identify the move, we need its ID, it's ref (text) and if the move is reversed or not
                # (as the two other element would identical for that specific case)
                'text': f"SIE {entry.get('id', '')}{'R' if is_reversed else ''} - {entry.get('text', '')}",
                'journal': journal_name,
            }
            infos = entry.find('sie:OriginalEntryInfo', namespaces=nsmap) or entry.find('sie:EntryInfo', namespaces=nsmap)
            if infos is None:
                file_entry_data['date'] = entry.get('journalDate')
            else:
                file_entry_data['date'] = infos.get('date')
                file_entry_data['by'] = infos.get('by')

            lines_data = []
            for line in entry.findall('sie:LedgerEntry', namespaces=nsmap):
                lines_data.append(_extract_line_data(line, is_reversed=is_reversed))
                # An Overstrike element specifies that this line has been canceled/deleted later, in Odoo we'll have
                # to add an is_reversed move line instead of not importing it
                if line.find('sie:Overstrike', namespaces=nsmap) is not None:  # lxml future requirements, avoids a FutureWarning
                    lines_data.append(_extract_line_data(line, is_reversed=not is_reversed))
            file_entry_data['lines'] = lines_data

            move_data = {'balance': 0, 'credit': 0, 'debit': 0}
            for line in file_entry_data['lines']:
                move_data['balance'] += line['balance']
                if line.get('other_currency'):
                    move_data.setdefault('other_currency', {'balance': 0, 'currency': None})
                    move_data['other_currency']['balance'] += line['other_currency']['balance']
                    move_data['other_currency']['currency'] = line['other_currency']['currency']
            file_entry_data['move'] = move_data

            if not is_reversed:
                for voucher_ref in entry.findall('sie:VoucherReference', namespaces=nsmap):
                    data = documents_data.get(voucher_ref.get('documentId'))
                    if data:
                        file_entry_data.setdefault('documents', []).append(data)

            return file_entry_data

        # Extract documents from file
        documents_data = self._get_documents_data(sie_tree)

        nsmap = _get_cleaned_namespace(sie_tree)

        journals_data = {}
        journals_to_create = []
        # There should always be at least one journal in the file
        sie_journals = sie_tree.findall('sie:Journal', nsmap)
        journals_to_activate = set()

        company_id = self.env.company.id
        journal_ids = self.env['account.journal'].with_context(active_test=False).search_read(
            [('company_id', '=', company_id), ('code', '=like', 'SIE%')],
            ('id', 'code', 'name', 'active')
        )
        existing_journals = {journal['code']: {'id': journal['id'], 'name': journal['name'], 'is_active': journal['active']} for journal in journal_ids}

        default_journal = self._get_sie_default_journal()
        if not default_journal.code in existing_journals:
            existing_journals['SIE'] = {'id': default_journal.id, 'name': default_journal.name, 'is_active': default_journal.active}
        journals_name_id_map = {default_journal.name: default_journal.id}
        journal_name_code_map = {journal['name']: code for code, journal in existing_journals.items()}

        # Make sure new journal codes indexes are unique and starts after pre-existing ones
        last_journal_code = f"SIE{max(int(code.replace('SIE', '0')) for code in existing_journals)}"

        for sie_journal in sie_journals:
            journal_file_id = sie_journal.get('id')
            journal_name = sie_journal.get('name')
            # Don't need to check for journal_file_id presence as it is mandatory data
            if not is_entry and journal_name:
                journal_name = _('SIE imported journal %(journal_file)s: %(journal)s', journal_file=journal_file_id, journal=journal_name)
            elif not journal_name:
                journal_name = default_journal.name

            if journal_name not in journal_name_code_map:
                last_journal_code = _get_next_journal_code(previous_code=last_journal_code)
                journal_name_code_map[journal_name] = last_journal_code

            for entry in sie_journal:
                file_object_refs = set()
                file_entry_data = _extract_move_data(entry, journal_name)
                if not file_entry_data['lines']:
                    continue

                # In the case where we have multiple partners for one move aka reconciliation move, we don't want to
                # attribute any partner as the system doesn't handle that case
                file_object_ref = file_object_refs.pop() if len(file_object_refs) == 1 else None
                journals_data.setdefault(file_object_ref, []).append(file_entry_data)

                if entry.find('sie:CorrectedBy', namespaces=nsmap) is not None:  # lxml future requirements, avoids a FutureWarning
                    # If this move is corrected by a later move in the file (or a future file), reverse it
                    journals_data[file_object_ref].append(_extract_move_data(entry, journal_name, is_reversed=True))
        if is_entry:
            if journal_name_code_map:
                missings = set(journal_name_code_map.keys()) - {journal_values['name'] for journal_values in existing_journals.values()}
                if missings:
                    # We don't want to create journals on SIE entry files, except the default one
                    raise UserError(_("The file journal(s) doesn't exist: %s", sorted(missings)))
        else:
            for name, code in journal_name_code_map.items():
                existing_journal_row = existing_journals.get(code)

                if existing_journal_row:
                    journals_name_id_map[name] = existing_journal_row['id']
                    if not existing_journal_row['is_active']:
                        journals_to_activate.add(existing_journal_row['id'])
                else:
                    journals_to_create.append({
                        'name': name,
                        'type': 'general',
                        'code': journal_name_code_map[name],
                        'company_id': company_id,
                    })

        if journals_to_create:
            created_journals = self.env['account.journal'].create(journals_to_create)
            journals_name_id_map.update({journal.name: journal.id for journal in created_journals})

        if journals_to_activate:
            self.env['account.journal'].browse(journals_to_activate).write({'active': True})
        return journals_name_id_map, journals_data

    @api.model
    def _create_missing_partners(self, sie_tree, partners_map):
        """ Extract partners data from file if the option is selected

        :param etree._Element sie_tree: main file element
        :param dict partners_map: dictionary containing mapping between file partners and record partners
        :return: mapping dictionary between partner file data and records
        :rtype: dict[str, models.Model]
        """
        partners_creation = []
        nsmap = _get_cleaned_namespace(sie_tree)

        # lxml compliant syntax
        # pylint: disable=len-as-condition
        customers = sie_tree.find('sie:Customers', nsmap)  # Cannot or [] because of lxml
        customers = customers if customers is not None and len(customers) else []
        suppliers = sie_tree.find('sie:Suppliers', nsmap)  # Cannot or [] because of lxml
        suppliers = suppliers if suppliers is not None and len(suppliers) else []

        for sie_partner in (*customers, *suppliers):
            # partner.get('country') returns a country code
            country_id = self.env.ref(f"base.{sie_partner['country']}").id if sie_partner.get('country') else None
            partner_id = _get_partner_id(partners_map, sie_partner.get('name'), sie_partner.get('vatNo'))
            if not partner_id:
                partners_creation.append({
                    'name': sie_partner.get('name'),
                    'company_registry': sie_partner.get('organizationId'),
                    'vat': sie_partner.get('vatNo'),
                    'street': sie_partner.get('address1'),
                    'street2': sie_partner.get('address2'),
                    'zip': sie_partner.get('zipcode'),
                    'city': sie_partner.get('city'),
                    'country_id': country_id,
                })
        if partners_creation:
            self.env['res.partner'].create(partners_creation)

    @api.model
    def _get_subdivided_accounts_data(self, sie_tree, move_type_data, partners_map):
        """ Extract customer/supplier invoices and other "subdivided accounts" data from file for future partner mapping

        :param etree._Element sie_tree: main file element

        :param dict[str, str] move_type_data: dictionary containing data for every kind of file moves
        :param dict[str, dict] partners_map: partner data mapping
        :return: list of dict data for moves to create, to update
        :rtype: tuple
        """
        nsmap = _get_cleaned_namespace(sie_tree)
        main_tree = sie_tree.find(move_type_data['main_tree'], namespaces=nsmap)

        file_object_partner_data = {}
        partners_to_create = set()
        partners_to_create_file_object_refs = []
        partners_to_activate = set()

        if main_tree is not None:  # lxml future requirements, avoids a FutureWarning
            primary_account = main_tree.get('primaryAccountId')
            for element in main_tree.findall(move_type_data['element'], namespaces=nsmap):
                file_object_ref = f"{primary_account}|{element.get('id', '')}"
                partner_id = None
                if 'partner_type' in move_type_data:
                    partner_name = partners_map['file_id'][move_type_data['partner_type']].get(element.get(move_type_data['id']), {})
                    if partner_name:
                        partner_id = _get_partner_id(partners_map, partner_name)
                    else:
                        partner_name = _('SIE undefined imported partner - %s', element.get(move_type_data['id']))
                        # Partner may exist from previous SIE file importation
                        partner_id = _get_partner_id(partners_map, partner_name)
                        if partner_id and not _get_partner_data_from_id(partners_map, partner_id)["active"]:
                            partners_to_activate.add(partner_id)
                        # If no partner is found then add it to the list for later creation
                        elif not partner_id and partner_name not in partners_to_create:
                            partners_to_create.add(partner_name)
                            # We need to store the file_object_ref to remap it to the records after the partner creation
                            partners_to_create_file_object_refs.append(file_object_ref)
                file_object_partner_data[file_object_ref] = partner_id
            self.env['res.partner'].browse(partners_to_activate).active = True

            # Create missing partners
            if partners_to_create:
                partner_ids = self.env['res.partner'].create([{'name': name} for name in partners_to_create])
                file_object_partner_data.update(dict(zip(partners_to_create_file_object_refs, partner_ids.ids)))
        return file_object_partner_data

    @api.model
    def _get_moves_data(self, journ_name_id_map, journals_data, accounts_map, file_object_partner_data):
        """ Extract customer invoices data from file

        :param dict journ_name_id_map: journals data mapping
        :param dict journals_data: journals data container
        :param dict accounts_map: Dictionary mapping account codes to account.account.ids
        :param dict file_object_partner_data: Dictionary mapping file element to partners
        :return: list of dict data for moves to create, to update
        :rtype: tuple
        """
        company = self.env.company
        company_currency_id = company.currency_id.id
        account_moves = []
        currencies = {
            currency['name']: currency['id']
            for currency in self.env['res.currency'].with_context(active_test=False).search_read([], ['id', 'name', 'active'])
        }
        currencies_to_activate = set()
        for file_object_ref, moves in journals_data.items():
            partner_id = file_object_partner_data.get(file_object_ref)
            for move_data in moves:
                move_currency_id = None
                lines_data = []
                for line in move_data['lines']:
                    account_id = accounts_map[line['account']][0]
                    line_currency_id = amount_currency = None
                    line_file_object_ref = line.get('file_object_ref')
                    if line.get('other_currency'):
                        move_currency_id = line_currency_id = currencies[line['other_currency']['currency']]
                        currencies_to_activate.add(line_currency_id)
                        amount_currency = line['other_currency'].get('balance')

                    lines_data.append({
                        'account_id': account_id,
                        'balance': line['balance'],
                        'currency_id': line_currency_id or company_currency_id,
                        'amount_currency': amount_currency or line['balance'],
                        # Following lines are for later use and are not mandatory to create the line
                        'date': move_data['date'],
                        'journal_id': journ_name_id_map[move_data['journal']],
                    })
                    if line_file_object_ref is not None:  # lxml future requirements, avoids a FutureWarning
                        lines_data[-1]['partner_id'] = file_object_partner_data.get(line_file_object_ref)
                account_move = {
                    'date': move_data['date'],
                    'ref': move_data['text'],
                    'journal_id': journ_name_id_map[move_data['journal']],
                    'company_id': company.id,
                    'currency_id': move_currency_id or company_currency_id,
                    'move_type': 'entry',
                    'line_ids': [Command.create(line_data) for line_data in lines_data],
                    'attachment_ids': move_data.get('documents'),
                    'partner_id': partner_id
                }
                account_moves.append(account_move)
        self.env['res.currency'].browse(currencies_to_activate).active = True
        account_moves_to_create, account_moves_to_update = [], []
        corr_moves = self.env['account.move'].search_fetch([('journal_id.code', '=like', 'SIE%')], ['ref', 'date'])
        for move in account_moves:
            corr_move = corr_moves.filtered(lambda x: x.ref == move['ref'] and x.date.isoformat() == move['date'])
            if corr_move:
                account_moves_to_update.append((move, corr_move))
            else:
                account_moves_to_create.append(move)
        return account_moves_to_create, account_moves_to_update

    @api.model
    def _update_moves(self, am_to_update):
        """ Update the account.move records according to previous computations

        :param list am_to_update: list of (account.move record, updated data dict) for every
        concerned move
        :return: set of all created and updated account.move records
        :rtype: set
        """
        moves_to_update = self.env['account.move']
        for move_data, move_id in am_to_update:
            moves_to_update |= move_id
        # Draft back all moves to update and remove all lines to recreate them properly
        moves_to_update.button_draft()
        moves_to_update.line_ids.unlink()
        for move_data, move_id in am_to_update:
            if move_data.get('attachment_ids'):
                move_data['attachment_ids'] = [Command.set(move_data['attachment_ids'])]
            # We don't want to override some data
            move_id.write({key: value for key, value in move_data.items() if key not in ('ref', 'journal_id', 'move_type')})
        return moves_to_update

    @api.model
    def _create_balance_moves(self, main_year_start, balances_check, accounts_map):
        """
        Compute and create balancing moves, amounts that aren't present in the journal entries but that are specified
        in the accounts balances. In the best case scenario these do not create any moves.

        :param str main_year_start: iso formatted start date for the file year
        :param dict balances_check: dictionary containing account balances data according to the imported file
        :param dict accounts_map: dictionary containing account code to account_id mapping data
        """

        company = self.env.company
        company_currency_id = company.currency_id.id
        default_journal = self._get_sie_default_journal()
        new_balance_moves = {}

        self.env['account.move.line'].flush_model(['account_id', 'date', 'balance', 'ref', 'parent_state', 'company_id'])
        query = Query(self.env, alias='aml', table=SQL.identifier('account_move_line'))
        query.add_join('JOIN', alias='account', table='account_account', condition=SQL('aml.account_id = account.id'))
        account_code = self.env['account.account']._field_to_sql('account', 'code', query)

        self._cr.execute(SQL("""
            SELECT %(account_code)s AS code,
                   aml.date,
                   SUM(aml.balance) AS balance,
                   aml.ref
              FROM %(from_clause)s
             WHERE aml.company_id = %(company_id)s
               AND aml.parent_state != 'cancel'
          GROUP BY %(account_code)s,
                   aml.date,
                   aml.ref
            """,
            account_code=account_code,
            from_clause=query.from_clause,
            company_id=company.id
        ))
        existing_balances = defaultdict(dict)
        for balance_row in self._cr.dictfetchall():
            existing_balances[balance_row['code']].update({(balance_row['date'], balance_row['ref']): balance_row['balance']})

        dates = set()
        for account in balances_check.values():  # All the dates containing balances must be checked
            for period in ('closing', 'opening'):
                for date in account[period]:
                    dates.add((date, period))
        dates = sorted(dates)
        for account_code in balances_check:
            running_correction = 0
            account_id = accounts_map[account_code][0]

            # Every year should have an opening and closing balance, but it may be omitted if it is 0
            # For every date, we need to know if there is a balance at that date or date prior (meaning the current date balance is 0)
            # Closing balances are "current date included", opening balances are "current date excluded",
            # for opening balances we check that we don't already have a pre-existing balance move as it would be overriden
            # and need to be taken into account
            for line_date, period in dates:
                balance_at_date = float(balances_check[account_code][period].get(line_date, 0))
                existing_sum = sum((
                    balance
                    for (date_of_balance, ref), balance in existing_balances[account_code].items()
                    if (period == 'closing' and date_of_balance <= line_date)
                       or (date_of_balance < line_date)
                       or (date_of_balance == line_date and ref == self.env._('SIE opening/closing balance move'))
                ))
                remaining = balance_at_date - existing_sum - running_correction
                if not float_is_zero(remaining, 6) and line_date.isoformat() >= main_year_start:
                    # Only the data after the starting date is to check
                    new_balance_moves.setdefault(line_date, {})[account_id] = remaining
                    running_correction = remaining
        missing_am_to_create = []
        for line_date, data in new_balance_moves.items():
            lines_data = []
            for account_id, balance in data.items():
                lines_data.append(Command.create({
                    'account_id': account_id,
                    'balance': balance,
                    'currency_id': company_currency_id,
                    'amount_currency': balance,
                    'date': line_date,
                    'journal_id': default_journal.id,
                }))
            if lines_data:
                missing_am_to_create.append({
                    'date': line_date,
                    'ref': _('SIE opening/closing balance move'),
                    'journal_id': default_journal.id,
                    'partner_id': None,
                    'company_id': company.id,
                    'currency_id': company_currency_id,
                    'move_type': 'entry',
                    'line_ids': lines_data,
                })
        if missing_am_to_create:
            self.env['account.move'].create(missing_am_to_create)

    @api.model
    def _import_sie_entry_file(self, sie_entry, is_entry=False):
        """ Import a SIE entry file or start the import of the SIE file

        :param etree._Element sie_entry: sie/sie entry file lxml tree
        :param bool is_entry: Is the file a SIE entry file or a complete SIE file (used for journal names)
        :return: Tuple with data used to finish import of a complete SIE file
        :rtype: tuple
        """

        # Validate the file company data against current company
        self._check_company_data(sie_entry)

        # Gather account.account selves and time-grouped accounts balances of current company from data
        accounts_map = self._get_accounts_data(sie_entry)

        # Gather detailed account.move data of current company from data
        journal_name_id_map, journals_data = self._get_journals_data(sie_entry, accounts_map, is_entry)

        # Update res.partner selfs from data
        partners_map = self._get_partners_map(sie_entry)
        self._create_missing_partners(sie_entry, partners_map)
        partners_map = self._get_partners_map(sie_entry, partners_map) # Update with new partners

        # Gather all account.move data of current company from data
        file_object_partner_data = {}
        for move_type_data in MOVE_TYPE_DATA:
            file_object_partner_data.update(self._get_subdivided_accounts_data(sie_entry, move_type_data, partners_map))

        am_to_create, am_to_update = self._get_moves_data(journal_name_id_map, journals_data, accounts_map, file_object_partner_data)

        # Create and update recorded account.move records
        all_moves = self.env['account.move'].create(am_to_create)
        all_moves |= self._update_moves(am_to_update)

        return accounts_map, all_moves

    @api.model
    def _import_sie_file(self, sie):
        """ Import a SIE file, or an SIE entry file. The former being a superset of the latter

        :param etree._Element sie: sie file lxml tree
        """

        if sie.tag.endswith('}Sie'):
            is_entry = False
        elif sie.tag.endswith('}SieEntry'):
            is_entry = True
        else:
            raise UserError(_('Wrong root tag found in file, should be `Sie` or `SieEntry'))

        self._verify_file_integrity(sie, is_entry)
        accounts_map, all_moves = self._import_sie_entry_file(sie, is_entry)

        if is_entry:
            return  # An entry file does not go further, as it isn't required for the accounts to be balanced

        # Create and update missing re-balancing account.move records (if any)
        balances_check = self._get_accounts_balances_data(sie)
        self._create_balance_moves(self._get_file_main_year(sie), balances_check, accounts_map)
        if all_moves:
            all_moves.action_post()

            lines_per_accounts = defaultdict(list)
            for line_id in all_moves.line_ids:
                if line_id.is_account_reconcile and line_id.move_id.ref != _('SIE opening/closing balance move'):
                    lines_per_accounts[line_id.account_id.id].append(line_id.id)

            for line_ids in lines_per_accounts.values():
                self.env['account.move.line'].browse(line_ids).reconcile()

    ###############################
    #       ACTIONS METHODS       #
    ###############################

    def action_import_sie(self):
        """ Imports the SIE and SIE entry files after some basic checks """
        for record in self:
            # Basic checks to start, we need a fiscal localization, and a proper file
            if not record.env.company.account_fiscal_country_id or not record.env.company.chart_template:
                action = record.env.ref('account.action_account_config')
                raise RedirectWarning(_('You should install a Fiscal Localization first.'), action.id, _('Accounting Settings'))

            data = base64.b64decode(record.attachment_id)
            try:
                self._import_sie_file(etree.fromstring(data))
            except etree.XMLSyntaxError:
                raise UserError(_("The file isn't a valid XML file"))
