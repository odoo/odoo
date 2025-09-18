import logging
import re

from odoo.libs.lint.scan import scan_regex_patterns
from odoo.modules import get_resource_from_path

from . import lint_case

_logger = logging.getLogger(__name__)

# Pattern 0: _t(`template string with ${expression}`)
TSTRING_RE = re.compile(r"_t\(\s*`.*?\s*`\s*\)", re.DOTALL)
EXPRESSION_RE = re.compile(r"\$\{.+?\}")
# Pattern 1: _('literal') or _("literal")
UNDERSCORE_RE = re.compile(r'\b_\(\s*[\'"]')

# Rust-compatible patterns (DOTALL via (?s) inline flag)
_RUST_TSTRING_PAT = r"(?s)_t\(\s*`.*?\s*`\s*\)"
_RUST_UNDERSCORE_PAT = r"""\b_\(\s*['"]"""


class TestJsTranslations(lint_case.LintCase):

    def check_text(self, text):
        """Search for translation errors in the text.

        :param text: The js text to search
        :return: A list of tuple with line number and invalid template string,
                 or None for underscore errors
        """
        error_list = []
        for m in TSTRING_RE.finditer(text):
            template_string = m.group(0)
            if EXPRESSION_RE.search(template_string):
                line_nb = text[: m.start()].count("\n") + 1
                error_list.append((line_nb, template_string))

        for m in UNDERSCORE_RE.finditer(text):
            lineno = text[: m.start()].count("\n") + 1
            error_list.append((lineno, None))

        return error_list

    def test_regular_expression(self):
        bad_js = """
        const foo = {
            valid: _t(`not useful but valid template-string`),
            invalid: _t(`invalid template-string
            that spans multiple lines ${expression}`)
        };
        """
        error_list = self.check_text(bad_js)
        self.assertEqual(len(error_list), 1)
        [(line, template_string)] = error_list
        self.assertEqual(line, 4)
        self.assertIn("invalid template-string", template_string)
        self.assertNotIn("but valid template-string", template_string)

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
        self.assertIn("foo ${this + is(a, very) - long == expression}", template_string)

    def test_matches_underscore(self):
        bad_js = """
        const thing1 = _('literal0');
        const thing0 = _([]);
        const thing2 = _("literal1");
        """
        self.assertEqual(self.check_text(bad_js), [(2, None), (4, None)])

    def test_js_translations(self):
        """Test that there are no translation of JS template strings or underscore
        calls misused as translation markers.
        """
        roots = self._module_roots()

        # Parallel regex scan across all .js files
        results = scan_regex_patterns(
            roots,
            [".js"],
            [_RUST_TSTRING_PAT, _RUST_UNDERSCORE_PAT],
            ["node_modules", "__pycache__"],
        )

        failures = 0
        for path, line, pat_idx, matched_text in results:
            # Exclusions: lodash (uses `_` for utility), minified third-party libs
            if path.endswith("/lodash.js"):
                continue
            if "/lib/" in path and path.endswith(".min.js"):
                continue

            if pat_idx == 0:
                # TSTRING_RE match — only flag if it contains ${expression}
                if not EXPRESSION_RE.search(matched_text):
                    continue
                prefix = "Translation of a template string"
                suffix = matched_text
            else:
                # UNDERSCORE_RE match — always flag
                prefix = "underscore.js used as translation function"
                suffix = "_t is the JS translation function"

            failures += 1
            try:
                mod, relative_path, _ = get_resource_from_path(path)
            except TypeError:
                mod, relative_path = "?", path

            _logger.error(
                "%s found in `%s/%s` at line %s: %s",
                prefix,
                mod,
                relative_path,
                line,
                suffix,
            )

        if failures > 0:
            self.fail(f"{failures} invalid template strings found in js files.")
