# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=import-outside-toplevel

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
    try:
        from xlrd import xlsx
    except ImportError:
        return None

    from lxml import etree

    xlsx.ET = etree
    xlsx.ET_has_iterparse = True
    xlsx.Element_has_iter = True

    return xlsx

def monkeypatch_OpenSSL():
    """
        OpenSSL v0.x.x uses OpenSSL.X509_get_notBefore and OpenSSL.X509_get_notAfter
        pyopenssl v19.0.0 uses those.
        OpenSSL v1.1.0a+ renamed them to OpenSSL.X509_getm_notBefore and OpenSSL.X509_getm_notAfter
        pyopenssl v20.0.0 adapted to those new ones.
        This monkeypatch prevents misalignments between versions.
    """
    try:
        import OpenSSL
        import ssl
    except ImportError:
        return None

    try:
        pyopenssl_version = tuple(int(x) for x in OpenSSL.__version__.split('.'))
        openssl_version = ssl.OPENSSL_VERSION_INFO[:3]
    except Exception:
        return None

    lib = OpenSSL._util.lib
    if pyopenssl_version >= (20, 0, 0) and openssl_version < (1, 1, 0):
        lib.X509_getm_notBefore = lib.X509_get_notBefore
        lib.X509_getm_notAfter = lib.X509_get_notAfter
    elif pyopenssl_version >= (19, 0, 0) and openssl_version >= (1, 1, 0):
        lib.X509_get_notBefore = lib.X509_getm_notBefore
        lib.X509_get_notAfter = lib.X509_getm_notAfter

    return OpenSSL

def monkeypatch_xlwt():
    """
        Add some sanitization to respect the excel sheet name restrictions
        as the sheet name is often translatable, can not control the input.
    """
    try:
        import re
        import xlwt
    except ImportError:
        return None

    class PatchedWorkbook(xlwt.Workbook):
        def add_sheet(self, sheetname, cell_overwrite_ok=False):
            # invalid Excel character: []:*?/\
            sheetname = re.sub(r'[\[\]:*?/\\]', '', sheetname)
            # maximum size is 31 characters
            sheetname = sheetname[:31]
            return super(PatchedWorkbook, self).add_sheet(sheetname, cell_overwrite_ok=cell_overwrite_ok)

    xlwt.Workbook = PatchedWorkbook
    return xlwt

def monkeypatch_xlsxwriter():
    """
        Add some sanitization to respect the excel sheet name restrictions
        as the sheet name is often translatable, can not control the input.
    """
    try:
        import re
        import xlsxwriter
    except ImportError:
        return None

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

def load_monkeypatched_module(name, monkeypatcher, parent_namespaces=None):
    import sys
    module = monkeypatcher()
    if not module:
        raise ModuleNotFoundError(name)
    module.__is_monkeypatched__ = True
    for parent_namespace in (parent_namespaces or ['']):
        key = parent_namespace and f"{parent_namespace}.{name}" or name
        sys.modules[key] = module
    return module

def load_monkeypatched_modules(monkeypatches, parent_namespaces=None):
    for module_name, monkeypatcher in monkeypatches.items():
        load_monkeypatched_module(module_name, monkeypatcher, parent_namespaces)


prefix = "monkeypatch_"
monkeypatches = {x[len(prefix):]: y for x, y in locals().items() if x.startswith(prefix)}
load_monkeypatched_modules(monkeypatches)
