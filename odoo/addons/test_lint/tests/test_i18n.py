import logging
import re

from . import lint_case

from odoo import tools

_logger = logging.getLogger(__name__)


class TestI18n(lint_case.LintCase):
    PROPS_RE = re.compile(
        r"""
        (
            <[A-Z]                          # Match the opening tag of a component node. We assume that tags starting with an uppercase letter refer to a component
                (
                    [^>]+                   # Match anything that is not a closing tag `>`. In other words, the rest of the component name and any prop that doesn't match the heuristics that follow
                )
        )
        \s
        (?!t-)                              # exclude directives (attributes starting with t-)
        (
            [a-zA-Z-]+                      # Match prop name
            =
            "'                              # Make sure that the value is a static string literal. Only static string literals are eligible for translation. We determine that the value is a string literal if the value begins and ends with a '
            [A-Z](\'|[^'"])*?                # Assumption: Text starting with an uppercase letter is probably supposed to be translated.
            [a-z]                           # Arbitrary constraint to avoid matching certain technical constants (e.g. ROW, COL)
            (\'|[^'"])*?                     # Match the content of the string
            '"                              # Value ends with the closing of a string literal
        )
        """,
        re.VERBOSE | re.DOTALL,
    )

    def test_directives_regex(self):
        """
        Checks that the regex:
            - Catches components that are spread across multiple lines.
            - Does not catch directives.
            - Does not catch props that use `.translate`.
            - Does not catch strings that do not start with a capital letter.
        """
        test_cases = [
            # Multi-line test case
            (
                """
            <Component
                t-esc="some_variable"
                customProp="'Custom String'"
            />""",
                [
                    ("customProp=\"'Custom String'\""),
                ],
            ),
            # Exclude directives starting with t-
            (
                """
            <Component t-title="'Some String'" t-esc="some_variable"/>
            """,
                [],
            ),
            # Doesn't catch .translate props
            (
                """
            <Component title.translate="'Some String'" t-esc="some_variable"/>
            """,
                [],
            ),
            # Include valid cases
            (
                """
            <Component title="'Another String'" t-esc="another_variable"/>
            <Component description="'Description here'" />
            <Component title="'String with an escaped single quote ' inside'"/>
            """,
                [
                    ("title=\"'Another String'\""),
                    ("description=\"'Description here'\""),
                    ("title=\"'String with an escaped single quote ' inside'\""),
                ],
            ),
            # Exclude attributes starting with t- in between valid attributes
            (
                """
            <Component title="'Valid Title'" t-esc="some_variable" t-title="'Should not be caught'" customProp="'Valid Prop'"/>
            """,
                [
                    ("customProp=\"'Valid Prop'\""),
                ],
            ),
            # Ensure it catches strings starting with capital letter and exclude others
            (
                """
            <Component name="'singleword'" title="'SingleWord'" prop="'another String'"/>
            """,
                [
                    ("title=\"'SingleWord'\""),
                ],
            ),
        ]

        error_count = 0
        for i, (file_content, expected_matches) in enumerate(test_cases):
            matches = [(m.group(3)) for m in self.PROPS_RE.finditer(file_content)]
            if matches != expected_matches:
                _logger.error("Test case %s failed: expected %s, got %s", i + 1, expected_matches, matches)
                error_count += 1
        self.assertEqual(error_count, 0)

    def test_user_content_as_prop_is_translatable(self):
        """
        Checks if there are any props that does not use `.translate` and reports it.
        """
        error_count = 0
        for file_path in self.iter_module_files("**/static/**/*.xml"):
            with tools.file_open(file_path, "r") as f:
                file_content = f.read()
                for m in self.PROPS_RE.finditer(file_content):
                    lineno = file_content[: m.start()].count("\n") + 1
                    _logger.error(
                        """The prop “%s” in file “%s” in the component node starting at line %s contains what looks like human-readable text. If the content of this prop is intended for display to the end user, add the .translate suffix to make the prop translatable.
                        If this is a false positive, please contact the i18n team.""",
                        m.group(3),
                        file_path,
                        lineno,
                    )
                    error_count += 1
        self.assertEqual(error_count, 0)
