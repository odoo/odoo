# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=import-outside-toplevel

"""

    Monkeypatching is not a good practice, but it's in some cases necessary.
    This is especiallly true when relying on third party modules.
    Reasons may vary:

        - to adjust for compatibility between versions,
        - to fix a small detail without reworking the external module.

    In Odoo, there were several places in which monkeypatching is done.
    This module aims to put the monkeypatching all together and to make clear
    at a glance which external modules are subject to it, and how.

    All the monkeypatching will be done so that import <module> will already load
    the monkeypatched module. Modules will have a new <module>.__is_monkeypatched__
    attribute set to True. This will remove the need to import from odoo.tools.misc.<module>
    and also ensure that people not aware of the monkeypatching use the wrong version.

"""

import sys

def monkeypatch_OpenSSL():
    """
        OpenSSL v0.x.x uses OpenSSL.X509_get_notBefore and OpenSSL.X509_get_notAfter
        pyopenssl v19.0.0 uses those.
        OpenSSL v1.1.0a+ renamed them to OpenSSL.X509_getm_notBefore and OpenSSL.X509_getm_notAfter
        pyopenssl v20.0.0 adapted to those new ones.
        This monkeypatch prevents misalignments between versions.
    """
    import OpenSSL
    import ssl

    pyopenssl_version = tuple(int(x) for x in OpenSSL.__version__.split('.'))
    openssl_version = ssl.OPENSSL_VERSION_INFO[:3]

    lib = OpenSSL._util.lib
    if pyopenssl_version >= (20, 0, 0) and openssl_version < (1, 1, 0):
        lib.X509_getm_notBefore = lib.X509_get_notBefore
        lib.X509_getm_notAfter = lib.X509_get_notAfter
    elif pyopenssl_version >= (19, 0, 0) and openssl_version >= (1, 1, 0):
        lib.X509_get_notBefore = lib.X509_getm_notBefore
        lib.X509_get_notAfter = lib.X509_getm_notAfter

    return OpenSSL

def monkeypatch_PyPDF2():
    """
        1) Fix invalid numbers like 0.000000000000-5684342
           Because some PDF generators are building PDF streams with invalid numbers.

        Ref: https://docs.python.org/3/library/zlib.html#zlib.decompressobj
        2) ensure that zlib does not throw error -5 when decompressing
           because some pdf won't fit into allocated memory.
    """
    import zlib
    import PyPDF2

    class PatchedFloatObject(PyPDF2.generic.FloatObject):
        def __new__(cls, value="0", context=None):
            if isinstance(value, bytes) and value[0] != b'-' and b'-' in value:
                value = b'-' + b''.join(value.split(b'-', 1))
            elif isinstance(value, str) and value[0] != '-' and '-' in value:
                value = '-' + ''.join(value.split('-', 1))

            return super().__new__(cls, value, context)

    def _decompress(data):
        zobj = zlib.decompressobj()
        return zobj.decompress(data)

    PyPDF2.generic.FloatObject = PatchedFloatObject
    PyPDF2.filters.decompress = _decompress

    return PyPDF2

def monkeypatch_xlsx():
    """
        xlrd.xlsx supports defusedxml, defusedxml's etree interface is broken
        (missing ElementTree and thus ElementTree.iter) which causes a fallback to
        Element.getiterator(), triggering a warning before 3.9 and an error from 3.9.

        We have defusedxml installed because zeep has a hard dep on defused and
        doesn't want to drop it (mvantellingen/python-zeep#1014).

        Ignore the check and set the relevant flags directly using lxml as we have a
        hard dependency on it.
    """
    from xlrd import xlsx
    from lxml import etree

    xlsx.ET = etree
    xlsx.ET_has_iterparse = True
    xlsx.Element_has_iter = True

    return xlsx

def monkeypatch_xlsxwriter():
    """
        Add some sanitization to respect the excel sheet name restrictions
        as the sheet name is often translatable, can not control the input.
    """
    import re
    import xlsxwriter

    class PatchedXlsxWorkbook(xlsxwriter.Workbook):
        # TODO when xlsxwriter bump to 0.9.8, add worksheet_class=None parameter instead of kw
        def add_worksheet(self, sheetname=None, **kw):
            if sheetname:
                # invalid Excel character: []:*?/\
                sheetname = re.sub(r'[\[\]:*?/\\]', '', sheetname)
                # maximum size is 31 characters
                sheetname = sheetname[:31]
            return super(PatchedXlsxWorkbook, self).add_worksheet(sheetname, **kw)

    xlsxwriter.Workbook = PatchedXlsxWorkbook
    return xlsxwriter

def monkeypatch_xlwt():
    """
        Add some sanitization to respect the excel sheet name restrictions
        as the sheet name is often translatable, can not control the input.
    """
    import re
    import xlwt

    class PatchedWorkbook(xlwt.Workbook):
        def add_sheet(self, sheetname, cell_overwrite_ok=False):
            # invalid Excel character: []:*?/\
            sheetname = re.sub(r'[\[\]:*?/\\]', '', sheetname)
            # maximum size is 31 characters
            sheetname = sheetname[:31]
            return super(PatchedWorkbook, self).add_sheet(sheetname, cell_overwrite_ok=cell_overwrite_ok)

    xlwt.Workbook = PatchedWorkbook
    return xlwt

def monkeypatch_xmlrpc():
    """
        Fix invalid numbers like 0.000000000000-5684342
        Because some PDF generators are building PDF streams with invalid numbers.
    """

    import re
    from datetime import date, datetime
    from odoo.loglevels import ustr
    from odoo.tools.func import lazy
    from odoo.tools.misc import frozendict, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

    import xmlrpc
    import xmlrpc.client

    # ustr decodes as utf-8 or latin1 so we can search for the ASCII bytes
    # 	Char	   ::=   	#x9 | #xA | #xD | [#x20-#xD7FF]
    XML_INVALID = re.compile(b'[\x00-\x08\x0B\x0C\x0F-\x1F]')

    class OdooMarshaller(xmlrpc.client.Marshaller):
        dispatch = dict(xmlrpc.client.Marshaller.dispatch)

        def dump_frozen_dict(self, value, write):
            value = dict(value)
            self.dump_struct(value, write)
        dispatch[frozendict] = dump_frozen_dict

        # By default, in xmlrpc, bytes are converted to xmlrpclib.Binary object.
        # Historically, odoo is sending binary as base64 string.
        # In python 3, base64.b64{de,en}code() methods now works on bytes.
        # Convert them to str to have a consistent behavior between python 2 and python 3.
        def dump_bytes(self, value, write):
            # XML 1.0 disallows control characters, check for them immediately to
            # see if this is a "real" binary (rather than base64 or somesuch) and
            # blank it out, otherwise they get embedded in the output and break
            # client-side parsers
            if XML_INVALID.search(value):
                self.dump_unicode('', write)
            else:
                self.dump_unicode(ustr(value), write)
        dispatch[bytes] = dump_bytes

        def dump_datetime(self, value, write):
            # override to marshall as a string for backwards compatibility
            value = value.strftime(DEFAULT_SERVER_DATETIME_FORMAT) if value else False
            self.dump_unicode(value, write)
        dispatch[datetime] = dump_datetime

        def dump_date(self, value, write):
            value = value.strftime(DEFAULT_SERVER_DATE_FORMAT) if value else False
            self.dump_unicode(value, write)
        dispatch[date] = dump_date

        def dump_lazy(self, value, write):
            v = value._value
            return self.dispatch[type(v)](self, v, write)
        dispatch[lazy] = dump_lazy

    # monkey-patch xmlrpc.client's marshaller
    xmlrpc.client.Marshaller = OdooMarshaller
    return xmlrpc

def load_monkeypatched_module(name, monkeypatcher, parent_namespaces=None):
    try:
        module = monkeypatcher()
        module.__is_monkeypatched__ = True
        for parent_namespace in (parent_namespaces or ['']):
            key = parent_namespace and f"{parent_namespace}.{name}" or name
            sys.modules[key] = module
    except Exception:
        module = None
    return module

def load_monkeypatched_modules(monkeypatches, parent_namespaces=None):
    for module_name, monkeypatcher in monkeypatches.items():
        load_monkeypatched_module(module_name, monkeypatcher, parent_namespaces)

prefix = "monkeypatch_"
monkeypatches = {x[len(prefix):]: y for x, y in locals().items() if x.startswith(prefix)}
load_monkeypatched_modules(monkeypatches)
