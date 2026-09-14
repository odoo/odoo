import logging
import re
from pathlib import Path

from odoo.tests import tagged

from . import _js_sources, lint_case

_logger = logging.getLogger(__name__)

REGISTRATION_RE = re.compile(
    r"^(?:onRpc|defineModels|defineParams|mockService)\(", re.MULTILINE
)
TEST_SUFFIX = ".test.js"


def _resolve(specifier, addon, path):
    spec = specifier.removesuffix(".js")
    if spec.startswith("@"):
        head, _, rest = spec[1:].partition("/")
        if rest.startswith("../"):
            return f"{head}/{rest[3:]}"
        return f"{head}/src/{rest}"
    if spec.startswith("."):
        here = path.as_posix().rsplit("/", 1)[0]
        resolved = Path(f"{here}/{spec}").resolve().as_posix()
        return _js_sources.module_key(addon, Path(resolved))
    return None


def _orphans(sources):
    imported = set()
    candidates = {}
    scanned = 0
    for addon, path, source in sources:
        scanned += 1
        imported.update(
            resolved
            for resolved in (
                _resolve(spec, addon, path)
                for spec in _js_sources.specifiers(source)
            )
            if resolved
        )
        posix = path.as_posix()
        if "/static/tests/" not in posix or posix.endswith(TEST_SUFFIX):
            continue
        if REGISTRATION_RE.search(source):
            key = _js_sources.module_key(addon, path)
            if key:
                candidates[posix] = key
    orphans = sorted(p for p, key in candidates.items() if key not in imported)
    return scanned, candidates, orphans


@tagged("post_install", "-at_install")
class TestOrphanTestRegistrations(lint_case.LintCase):
    def test_a_planted_module_scope_registration_is_caught(self):
        helper = Path("/x/thing/static/tests/thing_models.js")
        planted = [
            (
                "thing",
                helper,
                'import { defineModels } from "@web/../tests/web_test_helpers";\ndefineModels(models);\n',
            ),
            (
                "thing",
                Path("/x/thing/static/tests/wrapped.js"),
                "export function defineThingModels() {\n    defineModels(models);\n}\n",
            ),
        ]
        _scanned, candidates, orphans = _orphans(planted)
        self.assertEqual(list(candidates.values()), ["thing/tests/thing_models"])
        self.assertEqual(orphans, [helper.as_posix()])
        importer = (
            "thing",
            Path("/x/thing/static/tests/a.test.js"),
            'import "@thing/../tests/thing_models";\n',
        )
        self.assertEqual(_orphans([*planted, importer])[2], [])

    def test_no_registration_module_is_orphaned(self):
        scanned, candidates, orphans = _orphans(_js_sources.addon_js())

        _logger.info(
            "scanned %s addon js file(s), %s carry a module-scope registration",
            scanned,
            len(candidates),
        )
        self.assertTrue(
            scanned,
            "no addon JS was scanned — the layout this gate walks has "
            "moved, and the gate is now vacuous",
        )
        self.assertFalse(
            orphans,
            "test module(s) calling onRpc/defineModels at module scope that no "
            "other module imports; the bundle evaluates them outside any suite, "
            "so HOOT's `before()` has nothing to attach to and the registration "
            "is silently lost. Move the call into the helper the tests already "
            "invoke (defineXModels), not into an import — imports run before the "
            "module body, so the suite context is still absent:\n  "
            + "\n  ".join(orphans),
        )
