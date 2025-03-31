"""Auto-generated file, do not edit by hand. PA metadata"""
from ..phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata

PHONE_METADATA_PA = PhoneMetadata(id='PA', country_code=507, international_prefix='00',
    general_desc=PhoneNumberDesc(national_number_pattern='(?:00800|8\\d{3})\\d{6}|[68]\\d{7}|[1-57-9]\\d{6}', possible_length=(7, 8, 10, 11)),
    fixed_line=PhoneNumberDesc(national_number_pattern='(?:1(?:0\\d|1[479]|2[37]|3[0137]|4[17]|5[05]|6[58]|7[0167]|8[258]|9[1389])|2(?:[0235-79]\\d|1[0-7]|4[013-9]|8[02-9])|3(?:[089]\\d|1[0-7]|2[0-5]|33|4[0-79]|5[05]|6[068]|7[0-8])|4(?:00|3[0-579]|4\\d|7[0-57-9])|5(?:[01]\\d|2[0-7]|[56]0|79)|7(?:0[09]|2[0-26-8]|3[03]|4[04]|5[05-9]|6[056]|7[0-24-9]|8[6-9]|90)|8(?:09|2[89]|3\\d|4[0-24-689]|5[014]|8[02])|9(?:0[5-9]|1[0135-8]|2[036-9]|3[35-79]|40|5[0457-9]|6[05-9]|7[04-9]|8[35-8]|9\\d))\\d{4}', example_number='2001234', possible_length=(7,)),
    mobile=PhoneNumberDesc(national_number_pattern='(?:1[16]1|21[89]|6\\d{3}|8(?:1[01]|7[23]))\\d{4}', example_number='61234567', possible_length=(7, 8)),
    toll_free=PhoneNumberDesc(national_number_pattern='800\\d{4,5}|(?:00800|800\\d)\\d{6}', example_number='8001234', possible_length=(7, 8, 10, 11)),
    premium_rate=PhoneNumberDesc(national_number_pattern='(?:8(?:22|55|60|7[78]|86)|9(?:00|81))\\d{4}', example_number='8601234', possible_length=(7,)),
    number_format=[NumberFormat(pattern='(\\d{3})(\\d{4})', format='\\1-\\2', leading_digits_pattern=['[1-57-9]']),
        NumberFormat(pattern='(\\d{4})(\\d{4})', format='\\1-\\2', leading_digits_pattern=['[68]']),
        NumberFormat(pattern='(\\d{3})(\\d{3})(\\d{4})', format='\\1 \\2 \\3', leading_digits_pattern=['8'])],
    mobile_number_portable_region=True)
