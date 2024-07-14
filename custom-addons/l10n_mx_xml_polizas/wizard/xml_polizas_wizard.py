# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import re
import textwrap
import zipfile
from collections import defaultdict, namedtuple
from datetime import date, timedelta

import stdnum.mx
from werkzeug.urls import url_encode

from odoo import _, api, fields, models, tools
from odoo.exceptions import RedirectWarning, UserError, ValidationError

# Order number is constrained by this pattern, an example is given.
ORDER_NUMBER_PATTERN = re.compile('^[A-Z]{3}[0-6][0-9][0-9]{5}(/)[0-9]{2}$')
ORDER_NUMBER_EXAMPLE = 'ABC6987654/99'

# Process number is constrained by this pattern, an example is given.
PROCESS_NUMBER_PATTERN = re.compile('^[A-Z]{2}[0-9]{12}$')
PROCESS_NUMBER_EXAMPLE = 'AB123451234512'

_logger = logging.getLogger(__name__)

class MoveExportData(defaultdict):

    Period = namedtuple('Period', ['year', 'month'])
    Key = namedtuple('Key', ['date', 'journal_name', 'name'])

    def __init__(self):
        super().__init__(lambda: defaultdict(list))

    def append(self, move_date, journal_name, move_name, move_data):
        period = self.Period('%04d' % move_date.year, '%02d' % move_date.month)
        move_key = self.Key(date.strftime(move_date, '%Y-%m-%d'), journal_name, move_name)
        self[period][move_key].append(move_data)

class XmlPolizasExportWizard(models.TransientModel):
    _name = 'l10n_mx_xml_polizas.xml_polizas_wizard'
    _description = "Wizard for the XML Polizas export of Journal Entries"

    # Report fields
    report_data = fields.Binary('Report file', readonly=True, attachment=False)
    report_filename = fields.Char(string='Filename', readonly=True)
    mimetype = fields.Char(string='Mimetype', readonly=True)

    # Extra data for the report
    export_type = fields.Selection(
        string='Export type',
        selection=[
            ('AF', 'Tax audit'),
            ('FC', 'Audit certification'),
            ('DE', 'Return of goods'),
            ('CO', 'Compensation'),
        ],
        required=True)

    order_number = fields.Char(
        string='Order Number',
        help="Attribute to express the order number assigned to the tax audit to which "
             "the Journal Entry application refers.\n"
             "Required for request types 'AF' and 'FC'")
    process_number = fields.Char(
        string='Process Number',
        help="Attribute to express the process number assigned to the request for refund "
             "or compensation to which the request for the Journal Entry refers.\n"
             "Required for request types 'DE' and 'CO'")

    # Filter status booleans
    filter_partial_month = fields.Boolean(
        compute='_compute_filter_partial_month',
        help="The filter does not only include full months")
    filter_partial_journals = fields.Boolean(
        compute='_compute_filter_partial_journals',
        help="The filter does not include all journals")
    filter_all_entries = fields.Boolean(
        compute='_compute_filter_all_entries',
        help="The filter includes unposted entries")

    # ------------------------------
    #
    # Compute functions
    #
    # ------------------------------

    @api.depends('export_type')
    def _compute_filter_all_entries(self):
        """ Detects if the current filter selects unposted entries """
        self.filter_all_entries = self._options.get('all_entries', False)

    @api.depends('export_type')
    def _compute_filter_partial_journals(self):
        """ Detects if the current filter only selects one journal """
        journals_options = self._options.get('journals', None)
        partial_journals = False
        if journals_options:
            selected_journals = [x.get('selected', False) for x in journals_options if 'code' in x]
            partial_journals = any(selected_journals) and not all(selected_journals)
        self.filter_partial_journals = partial_journals

    @api.depends('export_type')
    def _compute_filter_partial_month(self):
        """ Detects if the current filter selects months partially """
        partial_month = False
        date_options = self._options.get('date', {})
        if date_options.get('mode', '') == 'range':
            start = fields.Date.to_date(date_options['date_from'])
            end = fields.Date.to_date(date_options['date_to'])
            if start.day != 1 or (end + timedelta(1)).day != 1 or end > date.today():
                partial_month = True
        self.filter_partial_month = partial_month

    # ------------------------------
    #
    # Properties
    #
    # ------------------------------

    @property
    def _options(self):
        """ Get the options from the context """
        return self._context.get('l10n_mx_xml_polizas_generation_options', {})

    # ------------------------------
    #
    # Onchange
    #
    # ------------------------------

    @api.onchange('export_type')
    def _onchange_export_type(self):
        """ Blanks out unrequired fields depending on the export_type """
        for record in self:
            if record.export_type in ['AF', 'FC']:
                record.process_number = False
            elif record.export_type in ['DE', 'CO']:
                record.order_number = False

    # ------------------------------
    #
    # Constraints
    #
    # ------------------------------

    @api.constrains('order_number')
    def _check_order_number(self):
        """ Checks that the order number follows the ORDER_NUMBER_PATTERN """
        for record in self:
            if not record.order_number:
                if self.export_type in ('AF', 'FC'):
                    selection = dict(self._fields['export_type']._description_selection(self.env))
                    raise ValidationError(_("Order number is required for Export Type %r or %r",
                                            selection['AF'], selection['FC']))
            elif not re.match(ORDER_NUMBER_PATTERN, record.order_number):
                raise ValidationError(_("Order number (%s) is invalid, must be like: %s",
                                        record.order_number, ORDER_NUMBER_EXAMPLE))

    @api.constrains('process_number')
    def _check_process_number(self):
        """ Checks that the process number follows the PROCESS_NUMBER_PATTERN """
        for record in self:
            if not record.process_number:
                if self.export_type in ('CO', 'DE'):
                    selection = dict(self._fields['export_type']._description_selection(self.env))
                    raise ValidationError(_("Process number is required for Export Type %r or %r",
                                            selection['CO'], selection['DE']))
            elif not re.match(PROCESS_NUMBER_PATTERN, record.process_number):
                raise ValidationError(_("Process number (%s) is invalid, must be like: %s",
                                        record.process_number, PROCESS_NUMBER_EXAMPLE))

    # ------------------------------
    #
    # Data retrieval
    #
    # ------------------------------

    def _do_query(self, ledger, options):
        """ Execute the query
        """
        tables, where_clause, where_params = ledger._query_get(options, domain=False, date_scope='strict_range')
        ct_query = self.env['account.report']._get_query_currency_table(options)
        query = f'''
            SELECT
                account_move_line.id,
                account_move_line.name,
                account_move_line.date,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                company.currency_id           AS company_currency_id,
                account.code                  AS account_code,
                account.name                  AS account_name,
                journal.name                  AS journal_name,
                currency.name                 AS currency_name,
                move.id                       AS move_id,
                move.name                     AS move_name,
                move.l10n_mx_edi_cfdi_uuid    AS l10n_mx_edi_cfdi_uuid,
                partner.vat                   AS partner_vat,
                country.code                  AS country_code
            FROM {tables}
            LEFT JOIN account_move move          ON move.id = account_move_line.move_id
            LEFT JOIN {ct_query}                 ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company        ON company.id = account_move_line.company_id
            LEFT JOIN account_account account    ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal    ON journal.id = account_move_line.journal_id
            LEFT JOIN res_currency currency      ON currency.id = account_move_line.currency_id
            LEFT JOIN res_partner partner        ON account_move_line.partner_id = partner.id
            LEFT JOIN res_country country        ON partner.country_id = country.id
            WHERE {where_clause}
            ORDER BY account_move_line.date, account_move_line.id
        '''
        self.env['account.move.line'].flush_model()
        self.env.cr.execute(query, where_params)

        result = self._cr.dictfetchall()

        # accunt_name and journal_name will be translatable in case l10n_multilang is installed (and the cursor will then return a dict instead of string)
        if self.env['account.journal']._fields['name'].translate:
            result = [
                {
                    **res,
                    'journal_name': res['journal_name'].get(self.env.user.lang, res['journal_name']['en_US']),
                    'account_name': res['account_name'].get(self.env.user.lang, res['account_name']['en_US']),
                } for res in result
            ]

        return result

    def _get_move_export_data(self, accounts_results):
        """ Parse db results in a structure feasible for xml report
        """
        move_conversion_rate = {}
        move_data = MoveExportData()

        for line in accounts_results:
            data = {
                'line_label': textwrap.shorten(
                    line['journal_name'] + ((' - ' + line['name']) if line['name'] else ''),
                    width=200),
                'account_name': line['account_name'],
                'account_code': line['account_code'],
                'credit': '%.2f' % line['credit'],
                'debit': '%.2f' % line['debit'],
            }
            if line.get('l10n_mx_edi_cfdi_uuid'):
                foreign_currency = line['currency_id'] and line['currency_id'] != line['company_currency_id']
                amount_total = line['amount_currency'] if foreign_currency else line['balance']
                if line['country_code'] != 'MX':
                    partner_rfc = 'XEXX010101000'
                elif line['partner_vat']:
                    partner_rfc = line['partner_vat'].strip()
                elif line['country_code'] in (False, 'MX'):
                    partner_rfc = 'XAXX010101000'
                else:
                    partner_rfc = 'XEXX010101000'

                currency_name = False
                currency_conversion_rate = False
                if foreign_currency:
                    # calculate conversion rate just once per move so we don't see
                    # rounding differences between lines
                    currency_name = line['currency_name']
                    currency_conversion_rate = move_conversion_rate.get(line['move_id'])
                    if not currency_conversion_rate:
                        amount_total_signed = line['balance']
                        if amount_total:
                            currency_conversion_rate = abs(amount_total_signed) / abs(amount_total)
                        else:
                            currency_conversion_rate = 1.0
                        currency_conversion_rate = '%.*f' % (5, currency_conversion_rate)
                        move_conversion_rate[line['move_id']] = currency_conversion_rate

                data.update({
                    'uuid': line['l10n_mx_edi_cfdi_uuid'],
                    'partner_rfc': partner_rfc,
                    'currency_name': currency_name,
                    'currency_conversion_rate': currency_conversion_rate,
                    'amount_total': '%.2f' % amount_total,
                })
            move_data.append(line['date'], line['journal_name'], line['move_name'], data)
        return move_data

    def _get_moves_data(self):
        """ Retrieve the moves data to be rendered with the template """

        # Retrieve the data from the ledger itself, unfolding every group
        ledger = self.env.ref('account_reports.general_ledger_report')

        # Options ---------------------------------
        # Ensure that the date range is enforced
        options = self._options.copy()

        # If the filter is on a date range, exclude initial balances
        if options.get('date', {}).get('mode', '') == 'range':
            options['general_ledger_strict_range'] = True

        # Unfold all lines from the ledger
        options['unfold_all'] = True

        # We don't need all companies
        options['companies'] = [{'name': self.env.company.name, 'id': self.env.company.id}]

        # Retrieve --------------------------------
        accounts_results = self._do_query(ledger, options)

        # Group data for (year, month / move)
        move_data = self._get_move_export_data(accounts_results)

        # Sort the lines by name, to have a consistent order
        for period, moves in move_data.items():
            for move_key, lines in moves.items():
                move_data[period][move_key] = sorted(lines, key=lambda x: x['line_label'])

        return move_data

    def _get_xml_data(self):
        """ Gather the XML Polizas information and render the template.
            This function is also called by tests. """
        records = []
        for period, moves in self._get_moves_data().items():
            # Render the template
            xml_content = self.env['ir.qweb']._render('l10n_mx_xml_polizas.xml_polizas', values={
                'period': period,
                'moves': moves,
                'export_type': self.export_type,
                'vat': self.env.company.vat,
                'order_number': self.order_number,
                'process_number': self.process_number,
            })

            # Validate against the XSD
            with tools.file_open('l10n_mx_xml_polizas/data/xsd/1.3/PolizasPeriodo_1_3.xsd', 'rb') as xsd:
                tools.xml_utils._check_with_xsd(xml_content, xsd)

            records.append({
                'year': period.year,
                'month': period.month,
                'filename': '%s%s%sPL.XML' % (self.env.company.vat, period.year, period.month),
                'content': xml_content
            })

        return records

    # ------------------------------
    #
    # Export
    #
    # ------------------------------

    def export_xml(self):
        """ Export the XML Polizas export for SAT, after some internal consistency check """

        # Check VAT
        vat = self.env.company.vat
        if not vat:
            action = self.env.ref('base.action_res_company_form')
            raise RedirectWarning(_('Please define the VAT on your company.'),
                                    action.id, _('Company Settings'))
        elif not stdnum.mx.rfc.is_valid(vat):
            raise UserError(_("The company's VAT is invalid for Mexico."))

        # Retrieve the records
        xml_records = self._get_xml_data()

        # If there's no record, there's an error
        if len(xml_records) == 0:
            raise UserError(_('No records could be exported with current selection.'))

        # If only one month was selected, return the XML
        elif len(xml_records) == 1:
            record = xml_records[0]
            self.write({
                'report_data': base64.b64encode(record['content'].encode()),
                'report_filename': record['filename'],
                'mimetype': 'application/xml',
            })

        # If there's more than one month, return a zipfile
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for record in xml_records:
                    zip_file.writestr(record['filename'], record['content'])
            self.write({
                'report_data': base64.b64encode(zip_buffer.getvalue()),
                'report_filename': '%sPL.zip' % vat,
                'mimetype': 'application/zip',
            })

        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/?' + url_encode({
                        'model': self._name,
                        'id': self.id,
                        'filename_field': 'report_filename',
                        'field': 'report_data',
                        'download': 'true'
                    }),
            'target': 'new'
        }
