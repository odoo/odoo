# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

from .version import __version__, __version_info__

__all__ = [
    '__version__',
    '__version_info__',
    'load_order',
]


def load_order():
    """
    Returns a list of the module and sub-module names for asn1crypto in
    dependency load order, for the sake of live reloading code

    :return:
        A list of unicode strings of module names, as they would appear in
        sys.modules, ordered by which module should be reloaded first
    """

    return [
        'asn1crypto._errors',
        'asn1crypto._int',
        'asn1crypto._ordereddict',
        'asn1crypto._teletex_codec',
        'asn1crypto._types',
        'asn1crypto._inet',
        'asn1crypto._iri',
        'asn1crypto.version',
        'asn1crypto.pem',
        'asn1crypto.util',
        'asn1crypto.parser',
        'asn1crypto.core',
        'asn1crypto.algos',
        'asn1crypto.keys',
        'asn1crypto.x509',
        'asn1crypto.crl',
        'asn1crypto.csr',
        'asn1crypto.ocsp',
        'asn1crypto.cms',
        'asn1crypto.pdf',
        'asn1crypto.pkcs12',
        'asn1crypto.tsp',
        'asn1crypto',
    ]
