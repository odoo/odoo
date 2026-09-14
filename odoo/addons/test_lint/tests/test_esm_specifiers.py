import logging
from pathlib import Path
from unittest.mock import patch

from odoo.modules import Manifest
from odoo.tools.assets.esm_registry import external_libs

from . import _js_sources, lint_case
from odoo.addons.base.models.ir_qweb_assets import IrQweb

_logger = logging.getLogger(__name__)


def _addon_js_sources():
    return _js_sources.addon_js_outside_lib()


class TestEsmSpecifiers(lint_case.LintCase):
    def test_specifiers_distinguish_code_from_comments_and_strings(self):
        cases = [
            ('const url = "https://example.test"; import("@web/real");', {"@web/real"}),
            ('const a = "/*"; import("@web/real"); const b = "*/";', {"@web/real"}),
            (
                '/** @type {import("@web/types").T} */ import("@web/real");',
                {"@web/real"},
            ),
            (
                "const code = 'import(\"@web/fake\")'; export * from '@web/real';",
                {"@web/real"},
            ),
            (
                'const text = `import("@web/fake") ${import("@web/real")}`;',
                {"@web/real"},
            ),
            (
                'const regex = /import\\("@web\\/fake"\\)/; import("@web/real");',
                {"@web/real"},
            ),
            (
                '// import("@web/fake")\nimport /* comment */ ("@web/real");',
                {"@web/real"},
            ),
            (
                'import { x } from "@web/static"; export { y } from "@web/export"; import("@web/dynamic");',
                {"@web/static", "@web/export", "@web/dynamic"},
            ),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                actual = _js_sources.specifiers(source)
                _logger.debug("ESM lexer probe: source=%r imports=%s", source, actual)
                self.assertEqual(actual, expected)

    def test_specifier_check_fails_when_lexer_is_unavailable(self):
        with patch.object(_js_sources, "lex_module", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "module lexer is unavailable"):
                _js_sources.specifiers('import "@web/missing";')

    def test_relative_specifiers_carry_their_extension(self):
        broken = []
        self.assertGreater(
            len(_addon_js_sources()), 1000, "the scan reached almost no JS"
        )
        for _addon, path, source in _addon_js_sources():
            for spec in _js_sources.specifiers(source):
                if not spec.startswith("."):
                    continue
                target = (path.parent / spec).resolve()
                if not target.is_file():
                    broken.append((path, spec, target))

        if broken:
            details = "\n".join(
                f"  {path}\n      imports {spec!r} -> no such file {target}"
                for path, spec, target in sorted(broken)
            )
            self.fail(
                f"{len(broken)} relative ESM specifier(s) that only esbuild can "
                f"resolve. Each one serves a blank web client under "
                f"?debug=assets. Write the path as it is served, extension "
                f"included:\n{details}"
            )

    def test_esm_specifiers_resolve(self):
        addon_paths = {
            manifest.name: Path(manifest.path)
            for manifest in Manifest.get_all_addon_manifests()
        }
        broken = []
        scanned = 0

        for _addon, path, source in _addon_js_sources():
            scanned += 1
            # JSDoc import() expressions resolve types, not runtime JS assets.
            for spec in _js_sources.specifiers(source):
                if spec in external_libs():
                    continue
                url = IrQweb._specifier_to_static_url(spec)
                if url is None:
                    continue
                addon, _, relative = url.lstrip("/").partition("/")
                root = addon_paths.get(addon)
                if root is None:
                    continue
                target = root / relative
                index = target.with_suffix("") / "index.js"
                if not target.is_file() and not index.is_file():
                    broken.append((path, spec, f"{addon}/{relative}"))

        _logger.info("checked ESM specifiers in %s js files", scanned)
        self.assertGreater(scanned, 1000, "the scan reached almost no JS")
        if broken:
            details = "\n".join(
                f"  {path}\n      imports {spec!r} -> no such file {target}"
                for path, spec, target in sorted(broken)
            )
            self.fail(
                f"{len(broken)} unresolvable ESM specifier(s). Each one fails the "
                f"entire asset bundle it lands in, which serves a blank web "
                f"client:\n{details}"
            )
