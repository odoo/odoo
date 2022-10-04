# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# pylint: disable=import-outside-toplevel

"""Monkeypatching is not a good practice, it should be avoided in all cases.
   Yet in some cases it's still necessary, mainly when relying on third party modules.
   Reasons may vary:

       - to adjust for compatibility between versions,
       - to fix a small detail without reworking the external module.

   In Odoo, there were several places in which monkeypatching is done.
   This module aims to put the monkeypatching all together and to make clear
   at a glance which external modules are subject to it, and how.

   All the monkeypatching will be done so that import <module> will already load
   the monkeypatched module. Modules will have a new <module>.__monkeypatched__
   attribute set to True. This will remove the need to import from odoo.tools.misc.<module>
   and also ensure that people not aware of the monkeypatching use the wrong version.

   Until now, the modules present here are of broad interest, and may belong to the "base" module.
   There are cases in which third-party monkeypatched module are of specific interest
   of a single Odoo module. We can leave the monkeypatching in that module, but we suggest
   using the `monkeypatch_register` function here to make it at least visible at runtime,
   so that from the Odoo shell we can query them:

   >>> from odoo.tools._monkeypatches import monkeypatched_modules
   >>> from pprint import pprint
   >>> pprint(monkeypatched_modules())
   {'OpenSSL': <module 'OpenSSL' from '/path/to/OpenSSL/OpenSSL.py>,
    'PyPDF2': <module 'PyPDF2' from '/path/to/PyPDF2/PyPDF2.py>,
    'xlrd': <module 'xlrd.xlsx' from '/path/to/xlrd/xlrd.py>,
    'xlsxwriter': <module 'xlsxwriter' from '/path/to/xlsxwriter/xlsxwriter.py>,
    'xlwt': <module 'xlwt' from '/path/to/xlwt/xlwt.py>,
    'xmlrpc': <module 'xmlrpc' from '/path/to/xmlrpc/xmlrpc.py>}
"""

import sys
import importlib


def monkeypatch_register(module_name):
    """Creates a monkeypatching decorator and returns it.
       The monkeypatching decorator will run and the module will be added
       to the sys.modules registry of imported modules with the module.__monkeypatched__
       flag set to True.
    """
    def monkeypatch_register_inner(monkeypatcher_func):
        try:
            monkeypatcher_func()
        except Exception:
            return
        module = importlib.import_module(module_name)
        module.__monkeypatched__ = True
    return monkeypatch_register_inner

def monkeypatched_modules():
    """Returns a dict with monkeypatched modules.
       The keys are the names, the values the modules themselves.
    """
    return {k: v for k, v in sys.modules.items() if getattr(v, '__monkeypatched__', False)}

@monkeypatch_register('OpenSSL')
def monkeypatch_OpenSSL():
    """OpenSSL v0.x.x uses OpenSSL.X509_get_notBefore and OpenSSL.X509_get_notAfter
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

@monkeypatch_register('PyPDF2')
def monkeypatch_PyPDF2():
    """PyPDF2 fixes:
       1) Fix invalid numbers like 0.000000000000-5684342
          Because some PDF generators are building PDF streams with invalid numbers.
          Ref: https://docs.python.org/3/library/zlib.html#zlib.decompressobj
       2) Ensure that zlib does not throw error -5 when decompressing
          because some pdf won't fit into allocated memory.
    """
    import zlib
    import PyPDF2

    orig_FloatObject___new__ = PyPDF2.generic.FloatObject.__new__

    def FloatObject___new__(cls, value="0", context=None):
        # Fix invalid numbers like 0.000000000000-5684342
        # Because some PDF generators are building PDF streams with invalid numbers
        if isinstance(value, bytes) and value[0] != b'-' and b'-' in value:
            value = b'-' + b''.join(value.split(b'-', 1))
        elif isinstance(value, str) and value[0] != '-' and '-' in value:
            value = '-' + ''.join(value.split('-', 1))
        return orig_FloatObject___new__(cls, value, context)

    def _decompress(data):
        zobj = zlib.decompressobj()
        return zobj.decompress(data)

    PyPDF2.generic.FloatObject.__new__ = FloatObject___new__
    PyPDF2.filters.decompress = _decompress

@monkeypatch_register('xlrd')
def monkeypatch_xlrd():
    """xlrd.xlsx supports defusedxml, defusedxml's etree interface is broken
       (missing ElementTree and thus ElementTree.iter) which causes a fallback to
       Element.getiterator(), triggering a warning before 3.9 and an error from 3.9.

       We have defusedxml installed because zeep has a hard dep on defused and
       doesn't want to drop it (mvantellingen/python-zeep#1014).

       Ignore the check and set the relevant flags directly using lxml as we have a
       hard dependency on it.
    """
    import xlrd
    from lxml import etree

    xlrd.xlsx.ET = etree
    xlrd.xlsx.ET_has_iterparse = True
    xlrd.xlsx.Element_has_iter = True

@monkeypatch_register('xlsxwriter')
def monkeypatch_xlsxwriter():
    """Xlsxwriter fix, add some sanitization to respect the excel sheet name restrictions
       as the sheet name is often translatable, can not control the input.
    """
    import re
    import xlsxwriter

    class PatchedXlsxWorkbook(xlsxwriter.Workbook):
        def add_worksheet(self, name=None, worksheet_class=None):
            if name:
                # invalid Excel character: []:*?/\
                name = re.sub(r'[\[\]:*?/\\]', '', name)
                # maximum size is 31 characters
                name = name[:31]
            return super(PatchedXlsxWorkbook, self).add_worksheet(name, worksheet_class)

    xlsxwriter.Workbook = PatchedXlsxWorkbook

@monkeypatch_register('xlwt')
def monkeypatch_xlwt():
    """Add some sanitization to respect the excel sheet name restrictions
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
