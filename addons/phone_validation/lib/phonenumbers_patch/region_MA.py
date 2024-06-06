"""Auto-generated file, do not edit by hand. MA metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_MA = PhoneMetadata(id='MA', country_code=212, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='[5-8]\\d{8}', possible_length=(9,)),
    fixed_line=PhoneNumberDesc(national_number_pattern='5(?:2(?:[0-25-79]\\d|3[1-578]|4[02-46-8]|8[0235-7])|3(?:[0-47]\\d|5[02-9]|6[02-8]|8[014-9]|9[3-9])|(?:4[067]|5[03])\\d)\\d{5}', example_number='520123456', possible_length=(9,)),
    mobile=PhoneNumberDesc(national_number_pattern='(?:6(?:[0-79]\\d|8[0-247-9])|7(?:[0167]\\d|2[0-4]|5[01]|8[0-3]))\\d{6}', example_number='650123456', possible_length=(9,)),
    toll_free=PhoneNumberDesc(national_number_pattern='80[0-7]\\d{6}', example_number='801234567', possible_length=(9,)),
    premium_rate=PhoneNumberDesc(national_number_pattern='89\\d{7}', example_number='891234567', possible_length=(9,)),
    voip=PhoneNumberDesc(national_number_pattern='(?:592(?:4[0-2]|93)|80[89]\\d\\d)\\d{4}', example_number='592401234', possible_length=(9,)),
    national_prefix='0',
    national_prefix_for_parsing='0',
    number_format=[NumberFormat(pattern='(\\d{3})(\\d{2})(\\d{2})(\\d{2})', format='\\1 \\2 \\3 \\4', leading_digits_pattern=['5[45]'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{4})(\\d{5})', format='\\1-\\2', leading_digits_pattern=['5(?:2[2-46-9]|3[3-9]|9)|8(?:0[89]|92)'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{2})(\\d{7})', format='\\1-\\2', leading_digits_pattern=['8'], national_prefix_formatting_rule='0\\1'),
        NumberFormat(pattern='(\\d{3})(\\d{6})', format='\\1-\\2', leading_digits_pattern=['[5-7]'], national_prefix_formatting_rule='0\\1')],
    main_country_for_code=True,
    mobile_number_portable_region=True)
