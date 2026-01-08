# coding: utf-8

"""
Encoding DER to PEM and decoding PEM to DER. Exports the following items:

 - armor()
 - detect()
 - unarmor()

"""

from __future__ import unicode_literals, division, absolute_import, print_function

import base64
import re
import sys

from ._errors import unwrap
from ._types import type_name as _type_name, str_cls, byte_cls

if sys.version_info < (3,):
    from cStringIO import StringIO as BytesIO
else:
    from io import BytesIO


def detect(byte_string):
    """
    Detect if a byte string seems to contain a PEM-encoded block

    :param byte_string:
        A byte string to look through

    :return:
        A boolean, indicating if a PEM-encoded block is contained in the byte
        string
    """

    if not isinstance(byte_string, byte_cls):
        raise TypeError(unwrap(
            '''
            byte_string must be a byte string, not %s
            ''',
            _type_name(byte_string)
        ))

    return byte_string.find(b'-----BEGIN') != -1 or byte_string.find(b'---- BEGIN') != -1


def armor(type_name, der_bytes, headers=None):
    """
    Armors a DER-encoded byte string in PEM

    :param type_name:
        A unicode string that will be capitalized and placed in the header
        and footer of the block. E.g. "CERTIFICATE", "PRIVATE KEY", etc. This
        will appear as "-----BEGIN CERTIFICATE-----" and
        "-----END CERTIFICATE-----".

    :param der_bytes:
        A byte string to be armored

    :param headers:
        An OrderedDict of the header lines to write after the BEGIN line

    :return:
        A byte string of the PEM block
    """

    if not isinstance(der_bytes, byte_cls):
        raise TypeError(unwrap(
            '''
            der_bytes must be a byte string, not %s
            ''' % _type_name(der_bytes)
        ))

    if not isinstance(type_name, str_cls):
        raise TypeError(unwrap(
            '''
            type_name must be a unicode string, not %s
            ''',
            _type_name(type_name)
        ))

    type_name = type_name.upper().encode('ascii')

    output = BytesIO()
    output.write(b'-----BEGIN ')
    output.write(type_name)
    output.write(b'-----\n')
    if headers:
        for key in headers:
            output.write(key.encode('ascii'))
            output.write(b': ')
            output.write(headers[key].encode('ascii'))
            output.write(b'\n')
        output.write(b'\n')
    b64_bytes = base64.b64encode(der_bytes)
    b64_len = len(b64_bytes)
    i = 0
    while i < b64_len:
        output.write(b64_bytes[i:i + 64])
        output.write(b'\n')
        i += 64
    output.write(b'-----END ')
    output.write(type_name)
    output.write(b'-----\n')

    return output.getvalue()


def _unarmor(pem_bytes):
    """
    Convert a PEM-encoded byte string into one or more DER-encoded byte strings

    :param pem_bytes:
        A byte string of the PEM-encoded data

    :raises:
        ValueError - when the pem_bytes do not appear to be PEM-encoded bytes

    :return:
        A generator of 3-element tuples in the format: (object_type, headers,
        der_bytes). The object_type is a unicode string of what is between
        "-----BEGIN " and "-----". Examples include: "CERTIFICATE",
        "PUBLIC KEY", "PRIVATE KEY". The headers is a dict containing any lines
        in the form "Name: Value" that are right after the begin line.
    """

    if not isinstance(pem_bytes, byte_cls):
        raise TypeError(unwrap(
            '''
            pem_bytes must be a byte string, not %s
            ''',
            _type_name(pem_bytes)
        ))

    # Valid states include: "trash", "headers", "body"
    state = 'trash'
    headers = {}
    base64_data = b''
    object_type = None

    found_start = False
    found_end = False

    for line in pem_bytes.splitlines(False):
        if line == b'':
            continue

        if state == "trash":
            # Look for a starting line since some CA cert bundle show the cert
            # into in a parsed format above each PEM block
            type_name_match = re.match(b'^(?:---- |-----)BEGIN ([A-Z0-9 ]+)(?: ----|-----)', line)
            if not type_name_match:
                continue
            object_type = type_name_match.group(1).decode('ascii')

            found_start = True
            state = 'headers'
            continue

        if state == 'headers':
            if line.find(b':') == -1:
                state = 'body'
            else:
                decoded_line = line.decode('ascii')
                name, value = decoded_line.split(':', 1)
                headers[name] = value.strip()
                continue

        if state == 'body':
            if line[0:5] in (b'-----', b'---- '):
                der_bytes = base64.b64decode(base64_data)

                yield (object_type, headers, der_bytes)

                state = 'trash'
                headers = {}
                base64_data = b''
                object_type = None
                found_end = True
                continue

            base64_data += line

    if not found_start or not found_end:
        raise ValueError(unwrap(
            '''
            pem_bytes does not appear to contain PEM-encoded data - no
            BEGIN/END combination found
            '''
        ))


def unarmor(pem_bytes, multiple=False):
    """
    Convert a PEM-encoded byte string into a DER-encoded byte string

    :param pem_bytes:
        A byte string of the PEM-encoded data

    :param multiple:
        If True, function will return a generator

    :raises:
        ValueError - when the pem_bytes do not appear to be PEM-encoded bytes

    :return:
        A 3-element tuple (object_name, headers, der_bytes). The object_name is
        a unicode string of what is between "-----BEGIN " and "-----". Examples
        include: "CERTIFICATE", "PUBLIC KEY", "PRIVATE KEY". The headers is a
        dict containing any lines in the form "Name: Value" that are right
        after the begin line.
    """

    generator = _unarmor(pem_bytes)

    if not multiple:
        return next(generator)

    return generator
