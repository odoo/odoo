"""Auto-generated file, do not edit by hand. ZM metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_ZM = PhoneMetadata(id='ZM', country_code=260, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='800\\d{6}|(?:21|[579]\\d|63)\\d{7}', possible_length=(9,), possible_length_local_only=(6,)),
    fixed_line=PhoneNumberDesc(national_number_pattern='21[1-8]\\d{6}', example_number='211234567', possible_length=(9,), possible_length_local_only=(6,)),
    mobile=PhoneNumberDesc(national_number_pattern='(?:[59][5-8]|7[5-9])\\d{7}', example_number='955123456', possible_length=(9,)),
    toll_free=PhoneNumberDesc(national_number_pattern='800\\d{6}', example_number='800123456', possible_length=(9,)),
    voip=PhoneNumberDesc(national_number_pattern='63\\d{7}', example_number='630123456', possible_length=(9,)),
    national_prefix='0',
    national_prefix_for_parsing='0',
    number_format=[NumberFormat(pattern='(\\d{3})(\\d{3})', format='\\1 \\2', leading_digits_pattern=['[1-9]']),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{3})', format='\\1 \\2 \\3', leading_digits_pattern=['[28]'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{2})(\\d{7})', format='\\1 \\2', leading_digits_pattern=['[579]'], national_prefix_formatting_rule='0\\1')],
    intl_number_format=[NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{3})', format='\\1 \\2 \\3', leading_digits_pattern=['[28]']),
        NumberFormat(pattern='(\\d{2})(\\d{7})', format='\\1 \\2', leading_digits_pattern=['[579]'])])
