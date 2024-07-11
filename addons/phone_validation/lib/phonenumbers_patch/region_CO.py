"""Auto-generated file, do not edit by hand. CO metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_CO = PhoneMetadata(id='CO', country_code=57, international_prefix='00(?:4(?:[14]4|56)|[579])',
    general_desc=PhoneNumberDesc(national_number_pattern='(?:60\\d\\d|9101)\\d{6}|(?:1\\d|3)\\d{9}', possible_length=(10, 11), possible_length_local_only=(7,)),
    fixed_line=PhoneNumberDesc(national_number_pattern='601055(?:[0-4]\\d|50)\\d\\d|6010(?:[0-4]\\d|5[0-4])\\d{4}|60(?:[124-7][2-9]|8[1-9])\\d{6}', example_number='6012345678', possible_length=(10,), possible_length_local_only=(7,)),
    mobile=PhoneNumberDesc(national_number_pattern='333301[0-5]\\d{3}|3333(?:00|2[5-9]|[3-9]\\d)\\d{4}|(?:3(?:24[1-9]|3(?:00|3[0-24-9]))|9101)\\d{6}|3(?:0[0-5]|1\\d|2[0-3]|5[01]|70)\\d{7}', example_number='3211234567', possible_length=(10,)),
    toll_free=PhoneNumberDesc(national_number_pattern='1800\\d{7}', example_number='18001234567', possible_length=(11,)),
    premium_rate=PhoneNumberDesc(national_number_pattern='19(?:0[01]|4[78])\\d{7}', example_number='19001234567', possible_length=(11,)),
    national_prefix='0',
    national_prefix_for_parsing='0([3579]|4(?:[14]4|56))?',
    number_format=[NumberFormat(pattern='(\\d{3})(\\d{7})', format='\\1 \\2', leading_digits_pattern=['6'], national_prefix_formatting_rule='(\\1)', domestic_carrier_code_formatting_rule='0$CC \\1'),
        NumberFormat(pattern='(\\d{3})(\\d{7})', format='\\1 \\2', leading_digits_pattern=['3[0-357]|91'], domestic_carrier_code_formatting_rule='0$CC \\1'),
        NumberFormat(pattern='(\\d)(\\d{3})(\\d{7})', format='\\1-\\2-\\3', leading_digits_pattern=['1'], national_prefix_formatting_rule='0\\1')],
    intl_number_format=[NumberFormat(pattern='(\\d{3})(\\d{7})', format='\\1 \\2', leading_digits_pattern=['6']),
        NumberFormat(pattern='(\\d{3})(\\d{7})', format='\\1 \\2', leading_digits_pattern=['3[0-357]|91']),
        NumberFormat(pattern='(\\d)(\\d{3})(\\d{7})', format='\\1 \\2 \\3', leading_digits_pattern=['1'])],
    mobile_number_portable_region=True)
