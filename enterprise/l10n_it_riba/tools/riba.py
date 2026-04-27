import unicodedata
from collections import Counter
from datetime import datetime
from itertools import starmap

from odoo import fields


def check_records(records):
    """ Check that Riba records are consistent within themselves """
    footer = records[-1]
    pos_total = footer['positive_total'] or 0.0
    neg_total = footer['negative_total'] or 0.0
    amounts_sum = round(sum(record.get('amount', 0.0) for record in records), 2)
    len_sections = len({record.get('section_number') for record in records})
    if not (amounts_sum == neg_total - pos_total) and (len_sections == footer['n_sections']):
        return False
    counter = Counter(record.get('record_type') for record in records)
    return (
        counter
        and (counter['IB'] == counter['EF'] == 1)
        and (counter['14'] == len_sections)
    )


def str_records(records):
    """ Serialize and format Riba records for printout """
    strings, section = [], 0
    for i, record in enumerate(records, 1):
        if record['record_type'] == 'IB':
            section += 1
            strings.append("Header:")
            strings.append(f"Section #{section}:")
        elif record['record_type'] == 'EF':
            strings.append("Footer:")
        strings.append(f"    {record['record_type']}: -----")
        for k, v in record.items():
            strings.append(f"    {k:<25s}{v}")
    return "\n".join(strings)


def eq_records(one, two):
    """ Compare two sets of Riba values for equality """
    if len(one) != len(two):
        return False

    removed = set(_add_default_values())
    for one_record, two_record in zip(one, two):
        def get_keys(record):
            return {key for key, val in record.items() if val} - removed
        one_keys, two_keys = get_keys(one_record), get_keys(two_record)
        if one_keys != two_keys:
            return False

        def get_vals(record, keys):
            return [_utf8_ascii(str(val or '')) for key, val in record.items() if key in keys]
        one_vals, two_vals = get_vals(one_record, one_keys), get_vals(two_record, two_keys)
        if one_vals != two_vals:
            return False

    return True


# Templates
# -------------------

def _int(x):
    """ Riba text to Python integer """
    return int(x) if x not in (False, None, '') else False


def _date(x):
    """ Riba text to Python date """
    return datetime.strptime(x, '%d%m%y').date() if x else False


TEMPLATE_MAP = {
    'IB': (  # Header
        ' ',                                   # filler
        'IB',                                  # record type
        ('creditor_sia_code', '>05', 5, str),
        ('creditor_abi', '>05', 5, str),
        ('today', '%d%m%y', 6, _date),
        ('support_name', '<20', 20),           # must be unique per date, creditor, receiver
        ('creditor_note', '<6', 6),
        f'{" ":<59}',                          # filler
        ('flow_kind', '1', 1),                 # 1 if ecommerce
        ('flow_specifier', '1', 1),            # fixed to '$' only if flow_kind is present
        ('gateway_bank_abi', '>5', 5, str),    # only if flow_kind is present
        '  ',                                  # filler
        ('currency', '1', 1),                  # Currency, Euros fixed
        ' ',                                   # filler
        '     ',                               # reserved
    ),
    '14': (  # Disposition
        ' ',                                   # filler
        '14',                                  # record type
        ('section_number', '>07', 7, _int),
        f'{" ":<12}',                          # filler
        ('payment_date', '%d%m%y', 6, _date),
        '30000',                               # reason, fixed
        ('amount', '>013', 13, _int),
        '-',                                   # sign, fixed
        ('creditor_abi', '>05', 5, str),
        ('creditor_cab', '>05', 5, str),
        ('creditor_ccn', '<12', 12, str),
        ('debitor_abi', '>05', 5, str),
        ('debitor_cab', '>05', 5, str),
        f'{" ":<12}',                          # filler
        ('creditor_sia_code', '>05', 5, str),
        '4',                                   # code type, fixed
        ('debitor_code', '<16', 16),
        ('debitor_type', '1', 1),
        '     ',                               # filler
        ('currency', '1', 1),
    ),
    '20': (  # Creditor description
        ' ',                                   # filler
        '20',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        ('segment_1', "<24", 24),
        ('segment_2', "<24", 24),
        ('segment_3', "<24", 24),
        ('segment_4', "<24", 24),
        f'{" ":<14}',                          # filler
    ),
    '30': (  # Debitor description
        ' ',                                   # filler
        '30',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        ('segment_1', "<30", 30),
        ('segment_2', "<30", 30),
        ('debitor_tax_code', "<16", 16),       # Codice Fiscale
        f'{" ":<34}',                          # filler
    ),
    '40': (  # Debitor address
        ' ',                                   # filler
        '40',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        ('debitor_address', '<30', 30),
        ('debitor_zip', '<5', 5),
        ('debitor_city', '<23', 23),
        ('debitor_state', '2', 2),
        ('debitor_bank_name', '<50', 50),
    ),
    '50': (  # Creditor address
        ' ',                                   # filler
        '50',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        ('segment_1', "<40", 40),
        ('segment_2', "<40", 40),
        f'{" ":<10}',                          # filler
        ('creditor_tax_code', "<16", 16),      # Creditor's tax code (16 characters)
        '    ',
    ),
    '51': (  # Creditor information
        ' ',                                   # filler
        '51',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        ('receipt_number', '>010', 10, _int),  # assigned by the creditor
        ('creditor_name', '<20', 20),          # in abbreviated form
        ('tax_office_state_name', '<15', 15),  # state name
        ('authorization_number', '<10', 10),
        ('authorization_date', '%d%m%y', 6, _date),
        f'{" ":<49}',                          # filler
    ),
    '70': (  # Summary
        ' ',                                   # filler
        '70',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        f'{" ":<78}',                          # filler
        ('circuit_indicators', '<12', 12),
        ('control_keys', '<20', 20),
    ),
    'EF': (  # Footer
        ' ',                                   # filler
        'EF',                                  # record type
        ('creditor_sia_code', '>05', 5, str),
        ('creditor_abi', '>05', 5, str),
        ('today', '%d%m%y', 6, _date),
        ('support_name', '<20', 20),           # must be unique per date, creditor, receiver
        ('creditor_note', '<6', 6),
        ('n_sections', '>07', 7, _int),
        ('negative_total', '>015', 15, _int),
        ('positive_total', '>015', 15, _int),
        ('n_records', '>07', 7, _int),
        f'{" ":<24}',                          # filler
        ('currency', '1', 1),                  # Currency, Euros fixed
        '      ',                              # reserved
    ),
}


# Read
# -----------------------

def file_import(content):
    return [_read(line) for line in content.splitlines()]


def _read(record):
    """ Detect the correct template and read the fields of a record """
    assert (len(record) == 120)
    template_type = record[1:3]
    return {
        'record_type': template_type,
        **_read_from_template(record, TEMPLATE_MAP.get(template_type)),
    }


def _read_from_template(record, line_template):
    """ Reads a record given the related template """

    def _slice(record, start, token_length):
        end = start + token_length
        return end, record[start:end].strip()

    def reader(record, line_template):
        total_length = 0
        for field in line_template:
            if isinstance(field, str):
                total_length += len(field)
                continue
            elif isinstance(field, tuple):
                name, _format, token_length, fmt_func = (field + (None,))[:4]
                total_length, token = _slice(record, total_length, token_length)
                value = fmt_func(token) if fmt_func else token
            if value or not isinstance(value, str):
                yield name, value
        assert total_length == 120
    return dict(reader(record, line_template))


# Write
# -------------------

def file_export(records):
    """ Export Riba records to string for file export """
    check_records(records)
    formatted_record = []
    for record in records:
        record_type = record['record_type']
        template = TEMPLATE_MAP[record_type]
        formatted = _format_record(record, template)
        formatted_record.append(formatted)
    return "\n".join(formatted_record) + "\n"


def _get_fstring(item):
    """ Get format string from Riba template """
    if isinstance(item, tuple):
        key, fmt, *_ = item
        return f'{{{key}:{fmt}}}'
    else:
        return item


def _trim_value(value, token_template):
    """ Trim a Riba value for output """
    if (
        isinstance(token_template, tuple)
        and len(token_template) == 3
        and isinstance(token_template[2], int)
    ):
        return value[:token_template[2]]
    return value


def _add_default_values(vals=None, line_template=None):
    """ Some records are just fixed, we rely on them as defaults.
        Unspecified values will be put as blanks.
    """
    vals = {
        'currency': 'E',
        'today': fields.Date.today(),
        **(vals or {}),
    }
    if line_template:
        for token_template in line_template:
            if isinstance(token_template, tuple) and len(token_template) > 1:
                key = token_template[0]
                if key not in vals or not vals[key]:
                    vals[key] = ''
    return vals


def _fix_missing_dates(vals, line_template):
    """ Dates have a '%y%m%d' format string, but if the value is missing
        and we have None or False, then we can't use that in formatting.
        We have to turn the formatstring into something that can format blank.
    """
    result = []
    for token_template in line_template:
        if (
            isinstance(token_template, tuple)
            and len(token_template) == 4
            and token_template[-1].__name__ == '_date'
        ):
            key, _fmt, trim, func = token_template
            if key not in vals or not vals[key]:
                result.append((key, f'<{trim}s', trim, func))
                continue
        result.append(token_template)
    return result


def _utf8_ascii(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')


def _format_record(vals, line_template):
    """ Return a formatted record, given:
            a dictionary of vals
            a line_tempate list of description of fields
    """
    vals = _add_default_values(vals, line_template)
    line_template = _fix_missing_dates(vals, line_template)
    fstrings = [_utf8_ascii(_get_fstring(item).format(**vals)) for item in line_template]
    record = "".join(starmap(_trim_value, zip(fstrings, line_template)))
    assert len(record) == 120, f"{record!a} is not 120 chars long"
    return record
