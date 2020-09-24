
from collections import namedtuple

Currency = namedtuple('Currency', ['iso_id', 'decimal'])

# ISO 4217 Data for currencies supported by sips
# NOTE: these are listed on the Atos Wordline SIPS POST documentation page
# at https://documentation.sips.worldline.com/en/WLSIPS.001-GD-Data-dictionary.html#Sips.001_DD_en-Value-currencyCode
# Yet with the simu environment, some of these currencies are *not* working
# I have no way to know if this is caused by the SIMU environment, or if it's
# the doc of SIPS that lists currencies that don't work, but since this list is
# restrictive, I'm gonna assume they are supported when using the right flow
# and payment methods, which may not work in SIMU...
# Since SIPS advises to use 'in production', well...
SIPS_SUPPORTED_CURRENCIES = {
    'ARS': Currency('032', 2),
    'AUD': Currency('036', 2),
    'BHD': Currency('048', 3),
    'KHR': Currency('116', 2),
    'CAD': Currency('124', 2),
    'LKR': Currency('144', 2),
    'CNY': Currency('156', 2),
    'HRK': Currency('191', 2),
    'CZK': Currency('203', 2),
    'DKK': Currency('208', 2),
    'HKD': Currency('344', 2),
    'HUF': Currency('348', 2),
    'ISK': Currency('352', 0),
    'INR': Currency('356', 2),
    'ILS': Currency('376', 2),
    'JPY': Currency('392', 0),
    'KRW': Currency('410', 0),
    'KWD': Currency('414', 3),
    'MYR': Currency('458', 2),
    'MUR': Currency('480', 2),
    'MXN': Currency('484', 2),
    'NPR': Currency('524', 2),
    'NZD': Currency('554', 2),
    'NOK': Currency('578', 2),
    'QAR': Currency('634', 2),
    'RUB': Currency('643', 2),
    'SAR': Currency('682', 2),
    'SGD': Currency('702', 2),
    'ZAR': Currency('710', 2),
    'SEK': Currency('752', 2),
    'CHF': Currency('756', 2),
    'THB': Currency('764', 2),
    'AED': Currency('784', 2),
    'TND': Currency('788', 3),
    'GBP': Currency('826', 2),
    'USD': Currency('840', 2),
    'TWD': Currency('901', 2),
    'RSD': Currency('941', 2),
    'RON': Currency('946', 2),
    'TRY': Currency('949', 2),
    'XOF': Currency('952', 0),
    'XPF': Currency('953', 0),
    'BGN': Currency('975', 2),
    'EUR': Currency('978', 2),
    'UAH': Currency('980', 2),
    'PLN': Currency('996', 2),
    'BRL': Currency('986', 2),
}
