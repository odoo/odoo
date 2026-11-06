"""Auto-generated file, do not edit by hand. SA metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_SA = PhoneMetadata(id='SA', country_code=966, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='(?:[15]\\d|800|92)\\d{7}', possible_length=(9, 10), possible_length_local_only=(7,)),
    fixed_line=PhoneNumberDesc(national_number_pattern='1(?:1\\d|2[24-8]|3[35-8]|4[3-68]|6[2-5]|7[235-7])\\d{6}', example_number='112345678', possible_length=(9,), possible_length_local_only=(7,)),
    mobile=PhoneNumberDesc(national_number_pattern='579[0-8]\\d{5}|5(?:[013-689]\\d|7[0-8])\\d{6}', example_number='512345678', possible_length=(9,)),
    toll_free=PhoneNumberDesc(national_number_pattern='800\\d{7}', example_number='8001234567', possible_length=(10,)),
    premium_rate=PhoneNumberDesc(national_number_pattern='925\\d{6}', example_number='925012345', possible_length=(9,)),
    shared_cost=PhoneNumberDesc(national_number_pattern='920\\d{6}', example_number='920012345', possible_length=(9,)),
    national_prefix='0',
    national_prefix_for_parsing='0',
    number_format=[NumberFormat(pattern='(\\d{4})(\\d{5})', format='\\1 \\2', leading_digits_pattern=['9']),
        NumberFormat(pattern='(\\d{2})(\\d{3})(\\d{4})', format='\\1 \\2 \\3', leading_digits_pattern=['1'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{2})(\\d{3})(\\d{4})', format='\\1 \\2 \\3', leading_digits_pattern=['5'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{4})', format='\\1 \\2 \\3', leading_digits_pattern=['8'])],
    mobile_number_portable_region=True)
