from datetime import datetime
from itertools import starmap

from odoo import fields


example = (
      " IB     05696240424RB-IX-P-151255                                                                                E      "
    "\n 140000001            300424300000000000073200-0569654900000003759X480839354850                 4               7      E"
    "\n 200000001Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000001ALUVETRO SRL UNIPERSONALE                                   03450700988                                       "
    "\n 400000001VIA LOMBARDIA, 4/6            25034ORZINUOVI              BSCRA DI BORGO SAN GIACOMO CREDITO COOPERATIVO SCRL "
    "\n 500000001Fatt. 176 del 31/03/24                                                                    03821260985         "
    "\n 5100000010000000176Dama Srl                                                                                            "
    "\n 700000001                                                                                          000                 "
    "\n 140000002            300424300000000000122305-0569654900000003759X480873554300                 4             115      E"
    "\n 200000002Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000002ARCHETTI OMAR                                               02717520981                                       "
    "\n 400000002VIA PAPA GIOVANNI II, 7       25030COCCAGLIO              BSBCC DI POMPIANO E DELLA FRANCIACORTA SCRL         "
    "\n 500000002Fatt. 201 del 31/03/24                                                                    03821260985         "
    "\n 5100000020000000201Dama Srl                                                                                            "
    "\n 700000002                                                                                          000                 "
    "\n 140000003            300424300000000000061000-0569654900000003759X480503454390                 4             769      E"
    "\n 200000003Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000003AZIENDA AGRICOLA FRATELLI MURATORI S.S.                     03535970176                                       "
    "\n 400000003VIA VALLI N. 31               25030ADRO                   BS                                                  "
    "\n 500000003Fatt. 185 del 31/03/24                                                                    03821260985         "
    "\n 5100000030000000185Dama Srl                                                                                            "
    "\n 700000003                                                                                          000                 "
    "\n 140000004            300424300000000000104005-0569654900000003759X480200811510                 4             788      E"
    "\n 200000004Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000004CALZATURIFICIO DEI COLLI SRL                                00157830209                                       "
    "\n 400000004VIA XXIV GIUGNO N. 39         46040SOLFERINO              MNCREDITO ITALIANO SPA                              "
    "\n 500000004Fatt. 210 del 31/03/24                                                                    03821260985         "
    "\n 5100000040000000210Dama Srl                                                                                            "
    "\n 700000004                                                                                          000                 "
    "\n 140000005            300424300000000000049105-0569654900000003759X480306952790                 4             180      E"
    "\n 200000005Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000005CASEIFICIO PALENI SRL                                       02708950163                                       "
    "\n 400000005VIA S. LORENZO N. 2           24060CASAZZA                BGBANCA INTESA BANCA COMMERCIALE ITALIANA SPA       "
    "\n 500000005Fatt. 208 del 31/03/24                                                                    03821260985         "
    "\n 5100000050000000208Dama Srl                                                                                            "
    "\n 700000005                                                                                          000                 "
    "\n 140000006            310323300000000000136157-0569654900000003759X480306953701                 4             191      E"
    "\n 200000006Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000006CONCERIA DI URGNANO SRL                                     10485380157                                       "
    "\n 400000006VIA LOCALITA' BATTAIANA       24059URGNANO                BSBANCA INTESA BANCA COMMERCIALE ITALIANA SPA       "
    "\n 500000006Fatt. 2 del 31/01/23                                                                      03821260985         "
    "\n 5100000060000000002Dama Srl                                                                                            "
    "\n 700000006                                                                                          000                 "
    "\n 140000007            300424300000000000115290-0569654900000003759X480693303410                 4             578      E"
    "\n 200000007Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                "
    "\n 300000007CORONET SPA                                                 01823610157                                       "
    "\n 400000007VIA UBERTO VISCONTI DI MODRONE20122MILANO                 MI                                                  "
    "\n 500000007Fatt. 172 del 31/03/24                                                                    03821260985         "
    "\n 5100000070000000172Dama Srl                                                                                            "
    "\n 700000007                                                                                          000                 "
    "\n EF     05696240424RB-IX-P-151255            00000070000000006610620000000000000000000051                        E      "
)


# Read
# -----------------------

def _read(record):
    """ Detect the correct template and read the fields of a record """
    template_map = {
        'IB': _template_ib,
        'EF': _template_ef,
        '14': _template_14,
        '20': _template_20,
        '30': _template_30,
        '40': _template_40,
        '50': _template_50,
        '51': _template_51,
        '70': _template_70,
    }
    assert (len(record) == 120)
    template_type = record[1:3]
    template = template_map.get(template_type)
    assert template
    return {
        'record_type': template_type,
        **_read_from_template(record, template()),
    }


def _transform(records):
    """ Group sections, separate header and footer """
    result = {'sections': []}
    for record in records:
        record_type = record['record_type']
        match record_type:
            case 'IB':
                result['header'] = record
            case 'EF':
                result['footer'] = record
            case _:
                section_no = record.pop('section_number')
                sections = result['sections']
                while len(sections) < section_no:
                    sections.append([])
                sections[section_no - 1].append(record)
    return result


# Write
# -------------------

def _get_fstring(item):
    """ Get format string from template """
    if isinstance(item, tuple):
        match item:
            case key, 'date':
                fmt = '%d%m%y'
            case key, str() as fmt, *_:
                pass
        return f'{{{key}:{fmt}}}'
    else:
        return item


def _trim_value(value, item):
    """ Trim a value for output """
    trim = False
    if isinstance(item, tuple):
        match item:
            case _, _, int() as trim:
                pass
    if trim:
        value = value[:trim]
    return value


def _add_default_values(vals, line_template):
    """ Some records are just fixed, we rely on them as defaults.
        Unspecified values will be put as blanks.
    """
    vals = {
        'currency': 'E',
        'today': fields.Date.today(),
        **vals,
    }
    for item in line_template:
        match item:
            case key, *_:
                if key not in vals:
                    vals[key] = ''
    return vals


def _format_record(vals, line_template):
    """ Return a formatted record, given:
            a dictionary of vals
            a line_tempate list of description of fields
    """
    vals = _add_default_values(vals, line_template)
    fstrings = (_get_fstring(item).format(**vals) for item in line_template)
    record = "".join(starmap(_trim_value, zip(fstrings, line_template)))
    assert len(record) == 120, f"{record!a} is not 120 chars long"
    return record


def _read_from_template(record, line_template):
    """ Reads a record given the related template """

    def _slice(record, start, token_length):
        end = start + token_length
        return end, record[start:end].strip()

    def reader(record, line_template):
        i = 0
        for field in line_template:
            match field:
                case str() as fixed:
                    i += len(fixed)
                    continue
                case (str() as name, 'date'):
                    i, token = _slice(record, i, 6)
                    value = token and datetime.strptime(token, '%d%m%y').date()
                case tuple():
                    args = dict(enumerate(field))
                    name = args.get(0)
                    fmt = args.get(1)
                    token_length = args.get(2)
                    fmt_func = args.get(3)
                    i, token = _slice(record, i, token_length)
                    if fmt and token and '>0' in fmt:
                        value = int(token)
                    else:
                        value = token
                    if fmt_func:
                        value = fmt_func(value)
            if value or not isinstance(value, str):
                yield name, value
        assert i == 120
    return dict(reader(record, line_template))


# Templates
# -------------------

def _template_ib():
    """ Header record """
    return (
        ' ',                                   # filler
        'IB',                                  # record type
        ('creditor_sia_code', '>05', 5),
        ('creditor_abi', '>05', 5),
        ('today', 'date'),
        ('support_name', '<20', 20),           # must be unique per date, creditor, receiver
        ('creditor_note', '<6', 6),
        f'{" ":<59}',                          # filler
        ('flow_kind', '1', 1),                 # 1 if ecommerce
        ('flow_specifier', '1', 1),            # fixed to '$' only if flow_kind is present
        ('gateway_bank_abi', '>05', 5),        # only if flow_kind is present
        '  ',                                  # filler
        ('currency', '1', 1),                  # Currency, Euros fixed
        ' ',                                   # filler
        '     ',                               # reserved
    )


def _template_ef():
    """ Footer record """
    return (
        ' ',                                   # filler
        'EF',                                  # record type
        ('creditor_sia_code', '>05', 5),
        ('creditor_abi', '>05', 5),
        ('today', 'date'),
        ('support_name', '<20', 20),           # must be unique per date, creditor, receiver
        ('creditor_note', '<6', 6),
        ('n_sections', '>07', 7),
        ('negative_total', '>015', 15, lambda x: x / 100),
        ('positive_total', '>015', 15, lambda x: x / 100),
        ('n_records', '>07', 7),
        f'{" ":<24}',                          # filler
        ('currency', '1', 1),                  # Currency, Euros fixed
        '      ',                              # reserved
    )


def _template_14():
    """ Disposition record """
    return (
        ' ',                                   # filler
        '14',                                  # record type
        ('section_number', '>07', 7),
        f'{" ":<12}',                          # filler
        ('payment_date', 'date'),
        '30000',                               # reason, fixed
        ('amount', '>013', 13, lambda x: x / 100),
        '-',                                   # sign, fixed
        ('creditor_abi', '>05', 5),
        ('creditor_cab', '>05', 5),
        ('creditor_ccn', '<12', 12),
        ('debitor_abi', '>05', 5),
        ('debitor_cab', '>05', 5),
        f'{" ":<12}',                          # filler
        ('creditor_sia_code', '>05', 5),
        '4',                                   # code type, fixed
        ('debitor_code', '>016', 16),
        ('debitor_type', '1', 1),
        '     ',                               # filler
        ('currency', '1', 1),
    )


def _template_20():
    """ Creditor description record """
    return (
        ' ',                                   # filler
        '20',                                  # record type
        ('section_number', '>07', 7),          # same as record 14
        ('segment_1', "<24", 24),
        ('segment_2', "<24", 24),
        ('segment_3', "<24", 24),
        ('segment_4', "<24", 24),
        f'{" ":<14}',                          # filler
    )


def _template_30():
    """ Debitor description record """
    return (
        ' ',                                   # filler
        '30',                                  # record type
        ('section_number', '>07', 7),          # same as record 14
        ('segment_1', "<30", 30),
        ('segment_2', "<30", 30),
        ('debitor_tax_code', "<16", 16),       # Codice Fiscale
        f'{" ":<34}',                          # filler
    )


def _template_40():
    """ Debitor address record """
    return (
        ' ',                                   # filler
        '40',                                  # record type
        ('section_number', '>07', 7),          # same as record 14
        ('debitor_address', '<30', 30),
        ('debitor_zip', '<5', 5),
        ('debitor_city_and_state', '<25', 25),
        ('debitor_bank_name', '<50', 50),
    )


def _template_50():
    """ Debitor address record """
    return (
        ' ',                                   # filler
        '50',                                  # record type
        ('section_number', '>07', 7),          # same as record 14
        ('segment_1', "<40", 40),
        ('segment_2', "<40", 40),
        f'{" ":<10}',                          # filler
        ('creditor_tax_code', "<16", 16),      # Creditor's tax code (16 characters)
        '    ',
    )


def _template_51():
    """ Creditor information record """
    return (
        ' ',                                   # filler
        '51',                                  # record type
        ('section_number', '>07', 7),          # same as record 14
        ('receipt_number', '>010', 10),        # assigned by the creditor
        ('creditor_name', '<20', 20),          # in abbreviated form
        ('tax_office_state_name', '<15', 15),  # state name
        ('authorization_number', '<10', 10),
        ('authorization_date', 'date'),
        f'{" ":<49}',                          # filler
    )


def _template_70():
    """ Summary record """
    return (
        ' ',                                   # filler
        '70',                                  # record type
        ('section_number', '>07', 7),          # same as record 14
        f'{" ":<78}',                          # filler
        ('circuit_indicators', '<12', 12),
        ('control_keys', '<20', 20),
    )
