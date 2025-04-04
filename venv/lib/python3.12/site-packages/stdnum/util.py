# util.py - common utility functions
# coding: utf-8
#
# Copyright (C) 2012-2021 Arthur de Jong
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

"""Common utility functions for other stdnum modules.

This module is meant for internal use by stdnum modules and is not
guaranteed to remain stable and as such not part of the public API of
stdnum.
"""

import pkgutil
import pydoc
import re
import sys
import unicodedata
import warnings

from stdnum.exceptions import *


# Regular expression to match doctests in docstrings
_strip_doctest_re = re.compile(r'^>>> .*\Z', re.DOTALL | re.MULTILINE)


# Regular expression to match digits
_digits_re = re.compile(r'^[0-9]+$')


def _mk_char_map(mapping):
    """Transform a dictionary with comma separated uniode character names
    to tuples with unicode characters as key."""
    for key, value in mapping.items():
        for char in key.split(','):
            try:
                yield (unicodedata.lookup(char), value)
            except KeyError:  # pragma: no cover (does not happen on Python3)
                pass


# build mapping of Unicode characters to equivalent ASCII characters
_char_map = dict(_mk_char_map({
    'HYPHEN-MINUS,ARMENIAN HYPHEN,HEBREW PUNCTUATION MAQAF,HYPHEN,'
    'NON-BREAKING HYPHEN,FIGURE DASH,EN DASH,EM DASH,HORIZONTAL BAR,'
    'SMALL HYPHEN-MINUS,FULLWIDTH HYPHEN-MINUS,MONGOLIAN NIRUGU,OVERLINE,'
    'HYPHEN BULLET,MACRON,MODIFIER LETTER MINUS SIGN,FULLWIDTH MACRON,'
    'OGHAM SPACE MARK,SUPERSCRIPT MINUS,SUBSCRIPT MINUS,MINUS SIGN,'
    'HORIZONTAL LINE EXTENSION,HORIZONTAL SCAN LINE-1,HORIZONTAL SCAN LINE-3,'
    'HORIZONTAL SCAN LINE-7,HORIZONTAL SCAN LINE-9,STRAIGHTNESS':
        '-',
    'ASTERISK,ARABIC FIVE POINTED STAR,SYRIAC HARKLEAN ASTERISCUS,'
    'FLOWER PUNCTUATION MARK,VAI FULL STOP,SMALL ASTERISK,FULLWIDTH ASTERISK,'
    'ASTERISK OPERATOR,STAR OPERATOR,HEAVY ASTERISK,LOW ASTERISK,'
    'OPEN CENTRE ASTERISK,EIGHT SPOKED ASTERISK,SIXTEEN POINTED ASTERISK,'
    'TEARDROP-SPOKED ASTERISK,OPEN CENTRE TEARDROP-SPOKED ASTERISK,'
    'HEAVY TEARDROP-SPOKED ASTERISK,EIGHT TEARDROP-SPOKED PROPELLER ASTERISK,'
    'HEAVY EIGHT TEARDROP-SPOKED PROPELLER ASTERISK,'
    'ARABIC FIVE POINTED STAR':
        '*',
    'COMMA,ARABIC COMMA,SINGLE LOW-9 QUOTATION MARK,IDEOGRAPHIC COMMA,'
    'ARABIC DECIMAL SEPARATOR,ARABIC THOUSANDS SEPARATOR,PRIME,RAISED COMMA,'
    'PRESENTATION FORM FOR VERTICAL COMMA,SMALL COMMA,'
    'SMALL IDEOGRAPHIC COMMA,FULLWIDTH COMMA,CEDILLA':
        ',',
    'FULL STOP,MIDDLE DOT,GREEK ANO TELEIA,ARABIC FULL STOP,'
    'IDEOGRAPHIC FULL STOP,SYRIAC SUPRALINEAR FULL STOP,'
    'SYRIAC SUBLINEAR FULL STOP,SAMARITAN PUNCTUATION NEQUDAA,'
    'TIBETAN MARK INTERSYLLABIC TSHEG,TIBETAN MARK DELIMITER TSHEG BSTAR,'
    'RUNIC SINGLE PUNCTUATION,BULLET,ONE DOT LEADER,HYPHENATION POINT,'
    'WORD SEPARATOR MIDDLE DOT,RAISED DOT,KATAKANA MIDDLE DOT,'
    'SMALL FULL STOP,FULLWIDTH FULL STOP,HALFWIDTH KATAKANA MIDDLE DOT,'
    'AEGEAN WORD SEPARATOR DOT,PHOENICIAN WORD SEPARATOR,'
    'KHAROSHTHI PUNCTUATION DOT,DOT ABOVE,ARABIC SYMBOL DOT ABOVE,'
    'ARABIC SYMBOL DOT BELOW,BULLET OPERATOR,DOT OPERATOR':
        '.',
    'SOLIDUS,SAMARITAN PUNCTUATION ARKAANU,FULLWIDTH SOLIDUS,DIVISION SLASH,'
    'MATHEMATICAL RISING DIAGONAL,BIG SOLIDUS,FRACTION SLASH':
        '/',
    'COLON,ETHIOPIC WORDSPACE,RUNIC MULTIPLE PUNCTUATION,MONGOLIAN COLON,'
    'PRESENTATION FORM FOR VERTICAL COLON,FULLWIDTH COLON,'
    'PRESENTATION FORM FOR VERTICAL TWO DOT LEADER,SMALL COLON':
        ':',
    'SPACE,NO-BREAK SPACE,EN QUAD,EM QUAD,EN SPACE,EM SPACE,'
    'THREE-PER-EM SPACE,FOUR-PER-EM SPACE,SIX-PER-EM SPACE,FIGURE SPACE,'
    'PUNCTUATION SPACE,THIN SPACE,HAIR SPACE,NARROW NO-BREAK SPACE,'
    'MEDIUM MATHEMATICAL SPACE,IDEOGRAPHIC SPACE':
        ' ',
    'FULLWIDTH DIGIT ZERO,MATHEMATICAL BOLD DIGIT ZERO,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT ZERO,MATHEMATICAL SANS-SERIF DIGIT ZERO,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT ZERO,MATHEMATICAL MONOSPACE DIGIT ZERO':
        '0',
    'FULLWIDTH DIGIT ONE,MATHEMATICAL BOLD DIGIT ONE,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT ONE,MATHEMATICAL SANS-SERIF DIGIT ONE,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT ONE,MATHEMATICAL MONOSPACE DIGIT ONE':
        '1',
    'FULLWIDTH DIGIT TWO,MATHEMATICAL BOLD DIGIT TWO,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT TWO,MATHEMATICAL SANS-SERIF DIGIT TWO,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT TWO,MATHEMATICAL MONOSPACE DIGIT TWO':
        '2',
    'FULLWIDTH DIGIT THREE,MATHEMATICAL BOLD DIGIT THREE,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT THREE,MATHEMATICAL SANS-SERIF DIGIT THREE,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT THREE,MATHEMATICAL MONOSPACE DIGIT THREE':
        '3',
    'FULLWIDTH DIGIT FOUR,MATHEMATICAL BOLD DIGIT FOUR,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT FOUR,MATHEMATICAL SANS-SERIF DIGIT FOUR,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT FOUR,MATHEMATICAL MONOSPACE DIGIT FOUR':
        '4',
    'FULLWIDTH DIGIT FIVE,MATHEMATICAL BOLD DIGIT FIVE,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT FIVE,MATHEMATICAL SANS-SERIF DIGIT FIVE,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT FIVE,MATHEMATICAL MONOSPACE DIGIT FIVE':
        '5',
    'FULLWIDTH DIGIT SIX,MATHEMATICAL BOLD DIGIT SIX,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT SIX,MATHEMATICAL SANS-SERIF DIGIT SIX,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT SIX,MATHEMATICAL MONOSPACE DIGIT SIX':
        '6',
    'FULLWIDTH DIGIT SEVEN,MATHEMATICAL BOLD DIGIT SEVEN,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT SEVEN,MATHEMATICAL SANS-SERIF DIGIT SEVEN,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT SEVEN,MATHEMATICAL MONOSPACE DIGIT SEVEN':
        '7',
    'FULLWIDTH DIGIT EIGHT,MATHEMATICAL BOLD DIGIT EIGHT,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT EIGHT,MATHEMATICAL SANS-SERIF DIGIT EIGHT,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT EIGHT,MATHEMATICAL MONOSPACE DIGIT EIGHT':
        '8',
    'FULLWIDTH DIGIT NINE,MATHEMATICAL BOLD DIGIT NINE,'
    'MATHEMATICAL DOUBLE-STRUCK DIGIT NINE,MATHEMATICAL SANS-SERIF DIGIT NINE,'
    'MATHEMATICAL SANS-SERIF BOLD DIGIT NINE,MATHEMATICAL MONOSPACE DIGIT NINE':
        '9',
    'APOSTROPHE,GRAVE ACCENT,ACUTE ACCENT,MODIFIER LETTER RIGHT HALF RING,'
    'MODIFIER LETTER LEFT HALF RING,MODIFIER LETTER PRIME,'
    'MODIFIER LETTER TURNED COMMA,MODIFIER LETTER APOSTROPHE,'
    'MODIFIER LETTER VERTICAL LINE,COMBINING GRAVE ACCENT,'
    'COMBINING ACUTE ACCENT,COMBINING TURNED COMMA ABOVE,'
    'COMBINING COMMA ABOVE,ARMENIAN APOSTROPHE,'
    'SINGLE HIGH-REVERSED-9 QUOTATION MARK,LEFT SINGLE QUOTATION MARK,'
    'RIGHT SINGLE QUOTATION MARK':
        "'",
}))


def _clean_chars(number):
    """Replace various Unicode characters with their ASCII counterpart."""
    return ''.join(_char_map.get(x, x) for x in number)


def clean(number, deletechars=''):
    """Remove the specified characters from the supplied number.

    >>> clean('123-456:78 9', ' -:')
    '123456789'
    >>> clean('1–2—3―4')
    '1-2-3-4'
    """
    try:
        number = ''.join(x for x in number)
    except Exception:  # noqa: B902
        raise InvalidFormat()
    if sys.version < '3' and isinstance(number, str):  # pragma: no cover (Python 2 specific code)
        try:
            number = _clean_chars(number.decode()).encode()
        except UnicodeError:
            try:
                number = _clean_chars(number.decode('utf-8')).encode('utf-8')
            except UnicodeError:
                pass
    else:  # pragma: no cover (Python 3 specific code)
        number = _clean_chars(number)
    return ''.join(x for x in number if x not in deletechars)


def isdigits(number):
    """Check whether the provided string only consists of digits."""
    # This function is meant to replace str.isdigit() which will also return
    # True for all kind of unicode digits which is generally not what we want
    return bool(_digits_re.match(number))


def to_unicode(text):
    """Convert the specified text to a unicode string."""
    if not isinstance(text, type(u'')):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            return text.decode('iso-8859-15')
    return text


def get_number_modules(base='stdnum'):
    """Yield all the number validation modules under the specified module."""
    __import__(base)
    module = sys.modules[base]
    # we ignore deprecation warnings from transitional modules
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=DeprecationWarning, module=r'stdnum\..*')
        for _loader, name, _is_pkg in pkgutil.walk_packages(
                module.__path__, module.__name__ + '.'):
            __import__(name)
            module = sys.modules[name]
            if hasattr(module, 'validate') and module.__name__ == name:
                yield module


def get_module_name(module):
    """Return the short description of the number."""
    return pydoc.splitdoc(pydoc.getdoc(module))[0].strip('.')


def get_module_description(module):
    """Return a description of the number."""
    doc = pydoc.splitdoc(pydoc.getdoc(module))[1]
    # remove the doctests
    return _strip_doctest_re.sub('', doc).strip()


def get_cc_module(cc, name):
    """Find the country-specific named module."""
    cc = cc.lower()
    # add suffix for python reserved words
    if cc in ('in', 'is', 'if'):
        cc += '_'
    try:
        mod = __import__('stdnum.%s' % cc, globals(), locals(), [str(name)])
        return getattr(mod, name, None)
    except ImportError:
        return


# this is a cache of SOAP clients
_soap_clients = {}


def get_soap_client(wsdlurl, timeout=30):  # pragma: no cover (not part of normal test suite)
    """Get a SOAP client for performing requests. The client is cached. The
    timeout is in seconds."""
    # this function isn't automatically tested because the functions using
    # it are not automatically tested
    if (wsdlurl, timeout) not in _soap_clients:
        # try zeep first
        try:
            from zeep.transports import Transport
            transport = Transport(timeout=timeout)
            from zeep import CachingClient
            client = CachingClient(wsdlurl, transport=transport).service
        except ImportError:
            # fall back to non-caching zeep client
            try:
                from zeep import Client
                client = Client(wsdlurl, transport=transport).service
            except ImportError:
                # other implementations require passing the proxy config
                try:
                    from urllib import getproxies
                except ImportError:
                    from urllib.request import getproxies
                # fall back to suds
                try:
                    from suds.client import Client
                    client = Client(
                        wsdlurl, proxy=getproxies(), timeout=timeout).service
                except ImportError:
                    # use pysimplesoap as last resort
                    try:
                        from pysimplesoap.client import SoapClient
                        client = SoapClient(
                            wsdl=wsdlurl, proxy=getproxies(), timeout=timeout)
                    except ImportError:
                        raise ImportError(
                            'No SOAP library (such as zeep) found')
        _soap_clients[(wsdlurl, timeout)] = client
    return _soap_clients[(wsdlurl, timeout)]
