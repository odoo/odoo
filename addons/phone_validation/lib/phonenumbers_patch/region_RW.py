"""Auto-generated file, do not edit by hand. RW metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_RW = PhoneMetadata(id='RW', country_code=250, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='(?:06|[27]\\d\\d|[89]00)\\d{6}', possible_length=(8, 9)),
    fixed_line=PhoneNumberDesc(national_number_pattern='(?:06|2[23568]\\d)\\d{6}', example_number='250123456', possible_length=(8, 9)),
    mobile=PhoneNumberDesc(national_number_pattern='7[237-9]\\d{7}', example_number='720123456', possible_length=(9,)),
    toll_free=PhoneNumberDesc(national_number_pattern='800\\d{6}', example_number='800123456', possible_length=(9,)),
    premium_rate=PhoneNumberDesc(national_number_pattern='900\\d{6}', example_number='900123456', possible_length=(9,)),
    national_prefix='0',
    national_prefix_for_parsing='0',
    number_format=[NumberFormat(pattern='(\\d{2})(\\d{2})(\\d{2})(\\d{2})', format='\\1 \\2 \\3 \\4', leading_digits_pattern=['0']),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{3})', format='\\1 \\2 \\3', leading_digits_pattern=['2']),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{3})', format='\\1 \\2 \\3', leading_digits_pattern=['[7-9]'], national_prefix_formatting_rule='0\\1')])
