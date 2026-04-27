import csv
import io
import zipfile

from lxml import etree

from odoo import _, api, fields, models

DOCUMENT_TYPE = 'invoice'


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    ###################################
    # CSV EXPORT
    ###################################

    def _custom_options_initializer(self, report, options, previous_options=None):
        """Adds a custom button for Turkish companies to generate e-Ledger CSV."""
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'TR':
            options['buttons'].append({
                'name': _("Generate e-Ledger"),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_tr_reports_export_general_ledger_csv',
                'file_export_type': _('ZIP'),
            })

    @api.model
    def _l10n_tr_reports_csv_columns(self):
        """Defines the header row for the e-Ledger CSV."""
        return [
            'LineNumber',
            'EnteredBy',
            'EnteredDate',
            'EntryNumberCounter',
            'EntryNumber',
            'EntryComment',
            'MainAccountID',
            'MainAccountDescription',
            'SubAccountID',
            'SubAccountDescription',
            'Amount',
            'AOAmount',
            'AOCurrency',
            'AOExchangeRate',
            'AOExchangeRateComment',
            'AOExchangeRateDate',
            'AOExchangeRateSource',
            'DebitCreditCode',
            'DocumentType',
            'DocumentTypeDescription',
            'DocumentNumber',
            'DocumentDate',
            'PaymentMethod',
            'DetailComment',
            'PostingDate',
            'DocumentReferance',
            'TaxNumber',
            'BranchNumber',
        ]

    @api.model
    def _l10n_tr_reports_format_file_name(self, date):
        """
        Format the file name based on the date range of the general ledger.
        For Example: e-ledger_1Jan2025-30Jan2025
        """

        return _(
            "e-ledger_%(from_date)s-%(to_date)s",
            from_date=fields.Date.from_string(date['date_from']).strftime('%d%b%Y'),
            to_date=fields.Date.from_string(date['date_to']).strftime('%d%b%Y'),
        )

    @api.model
    def _l10n_tr_reports_format_timestamp(self, date):
        """Convert Date to Datetime by adding 00:00:00 time"""
        return date.strftime('%-d.%m.%Y %H:%M:%S')

    @api.model
    def _get_l10n_tr_reports_company_currency_info(self, line):
        """Gets amount and debit/credit code for the line in company currency."""
        balance = line.balance
        debit_credit_indicator = 'C' if balance < 0.0 else 'D'
        return {
            'amount': str(abs(balance)).replace('.', ','),
            'credit_debit': debit_credit_indicator,
        }

    @api.model
    def _get_l10n_tr_reports_original_currency_info(self, line):
        """Gets details if the original currency differs from company currency."""
        currency_info = {
            'ao_amount': None,
            'ao_currency': None,
            'ao_exchange_rate': None,
            'ao_exchange_rate_comment': None,
            'ao_exchange_rate_date': None,
            'ao_exchange_rate_source': None,
        }

        if not line.is_same_currency:
            amount_currency = line.amount_currency
            amount = abs(amount_currency)
            currency_provider = dict(
                line.company_id._fields['currency_provider'].selection
            ).get(line.company_id.currency_provider)

            # Update Dictionary
            currency_info.update({
                'ao_amount': str(amount).replace('.', ','),
                'ao_currency': line.currency_id.name,
                'ao_exchange_rate': line.currency_rate,
                'ao_exchange_rate_comment': None,
                'ao_exchange_rate_date': line.date,
                'ao_exchange_rate_source': currency_provider,
            })

        return currency_info

    def _get_l10n_tr_reports_document_number_ref(self, line):
        """Returns ID from UBL XML if E-Invoice sent successfully to Nilvera, otherwise fallback to move name."""
        move = line.move_id
        document_vals = {'number': move.name, 'ref': move.ref or None}

        def _get_document_id(attachment):
            """ Helper to decode XML and extract <cbc:ID> """
            if not attachment:
                return None
            try:
                tree = etree.fromstring(attachment.raw)
                return tree.findtext('./{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID')
            except (etree.XMLSyntaxError, AttributeError, ValueError, TypeError):
                return None

        # Checking whether the 'l10n_tr_nilvera_einvoice' module is installed or not
        if 'l10n_tr_nilvera_send_status' not in move._fields:
            return document_vals

        if (  # Handle Sale Documents (Invoice)
            move.is_sale_document(include_receipts=True)
            and move.l10n_tr_nilvera_send_status == 'succeed'
            and (ubl_id := _get_document_id(move.ubl_cii_xml_id))
        ):
            document_vals['number'] = ubl_id
        elif (  # Handle Purchase Documents (Vendor Bill)
            move.is_purchase_document(include_receipts=True)
            and move.ref
        ):
            attachment_ids = self.env['ir.attachment'].search([
                ('id', 'in', move.attachment_ids.ids),
                ('mimetype', '=', 'application/xml'),
                ('name', '=', move.ref + '.xml'),
            ])
            for attachment in attachment_ids:
                if ubl_id := _get_document_id(attachment):
                    document_vals['number'] = ubl_id
                    document_vals['ref'] = None
                    break  # As we only need the first valid attachment

        return document_vals

    def _prepare_l10n_tr_reports_csv_row(self, line, counter):
        """Constructs a single row of data for the e-Ledger CSV export."""
        move = line.move_id
        company = line.company_id
        account = line.account_id

        currency_info = self._get_l10n_tr_reports_original_currency_info(line)
        company_currency_info = self._get_l10n_tr_reports_company_currency_info(line)
        formated_date = self._l10n_tr_reports_format_timestamp(line.date)
        document_vals = self._get_l10n_tr_reports_document_number_ref(line)

        return [
            None,  # LineNumber - handled by external system or post-process
            line.create_uid.name,
            formated_date,
            counter,  # EntryNumberCounter - Should be same across the journal items of particular move
            move.name,
            move.name,
            account.code[:3],
            account.name,
            account.code,
            account.name,
            company_currency_info['amount'],
            currency_info['ao_amount'],
            currency_info['ao_currency'],
            currency_info['ao_exchange_rate'],
            currency_info['ao_exchange_rate_comment'],
            currency_info['ao_exchange_rate_date'],
            currency_info['ao_exchange_rate_source'],
            company_currency_info['credit_debit'],
            DOCUMENT_TYPE,
            None,  # DocumentTypeDescription
            document_vals['number'],
            formated_date,
            None,  # PaymentMethod
            None,  # DetailComment
            None,  # PostingDate
            document_vals['ref'],
            company.vat or None,
            company.company_registry or None,
        ]

    def l10n_tr_reports_export_general_ledger_csv(self, options):
        """
        Export general ledger lines to a ZIP file containing a CSV,
        formatted for Turkish e-Ledger requirements.

        :param options: Report options
        :return: A dict containing the ZIP values.
        """

        def generate_csv_rows(move_lines):
            """Generate rows for the CSV file, grouped by move."""
            counter = 0
            last_move_id = None

            yield self._l10n_tr_reports_csv_columns()

            for line in move_lines:
                if line.move_id.id != last_move_id:
                    counter += 1  # Increment when move changes
                    last_move_id = line.move_id.id
                yield self._prepare_l10n_tr_reports_csv_row(line, counter)

        # Extract all account.move.line IDs from the report
        report = self.env['account.report'].browse(options['report_id'])
        move_line_ids = []
        for line_data in report._get_lines({**options, 'unfold_all': True}):
            model, record_id = report._get_model_info_from_id(line_data['id'])
            if model == 'account.move.line':
                move_line_ids.append(record_id)
        move_lines = self.env['account.move.line'].search([('id', 'in', move_line_ids)])

        zip_buffer = io.BytesIO()
        file_name = self._l10n_tr_reports_format_file_name(options['date'])
        with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            with io.TextIOWrapper(zip_file.open(f'{file_name}.csv', 'w'), 'utf-8') as w:
                csv.writer(w, delimiter=';').writerows(generate_csv_rows(move_lines))

        return {
            'file_name': f'{file_name}.zip',
            'file_content': zip_buffer.getvalue(),
            'file_type': 'zip',
        }

    ###################################
    # WARNING
    ###################################

    @api.model
    def _get_waiting_nilvera_moves(self, domain):
        """
        Retrieves account move ids with waiting Nilvera Status.

        :param domain: Report domain to filter moves.
        :return: A tuple containing warning_template and move_ids.ids.
        """
        move_ids = []
        if 'l10n_tr_nilvera_send_status' in self.env['account.move']._fields:
            move_ids = self.env['account.move.line'].search([
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.l10n_tr_nilvera_send_status', '!=', 'succeed'),
            ] + domain).move_id.ids
        return 'l10n_tr_reports.waiting_nilvera_status_warning', move_ids

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        # Get domain for filtering moves based on report options
        report_domain = report._get_options_domain(options, date_scope='strict_range')
        warning_template, waiting_move_ids = self._get_waiting_nilvera_moves(report_domain)

        # Add warning if there are waiting moves
        if waiting_move_ids:
            warnings[warning_template] = {
                'ids': waiting_move_ids,
                'alert_type': 'warning',
            }

    @api.model
    def action_view_waiting_nilvera_moves(self, options, params):
        """Opens action to display account move ids with waiting Nilvera status."""
        return {
            'type': 'ir.actions.act_window',
            'name': "Waiting Moves",
            'res_model': 'account.move',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', params['ids'])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }
