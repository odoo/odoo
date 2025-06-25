"""Auto-generated file, do not edit by hand. CI metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_CI = PhoneMetadata(id='CI', country_code=225, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='[02]\\d{9}', possible_length=(10,)),
    fixed_line=PhoneNumberDesc(national_number_pattern='2(?:[15]\\d{3}|7(?:2(?:0[23]|1[2357]|[23][45]|4[3-5])|3(?:06|1[69]|[2-6]7)))\\d{5}', example_number='2123456789', possible_length=(10,)),
    mobile=PhoneNumberDesc(national_number_pattern='0704[0-7]\\d{5}|0(?:[15]\\d\\d|7(?:0[0-37-9]|[4-9][7-9]))\\d{6}', example_number='0123456789', possible_length=(10,)),
    number_format=[NumberFormat(pattern='(\\d{2})(\\d{2})(\\d)(\\d{5})', format='\\1 \\2 \\3 \\4', leading_digits_pattern=['2']),
        NumberFormat(pattern='(\\d{2})(\\d{2})(\\d{2})(\\d{4})', format='\\1 \\2 \\3 \\4', leading_digits_pattern=['0'])])
