import re
import datetime
import calendar

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import get_barcode_check_digit

FNC1_CHAR = '\x1D'


class BarcodeNomenclature(models.Model):
    _inherit = 'barcode.nomenclature'

    is_gs1_nomenclature = fields.Boolean(
        string="Is GS1 Nomenclature",
        help="This Nomenclature use the GS1 specification, only GS1-128 encoding rules is accepted is this kind of nomenclature.")
    gs1_separator_fnc1 = fields.Char(
        string="FNC1 Separator", trim=False, default=r'(Alt029|#|\x1D)',
        help="Alternative regex delimiter for the FNC1. The separator must not match the begin/end of any related rules pattern.")

    @api.constrains('gs1_separator_fnc1')
    def _check_pattern(self):
        for nom in self:
            if nom.is_gs1_nomenclature and nom.gs1_separator_fnc1:
                try:
                    re.compile("(?:%s)?" % nom.gs1_separator_fnc1)
                except re.error as error:
                    raise ValidationError(_("The FNC1 Separator Alternative is not a valid Regex: ") + str(error))

    @api.model
    def gs1_date_to_date(self, gs1_date):
        """ Converts a GS1 date into a datetime.date.

        :param gs1_date: A year formated as yymmdd
        :type gs1_date: str
        :return: converted date
        :rtype: datetime.date
        """
        # See 7.12 Determination of century in dates:
        # https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
        now = datetime.date.today()
        current_century = now.year // 100
        substract_year = int(gs1_date[0:2]) - (now.year % 100)
        century = (51 <= substract_year <= 99 and current_century - 1) or\
            (-99 <= substract_year <= -50 and current_century + 1) or\
            current_century
        year = century * 100 + int(gs1_date[0:2])

        if gs1_date[-2:] == '00':  # Day is not mandatory, when not set -> last day of the month
            date = datetime.datetime.strptime(str(year) + gs1_date[2:4], '%Y%m')
            date = date.replace(day=calendar.monthrange(year, int(gs1_date[2:4]))[1])
        else:
            date = datetime.datetime.strptime(str(year) + gs1_date[2:], '%Y%m%d')
        return date.date()

    def parse_gs1_rule_pattern(self, match, rule):
        result = {
            'rule': rule,
            'ai': match.group(1),
            'string_value': match.group(2),
        }
        if rule.gs1_content_type == 'measure':
            try:
                decimal_position = 0  # Decimal position begins at the end, 0 means no decimal.
                if rule.gs1_decimal_usage:
                    decimal_position = int(match.group(1)[-1])
                if decimal_position > 0:
                    result['value'] = float(match.group(2)[:-decimal_position] + "." + match.group(2)[-decimal_position:])
                else:
                    result['value'] = int(match.group(2))
            except Exception:
                raise ValidationError(_(
                    "There is something wrong with the barcode rule \"%s\" pattern.\n"
                    "If this rule uses decimal, check it can't get sometime else than a digit as last char for the Application Identifier.\n"
                    "Check also the possible matched values can only be digits, otherwise the value can't be casted as a measure.",
                    rule.name))
        elif rule.gs1_content_type == 'identifier':
            # Check digit and remove it of the value
            if match.group(2)[-1] != str(get_barcode_check_digit("0" * (18 - len(match.group(2))) + match.group(2))):
                return None
            result['value'] = match.group(2)
        elif rule.gs1_content_type == 'date':
            if len(match.group(2)) != 6:
                return None
            result['value'] = self.gs1_date_to_date(match.group(2))
        else:  # when gs1_content_type == 'alpha':
            result['value'] = match.group(2)
        return result

    def gs1_decompose_extanded(self, barcode):
        """Try to decompose the gs1 extanded barcode into several unit of information using gs1 rules.

        Return a ordered list of dict
        """
        self.ensure_one()
        separator_group = FNC1_CHAR + "?"
        if self.gs1_separator_fnc1:
            separator_group = "(?:%s)?" % self.gs1_separator_fnc1
        # zxing-library patch, removing GS1 identifiers
        for identifier in [']C1', ']e0', ']d2', ']Q3', ']J1']:
            if barcode.startswith(identifier):
                barcode = barcode.replace(identifier, '')
                break
        results = []
        gs1_rules = self.rule_ids.filtered(lambda r: r.encoding == 'gs1-128')

        def find_next_rule(remaining_barcode):
            for rule in gs1_rules:
                match = re.search("^" + rule.pattern + separator_group, remaining_barcode)
                # If match and contains 2 groups at minimun, the first one need to be the AI and the second the value
                # We can't use regex nammed group because in JS, it is not the same regex syntax (and not compatible in all browser)
                if match and len(match.groups()) >= 2:
                    res = self.parse_gs1_rule_pattern(match, rule)
                    if res:
                        return res, remaining_barcode[match.end():]
            return None

        while len(barcode) > 0:
            res_bar = find_next_rule(barcode)
            # Cannot continue -> Fail to decompose gs1 and return
            if not res_bar or res_bar[1] == barcode:
                return None
            barcode = res_bar[1]
            results.append(res_bar[0])

        return results

    def parse_barcode(self, barcode):
        if self.is_gs1_nomenclature:
            return self.gs1_decompose_extanded(barcode)
        return super().parse_barcode(barcode)

    @api.model
    def _preprocess_gs1_search_args(self, args, barcode_types, field='barcode'):
        """Helper method to preprocess 'args' in _search method to add support to
        search with GS1 barcode result.
        Cut off the padding if using GS1 and searching on barcode. If the barcode
        is only digits to keep the original barcode part only.
        """
        nomenclature = self.env.company.nomenclature_id
        if nomenclature.is_gs1_nomenclature:
            for i, arg in enumerate(args):
                if not isinstance(arg, (list, tuple)) or len(arg) != 3:
                    continue
                field_name, operator, value = arg
                if field_name != field or operator not in ['ilike', 'not ilike', '=', '!='] or value is False:
                    continue

                parsed_data = []
                try:
                    parsed_data += nomenclature.parse_barcode(value) or []
                except (ValidationError, ValueError):
                    pass

                replacing_operator = 'ilike' if operator in ['ilike', '='] else 'not ilike'
                for data in parsed_data:
                    data_type = data['rule'].type
                    value = data['value']
                    if data_type in barcode_types:
                        if data_type == 'lot':
                            args[i] = (field_name, operator, value)
                            break
                        match = re.match('0*([0-9]+)$', str(value))
                        if match:
                            unpadded_barcode = match.groups()[0]
                            args[i] = (field_name, replacing_operator, unpadded_barcode)
                        break

                # The barcode isn't a valid GS1 barcode, checks if it can be unpadded.
                if not parsed_data:
                    match = re.match('0+([0-9]+)$', value)
                    if match:
                        args[i] = (field_name, replacing_operator, match.groups()[0])
        return args
