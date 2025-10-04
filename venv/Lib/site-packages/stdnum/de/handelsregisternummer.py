# handelsregisternummer.py - functions for handling German company registry id
# coding: utf-8
#
# Copyright (C) 2015 Holvi Payment Services Oy
# Copyright (C) 2018-2019 Arthur de Jong
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

"""Handelsregisternummer (German company register number).

The number consists of the court where the company has registered, the type
of register and the registration number.

The type of the register is either HRA or HRB where the letter "B" stands for
HR section B, where limited liability companies and corporations are entered
(GmbH's and AG's). There is also a section HRA for business partnerships
(OHG's, KG's etc.). In other words: businesses in section HRB are limited
liability companies, while businesses in HRA have personally liable partners.

More information:

* https://www.handelsregister.de/
* https://en.wikipedia.org/wiki/German_Trade_Register
* https://offeneregister.de/

>>> validate('Aachen HRA 11223')
'Aachen HRA 11223'
>>> validate('Frankfurt/Oder GnR 11223', company_form='e.G.')
'Frankfurt/Oder GnR 11223'
>>> validate('Aachen HRC 44123')
Traceback (most recent call last):
  ...
InvalidFormat: ...
>>> validate('Aachen HRA 44123', company_form='GmbH')
Traceback (most recent call last):
  ...
InvalidComponent: ...
"""

import re
import unicodedata

from stdnum.exceptions import *
from stdnum.util import clean, to_unicode


# The known courts that have a Handelsregister
GERMAN_COURTS = (
    'Aachen',
    'Altenburg',
    'Amberg',
    'Ansbach',
    'Apolda',
    'Arnsberg',
    'Arnstadt Zweigstelle Ilmenau',
    'Arnstadt',
    'Aschaffenburg',
    'Augsburg',
    'Aurich',
    'Bad Hersfeld',
    'Bad Homburg v.d.H.',
    'Bad Kreuznach',
    'Bad Oeynhausen',
    'Bad Salzungen',
    'Bamberg',
    'Bayreuth',
    'Berlin (Charlottenburg)',
    'Bielefeld',
    'Bochum',
    'Bonn',
    'Braunschweig',
    'Bremen',
    'Chemnitz',
    'Coburg',
    'Coesfeld',
    'Cottbus',
    'Darmstadt',
    'Deggendorf',
    'Dortmund',
    'Dresden',
    'Duisburg',
    'Düren',
    'Düsseldorf',
    'Eisenach',
    'Erfurt',
    'Eschwege',
    'Essen',
    'Flensburg',
    'Frankfurt am Main',
    'Frankfurt/Oder',
    'Freiburg',
    'Friedberg',
    'Fritzlar',
    'Fulda',
    'Fürth',
    'Gelsenkirchen',
    'Gera',
    'Gießen',
    'Gotha',
    'Greiz',
    'Göttingen',
    'Gütersloh',
    'Hagen',
    'Hamburg',
    'Hamm',
    'Hanau',
    'Hannover',
    'Heilbad Heiligenstadt',
    'Hildburghausen',
    'Hildesheim',
    'Hof',
    'Homburg',
    'Ingolstadt',
    'Iserlohn',
    'Jena',
    'Kaiserslautern',
    'Kassel',
    'Kempten (Allgäu)',
    'Kiel',
    'Kleve',
    'Koblenz',
    'Korbach',
    'Krefeld',
    'Köln',
    'Königstein',
    'Landau',
    'Landshut',
    'Langenfeld',
    'Lebach',
    'Leipzig',
    'Lemgo',
    'Limburg',
    'Ludwigshafen a.Rhein (Ludwigshafen)',
    'Lübeck',
    'Lüneburg',
    'Mainz',
    'Mannheim',
    'Marburg',
    'Meiningen',
    'Memmingen',
    'Merzig',
    'Montabaur',
    'Mönchengladbach',
    'Mühlhausen',
    'München',
    'Münster',
    'Neubrandenburg',
    'Neunkirchen',
    'Neuruppin',
    'Neuss',
    'Nordhausen',
    'Nürnberg',
    'Offenbach am Main',
    'Oldenburg (Oldenburg)',
    'Osnabrück',
    'Ottweiler',
    'Paderborn',
    'Passau',
    'Pinneberg',
    'Potsdam',
    'Pößneck Zweigstelle Bad Lobenstein',
    'Pößneck',
    'Recklinghausen',
    'Regensburg',
    'Rostock',
    'Rudolstadt Zweigstelle Saalfeld',
    'Rudolstadt',
    'Saarbrücken',
    'Saarlouis',
    'Schweinfurt',
    'Schwerin',
    'Siegburg',
    'Siegen',
    'Sondershausen',
    'Sonneberg',
    'St. Ingbert (St Ingbert)',
    'St. Wendel (St Wendel)',
    'Stadthagen',
    'Stadtroda',
    'Steinfurt',
    'Stendal',
    'Stralsund',
    'Straubing',
    'Stuttgart',
    'Suhl',
    'Sömmerda',
    'Tostedt',
    'Traunstein',
    'Ulm',
    'Völklingen',
    'Walsrode',
    'Weiden i. d. OPf.',
    'Weimar',
    'Wetzlar',
    'Wiesbaden',
    'Wittlich',
    'Wuppertal',
    'Würzburg',
    'Zweibrücken',
)


def _to_min(court):
    """Convert the court name for quick comparison without encoding issues."""
    return ''.join(
        x for x in unicodedata.normalize('NFD', to_unicode(court).lower())
        if x in 'abcdefghijklmnopqrstuvwxyz')


# Build a dictionary for lookup up courts
_courts = dict(
    (_to_min(court), court) for court in GERMAN_COURTS)
_courts.update(
    (_to_min(alias), court) for alias, court in (
        ('Allgäu', 'Kempten (Allgäu)'),
        ('Bad Homburg', 'Bad Homburg v.d.H.'),
        ('Berlin', 'Berlin (Charlottenburg)'),
        ('Charlottenburg', 'Berlin (Charlottenburg)'),
        ('Kaln', 'Köln'),  # for encoding issues
        ('Kempten', 'Kempten (Allgäu)'),
        ('Ludwigshafen am Rhein (Ludwigshafen)', 'Ludwigshafen a.Rhein (Ludwigshafen)'),
        ('Ludwigshafen am Rhein', 'Ludwigshafen a.Rhein (Ludwigshafen)'),
        ('Ludwigshafen', 'Ludwigshafen a.Rhein (Ludwigshafen)'),
        ('Oldenburg', 'Oldenburg (Oldenburg)'),
        ('St. Ingbert', 'St. Ingbert (St Ingbert)'),
        ('St. Wendel', 'St. Wendel (St Wendel)'),
        ('Weiden in der Oberpfalz', 'Weiden i. d. OPf.'),
        ('Weiden', 'Weiden i. d. OPf.'),
        ('Paderborn früher Höxter', 'Paderborn'),
    ))


# The known registry types
REGISTRY_TYPES = (
    'HRA',
    'HRB',
    'PR',
    'GnR',
    'VR',
)

COMPANY_FORM_REGISTRY_TYPES = {
    'e.K.': 'HRA',
    'e.V.': 'VR',
    'Verein': 'VR',
    'OHG': 'HRA',
    'KG': 'HRA',
    'KGaA': 'HRB',
    'Vor-GmbH': 'HRB',
    'GmbH': 'HRB',
    'UG': 'HRB',
    'UG i.G.': 'HRB',
    'AG': 'HRB',
    'e.G.': 'GnR',
    'PartG': 'PR',
}


# possible formats the number can be specified in
_court_re = r'(?P<court>.*)'
_registry_re = r'(?P<registry>%s)' % '|'.join(REGISTRY_TYPES)
_number_re = r'(?P<nr>[1-9][0-9]{0,5})(\s*(?P<x>[A-ZÖ]{1,3}))?'
_formats = [
    _registry_re + r'\s+' + _number_re + r',?\s+' + _court_re + '$',
    _court_re + r',?\s+' + _registry_re + r'\s+' + _number_re + '$',
]


def _split(number):
    """Split the number into a court, registry, register number and
    optionally qualifier."""
    number = clean(number).strip()
    for fmt in _formats:
        m = re.match(fmt, number, flags=re.I | re.U)
        if m:
            return m.group('court').strip(), m.group('registry'), m.group('nr'), m.group('x')
    raise InvalidFormat()


def compact(number):
    """Convert the number to the minimal representation. This strips the
    number of any valid separators and removes surrounding whitespace."""
    court, registry, number, qualifier = _split(number)
    return ' '.join(x for x in [court, registry, number, qualifier] if x)


def validate(number, company_form=None):
    """Check if the number is a valid company registry number. If a
    company_form (eg. GmbH or PartG) is given, the number is validated to
    have the correct registry type."""
    court, registry, number, qualifier = _split(number)
    court = _courts.get(_to_min(court))
    if not court:
        raise InvalidComponent()
    if not isinstance(court, type(number)):  # pragma: no cover (Python 2 code)
        court = court.decode('utf-8')
    if company_form and COMPANY_FORM_REGISTRY_TYPES.get(company_form) != registry:
        raise InvalidComponent()
    return ' '.join(x for x in [court, registry, number, qualifier] if x)


def is_valid(number):
    """Check if the number is a valid company registry number."""
    try:
        return bool(validate(number))
    except ValidationError:
        return False


# The base URL for performing lookups
_offeneregister_url = 'https://db.offeneregister.de/openregister-ef9e802.json'


def check_offeneregister(number, timeout=30):  # pragma: no cover (not part of normal test suite)
    """Retrieve registration information from the OffeneRegister.de web site.

    This basically returns the JSON response from the web service as a dict.
    It will contain something like the following::

        {
            'retrieved_at': '2018-06-24T12:34:53Z',
            'native_company_number': 'The number requested',
            'company_number': 'Compact company number',
            'registrar': 'Registar',
            'federal_state': 'State name',
            'registered_office': 'Office',
            'register_art': 'Register type',
            'register_nummer': 'Number'
            'name': 'The name of the organisation',
            'current_status': 'currently registered',
        }

    Will return None if the number is invalid or unknown.
    """
    # this function isn't automatically tested because it would require
    # network access for the tests and unnecessarily load the web service
    import requests
    court, registry, number, qualifier = _split(number)
    # First lookup the registrar code
    # (we could look up the number by registrar (court), registry and number
    # but it seems those queries are too slow)
    response = requests.get(
        _offeneregister_url,
        params={
            'sql': 'select company_number from company where registrar = :p0 limit 1',
            'p0': court},
        timeout=timeout)
    response.raise_for_status()
    try:
        registrar = response.json()['rows'][0][0].split('_')[0]
    except (KeyError, IndexError) as e:  # noqa: F841
        raise InvalidComponent()  # unknown registrar code
    # Lookup the number
    number = '%s_%s%s' % (registrar, registry, number)
    response = requests.get(
        _offeneregister_url,
        params={
            'sql': 'select * from company where company_number = :p0 limit 1',
            'p0': number},
        timeout=timeout)
    response.raise_for_status()
    try:
        json = response.json()
        return dict(zip(json['columns'], json['rows'][0]))
    except (KeyError, IndexError) as e:  # noqa: F841
        return  # number not found
