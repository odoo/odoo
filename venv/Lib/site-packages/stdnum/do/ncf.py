# ncf.py - functions for handling Dominican Republic invoice numbers
# coding: utf-8
#
# Copyright (C) 2017-2018 Arthur de Jong
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA

# Development of this functionality was funded by iterativo | https://iterativo.do

"""NCF (Números de Comprobante Fiscal, Dominican Republic receipt number).

The NCF is used to number invoices and other documents for the purpose of tax
filing. The e-CF (Comprobante Fiscal Electrónico) is used together with a
digital certificate for the same purpose. The number is either 19, 11 or 13
(e-CF) digits long.

The 19 digit number starts wit a letter (A or P) to indicate that the number
was assigned by the taxpayer or the DGII, followed a 2-digit business unit
number, a 3-digit location number, a 3-digit mechanism identifier, a 2-digit
document type and a 8-digit serial number.

The 11 digit number always starts with a B followed a 2-digit document type
and a 7-digit serial number.

The 13 digit e-CF starts with an E followed a 2-digit document type and an
8-digit serial number.

More information:

 * https://www.dgii.gov.do/
 * https://dgii.gov.do/workshopProveedoresTI-eCE/Documents/Norma05-19.pdf
 * https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscales/Paginas/tiposComprobantes.aspx

>>> validate('E310000000005')  # format since 2019-04-08
'E310000000005'
>>> validate('B0100000005')  # format since 2018-05-01
'B0100000005'
>>> validate('A020010210100000005')  # format before 2018-05-01
'A020010210100000005'
>>> validate('Z0100000005')
Traceback (most recent call last):
    ...
InvalidFormat: ...
"""

from stdnum.exceptions import *
from stdnum.util import clean, isdigits


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    return clean(number, ' ').strip().upper()


# The following document types are known:
_ncf_document_types = (
    '01',  # invoices for fiscal declaration (or tax reporting)
    '02',  # invoices for final consumer
    '03',  # debit note
    '04',  # credit note (refunds)
    '11',  # informal supplier invoices (purchases)
    '12',  # single income invoices
    '13',  # minor expenses invoices (purchases)
    '14',  # invoices for special customers (tourists, free zones)
    '15',  # invoices for the government
    '16',  # invoices for export
    '17',  # invoices for payments abroad
)

_ecf_document_types = (
    '31',  # invoices for fiscal declaration (or tax reporting)
    '32',  # invoices for final consumer
    '33',  # debit note
    '34',  # credit note (refunds)
    '41',  # supplier invoices (purchases)
    '43',  # minor expenses invoices (purchases)
    '44',  # invoices for special customers (tourists, free zones)
    '45',  # invoices for the government
)


def validate(number):
    """Check if the number provided is a valid NCF."""
    number = compact(number)
    if len(number) == 13:
        if number[0] != 'E' or not isdigits(number[1:]):
            raise InvalidFormat()
        if number[1:3] not in _ecf_document_types:
            raise InvalidComponent()
    elif len(number) == 11:
        if number[0] != 'B' or not isdigits(number[1:]):
            raise InvalidFormat()
        if number[1:3] not in _ncf_document_types:
            raise InvalidComponent()
    elif len(number) == 19:
        if number[0] not in 'AP' or not isdigits(number[1:]):
            raise InvalidFormat()
        if number[9:11] not in _ncf_document_types:
            raise InvalidComponent()
    else:
        raise InvalidLength()
    return number


def is_valid(number):
    """Check if the number provided is a valid NCF."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


def _convert_result(result):  # pragma: no cover
    """Translate SOAP result entries into dictionaries."""
    translation = {
        'NOMBRE': 'name',
        'COMPROBANTE': 'proof',
        'ES_VALIDO': 'is_valid',
        'MENSAJE_VALIDACION': 'validation_message',
        'RNC': 'rnc',
        'NCF': 'ncf',
        u'RNC / Cédula': 'rnc',
        u'RNC/Cédula': 'rnc',
        u'Nombre / Razón Social': 'name',
        u'Nombre/Razón Social': 'name',
        'Estado': 'status',
        'Tipo de comprobante': 'type',
        u'Válido hasta': 'valid_until',
    }
    return dict(
        (translation.get(key, key), value)
        for key, value in result.items())


def check_dgii(rnc, ncf, timeout=30):  # pragma: no cover
    """Validate the RNC, NCF combination on using the DGII online web service.

    This uses the validation service run by the the Dirección General de
    Impuestos Internos, the Dominican Republic tax department to check
    whether the combination of RNC and NCF is valid. The timeout is in
    seconds.

    Returns a dict with the following structure::

        {
            'name': 'The registered name',
            'status': 'VIGENTE',
            'type': 'FACTURAS DE CREDITO FISCAL',
            'rnc': '123456789',
            'ncf': 'A020010210100000005',
            'validation_message': 'El NCF digitado es válido.',
        }

    Will return None if the number is invalid or unknown."""
    import lxml.html
    import requests
    from stdnum.do.rnc import compact as rnc_compact  # noqa: I003
    rnc = rnc_compact(rnc)
    ncf = compact(ncf)
    url = 'https://dgii.gov.do/app/WebApps/ConsultasWeb2/ConsultasWeb/consultas/ncf.aspx'
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (python-stdnum)',
    })
    # Get the page to pick up needed form parameters
    document = lxml.html.fromstring(
        session.get(url, timeout=timeout).text)
    validation = document.find('.//input[@name="__EVENTVALIDATION"]').get('value')
    viewstate = document.find('.//input[@name="__VIEWSTATE"]').get('value')
    data = {
        '__EVENTVALIDATION': validation,
        '__VIEWSTATE': viewstate,
        'ctl00$cphMain$btnConsultar': 'Buscar',
        'ctl00$cphMain$txtNCF': ncf,
        'ctl00$cphMain$txtRNC': rnc,
    }
    # Do the actual request
    document = lxml.html.fromstring(
        session.post(url, data=data, timeout=timeout).text)
    result = document.find('.//div[@id="cphMain_pResultado"]')
    if result is not None:
        data = {
            'validation_message': document.findtext('.//*[@id="cphMain_lblInformacion"]').strip(),
        }
        data.update(zip(
            [x.text.strip() for x in result.findall('.//th')],
            [x.text.strip() for x in result.findall('.//td/span')]))
        return _convert_result(data)
