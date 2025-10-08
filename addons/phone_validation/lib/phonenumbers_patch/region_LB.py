"""Auto-generated file, do not edit by hand. LB metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_LB = PhoneMetadata(id='LB', country_code=961, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='[27-9]\\d{7}|[13-9]\\d{6}', possible_length=(7, 8)),
    fixed_line=PhoneNumberDesc(national_number_pattern='7(?:62|8[0-6]|9[04-9])\\d{4}|(?:[14-69]\\d|2(?:[14-69]\\d|[78][1-9])|7[2-57]|8[02-9])\\d{5}', example_number='1123456', possible_length=(7, 8)),
    mobile=PhoneNumberDesc(national_number_pattern='(?:(?:3|81)\\d|7(?:[01]\\d|6[013-9]|8[7-9]|9[1-3]))\\d{5}', example_number='71123456', possible_length=(7, 8)),
    premium_rate=PhoneNumberDesc(national_number_pattern='9[01]\\d{6}', example_number='90123456', possible_length=(8,)),
    shared_cost=PhoneNumberDesc(national_number_pattern='80\\d{6}', example_number='80123456', possible_length=(8,)),
    national_prefix='0',
    national_prefix_for_parsing='0',
    number_format=[NumberFormat(pattern='(\\d)(\\d{3})(\\d{3})', format='\\1 \\2 \\3', leading_digits_pattern=['[13-69]|7(?:[2-57]|62|8[0-6]|9[04-9])|8[02-9]'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{2})(\\d{3})(\\d{3})', format='\\1 \\2 \\3', leading_digits_pattern=['[27-9]'])])
