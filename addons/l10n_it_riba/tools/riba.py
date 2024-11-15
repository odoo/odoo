from datetime import datetime
from itertools import starmap

from odoo import fields


example = """\
 IB     05696240424RB-IX-P-151255                                                                                E      
 140000001            300424300000000000073200-0569654900000003759X480839354850                 4               7      E
 200000001Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000001ALUVETRO SRL UNIPERSONALE                                   03450700988                                       
 400000001VIA LOMBARDIA, 4/6            25034ORZINUOVI              BSCRA DI BORGO SAN GIACOMO CREDITO COOPERATIVO SCRL 
 500000001Fatt. 176 del 31/03/24                                                                    03821260985         
 5100000010000000176Dama Srl                                                                                            
 700000001                                                                                          000                 
 140000002            300424300000000000122305-0569654900000003759X480873554300                 4             115      E
 200000002Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000002ARCHETTI OMAR                                               02717520981                                       
 400000002VIA PAPA GIOVANNI II, 7       25030COCCAGLIO              BSBCC DI POMPIANO E DELLA FRANCIACORTA SCRL         
 500000002Fatt. 201 del 31/03/24                                                                    03821260985         
 5100000020000000201Dama Srl                                                                                            
 700000002                                                                                          000                 
 140000003            300424300000000000061000-0569654900000003759X480503454390                 4             769      E
 200000003Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000003AZIENDA AGRICOLA FRATELLI MURATORI S.S.                     03535970176                                       
 400000003VIA VALLI N. 31               25030ADRO                   BS                                                  
 500000003Fatt. 185 del 31/03/24                                                                    03821260985         
 5100000030000000185Dama Srl                                                                                            
 700000003                                                                                          000                 
 140000004            300424300000000000104005-0569654900000003759X480200811510                 4             788      E
 200000004Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000004CALZATURIFICIO DEI COLLI SRL                                00157830209                                       
 400000004VIA XXIV GIUGNO N. 39         46040SOLFERINO              MNCREDITO ITALIANO SPA                              
 500000004Fatt. 210 del 31/03/24                                                                    03821260985         
 5100000040000000210Dama Srl                                                                                            
 700000004                                                                                          000                 
 140000005            300424300000000000049105-0569654900000003759X480306952790                 4             180      E
 200000005Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000005CASEIFICIO PALENI SRL                                       02708950163                                       
 400000005VIA S. LORENZO N. 2           24060CASAZZA                BGBANCA INTESA BANCA COMMERCIALE ITALIANA SPA       
 500000005Fatt. 208 del 31/03/24                                                                    03821260985         
 5100000050000000208Dama Srl                                                                                            
 700000005                                                                                          000                 
 140000006            310323300000000000136157-0569654900000003759X480306953701                 4             191      E
 200000006Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000006CONCERIA DI URGNANO SRL                                     10485380157                                       
 400000006VIA LOCALITA' BATTAIANA       24059URGNANO                BSBANCA INTESA BANCA COMMERCIALE ITALIANA SPA       
 500000006Fatt. 2 del 31/01/23                                                                      03821260985         
 5100000060000000002Dama Srl                                                                                            
 700000006                                                                                          000                 
 140000007            300424300000000000115290-0569654900000003759X480693303410                 4             578      E
 200000007Dama Srl                Via Mons. Zeno PiccinnelPalazzolo sull'Oglio               03821260985                
 300000007CORONET SPA                                                 01823610157                                       
 400000007VIA UBERTO VISCONTI DI MODRONE20122MILANO                 MI                                                  
 500000007Fatt. 172 del 31/03/24                                                                    03821260985         
 5100000070000000172Dama Srl                                                                                            
 700000007                                                                                          000                 
 EF     05696240424RB-IX-P-151255            00000070000000006610620000000000000000000051                        E      
"""


"""
Header:
    record_type              IB
    creditor_sia_code        False
    creditor_abi             05696
    today                    2024-04-24
    support_name             RB-IX-P-151255
    currency                 E
Section #0:
    14: ---
    record_type              14
    payment_date             2024-04-30
    amount                   732.0
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              08393
    debitor_cab              54850
    debitor_code             7
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                ALUVETRO SRL UNIPERSONALE
    debitor_tax_code         03450700988
    40: ---
    record_type              40
    debitor_address          VIA LOMBARDIA, 4/6
    debitor_zip              25034
    debitor_city             ORZINUOVI
    debitor_state            BS
    debitor_bank_name        CRA DI BORGO SAN GIACOMO CREDITO COOPERATIVO SCRL
    50: ---
    record_type              50
    segment_1                Fatt. 176 del 31/03/24
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           176
    creditor_name            Dama Srl
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Section #1:
    14: ---
    record_type              14
    payment_date             2024-04-30
    amount                   1223.05
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              08735
    debitor_cab              54300
    debitor_code             115
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                ARCHETTI OMAR
    debitor_tax_code         02717520981
    40: ---
    record_type              40
    debitor_address          VIA PAPA GIOVANNI II, 7
    debitor_zip              25030
    debitor_city             COCCAGLIO
    debitor_state            BS
    debitor_bank_name        BCC DI POMPIANO E DELLA FRANCIACORTA SCRL
    50: ---
    record_type              50
    segment_1                Fatt. 201 del 31/03/24
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           201
    creditor_name            Dama Srl
    authorization_name       False
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Section #2:
    14: ---
    record_type              14
    payment_date             2024-04-30
    amount                   610.0
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              05034
    debitor_cab              54390
    debitor_code             769
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                AZIENDA AGRICOLA FRATELLI MURA
    segment_2                TORI S.S.
    debitor_tax_code         03535970176
    40: ---
    record_type              40
    debitor_address          VIA VALLI N. 31
    debitor_zip              25030
    debitor_city             ADRO
    debitor_state            BS
    50: ---
    record_type              50
    segment_1                Fatt. 185 del 31/03/24
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           185
    creditor_name            Dama Srl
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Section #3:
    14: ---
    record_type              14
    payment_date             2024-04-30
    amount                   1040.05
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              02008
    debitor_cab              11510
    debitor_code             788
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                CALZATURIFICIO DEI COLLI SRL
    debitor_tax_code         00157830209
    40: ---
    record_type              40
    debitor_address          VIA XXIV GIUGNO N. 39
    debitor_zip              46040
    debitor_city             SOLFERINO
    debitor_state            MN
    debitor_bank_name        CREDITO ITALIANO SPA
    50: ---
    record_type              50
    segment_1                Fatt. 210 del 31/03/24
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           210
    creditor_name            Dama Srl
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Section #4:
    14: ---
    record_type              14
    payment_date             2024-04-30
    amount                   491.05
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              03069
    debitor_cab              52790
    debitor_code             180
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                CASEIFICIO PALENI SRL
    debitor_tax_code         02708950163
    40: ---
    record_type              40
    debitor_address          VIA S. LORENZO N. 2
    debitor_zip              24060
    debitor_city             CASAZZA
    debitor_state            BG
    debitor_bank_name        BANCA INTESA BANCA COMMERCIALE ITALIANA SPA
    50: ---
    record_type              50
    segment_1                Fatt. 208 del 31/03/24
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           208
    creditor_name            Dama Srl
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Section #5:
    14: ---
    record_type              14
    payment_date             2023-03-31
    amount                   1361.57
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              03069
    debitor_cab              53701
    debitor_code             191
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                CONCERIA DI URGNANO SRL
    debitor_tax_code         10485380157
    40: ---
    record_type              40
    debitor_address          VIA LOCALITA' BATTAIANA
    debitor_zip              24059
    debitor_city             URGNANO
    debitor_state            BS
    debitor_bank_name        BANCA INTESA BANCA COMMERCIALE ITALIANA SPA
    50: ---
    record_type              50
    segment_1                Fatt. 2 del 31/01/23
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           2
    creditor_name            Dama Srl
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Section #6:
    14: ---
    record_type              14
    payment_date             2024-04-30
    amount                   1152.9
    creditor_abi             05696
    creditor_cab             54900
    creditor_ccn             000003759X48
    debitor_abi              06933
    debitor_cab              03410
    debitor_code             578
    currency                 E
    20: ---
    record_type              20
    segment_1                Dama Srl
    segment_2                Via Mons. Zeno Piccinnel
    segment_3                Palazzolo sull'Oglio
    segment_4                03821260985
    30: ---
    record_type              30
    segment_1                CORONET SPA
    debitor_tax_code         01823610157
    40: ---
    record_type              40
    debitor_address          VIA UBERTO VISCONTI DI MODRONE
    debitor_zip              20122
    debitor_city             MILANO
    debitor_state            MI
    50: ---
    record_type              50
    segment_1                Fatt. 172 del 31/03/24
    creditor_tax_code        03821260985
    51: ---
    record_type              51
    receipt_number           172
    creditor_name            Dama Srl
    authorization_date       False
    70: ---
    record_type              70
    control_keys             000
Footer:
    record_type              EF
    creditor_abi             05696
    today                    2024-04-24
    support_name             RB-IX-P-151255
    n_sections               7
    negative_total           6610.62
    positive_total           False
    n_records                51
    currency                 E
"""

def _read_example():
    return file_import(example)


# Read
# -----------------------


class RibaValues:
    def __init__(self, header, sections, footer, check=True):
        self.header = header
        self.sections = sections
        self.footer = footer
        if check:
            self.check()

    def __str__(self):
        def fmt(k, v):
            return f"    {k:<25s}{v}"
        s = ["Header:"]
        for k, v in self.header.items():
            s.append(fmt(k,v))

        for i, section in enumerate(self.sections):
            s.append(f"Section #{i}:")
            for row in section:
                s.append(f"    {row['record_type']}: ---")
                for k, v in row.items():
                    s.append(fmt(k, v))

        s.append("Footer:")
        for k, v in self.footer.items():
            s.append(fmt(k, v))

        return "\n".join(s)

    def check(self):
        assert self._check_totals()
        assert self._check_sections()

    def _check_totals(self):
        def round2(x):
            return round(x, 2)
        amounts_sum = round2(sum(
            round2(row.get('amount', 0))
            for section in self.sections
            for row in section
        ))
        pos_total = (self.footer['positive_total'] or 0.0)
        neg_total = (self.footer['negative_total'] or 0.0)
        return amounts_sum == -(pos_total - neg_total)

    def _check_sections(self):
        return len(self.sections) == self.footer['n_sections']


def file_import(content):
    return _transform_read(_read(line) for line in content.splitlines())


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


def _transform_read(records):
    """ Group sections, separate header and footer """
    header, sections, footer = None, [], None
    for record in records:
        record_type = record['record_type']
        match record_type:
            case 'IB':
                header = record
            case 'EF':
                footer = record
            case _:
                section_no = record.pop('section_number')
                while len(sections) < section_no:
                    sections.append([])
                sections[section_no - 1].append(record)
    return RibaValues(header, sections, footer)


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
                case tuple():
                    args = dict(enumerate(field))
                    name = args.get(0)
                    token_length = args.get(2)
                    fmt_func = args.get(3)
                    i, token = _slice(record, i, token_length)
                    if callable(fmt_func):
                        value = fmt_func(token)
                    else:
                        value = token
            if value or not isinstance(value, str):
                yield name, value
        assert i == 120
    return dict(reader(record, line_template))


def _int(x):
    if x not in (False, None, ''):
        return int(x)
    return False


def _cent(x):
    if i := _int(x):
        return i / 100
    return False


def _date(x):
    return datetime.strptime(x, '%d%m%y').date() if x else False


# Write
# -------------------


def file_export(values):
    raise NotImplementedError()


def _get_fstring(item):
    """ Get format string from template """
    if isinstance(item, tuple):
        key, fmt, *_ = item
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


# Templates
# -------------------

def _template_ib():
    """ Header record """
    return (
        ' ',                                   # filler
        'IB',                                  # record type
        ('creditor_sia_code', '>05', 5, _int),
        ('creditor_abi', '>05', 5, str),
        ('today', '%d%m%y', 6, _date),
        ('support_name', '<20', 20),           # must be unique per date, creditor, receiver
        ('creditor_note', '<6', 6),
        f'{" ":<59}',                          # filler
        ('flow_kind', '1', 1),                 # 1 if ecommerce
        ('flow_specifier', '1', 1),            # fixed to '$' only if flow_kind is present
        ('gateway_bank_abi', '>05', 5, str),   # only if flow_kind is present
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
        ('creditor_sia_code', '>05', 5, str),
        ('creditor_abi', '>05', 5, str),
        ('today', '%d%m%y', 6, _date),
        ('support_name', '<20', 20),           # must be unique per date, creditor, receiver
        ('creditor_note', '<6', 6),
        ('n_sections', '>07', 7, _int),
        ('negative_total', '>015', 15, _cent),
        ('positive_total', '>015', 15, _cent),
        ('n_records', '>07', 7, _int),
        f'{" ":<24}',                          # filler
        ('currency', '1', 1),                  # Currency, Euros fixed
        '      ',                              # reserved
    )


def _template_14():
    """ Disposition record """
    return (
        ' ',                                   # filler
        '14',                                  # record type
        ('section_number', '>07', 7, _int),
        f'{" ":<12}',                          # filler
        ('payment_date', '%d%m%y', 6, _date),
        '30000',                               # reason, fixed
        ('amount', '>013', 13, _cent),
        '-',                                   # sign, fixed
        ('creditor_abi', '>05', 5, str),
        ('creditor_cab', '>05', 5, str),
        ('creditor_ccn', '<12', 12, str),
        ('debitor_abi', '>05', 5, str),
        ('debitor_cab', '>05', 5, str),
        f'{" ":<12}',                          # filler
        ('creditor_sia_code', '>05', 5, str),
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
        ('section_number', '>07', 7, _int),    # same as record 14
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
        ('section_number', '>07', 7, _int),    # same as record 14
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
        ('section_number', '>07', 7, _int),    # same as record 14
        ('debitor_address', '<30', 30),
        ('debitor_zip', '<5', 5),
        ('debitor_city', '<23', 23),
        ('debitor_state', '2', 2),
        ('debitor_bank_name', '<50', 50),
    )


def _template_50():
    """ Debitor address record """
    return (
        ' ',                                   # filler
        '50',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
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
        ('section_number', '>07', 7, _int),    # same as record 14
        ('receipt_number', '>010', 10, _int),  # assigned by the creditor
        ('creditor_name', '<20', 20),          # in abbreviated form
        ('tax_office_state_name', '<15', 15),  # state name
        ('authorization_number', '<10', 10),
        ('authorization_date', '%d%m%y', 6, _date),
        f'{" ":<49}',                          # filler
    )


def _template_70():
    """ Summary record """
    return (
        ' ',                                   # filler
        '70',                                  # record type
        ('section_number', '>07', 7, _int),    # same as record 14
        f'{" ":<78}',                          # filler
        ('circuit_indicators', '<12', 12),
        ('control_keys', '<20', 20),
    )
