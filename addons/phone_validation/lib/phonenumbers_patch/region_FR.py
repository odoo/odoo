"""Auto-generated file, do not edit by hand. FR metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_FR = PhoneMetadata(id='FR', country_code=33, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='[1-9]\\d{8}', possible_length=(9,)),
    fixed_line=PhoneNumberDesc(national_number_pattern='(?:26[013-9]|59[1-35-9])\\d{6}|(?:[13]\\d|2[0-57-9]|4[1-9]|5[0-8])\\d{7}', example_number='123456789', possible_length=(9,)),
    mobile=PhoneNumberDesc(national_number_pattern='(?:[67](?:[0-24-8]\\d|3[0-8]|9[589])|7[3-9]\\d)\\d{6}', example_number='612345678', possible_length=(9,)),
    toll_free=PhoneNumberDesc(national_number_pattern='80[0-5]\\d{6}', example_number='801234567', possible_length=(9,)),
    premium_rate=PhoneNumberDesc(national_number_pattern='836(?:0[0-36-9]|[1-9]\\d)\\d{4}|8(?:1[2-9]|2[2-47-9]|3[0-57-9]|[569]\\d|8[0-35-9])\\d{6}', example_number='891123456', possible_length=(9,)),
    shared_cost=PhoneNumberDesc(national_number_pattern='8(?:1[01]|2[0156]|4[02]|84)\\d{6}', example_number='884012345', possible_length=(9,)),
    voip=PhoneNumberDesc(national_number_pattern='9\\d{8}', example_number='912345678', possible_length=(9,)),
    uan=PhoneNumberDesc(national_number_pattern='80[6-9]\\d{6}', example_number='806123456', possible_length=(9,)),
    national_prefix='0',
    national_prefix_for_parsing='0',
    number_format=[NumberFormat(pattern='(\\d{4})', format='\\1', leading_digits_pattern=['10']),
        NumberFormat(pattern='(\\d{3})(\\d{3})', format='\\1 \\2', leading_digits_pattern=['1']),
        NumberFormat(pattern='(\\d{3})(\\d{2})(\\d{2})(\\d{2})', format='\\1 \\2 \\3 \\4', leading_digits_pattern=['8'], national_prefix_formatting_rule='0 \\1'),
        NumberFormat(pattern='(\\d)(\\d{2})(\\d{2})(\\d{2})(\\d{2})', format='\\1 \\2 \\3 \\4 \\5', leading_digits_pattern=['[1-79]'], national_prefix_formatting_rule='0\\1')],
    intl_number_format=[NumberFormat(pattern='(\\d{3})(\\d{2})(\\d{2})(\\d{2})', format='\\1 \\2 \\3 \\4', leading_digits_pattern=['8']),
        NumberFormat(pattern='(\\d)(\\d{2})(\\d{2})(\\d{2})(\\d{2})', format='\\1 \\2 \\3 \\4 \\5', leading_digits_pattern=['[1-79]'])],
    mobile_number_portable_region=True)
