# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
import odoo.release
from odoo.tools.float_utils import float_split_str

from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
import unicodedata


SPANISH_PROVINCES_REPORT_CODES = {
        'VI': '01',
        'AB': '02',
        'A': '03',
        'AL': '04',
        'AV': '05',
        'BA': '06',
        'PM': '07',
        'B': '08',
        'BU': '09',
        'CC': '10',
        'CA': '11',
        'CS': '12',
        'CR': '13',
        'CO': '14',
        'C': '15',
        'CU': '16',
        'GI': '17',
        'GR': '18',
        'GU': '19',
        'SS': '20',
        'H': '21',
        'HU': '22',
        'J': '23',
        'LE': '24',
        'L': '25',
        'LO': '26',
        'LU': '27',
        'M': '28',
        'MA': '29',
        'MU': '30',
        'NA': '31',
        'OR': '32',
        'O': '33',
        'P': '34',
        'GC': '35',
        'PO': '36',
        'SA': '37',
        'TF': '38',
        'S': '39',
        'SG': '40',
        'SE': '41',
        'SO': '42',
        'T': '43',
        'TE': '44',
        'TO': '45',
        'V': '46',
        'VA': '47',
        'BI': '48',
        'ZA': '49',
        'Z': '50',
        'CE': '51',
        'ME': '52',
}

MOD_347_CUSTOM_ENGINES_DOMAINS = {
    '_report_custom_engine_threshold_insurance_bought': [
        ('move_id.l10n_es_reports_mod347_invoice_type', '=', 'insurance'),
        ('move_id.move_type', 'in', ('in_invoice', 'in_refund', 'in_receipt')),
        ('account_type', '=', 'liability_payable'),
    ],

    '_report_custom_engine_threshold_regular_bought': [
        ('move_id.l10n_es_reports_mod347_invoice_type', '=', 'regular'),
        ('move_id.move_type', 'in', ('in_invoice', 'in_refund', 'in_receipt')),
        ('account_type', '=', 'liability_payable'),
    ],

    '_report_custom_engine_threshold_regular_sold': [
        ('move_id.l10n_es_reports_mod347_invoice_type', '=', 'regular'),
        ('move_id.move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt')),
        ('account_type', '=', 'asset_receivable'),
    ],

    '_report_custom_engine_threshold_all_operations': [
        ('move_id.l10n_es_reports_mod347_invoice_type', '!=', None),
        ('account_type', 'in', ('asset_receivable', 'liability_payable'))
    ],
}


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_expression_audit_aml_domain(self, expression, options):
        # Overridden to allow auditing mod347's threshold lines (for consistency: this way all the lines of the report are audited in the same way)
        if expression.engine == 'custom' and expression.formula in MOD_347_CUSTOM_ENGINES_DOMAINS:
            return MOD_347_CUSTOM_ENGINES_DOMAINS[expression.formula]
        else:
            return super()._get_expression_audit_aml_domain(expression, options)


class SpanishTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler'

    def _append_boe_button(self, options, boe_number):
        options['buttons'].append(
            {
                'name': _('BOE'),
                'sequence': 0,
                'action': 'open_boe_wizard',
                'action_param': boe_number,
                'file_export_type': _('BOE'),
            })

    def open_boe_wizard(self, options, boe_number):
        """ Triggers the generation of the BOE file for the current mod report.
        In case this BOE file needs some more data to be entered manually by
        the user, it show instead a wizard prompting for them, which will, once
        validated and closed, trigger the generation of the BOE itself.
        """
        period, _year = self._get_mod_period_and_year(options)
        if boe_number == 390:
            # period will be falsy if a whole year is selected
            if period and not options.get('_running_export_test'):
                raise UserError(_("Wrong report dates for BOE generation : please select a range of a year."))
        elif boe_number != 347 and not period:
            raise UserError(_("Wrong report dates for BOE generation : please select a range of one month or a trimester."))

        return {
            'name': _('Print BOE'),
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': f'l10n_es_reports.aeat.boe.mod{boe_number}.export.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                **self.env.context,
                'l10n_es_reports_report_options': options,
                'default_report_id': options['sections_source_id'],
            },
        }

    def _get_mod_period_and_year(self, options):
        """ Returns the period and year (in terms of AEAT modulo reports regulation)
        corresponding to the report options given in parameters, in the form
        of a tuple (period, year). Period will be None if the dates do not fit
        any.

        A UserError will be raised if the start and end date of given in the
        options do not corresond to the first and last day of their respective
        month, or belong to two different years.
        """
        date_from = datetime.strptime(options['date']['date_from'], "%Y-%m-%d")
        date_to = datetime.strptime(options['date']['date_to'], "%Y-%m-%d")

        if not date_from.year == date_to.year:
            raise UserError(_("Cannot generate a BOE file for two different years"))

        if date_from.day != 1 or date_to.day != (date_to + relativedelta(day=31)).day:
            raise UserError(_("Your date range does not cover entire months, please use a start and end date matching respectively the first and last day of a month."))

        rslt_period = None
        rslt_year = str(date_from.year) # Identical to date_to.year thanks to the previous conditions
        if date_from.month == date_to.month:
            rslt_period = '%02d' % (date_from.month)
        elif date_from.month == date_to.month - 2 and self._retrieve_period_and_year(date_from, trimester=True)[0] == self._retrieve_period_and_year(date_to, trimester=True)[0]:
            rslt_period = '%01dT' % (date_to.month / 3)
        # Period stays None otherwize, so we can use rslt_period == None to check if a trimester or year is selected

        return rslt_period, rslt_year

    def _retrieve_period_and_year(self, date, trimester=False):
        """ Retrieves the period and year (in the form of a tuple) corresponding
        to a given date.

        :param trimester: whether or not we use trimesters as periods.
        """
        if trimester:
            return '%01dT' % (1 + ((date.month - 1) // 3)), str(date.year)
        else:
            return '%02d' % date.month, str(date.year)

    def _convert_period_to_dates(self, period, year):
        """ Converts a period and a year to a tuple of two dates, respectively its
        start and end date.
        """
        if period[-1] == 'T':
            quarter = int(period[:-1])
            return datetime(day=1, month= 1 + (quarter - 1) * 3, year=int(year)), (datetime(day=1, month= quarter * 3, year=int(year)) + relativedelta(day=31)) # relativedelta used to force last day of the month without triggering ValueError for months with less than 31 days
        else:
            return datetime(day=1, month=int(period), year=int(year)), datetime(day=1, month=int(period), year=int(year)) + relativedelta(day=31)

    def _l10n_es_boe_format_string(self, string, length=-1, align='left', fill_char=b' '):
        """ Formats a string so that it is BOE-compatible.

        :param string: the string to format
        :param length: the desired length of the resulting string, or -1 if there is not
        :param align: 'left' or 'right', depending on the side of the result string where string must placed (no effect if no length is given)
        :param fill_char: the character that will be used to bring the result string to a size of length (no effect if length is not specified)
        """
        string = string.upper()

        rslt = b''
        for char in unicodedata.normalize('NFKC', string): # We use a normalized version of the string here so that we are sure accentuated charcaters are each time encoded with only one character (and not a regular character followed by a combining one)
            if not char in ('Ñ', 'Ç'):
                normalized_char = unicodedata.normalize('NFD', char) # Not NFKD, as the NFKC normalization in the loop already ensures good treatment of compatibility characters. NFD splits accentuated characters in two parts: the original character, and the accent to combine it with
                rslt += normalized_char.encode('ISO-8859-1', 'ignore') # Combinable accentuation characters are not supported by this encoding, and disappear when transcoding.
            else:
                rslt += char.encode('ISO-8859-1')

        if length > -1:
            rslt = rslt[:length]
            if align == 'left':
                rslt = rslt.ljust(length, fill_char)
            elif align =='right':
                rslt = rslt.rjust(length, fill_char)

        return rslt

    def _l10n_es_boe_format_number(self, options, number, length=-1, decimal_places=0, signed=False, sign_neg='N', sign_pos='', in_currency=False):
        """ Formats a number to a BOE-compatible string.

        :param number: the number to format
        :param length: the desired length for the resulting string, or -1, to just use the number of characters of the number.
        :param decimal_places: the number of decimal places to use (these characters are part of the length limit)
        :param signed: whether or not the number must be signed in the resulting string
        :param sign_neg: the character to use as the first character of the resulting string if signed is True and
                         the number was negative (the resulting string will contain no additional - sign)
        :param sign_pos: same as sign_neg, but if number is positive
        :param in_currency: True iff number is expressed in company currency (and thus needs to be converted in €)
        """
        company = self.env.company

        if in_currency:
            # If number is an amount expressed in company currency, we ensure that it
            # is written in € in BOE file
            conversion_date = options['date']['date_to']
            curr_eur = self.env["res.currency"].search([('name', '=', 'EUR')], limit=1)
            number = company.currency_id._convert(number, curr_eur, company, conversion_date)

        if isinstance(number, float):
            split_number = float_split_str(abs(number), decimal_places)
            str_number = split_number[0] + split_number[1]
        else:
            str_number = str(abs(number)) + '0' * decimal_places

        negative_amount = in_currency and company.currency_id.compare_amounts(number, 0.0)==-1 or number<0
        sign_str = signed and (negative_amount and sign_neg or sign_pos) or ''

        # Done in two parts, so that sign str is always in front of the filling characters
        return self._l10n_es_boe_format_string(sign_str) + self._l10n_es_boe_format_string(str_number, length=length - len(sign_str), align='right', fill_char=b'0')

    def _retrieve_casilla_lines(self, report_lines):
        """ Retrieves the values of the casillas contained in report_lines, using
        the fact that these lines' names are prefixed by their number between [] to
        identify them. Returns a dictionnary, with casillas as keys and their values
        as values.
        """
        casilla_pattern = re.compile(r'\[(?P<casilla>.*)\]')
        rslt = {}
        for line in report_lines:
            matcher = casilla_pattern.match(line['name'])
            if matcher:
                casilla = matcher.group('casilla')
                casilla_value = line['columns'][0]['no_format'] # Element [0] is the current period, in case we are comparing

                rslt[casilla] = casilla_value

        return rslt

    def _retrieve_report_expression(self, options, xmlid):
        """ Retrieves the data of the report line denoted by xmlid, with respect
        to the given options.
        """
        expression = self.env.ref(xmlid)
        expression_totals = self.env['account.report'].browse(options['report_id'])._compute_expression_totals_for_each_column_group(expression._expand_aggregations(), options)
        # This considers we have but one column group
        return next(expr_total[expression]['value'] for expr_total in expression_totals.values())

    def _get_bic_and_iban(self, res_partner_bank):
        """ Convenience method returning (bic,iban) of the given account if
        this account exists, or a tuple of empty strings otherwise.
        """
        if res_partner_bank:
            return res_partner_bank.bank_bic or "", res_partner_bank.sanitized_acc_number

        return '', ''

    def _retrieve_boe_manual_wizard(self, options, modelo_number):
        """ Retrieves a BOE manual wizard object from its id, contained within the
        options dict.
        """
        return self.env[f'l10n_es_reports.aeat.boe.mod{modelo_number}.export.wizard'].browse(options['l10n_es_reports_boe_wizard_id'])

    def _call_on_partner_sublines(self, report_options, line_xml_id, fun_to_call, required_ids_set=None):
        """ Calls a function on the data of all the sublines generated by a
        groupby parameter for a report line (except the one giving the total).

        :param report_options: the options to use to generate line data
        :param line_xml_id: the xml id of the report line whose children we want to call our function on
        :param fun_to_call: the function to call on sublines. It must take only one argument, the data dictionary of the subline.
        :param required_ids_set: a set containing ids on which we want fun_to_call to be called.
                                 This is used to generate data for models that are not present
                                 in the grouped line displayed on the report. (this can for example
                                 happen if they have no operation in this year; but
                                 some data to be added into BOE make in necessary to still include
                                 them in the file). This set will be modified by the function.
        """
        if required_ids_set is None:
            required_ids_set = set()
        rslt = self._l10n_es_boe_format_string('')
        report = self.env['account.report'].browse(report_options['report_id'])
        report_line = self.env.ref(line_xml_id)
        line_dict_id = report._get_generic_line_id('account.report.line', report_line.id)
        for subline in report._report_expand_unfoldable_line_with_groupby(line_dict_id, report_line.groupby, report_options, None, 0)['lines']:
            subline_model, subline_model_id = report._get_model_info_from_id(subline['id'])

            if subline_model == 'res.partner':
                rslt += fun_to_call({'line_data': subline, 'line_xml_id': line_xml_id, 'report_options': report_options})
                if subline_model_id in required_ids_set:
                    required_ids_set.remove(subline_model_id)

        for element in required_ids_set: # These elements are the ones for wich no line was generated, but that were into the original required ids set. So, we still treat them.
            rslt += fun_to_call({
                'line_data': {'id': report._get_generic_line_id('res.partner', element)},
                'line_xml_id': line_xml_id,
                'report_options': report_options
            })

        return rslt

    def _get_partner_subline(self, report_options, line_xml_id, partner_id):
        """ Returns the data of a subline generated by a groupby parameter, if its
        'id' (i.e. the actual id of the model denoted by groupby represented by the
        line) is equal to a given value.

        :param report_options: the options to use to generate data
        :param line_xml_id: the xml id of the parent line
        :param sub_line_id: the id of the "grouped by" model corresponding to the subline we want to retrieve
        """
        report = self.env['account.report'].browse(report_options['report_id'])
        report_line = self.env.ref(line_xml_id)
        line_dict_id = report._get_generic_line_id('account.report.line', report_line.id)
        for subline in report._report_expand_unfoldable_line_with_groupby(line_dict_id, report_line.groupby, report_options, None, 0)['lines']:
            subline_model, model_id = report._get_model_info_from_id(subline['id'])
            if subline_model == 'res.partner' and model_id == partner_id:
                return subline

    def _extract_tin(self, partner, error_if_no_tin=True):
        if not partner.vat:
            if error_if_no_tin:
                raise UserError(_("No TIN set for partner %s (id %d). Please define one.", partner.name, partner.id))
            else:
                return ''

        country_code, number = partner._split_vat(partner.vat)
        return country_code.upper() + number

    def _extract_spanish_tin(self, partner, except_if_foreign=False):
        formatted_tin = self._extract_tin(partner, error_if_no_tin=True)
        if formatted_tin[:2] != 'ES':
            if except_if_foreign:
                raise UserError(_("Reading a non-Spanish TIN as a Spanish TIN."))
            else:
                return ''
        return formatted_tin[2:]

    def _generate_111_115_common_header(self, options, period, year, modelo_number):
        rslt = b''

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, modelo_number)

        # Header
        current_company = self.env.company
        rslt += self._l10n_es_boe_format_string(f"<T{modelo_number}0{year}{period}0000>")
        rslt += self._l10n_es_boe_format_string('<AUX>')
        rslt += self._l10n_es_boe_format_string(' ' * 70) # Reserved for AEAT
        odoo_version = odoo.release.version.split('.')
        rslt += self._l10n_es_boe_format_string(str(odoo_version[0]) + str(odoo_version[1]), length=4)
        rslt += self._l10n_es_boe_format_string(' ' * 4) # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(' ' * 213) # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string('</AUX>')

        # Fills in the common fields between mod 111 and 115
        rslt += self._l10n_es_boe_format_string(f"<T{modelo_number}01000>")
        rslt += self._l10n_es_boe_format_string(' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.declaration_type)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(current_company.name, length=60)
        rslt += self._l10n_es_boe_format_string(' ' * 20) # We keep the name of the declaring party blank here, as it is a company
        rslt += self._l10n_es_boe_format_string(year)
        rslt += self._l10n_es_boe_format_string(period)

        return rslt


class SpanishMod111TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod111.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod111)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 111)

    def export_boe(self, options):
        period, year = self._get_mod_period_and_year(options)

        rslt = self._generate_111_115_common_header(options, period, year, 111)
        report = self.env['account.report'].browse(options['report_id'])
        report_lines = report._get_lines(options)
        casilla_lines_map = self._retrieve_casilla_lines(report_lines)

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 111)

        # Content of the report
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['01'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['02'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['03'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['04'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['05'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['06'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['07'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['08'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['09'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['10'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['11'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['12'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['13'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['14'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['15'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['16'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['17'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['18'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['19'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['20'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['21'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['22'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['23'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['24'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['25'], length=8, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['26'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['27'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['28'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['29'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['30'], length=17, decimal_places=2, signed=True, in_currency=True)

        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and boe_wizard.previous_report_number or '', length=13)
        rslt += self._l10n_es_boe_format_string(' ') # Reserved for AEAT
        dummy, iban = self._get_bic_and_iban(boe_wizard.partner_bank_id)
        rslt += self._l10n_es_boe_format_string(iban, length=34)
        rslt += self._l10n_es_boe_format_string(' ' * 389) # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 13) # Reserved for AEAT

        # We close the tags... (They have been opened by _generate_111_115_common_header)
        rslt += self._l10n_es_boe_format_string('</T11101000>')
        rslt += self._l10n_es_boe_format_string('</T1110' + year + period + '0000>')

        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': rslt,
            'file_type': 'txt',
        }


class SpanishMod115TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod115.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod115)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 115)

    def export_boe(self, options):
        period, year = self._get_mod_period_and_year(options)

        rslt = self._generate_111_115_common_header(options, period, year, 115)
        report = self.env['account.report'].browse(options['report_id'])
        report_lines = report._get_lines(options)
        casilla_lines_map = self._retrieve_casilla_lines(report_lines)

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 115)

        # Content of the report
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['01'], length=15, signed=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['02'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['03'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['04'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['05'], length=17, decimal_places=2, signed=True, in_currency=True)

        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and boe_wizard.previous_report_number or '', length=13)
        dummy, iban = self._get_bic_and_iban(boe_wizard.partner_bank_id)
        rslt += self._l10n_es_boe_format_string(iban, length=34)
        rslt += self._l10n_es_boe_format_string(' ' * 236) # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 13) # Reserved for AEAT

        # We close the tags... (They have been opened by _generate_111_115_common_header)
        rslt += self._l10n_es_boe_format_string('</T11501000>')
        rslt += self._l10n_es_boe_format_string('</T1150' + year + period + '0000>')

        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': rslt,
            'file_type': 'txt',
        }


class SpanishMod303TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod303.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod303)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 303)

    def export_boe(self, options):
        period, year = self._get_mod_period_and_year(options)

        report = self.env['account.report'].browse(options['report_id'])
        report_lines = report._get_lines(options)
        casilla_lines_map = self._retrieve_casilla_lines(report_lines)
        current_company = self.env.company

        # Header
        rslt = self._l10n_es_boe_format_string('<T3030' + year + period + '0000>')
        rslt += self._l10n_es_boe_format_string('<AUX>')
        rslt += self._l10n_es_boe_format_string(' ' * 70)
        odoo_version = odoo.release.version.split('.')
        rslt += self._l10n_es_boe_format_string(str(odoo_version[0]) + str(odoo_version[1]), length=4)
        rslt += self._l10n_es_boe_format_string(' ' * 4)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(' ' * 213)
        rslt += self._l10n_es_boe_format_string('</AUX>')

        rslt += self._generate_page1(report, options, current_company, period, year, casilla_lines_map)
        rslt += self._generate_page3(report, options, current_company, period, year, casilla_lines_map)
        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._generate_page_did(report, options, current_company, period, year, casilla_lines_map)
        # We don't need page 2 and 4 (specified in AEAT doc)

        # We close the tags...
        rslt += self._l10n_es_boe_format_string('</T3030' + year + period + '0000>')

        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': rslt,
            'file_type': 'txt',
        }

    def _generate_page1(self, report, options, current_company, period, year, casilla_lines_map):
        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 303)

        rslt = self._l10n_es_boe_format_string('<T30301000>')
        rslt += self._l10n_es_boe_format_string(' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.declaration_type)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(current_company.name, length=80)
        rslt += self._l10n_es_boe_format_string(year)
        rslt += self._l10n_es_boe_format_string(period)

        # Identification
        rslt += self._l10n_es_boe_format_number(options, 2) # Tributación exclusivamente foral => Always "no", for simplicity
        rslt += self._l10n_es_boe_format_number(options, boe_wizard.monthly_return and 1 or 2)
        rslt += self._l10n_es_boe_format_number(options, 3)
        rslt += self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_string(' ' * 8)
        rslt += self._l10n_es_boe_format_string(' ')
        rslt += self._l10n_es_boe_format_number(options, boe_wizard._get_using_sii_2021_value())

        exonerated_from_mod_390 = boe_wizard._get_exonerated_from_mod_390_2021_value(period)
        rslt += self._l10n_es_boe_format_number(options, exonerated_from_mod_390)

        if exonerated_from_mod_390 == 1:
            profit_and_loss_report = self.env.ref('l10n_es_reports.financial_report_es_profit_and_loss')
            end_date = fields.Date.from_string(options['date']['date_to'])
            transactions_volume_options = profit_and_loss_report.get_options({
                'date': {
                    'date_from': '%s-01-01' % end_date.year,
                    'date_to': '%s-12-31' % end_date.year,
                    'filter': 'custom',
                    'mode': 'range',
                },
            })

            transactions_volume = self._retrieve_report_expression(transactions_volume_options, 'l10n_es_reports.es_profit_and_loss_line_1_balance')
            annual_volume_indicator = current_company.currency_id.is_zero(transactions_volume) and 2 or 1
        else:
            annual_volume_indicator = 0

        rslt += self._l10n_es_boe_format_number(options, annual_volume_indicator)

        # Casillas
        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('150', 0), length=17, decimal_places=2, in_currency=True)
            rslt += self._l10n_es_boe_format_number(options, 0, length=5)  # Casilla 151 is constant
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('152', 0), length=17, decimal_places=2, in_currency=True)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['01'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 400, length=5) # Casilla 02 is constant
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['03'], length=17, decimal_places=2, in_currency=True)

        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('153', 0), length=17, decimal_places=2, in_currency=True)
            rslt += self._l10n_es_boe_format_number(options, 500, length=5)  # Casilla 154 is constant
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('155', 0), length=17, decimal_places=2, in_currency=True)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['04'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 1000, length=5) # Casilla 05 is constant
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['06'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['07'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 2100, length=5) # Casilla 08 is constant
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['09'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['10'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['11'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['12'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['13'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['14'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['15'], length=17, decimal_places=2, signed=True, in_currency=True)

        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('156', 0), length=17, decimal_places=2, in_currency=True)
            rslt += self._l10n_es_boe_format_number(options, 175, length=5)  # Casilla 157 is constant
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('158', 0), length=17, decimal_places=2, in_currency=True)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['16'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 50, length=5) # Casilla 17 is constant (any of 00000, 00050, 00062)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['18'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['19'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 140, length=5) # Casilla 20 is constant
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['21'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['22'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 520, length=5) # Casilla 23 is constant
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['24'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['25'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['26'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['27'], length=17, decimal_places=2, signed=True, in_currency=True)

        for casilla in range(28, 40):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)

        for casilla in range(40, 47):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, signed=True, in_currency=True)

        # Footer of page 1
        rslt += self._l10n_es_boe_format_string(' ' * 600) # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 13) # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string('</T30301000>')

        return rslt

    def _generate_page3(self, report, options, current_company, period, year, casilla_lines_map):
        rslt = self._l10n_es_boe_format_string('<T30303000>')

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 303)

        # Casillas
        to_treat = ['59', '60']

        for casilla in to_treat:
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[casilla], length=17, decimal_places=2, signed=True, in_currency=True)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['120'], length=17, decimal_places=2, signed=True, in_currency=True)

        if options['date']['date_from'] < '2022-01-01':
            rslt += self._l10n_es_boe_format_number(options, 0, length=17)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['122'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['123'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['124'], length=17, decimal_places=2, signed=True, in_currency=True)

        # Next casillas
        for casilla in (62, 63, 74, 75):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, 0, length=17)  # Normally casilla 76 (Regularization of quotas art. 80.Cinco.5ª LIVA)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['46'], length=17, decimal_places=2, signed=True, in_currency=True) # Should normally be casilla 64 (= sum of casillas 46, 58 and 76), but only casilla 46 is in our version of the report
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['65'], length=5, decimal_places=2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['66'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['77'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('110', 0), length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('78', 0), length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('87', 0), length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['68'], length=17, decimal_places=2, signed=True, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['69'], length=17, decimal_places=2, signed=True, in_currency=True)

        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['70'], length=17, decimal_places=2, in_currency=True)  # Unsigned from 2023 on
        else:
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['70'], length=17, decimal_places=2, signed=True, in_currency=True)

        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map.get('109', 0.0), length=17, decimal_places=2, in_currency=True)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['71'], length=17, decimal_places=2, signed=True, in_currency=True)

        # Information about declaration
        if options['date']['date_from'] >= '2023-01-01':
            rslt += self._l10n_es_boe_format_string(casilla_lines_map['71'] == 0 and 'X' or ' ')
            rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
            rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and boe_wizard.previous_report_number or '', length=13)
        else:
            rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
            rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and boe_wizard.previous_report_number or '', length=13)
            rslt += self._l10n_es_boe_format_string(casilla_lines_map['71'] == 0 and 'X' or ' ')

        if options['date']['date_from'] < '2023-01-01':
            gov_giving_back = current_company.currency_id.compare_amounts(casilla_lines_map['71'], 0) == -1
            partner_bank = boe_wizard.partner_bank_id

            bic, iban = self._get_bic_and_iban(partner_bank)

            rslt += self._l10n_es_boe_format_string(bic if gov_giving_back and iban and iban[:2] != 'ES' else '', length=11)
            rslt += self._l10n_es_boe_format_string(iban, length=34)

            # Reserved by AEAT
            rslt += self._l10n_es_boe_format_string(' ' * 17)

            # Devolución
            if gov_giving_back:
                bank = partner_bank.bank_id
                rslt += self._l10n_es_boe_format_string(bank.name or '', length=70)
                rslt += self._l10n_es_boe_format_string(' '.join([bank.street or '', bank.street2 or '']), length=35)
                rslt += self._l10n_es_boe_format_string(bank.city or '', length=30)
                rslt += self._l10n_es_boe_format_string(bank.country.code or '', length=2)

                # Marca SEPA
                if iban and boe_wizard.declaration_type != 'N':
                    iban_country_code = iban[:2]
                    if iban_country_code == 'ES':
                        marca = '1'
                    elif iban_country_code in self.env.ref('base.sepa_zone').mapped('country_ids.code'):
                        marca = '2'
                    else:
                        marca = '3'
                else:
                    marca = '0'

                rslt += self._l10n_es_boe_format_string(marca, length=1)

            else:
                # All those fields must be empty if the report for the current period isn't a return (Devolución),
                # the file is rejected if they are not.
                rslt += self._l10n_es_boe_format_string('', length=138)

        # Reserved by AEAT
        reserved_empty_chars = 600
        if options['date']['date_from'] < '2022-01-01':
            reserved_empty_chars = 445

        rslt += self._l10n_es_boe_format_string(' ' * reserved_empty_chars)

        # Footer of page 3
        rslt += self._l10n_es_boe_format_string('</T30303000>')

        return rslt

    def _generate_page_did(self, report, options, current_company, period, year, casilla_lines_map):
        rslt = self._l10n_es_boe_format_string('<T303DID00>')

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 303)

        partner_bank = boe_wizard.partner_bank_id

        bic, iban = self._get_bic_and_iban(partner_bank)

        rslt += self._l10n_es_boe_format_string(bic if boe_wizard.declaration_type == 'X' else '', length=11)
        rslt += self._l10n_es_boe_format_string(iban, length=34)

        # Return in foreign bank account
        if boe_wizard.declaration_type == 'X':
            bank = partner_bank.bank_id
            rslt += self._l10n_es_boe_format_string(bank.name or '', length=70)
            rslt += self._l10n_es_boe_format_string(' '.join([bank.street or '', bank.street2 or '']), length=35)
            rslt += self._l10n_es_boe_format_string(bank.city or '', length=30)
            rslt += self._l10n_es_boe_format_string(bank.country.code or '', length=2)
        else:
            rslt += self._l10n_es_boe_format_string('', length=137)

        # Marca SEPA
        if iban and boe_wizard.declaration_type in ('D', 'X'):
            iban_country_code = iban[:2]
            if iban_country_code == 'ES':
                marca = '1'
            elif iban_country_code in self.env.ref('base.sepa_zone').mapped('country_ids.code'):
                marca = '2'
            else:
                marca = '3'
        else:
            marca = '0'

        rslt += self._l10n_es_boe_format_string(marca, length=1)

        # Reserved by AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 617)

        # Footer of page 3
        rslt += self._l10n_es_boe_format_string('</T303DID00>')

        return rslt


class SpanishMod347TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod347.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod347)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 347)

    def _report_custom_engine_threshold_insurance_bought(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        domain = MOD_347_CUSTOM_ENGINES_DOMAINS['_report_custom_engine_threshold_insurance_bought']
        return self._custom_threshold_common(domain, expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_threshold_regular_bought(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        domain = MOD_347_CUSTOM_ENGINES_DOMAINS['_report_custom_engine_threshold_regular_bought']
        return self._custom_threshold_common(domain, expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_threshold_regular_sold(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        domain = MOD_347_CUSTOM_ENGINES_DOMAINS['_report_custom_engine_threshold_regular_sold']
        return self._custom_threshold_common(domain, expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_threshold_all_operations(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        domain = MOD_347_CUSTOM_ENGINES_DOMAINS['_report_custom_engine_threshold_all_operations']
        return self._custom_threshold_common(domain, expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)

    def _custom_threshold_common(self, domain, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None):
        """ Some lines of mod 347 report need to be grouped by partner, only keeping the partners whose balance for the line is above 3005.06€.
        This function serves as a common helper to the custom engines handling these lines.
        """
        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        from_fy_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))
        to_fy_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_to']))
        fy_options = {**options, 'date': options['date'].copy()}

        # Only adapt dates for the threshold if from and to dates belong to the same fiscal year.
        if from_fy_dates == to_fy_dates:
            fy_options['date'].update({
                'date_from': fields.Date.to_string(from_fy_dates['date_from']),
                'date_to': fields.Date.to_string(from_fy_dates['date_to']),
                'mode': 'range',
            })

        # First get all the partners that match the domain but don't reach the threshold. We'll have to exclude them
        ct_query = report._get_query_currency_table(options)
        tables, where_clause, where_params = report._query_get(fy_options, date_scope, domain=domain + options.get('forced_domain', []))
        threshold_value = self._convert_threshold_to_company_currency(3005.06, options)
        partners_to_exclude_params = [*where_params, threshold_value]
        partners_to_exclude_query = f"""
            SELECT account_move_line.partner_id
            FROM {tables}
            JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
            WHERE {where_clause}
            GROUP BY account_move_line.partner_id
            HAVING SUM(currency_table.rate * account_move_line.balance * (CASE WHEN account_move_line__move_id.move_type IN ('in_invoice', 'in_refund', 'in_receipt') THEN -1 ELSE 1 END)) <= %s
        """

        self._cr.execute(partners_to_exclude_query, partners_to_exclude_params)
        partner_ids_to_exclude = [partner_id for (partner_id,) in self._cr.fetchall()]

        # Then, add a forced domain because it could be too long later when ast.literal_eval will be applied on it
        forced_domain = [*options.get('forced_domain', []), ('partner_id', 'not in', partner_ids_to_exclude)]
        domain_options = {**options, 'forced_domain': forced_domain}
        domain_formulas_dict = {str(domain): expressions}
        domain_result = report._compute_formula_batch_with_engine_domain(domain_options, date_scope, domain_formulas_dict, current_groupby, next_groupby,
                                                                         offset=0, limit=None)
        return next(result for result in domain_result.values())

    def _convert_threshold_to_company_currency(self, threshold, options):
        """ Returns a EUR threshold to company currency, using the options' date_to for conversion
        """
        threshold_currency = self.env.ref('base.EUR')

        if not threshold_currency.active:
            raise UserError(_("Currency %s, used for a threshold in this report, is either nonexistent or inactive. Please create or activate it.", threshold_currency.name))

        company_currency = self.env.company.currency_id
        return threshold_currency._convert(threshold, company_currency, self.env.company, options['date']['date_to'])

    def _build_boe_report_options(self, options, year):
        return self.env['account.report'].browse(options['report_id']).get_options(
            previous_options={
                **options,

                'date': {'filter': 'custom', 'string': 'Q4 '+year, 'date_from': year+'-10-01', 'date_to': year+'-12-31', 'mode': 'range'},

                'comparison': {
                    'date_to': year+'-09-30',
                    'periods': [
                        {'date_to': year+'-09-30', 'date_from': year+'-07-01', 'string': 'Q3 '+year, 'mode': 'range'},
                        {'date_to': year+'-06-30', 'date_from': year+'-04-01', 'string': 'Q2 '+year, 'mode': 'range'},
                        {'date_to': year+'-03-31', 'date_from': year+'-01-01', 'string': 'Q1 '+year, 'mode': 'range'}
                    ],
                    'number_period': 3,
                    'string': f'Q3 {year}',
                    'filter': 'previous_period',
                    'date_from': f'{year}-07-01',
                },
           }
       )

    def _get_required_partner_ids_for_boe(self, mod_invoice_type, date_from, date_to, boe_wizard, operation_key, operation_class):
        cash_basis_manual_data = boe_wizard.cash_basis_mod347_data.filtered(lambda x: x.operation_key == operation_key and x.operation_class == operation_class)
        all_partners = cash_basis_manual_data.mapped('partner_id')

        if operation_key == 'B': # Only for perceived amounts
            # If invoice is not in the current period but cash payment is,
            # we need to inject the partner into BOE so that this cash amount is reported
            cash_payments_aml = self.env['account.partial.reconcile'].search([('credit_move_id.date', '<=' ,date_to),
                                                                              ('credit_move_id.date', '>=', date_from),
                                                                              ('credit_move_id.journal_id.type', '=', 'cash'),
                                                                              ('debit_move_id.move_id.l10n_es_reports_mod347_invoice_type', '=', mod_invoice_type),
                                                                              ('credit_move_id.account_id.account_type', '=', 'asset_receivable'),
                                                                            ])
            all_partners += cash_payments_aml.mapped('credit_move_id.partner_id')

        return set(all_partners.ids)

    def _write_type2_header_record(self, current_company, boe_wizard, boe_report_options, year=None):
        if not year:
            year = str(fields.Date.today().year)

        # The header is there once for the whole year. It should use the year as date range and not quarterly. No comparison.
        yearly_options = boe_report_options.copy()
        del yearly_options['comparison']
        yearly_options = self.env['account.report'].browse(boe_report_options['report_id']).get_options(
            previous_options={
                **yearly_options,
                'date': {'date_from': '%s-01-01' % year, 'date_to': '%s-12-31' % year, 'filter': 'custom', 'mode': 'range'},
            }
        )

        rslt = self._l10n_es_boe_format_number(yearly_options, 1)
        rslt += self._l10n_es_boe_format_number(yearly_options, 347)
        rslt += self._l10n_es_boe_format_string(year, length=4)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(current_company.name, length=40)
        rslt += self._l10n_es_boe_format_string('T')
        rslt += self._l10n_es_boe_format_string(boe_wizard.get_formatted_contact_phone(), length=9)
        rslt += self._l10n_es_boe_format_string(boe_wizard.contact_person_name, length=40)
        mod_347_boe_sequence = current_company.sudo()._get_mod_boe_sequence("347")
        rslt += self._l10n_es_boe_format_number(yearly_options, 347) + self._l10n_es_boe_format_string(mod_347_boe_sequence.next_by_id(), length=10)
        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.substitutive_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.previous_report_number or '', length=13, fill_char=b'0', align='right')

        declarados_count = self._retrieve_report_expression(yearly_options, 'l10n_es_reports.mod_347_statistics_operations_count_balance')
        rslt += self._l10n_es_boe_format_number(yearly_options, declarados_count, length=9)
        declarados_total = self._retrieve_report_expression(yearly_options, 'l10n_es_reports.mod_347_operations_title_balance')
        rslt += self._l10n_es_boe_format_number(yearly_options, declarados_total, length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

        real_estates_data = self._get_real_estates_data(yearly_options, current_company.currency_id)
        rslt += self._l10n_es_boe_format_number(yearly_options, real_estates_data['count'], length=9)

        rslt += self._l10n_es_boe_format_number(yearly_options, real_estates_data['total'], length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

        rslt += self._l10n_es_boe_format_string(' ' * 205)
        rslt += self._l10n_es_boe_format_string(' ' * 9) # TIN of the legal representant; blank if 14 years or older
        rslt += self._l10n_es_boe_format_string(' ' * 88)
        rslt += self._l10n_es_boe_format_string(' ' * 13) # "Sello Electronico" => for administration
        rslt += b'\r\n'

        return rslt

    def _get_real_estates_data(self, boe_report_options, currency_id):
        """ Real estates are not directly supported by l10n_es_reports, but by the
        submodule l10n_es_real_estates. This function is used as a hook, so that we
        don't have to access the result of _write_type2_header_record by indexes
        in order to write the real estates data at the right place in the BOE
        (which is better in case the code of the header function needs to be extended).
        """
        return {'count': 0, 'total': 0}

    def _write_type2_partner_record(self, options, report_data, year, current_company, operation_key, manual_parameters_map, insurance=False, local_negocio=False):
        currency_id = current_company.currency_id
        line_partner = self.env['res.partner'].browse(self.env['account.report']._get_model_info_from_id(report_data['line_data']['id'])[1])

        rslt = self._l10n_es_boe_format_number(options, 2)
        rslt += self._l10n_es_boe_format_number(options, 347)
        rslt += self._l10n_es_boe_format_string(year, length=4)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(line_partner.country_id.code == 'ES' and self._extract_spanish_tin(line_partner) or '', length=9)
        rslt += self._l10n_es_boe_format_string(' ' * 9) # TIN of the legal representant; blank if 14 years or older
        rslt += self._l10n_es_boe_format_string(line_partner.display_name, length=40)
        rslt += self._l10n_es_boe_format_string('D') # 'Tipo de hoja', constant

        province_code = line_partner.state_id and SPANISH_PROVINCES_REPORT_CODES.get(line_partner.state_id.code) or '99'
        rslt += self._l10n_es_boe_format_string(province_code, length=2)
        # The country code is only mandatory if there is no province code (hence: no head office in Spain)
        if province_code == '99':
            if not line_partner.country_id or not line_partner.country_id.code:
                raise UserError(_("Partner with %s (id %d) is not associated to any Spanish province, and should hence have a country code. For this, fill in its 'country' field.", line_partner.name, line_partner.id))

            if line_partner.country_id.code == 'ES':
                raise UserError(_("Partner %s (id %s) is located in Spain but does not have any province. Please set one.", line_partner.name, line_partner.id))

        partner_country_code = line_partner.country_id.code
        rslt += self._l10n_es_boe_format_string(partner_country_code if partner_country_code and partner_country_code != 'ES' else '', length=2)
        rslt += self._l10n_es_boe_format_string(' ') # Constant
        rslt += self._l10n_es_boe_format_string(operation_key, length=1)

        # Total amount of operations over the year
        year_operations_sum = currency_id.round(sum(i['no_format'] for i in report_data['line_data'].get('columns', [])))
        rslt += self._l10n_es_boe_format_number(options, year_operations_sum, length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

        rslt += self._l10n_es_boe_format_string(insurance and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(local_negocio and 'X' or ' ')

        # En metálico
        invoice_types_by_xmlid = {
            'l10n_es_reports.mod_347_operations_insurance_bought': 'insurance',
            'l10n_es_reports.mod_347_operations_regular_sold': 'regular',
            'l10n_es_reports.mod_347_operations_regular_bought': 'regular'
        }
        current_invoice_type = invoice_types_by_xmlid[report_data['line_xml_id']]

        account_type = operation_key == 'B' and 'asset_receivable' or 'liability_payable'
        matching_field = operation_key == 'B' and 'debit' or 'credit'
        cash_payments_lines_in_period = self.env['account.move.line'].search([('date', '<=', year + '-12-31'), ('date', '>=', year + '-01-01'), ('journal_id.type', '=', 'cash'), ('payment_id', '!=', False), ('partner_id', '=', line_partner.id), ('account_type', '=', account_type), ('company_id', '=', current_company.id)])
        metalico_amount = 0
        for cash_payment_aml in cash_payments_lines_in_period:
            partial_reconcile_ids = cash_payment_aml['matched_' + matching_field + '_ids']
            partial_rec_on_inv_type = partial_reconcile_ids.filtered(lambda x: x[matching_field + '_move_id'].move_id.l10n_es_reports_mod347_invoice_type == current_invoice_type)
            for partial_rec in partial_rec_on_inv_type:
                metalico_amount += partial_rec.amount

        # Context key used for conversion date is set in get_txt.
        curr_eur = self.env["res.currency"].search([('name', '=', 'EUR')], limit=1)
        threshold = curr_eur._convert(6000, currency_id, current_company, options['date']['date_to'])
        if currency_id.compare_amounts(metalico_amount, threshold) == 1: # We only must report this amount if it is above 6000 €
            rslt += self._l10n_es_boe_format_number(options, metalico_amount, length=15, decimal_places=2, in_currency=True)
        else:
            rslt += self._l10n_es_boe_format_number(options, 0, length=15)

        # Inmuebles sujetas a la IVA
        operation_class = insurance and 'seguros' or local_negocio and 'local_negocio' or 'otras'
        real_estates_vat_year_total = 0
        real_estates_vat_by_trimester = []
        for trimester in range(1, 5):
            # This module does not support real estates on its own, but we give the possibility
            # to add a real_estates_vat key to the manual parameters map with the needed data,
            # through anoter module (l10n_es_real_estates does that)
            real_estates_vat_partner_dict = manual_parameters_map.get('real_estates_vat', {}).get(line_partner.id)
            real_estates_vat_amount = real_estates_vat_partner_dict and real_estates_vat_partner_dict[str(trimester)][operation_class][operation_key] or 0
            real_estates_vat_year_total += real_estates_vat_amount
            real_estates_vat_by_trimester.append(real_estates_vat_amount)

        real_estates_vat_year_total = currency_id.round(real_estates_vat_year_total)
        rslt += self._l10n_es_boe_format_number(options, real_estates_vat_year_total, length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

        rslt += self._l10n_es_boe_format_string('0000', length=4) # Ejercicio for metalico operations ; automatic computation not supported

        for trimester_index in range(3, -1, -1): # 4th trimester is at position 0 ; 1st at position 3
            trimester_total = report_data['line_data'].get('columns', [{} for i in range(0, 4)])[trimester_index].get('no_format', 0)
            rslt += self._l10n_es_boe_format_number(options, trimester_total, length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)
            rslt += self._l10n_es_boe_format_number(options, real_estates_vat_by_trimester[trimester_index], length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

        # 'NIF Operador Comunitario'
        europe_countries = self.env.ref('base.europe').country_ids - self.env.ref('base.es')
        intracom_tin = ''
        if line_partner.country_id in europe_countries:
            intracom_tin = self._extract_tin(line_partner, error_if_no_tin=False)
        rslt += self._l10n_es_boe_format_string(intracom_tin.upper(), length=17)

        # Cash Basis (Regimen Especial de Caja)
        cash_basis_partner = manual_parameters_map['cash_basis'].get(line_partner.id)
        cash_basis_data = cash_basis_partner and cash_basis_partner[operation_class][operation_key] or None
        rslt += self._l10n_es_boe_format_string(cash_basis_data is not None and 'X' or ' ')

        rslt += self._l10n_es_boe_format_string(line_partner == current_company.partner_id and 'X' or ' ')

        rslt += self._l10n_es_boe_format_string(' ')  # Not supported by Odoo; according to the partners, too few people need this option

        rslt += self._l10n_es_boe_format_number(options, cash_basis_data or 0, length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

        rslt += self._l10n_es_boe_format_string(' ' * 201)
        rslt += b'\r\n'

        return rslt

    def export_boe(self, options):
        dummy, year = self._get_mod_period_and_year(options)
        current_company = self.env.company
        report = self.env['account.report'].browse(options['report_id'])

        # Report options to use to retrieve data for the BOE
        boe_report_options = self._build_boe_report_options(options, year)

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 347)

        manual_params = boe_wizard.l10n_es_get_partners_manual_parameters_map()

        # Header
        rslt = self._write_type2_header_record(current_company, boe_wizard, boe_report_options, year=year)
        seguros_required_b = self._get_required_partner_ids_for_boe('insurance', year+'-01-01', year+'-12-31', boe_wizard, 'A', 'seguros')
        rslt += self._call_on_partner_sublines(
            boe_report_options,
            'l10n_es_reports.mod_347_operations_insurance_bought',
            lambda report_data: self._write_type2_partner_record(boe_report_options, report_data, year, current_company, 'A',
                                                                                manual_parameters_map=manual_params, insurance=True),
            required_ids_set=seguros_required_b
        )

        otras_required_a = self._get_required_partner_ids_for_boe('regular', year+'-01-01', year+'-12-31', boe_wizard, 'B', 'otras')
        rslt += self._call_on_partner_sublines(
            boe_report_options,
            'l10n_es_reports.mod_347_operations_regular_sold',
            lambda report_data: self._write_type2_partner_record(boe_report_options, report_data, year, current_company, 'B',
                                                                                manual_parameters_map=manual_params),
            required_ids_set=otras_required_a
        )

        otras_required_b = self._get_required_partner_ids_for_boe('regular', year+'-01-01', year+'-12-31', boe_wizard, 'A', 'otras')
        rslt += self._call_on_partner_sublines(
            boe_report_options,
            'l10n_es_reports.mod_347_operations_regular_bought',
            lambda report_data: self._write_type2_partner_record(boe_report_options, report_data, year, current_company, 'A',
                                                                                manual_parameters_map=manual_params),
            required_ids_set=otras_required_b
        )

        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': rslt,
            'file_type': 'txt',
        }


class SpanishMod349TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod349.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod349)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 349)

    def _write_type1_header_record(self, options, period, year, current_company, boe_wizard):
        rslt = self._l10n_es_boe_format_string('1349')
        rslt += self._l10n_es_boe_format_string(year, length=4)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(current_company.name, length=40)
        rslt += self._l10n_es_boe_format_string('T')
        rslt += self._l10n_es_boe_format_string(boe_wizard.get_formatted_contact_phone(), length=9)
        rslt += self._l10n_es_boe_format_string(boe_wizard.contact_person_name, length=40)
        mod_349_boe_sequence = current_company.sudo()._get_mod_boe_sequence("349")
        rslt += self._l10n_es_boe_format_number(options, 349) + self._l10n_es_boe_format_string(mod_349_boe_sequence.next_by_id(), length=10)
        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.substitutive_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.previous_report_number or '', length=13, fill_char=b'0', align='right')
        rslt += self._l10n_es_boe_format_string(period, length=2)
        rslt += self._l10n_es_boe_format_number(options, self._retrieve_report_expression(options, 'l10n_es_reports.mod_349_statistics_invoices_partners_count_balance'), length=9)
        rslt += self._l10n_es_boe_format_number(options, self._retrieve_report_expression(options, 'l10n_es_reports.mod_349_statistics_invoices_total_amount_balance'), length=15, in_currency=True, decimal_places=2)
        rslt += self._l10n_es_boe_format_number(options, self._retrieve_report_expression(options, 'l10n_es_reports.mod_349_statistics_refunds_partners_count_balance'), length=9)
        rslt += self._l10n_es_boe_format_number(options, self._retrieve_report_expression(options, 'l10n_es_reports.mod_349_statistics_refunds_total_amount_balance'), length=15, in_currency=True, decimal_places=2)
        rslt += self._l10n_es_boe_format_string(boe_wizard.trimester_2months_report and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(' ' * 204)
        rslt += self._l10n_es_boe_format_string(' ' * 9) # TIN of the legal representative, if under 14 years old
        rslt += self._l10n_es_boe_format_string(' ' * 101) # Constant
        rslt += b'\r\n'
        return rslt

    def _write_type2_invoice_record(self, options, report_data, year, key, current_company):
        line_partner = self.env['res.partner'].browse(self.env['account.report']._get_model_info_from_id(report_data['line_data']['id'])[1])
        rslt = self._l10n_es_boe_format_string('2349')
        rslt += self._l10n_es_boe_format_string(year, length=4)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(' ' * 58)
        rslt += self._l10n_es_boe_format_string(self._extract_tin(line_partner), length=17)
        rslt += self._l10n_es_boe_format_string(line_partner.name, length=40)
        rslt += self._l10n_es_boe_format_string(key, length=1)
        rslt += self._l10n_es_boe_format_number(options, report_data['line_data']['columns'][0]['no_format'], length=13, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string(' ' * 354)
        rslt += b'\r\n'

        return rslt

    def _write_type2_refund_records(self, options, report_data, current_company, mod_349_type, invoice_report_line_xml_id, report_period, report_year):
        line_partner = self.env['res.partner'].browse(self.env['account.report']._get_model_info_from_id(report_data['line_data']['id'])[1])
        report_date_from = options['date']['date_from']
        report_date_to = options['date']['date_to']

        rslt = self._l10n_es_boe_format_string('')
        for refund_invoice in self.env['account.move'].search([('date', '<=', report_date_to), ('date', '>=', report_date_from), ('move_type', 'in', ['in_refund', 'out_refund']), ('l10n_es_reports_mod349_invoice_type', '=', mod_349_type), ('partner_id', '=', line_partner.id)]):
            original_invoice = refund_invoice.reversed_entry_id
            if not original_invoice:
                raise UserError(_('Refund Invoice %s was created without a link to the original invoice that was credited, '
                                  'while we need that information for this report. ', refund_invoice.display_name))

            invoice_period, invoice_year = self._retrieve_period_and_year(original_invoice.date, trimester=report_period[-1] == 'T')
            group_key = (invoice_period, invoice_year, refund_invoice.l10n_es_reports_mod349_invoice_type)

            # We compute the total refund for this invoice until the current period
            all_previous_refunds = self.env['account.move'].search([('reversed_entry_id', '=', original_invoice.id), ('date', '<=', report_date_to)])
            total_refund = sum(all_previous_refunds.mapped('amount_total'))

            # Compute invoice report line at the time of the original invoice
            line_options = options.copy()
            line_date_from, line_date_to = self._convert_period_to_dates(invoice_period, invoice_year)
            line_options['date']['date_from'] =  datetime.strftime(line_date_from, '%Y-%m-%d')
            line_options['date']['date_to'] =  datetime.strftime(line_date_to, '%Y-%m-%d')

            invoice_line_data = self._get_partner_subline(line_options, invoice_report_line_xml_id, line_partner.id)
            previous_report_amount = invoice_line_data['columns'][0]['no_format']

            # Now, we can report the record!
            rslt += self._l10n_es_boe_format_string('2349')
            rslt += self._l10n_es_boe_format_string(report_year, length=4)
            rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
            rslt += self._l10n_es_boe_format_string(' ' * 58)
            rslt += self._l10n_es_boe_format_string(self._extract_tin(line_partner), length=17)
            rslt += self._l10n_es_boe_format_string(line_partner.name, length=40)
            rslt += self._l10n_es_boe_format_string(mod_349_type, length=1)
            rslt += self._l10n_es_boe_format_string(' ' * 13) # Constant
            rslt += self._l10n_es_boe_format_string(invoice_year, length=4)
            rslt += self._l10n_es_boe_format_string(invoice_period, length=2)
            rslt += self._l10n_es_boe_format_number(options, current_company.currency_id.round(previous_report_amount - total_refund), length=13, decimal_places=2, in_currency=True)
            rslt += self._l10n_es_boe_format_number(options, previous_report_amount, length=13, decimal_places=2, in_currency=True)
            rslt += self._l10n_es_boe_format_string(' ' * 322)
            rslt += b'\r\n'

        return rslt

    def export_boe(self, options):
        period, year = self._get_mod_period_and_year(options)
        current_company = self.env.company

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 349)

        rslt = self._l10n_es_boe_format_string('')

        if boe_wizard.trimester_2months_report:
            if period[-1] == 'T':
                options = options.copy()
                end_date = datetime.strptime(options['date']['date_to'], '%Y-%m-%d')
                options['date']['date_to'] = (end_date + relativedelta(day=31, months=-1)).strftime('%Y-%m-%d')
            else:
                raise UserError(_("You cannot generate a BOE file for the first two months of a trimester if only one month is selected!"))

        # Header
        rslt = self._write_type1_header_record(options, period, year, current_company, boe_wizard)

        # Invoices lines
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_supplies', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'E', current_company))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_acquisitions', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'A', current_company))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_triangular', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'T', current_company))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_services_sold', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'S', current_company))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_services_acquired', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'I', current_company))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_supplies_without_taxes', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'M', current_company))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_supplies_without_taxes_legal_representative', lambda report_data: self._write_type2_invoice_record(options, report_data, year, 'H', current_company))

        # Refunds lines
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_supplies_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'E', 'l10n_es_reports.mod_349_supplies', period, year))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_acquisitions_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'A', 'l10n_es_reports.mod_349_acquisitions', period, year))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_triangular_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'T', 'l10n_es_reports.mod_349_triangular', period, year))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_services_sold_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'S', 'l10n_es_reports.mod_349_services_sold', period, year))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_services_acquired_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'I', 'l10n_es_reports.mod_349_services_acquired', period, year))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_supplies_without_taxes_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'M', 'l10n_es_reports.mod_349_supplies_without_taxes', period, year))
        rslt += self._call_on_partner_sublines(options, 'l10n_es_reports.mod_349_supplies_without_taxes_legal_representative_refunds', lambda report_data: self._write_type2_refund_records(options, report_data, current_company, 'H', 'l10n_es_reports.mod_349_supplies_without_taxes_legal_representative', period, year))

        return {
            'file_name': self.env['account.report'].browse(options['report_id']).get_default_report_filename(options, 'txt'),
            'file_content': rslt,
            'file_type': 'txt',
        }


class SpanishMod390TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es.mod390.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod390)'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 390)

    def export_boe(self, options):
        _period, year = self._get_mod_period_and_year(options)
        boe_wizard = self._retrieve_boe_manual_wizard(options, 390)
        current_company = self.env.company
        casilla_lines_map = {}
        for section in options['sections']:
            section_report = self.env['account.report'].browse(section['id'])
            report_lines = section_report._get_lines(section_report.get_options())
            casilla_lines_map.update(self._retrieve_casilla_lines(report_lines))

        # Header
        rslt = self._l10n_es_boe_format_string('<T3900' + year + '0A0000>')
        rslt += self._l10n_es_boe_format_string('<AUX>')
        rslt += self._l10n_es_boe_format_string(' ' * 70)
        odoo_version = odoo.release.version.split('.')
        rslt += self._l10n_es_boe_format_string(str(odoo_version[0]) + str(odoo_version[1]), length=4)
        rslt += self._l10n_es_boe_format_string(' ' * 4)
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(' ' * 213)
        rslt += self._l10n_es_boe_format_string('</AUX>')

        rslt += self._generate_mod_390_page1(options, current_company, year, boe_wizard)
        rslt += self._generate_mod_390_page2(options, casilla_lines_map)
        rslt += self._generate_mod_390_page3(options, casilla_lines_map)
        rslt += self._generate_mod_390_page4(options, casilla_lines_map)
        # We don't handle page 5 for now (Simplified regime operations, including agricultural, livestock and forestry)
        rslt += self._generate_mod_390_page6(options, casilla_lines_map)
        rslt += self._generate_mod_390_page7(options, casilla_lines_map)
        rslt += self._generate_mod_390_page8(options, casilla_lines_map)

        rslt += self._l10n_es_boe_format_string('</T3900' + year + '0A0000>')

        return {
            'file_name': f'Modelo390 - {year}',
            'file_content': rslt,
            'file_type': 'txt',
        }

    def _generate_mod_390_page1(self, options, current_company, year, boe_wizard):
        # Main info regarding the company, the representant, the dates and the report itself
        # Header
        rslt = self._l10n_es_boe_format_string('<T39001000>  ')
        rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
        rslt += self._l10n_es_boe_format_string(current_company.name, length=60)
        rslt += self._l10n_es_boe_format_string(boe_wizard.physical_person_name, length=20)

        rslt += self._l10n_es_boe_format_string(year)
        rslt += self._l10n_es_boe_format_string('  ')

        rslt += self._l10n_es_boe_format_string('1' if boe_wizard.monthly_return else '0')

        tax_unit_option = options.get('tax_unit')
        group_of_entities = True if tax_unit_option and tax_unit_option != 'company_only' else False

        rslt += self._l10n_es_boe_format_string('1' if group_of_entities else '0')# Part of a group of entities
        rslt += self._l10n_es_boe_format_string(boe_wizard.group_number, length=7) if boe_wizard.group_number else self._l10n_es_boe_format_string(' ' * 7)
        rslt += self._l10n_es_boe_format_string('1' if group_of_entities else '0')# Dominant --> True if we're in a tax unit
        rslt += self._l10n_es_boe_format_string('0')# Dependant --> always False
        rslt += self._l10n_es_boe_format_string('1' if boe_wizard.special_regime_applicable_163 else '0')
        # "NIF de la entidad dominante" must only be filled if the declarant is not the dominant entity
        # see official documentation : https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/G412/instr390.pdf
        rslt += self._l10n_es_boe_format_string(' ' * 9)
        rslt += self._l10n_es_boe_format_string('2')# Bankrupcy
        rslt += self._l10n_es_boe_format_string('1' if boe_wizard.special_cash_basis else '2')
        rslt += self._l10n_es_boe_format_string('1' if boe_wizard.special_cash_basis_beneficiary else '2')
        rslt += self._l10n_es_boe_format_string('1' if boe_wizard.is_substitute_declaration else '0')
        rslt += self._l10n_es_boe_format_string('1' if boe_wizard.is_substitute_decl_by_rectif_of_quotas else '0')
        rslt += self._l10n_es_boe_format_string(boe_wizard.previous_decl_number, length=13) if boe_wizard.previous_decl_number else self._l10n_es_boe_format_string(' ' * 13)
        rslt += self._l10n_es_boe_format_string(boe_wizard.principal_activity, length=40)
        rslt += self._l10n_es_boe_format_string(boe_wizard.principal_code_activity, length=3)
        rslt += self._l10n_es_boe_format_string(boe_wizard.principal_iae_epigrafe, length=4)

        # Other Activities
        for _i in range(0, 5):
            # Activity name (40), activity code (3) & activity epigrafe (4)
            rslt += self._l10n_es_boe_format_string(' ' * (40 + 3 + 4))

        # Joint Declaration
        rslt += self._l10n_es_boe_format_string('0')
        rslt += self._l10n_es_boe_format_string(' ' * (9 + 37))

        # Representant
        rslt += self._l10n_es_boe_format_string(' ' * (9 + 80 + 2 + 17 + 5 + 2 + 2 + 2 + 9 + 20 + 15 + 5))

        # Personas Jurídicas
        # Only one persona juridica is mandatory, the others are left blank
        rslt += self._l10n_es_boe_format_string(boe_wizard.judicial_person_name, length=80)
        rslt += self._l10n_es_boe_format_string(boe_wizard.judicial_person_nif, length=9)
        rslt += self._l10n_es_boe_format_string(datetime.strftime(boe_wizard.judicial_person_procuration_date, "%d%m%Y"), length=8)
        rslt += self._l10n_es_boe_format_string(boe_wizard.judicial_person_notary, length=12)
        rslt += self._l10n_es_boe_format_string(((' ' * (80 + 9)) + '00000000' + (' ' * 12))*2)

        # Footer of page 1
        rslt += self._l10n_es_boe_format_string(' ' * (21 + 13 + 20 + 150))  # Reserved for AEAT
        rslt += self._l10n_es_boe_format_string('</T39001000>')

        return rslt

    def _generate_mod_390_page2(self, options, casilla_lines_map):
        # Operations carried out under the general regime : accrued VAT
        # Header
        rslt = self._l10n_es_boe_format_string('<T39002000> ')
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)

        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['01'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['02'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(3, 7):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['0%s' % casilla], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['500'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['501'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(502, 506):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['643'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['644'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(645, 649):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['07'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['08'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['09'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(10, 15):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['21'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['22'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(23, 27):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['545'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['546'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['547'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['548'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['551'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['552'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(27, 31):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['649'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['650'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(31, 37):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        for casilla in range(599, 603):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        for casilla in range(41, 48):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        # Blank space for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 150)
        # Footer
        rslt += self._l10n_es_boe_format_string('</T39002000>')

        return rslt

    def _generate_mod_390_page3(self, options, casilla_lines_map):
        # Operations carried out under the general regime : VAT deductible
        # Header
        rslt = self._l10n_es_boe_format_string('<T39003000> ')

        # Casillas
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['190'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['191'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(603, 607):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['48'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['49'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['506'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['507'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(607, 611):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['512'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['513'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['196'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['197'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(611, 615):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['50'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['51'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['514'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['515'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(615, 619):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['520'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['521'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['202'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['203'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(619, 623):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['52'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['53'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['208'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['209'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(623, 627):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['54'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['55'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['214'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['215'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(627, 631):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['56'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['57'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['220'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['221'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(631, 635):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['58'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['59'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['587'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['588'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 2)
        for casilla in range(635, 639):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['597'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['598'], length=17, decimal_places=2, in_currency=True)

        # Blank space for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 150)
        # Footer
        rslt += self._l10n_es_boe_format_string('</T39003000>')

        return rslt

    def _generate_mod_390_page4(self, options, casilla_lines_map):
        #Header
        rslt = self._l10n_es_boe_format_string('<T39004000> ')

        # Casillas
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['60'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['61'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['660'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['661'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['639'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['62'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['651'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['652'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['63'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['522'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['64'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['65'], length=17, decimal_places=2, in_currency=True)

        # Blank space for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 150)
        # Footer
        rslt += self._l10n_es_boe_format_string('</T39004000>')

        return rslt

    def _generate_mod_390_page6(self, options, casilla_lines_map):
        # Header
        rslt = self._l10n_es_boe_format_string('<T39006000> ')
        # Section 7  : Annual settlement result (Only for taxpayers who are taxed exclusively in common territory)
        # Casillas
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['658'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['84'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['659'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['85'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['86'], length=17, decimal_places=2, in_currency=True)
        # We don't cover the section 8 of the modelo 390, the casillas are replaced by zeros.
        # 87 --> 91: Administraciones : Territorio commùn (5), Álava (5), Guipúzcoa(5), Vizcaya(5), Navarra(5)
        rslt += self._l10n_es_boe_format_string('0' * 5 * 5)
        # 658 : Administraciones - Regularización cuotas art. 80.Cinco.5ª LIVA (17)
        # 84 : Administraciones - Suma de resultados (17)
        # 92 : Administraciones - Resultado atribuible a territorio común (17)
        # 659 : Administraciones -IVA a la importación liquidado por la Aduana (17)
        # 93 : Administraciones - Compens. cuotas ej. anterior atrib. territ. com. (17)
        # 94 : Administraciones -Resultado liq. anual atribuible territ. comun (17)
        rslt += self._l10n_es_boe_format_string('0' * 17 * 6)
        # Section 9 : Result of settlements
        #   Periods that are not taxed under the Special Regime of the group of entities
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['95'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['96'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['524'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['97'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['98'], length=17, decimal_places=2, in_currency=True)
        #   Periods that are taxed under the Special Regime of the group of entities
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['662'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['525'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['526'], length=17, decimal_places=2, in_currency=True)
        # Section 10 : Trading volume
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['99'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['653'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['103'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['104'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['105'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['110'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['125'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['126'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['127'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['128'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['100'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['101'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['102'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['227'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['228'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['106'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['107'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['108'], length=17, decimal_places=2, in_currency=True)

        # Blank space for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 150)
        # Footer
        rslt += self._l10n_es_boe_format_string('</T39006000>')

        return rslt

    def _generate_mod_390_page7(self, options, casilla_lines_map):
        # Header
        rslt = self._l10n_es_boe_format_string('<T39007000> ')

        # Casillas
        # Section 11: Specific operations in the carried out during the year
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['230'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['109'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['231'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['232'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['111'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['113'], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['523'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(654, 658):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        # We don't cover the section 12 of the modelo 390, the casillas are replaced by blank spaces
        for _i in range(0, 5):
            rslt += self._l10n_es_boe_format_string(' ' * 40)  # Prorratas - Actividad desarrollada
            rslt += self._l10n_es_boe_format_string(' ' * 3)  # 12. Prorratas - Código CNAE [114]
            rslt += self._l10n_es_boe_format_string('0' * 17)  # 12. Prorratas - Importe de operaciones [115]
            rslt += self._l10n_es_boe_format_string('0' * 17)  # 12. Prorratas - Importe de operaciones con derecho a deducción [116]
            rslt += self._l10n_es_boe_format_string(' ')  # 12. Prorratas - Tipo de prorrata [117]
            rslt += self._l10n_es_boe_format_string('0' * 5)  # 12. Prorratas - % de prorrata [118]

        # Blank space for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 150)
        # Footer
        rslt += self._l10n_es_boe_format_string('</T39007000>')

        return rslt

    def _generate_mod_390_page8(self, options, casilla_lines_map):
        # Activities with differentiated deduction regimes
        # Header
        rslt = self._l10n_es_boe_format_string('<T39008000> ')

        # Casillas
        for casilla in range(139, 153):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['640'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(153, 170):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['641'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(170, 187):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)
        rslt += self._l10n_es_boe_format_number(options, casilla_lines_map['642'], length=17, decimal_places=2, in_currency=True)
        for casilla in range(187, 190):
            rslt += self._l10n_es_boe_format_number(options, casilla_lines_map[str(casilla)], length=17, decimal_places=2, in_currency=True)

        # Blank space for AEAT
        rslt += self._l10n_es_boe_format_string(' ' * 150)
        # Footer
        rslt += self._l10n_es_boe_format_string('</T39008000>')

        return rslt
