import re
import datetime
import calendar

from odoo import api, models
from odoo.exceptions import ValidationError

FNC1_CHAR = '\x1D'


class BarcodeNomenclature(models.Model):
    _inherit = 'barcode.nomenclature'

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

    @api.model
    def _preprocess_gs1_search_args(self, args, barcode_types, field='barcode'):
        """Helper method to preprocess 'args' in _search method to add support to
        search with GS1 barcode result.
        Cut off the padding if using GS1 and searching on barcode. If the barcode
        is only digits to keep the original barcode part only.
        """
        combined_nomenclatures = self.env['barcode.nomenclature'].search([('is_combined', '=', True)])
        parsed_data = []
        for i, arg in enumerate(args):
            if not isinstance(arg, (list, tuple)) or len(arg) != 3:
                continue
            field_name, operator, value = arg
            if field_name != field or operator not in ['ilike', 'not ilike', '=', '!='] or value is False:
                continue

            for nomenclature in combined_nomenclatures:
                try:
                    parsed_data += nomenclature.parse_barcode(value) or []
                except (ValidationError, ValueError):
                    pass

                replacing_operator = 'ilike' if operator in ['ilike', '='] else 'not ilike'
                for data in parsed_data:
                    data_type = data['group'].type
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
            if combined_nomenclatures and not parsed_data:
                match = re.match('0+([0-9]+)$', value)
                if match:
                    args[i] = (field_name, replacing_operator, match.groups()[0])
        return args
