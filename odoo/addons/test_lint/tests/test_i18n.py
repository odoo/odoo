import logging
import re

from . import lint_case

from odoo import tools
from odoo.tools import TRANSLATED_ATTRS

_logger = logging.getLogger(__name__)


class TestI18n(lint_case.LintCase):
    # Assumption: Text starting with an uppercase letter is likely supposed to be translated.
    DIRECTIVES_RE = re.compile(r"t-(value|out|esc)=\"'[A-Z][a-z]")
    ATTRS_AS_PROPS_RE = re.compile(r"\b(%s)=\"'[A-Z][a-z]" % "|".join(TRANSLATED_ATTRS))
    JS_GETTEXT_RE = re.compile(r"\b_t\(")
    BACKSLASH_NEWLINE_RE = re.compile(r"""
        _t\(\s*
            (
                '(\\'|[^'])+\\$
                |
                "(\\"|[^"])+\\$
            )
    """, re.MULTILINE | re.VERBOSE)

    def test_js_translatability(self):
        """
        Checks for:
        - Backslash-newline inside JS translated strings:
            https://github.com/python-babel/babel/issues/1056
        """
        error_count = 0
        for file_path in self.iter_module_files("*.js"):
            with tools.file_open(file_path, "r") as f:
                file_content = f.read()
                for m in self.BACKSLASH_NEWLINE_RE.finditer(file_content):
                    lineno = file_content[: m.start()].count("\n") + 1
                    _logger.error(f"Backslash-newline in translated string in file {file_path} at line {lineno}")
                    error_count += 1
        self.assertEqual(error_count, 0)

    def test_xml_translatability(self):
        """
        Checks for:
        - Translated attributes as props:
            <MyComponent title="'Shrek The Musical'"/>
            The title is not exported or translated because it is a prop, not an attribute.
        - Human-readable text in Qweb directives:
            <t t-set="page_title" t-value="'Payment Confirmation'"/>
            Content of Qweb directives is not exported or translated.
        - Calls to _t in Owl templates:
            <t t-esc="something ? something : _t('Nothing')"/>
            Calls to gettext inside templates aren't exported.
        """
        error_count = 0
        for file_path in self.iter_module_files("*.xml"):
            with tools.file_open(file_path, "r") as f:
                file_content = f.read()
                for m in self.DIRECTIVES_RE.finditer(file_content):
                    lineno = file_content[: m.start()].count("\n") + 1
                    _logger.error(f"Human-readable text in Qweb directives in file {file_path} at line {lineno}")
                    error_count += 1
        for file_path in self.iter_module_files("*/static/src/**/*.xml"):
            with tools.file_open(file_path, "r") as f:
                file_content = f.read()
                for m in self.JS_GETTEXT_RE.finditer(file_content):
                    lineno = file_content[: m.start()].count("\n") + 1
                    _logger.error(f"Call to “_t” in Owl template in file {file_path} at line {lineno}")
                    error_count += 1
                for m in self.ATTRS_AS_PROPS_RE.finditer(file_content):
                    lineno = file_content[: m.start()].count("\n") + 1
                    _logger.error(f"Translated attribute as a prop in file {file_path} at line {lineno}")
                    error_count += 1
        self.assertEqual(error_count, 0)
