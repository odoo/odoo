# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=unbalanced-tuple-unpacking

import logging
import re

from odoo import tools
from odoo.modules import get_resource_from_path

from . import lint_case

_logger = logging.getLogger(__name__)

TSTRING_RE = re.compile(r'_l?t\(\s*`.*?\s*`\s*\)', re.DOTALL)
EXPRESSION_RE = re.compile(r'\$\{.+?\}')
UNDERSCORE_RE = re.compile(r'\b_\(\s*[\'"]')

class TestJsTranslations(lint_case.LintCase):

    def check_text(self, text):
        """ Search for translation errors in the text

        :param text: The js text to search
        :return: A list of tuple with line number and invalid template string,
                 or None for underscore errors
        """
        error_list = list()
        for m in TSTRING_RE.finditer(text):
            template_string = m.group(0)
            if EXPRESSION_RE.search(template_string):
                line_nb = text[:m.start()].count('\n') + 1
                error_list.append((line_nb, template_string))

        for m in UNDERSCORE_RE.finditer(text):
            lineno = text[:m.start()].count('\n') + 1
            error_list.append((lineno, None))

        return error_list

    def test_regular_expression(self):
        bad_js = """
        const foo = {
            valid: _lt(`not useful but valid template-string`),
            invalid: _lt(`invalid template-string
            that spans multiple lines ${expression}`)
        };
        """
        error_list = self.check_text(bad_js)
        self.assertEqual(len(error_list), 1)
        [(line, template_string)] = error_list
        self.assertEqual(line, 4)
        self.assertIn('invalid template-string', template_string)
        self.assertNotIn('but valid template-string', template_string)

    def test_regular_expression_long(self):
        bad_js = """
        thing = _t(
            `foo ${this + is(a, very) - long == expression}`
        );
        """

        error_list = self.check_text(bad_js)
        self.assertEqual(len(error_list), 1)
        [(line, template_string)] = error_list
        self.assertEqual(line, 2)
        self.assertIn('foo ${this + is(a, very) - long == expression}', template_string)

    def test_matches_underscore(self):
        bad_js = """
        const thing1 = _('literal0');
        const thing0 = _([]);
        const thing2 = _("literal1");
        """
        self.assertEqual(
            self.check_text(bad_js),
            [(2, None), (4, None)]
        )

    def test_js_translations(self):
        """ Test that there are no translation of JS template strings or underscore
        calls misused as translation markers
        """

        counter = 0
        failures = 0
        for js_file in self.iter_module_files('*.js'):
            # lodash has string methods and occurrences of `_('text')` in its comments
            if js_file.endswith('/lodash.js'):
                continue

            counter += 1
            with tools.file_open(js_file, 'r') as f:
                js_txt = f.read()

            error_list = self.check_text(js_txt)
            for line_number, template_string in error_list:
                failures += 1
                mod, relative_path, _ = get_resource_from_path(js_file)
                if template_string:
                    prefix = "Translation of a template string"
                    suffix = template_string
                else:
                    prefix = "underscore.js used as translation function"
                    suffix = "_t and _lt are the JS translation functions"

                _logger.error("%s found in `%s/%s` at line %s: %s", prefix, mod, relative_path, line_number, suffix)

        _logger.info('%s files tested', counter)
        if failures > 0:
            self.fail("%s invalid template strings found in js files." % failures)
