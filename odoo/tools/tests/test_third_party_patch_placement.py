import ast
import pathlib
import subprocess
import sys
import unittest

_CORE = pathlib.Path(__file__).resolve().parents[3] / "odoo"


KNOWN_PATCHES: dict[tuple[str, str], str] = {
    ("tests/common.py", "freezegun.freeze_time"): (
        "Replaces freezegun's decorator so @freeze_time also patches Odoo's own "
        "clock sources. Lives beside the replacement class it installs; a "
        "_monkeypatches/freezegun.py would be the placement the rule asks for, "
        "but the patch is only meaningful once odoo.tests is imported. DEBT, "
        "small."
    ),
    ("logutils.py", "logging.RUNBOT"): (
        "Registers a custom log level. logutils IS the logging module of this "
        "codebase; _monkeypatches/logging.py would invert that."
    ),
    ("logutils.py", "logging.Logger.runbot"): "The method for the level above.",
    ("tools/config.py", "optparse._"): (
        "Neutralises optparse's gettext so option help is not translated at "
        "import time. DEBT: this is a textbook _monkeypatches/optparse.py."
    ),
}

_SKIP_TOP = {"addons", "_monkeypatches", "upgrade"}


def _is_test_suite(parts: tuple[str, ...]) -> bool:
    return "tests" in parts[1:]


def _module_level_statements(tree: ast.Module):
    stack = list(tree.body)
    while stack:
        stmt = stack.pop()
        yield stmt
        if isinstance(stmt, ast.If | ast.Try | ast.With):
            stack.extend(stmt.body)
            stack.extend(getattr(stmt, "orelse", []))
            stack.extend(getattr(stmt, "finalbody", []))
            for handler in getattr(stmt, "handlers", []):
                stack.extend(handler.body)


def _foreign_names(tree: ast.Module) -> dict[str, str]:
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("odoo"):
                    bound[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module and not node.module.startswith("odoo"):
                for alias in node.names:
                    bound[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return bound


def find_patches() -> list[tuple[str, str, int]]:
    found: list[tuple[str, str, int]] = []
    for path in sorted(_CORE.rglob("*.py")):
        parts = path.relative_to(_CORE).parts
        if (
            parts[0] in _SKIP_TOP
            or _is_test_suite(parts)
            or path.name.startswith("test_")
        ):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError, UnicodeDecodeError:
            continue
        foreign = _foreign_names(tree)
        if not foreign:
            continue
        rel = path.relative_to(_CORE).as_posix()
        for stmt in _module_level_statements(tree):
            if isinstance(stmt, ast.Assign):
                targets = stmt.targets
            elif isinstance(stmt, ast.AnnAssign):
                targets = [stmt.target]
            else:
                continue
            for target in targets:
                if not isinstance(target, ast.Attribute):
                    continue
                base: ast.expr = target
                while isinstance(base, ast.Attribute):
                    base = base.value
                if isinstance(base, ast.Name) and base.id in foreign:
                    found.append((rel, ast.unparse(target), stmt.lineno))
    return found


class TestThirdPartyPatchPlacement(unittest.TestCase):
    def test_sandbox_timezone_configuration_does_not_patch_dateutil(self):
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import dateutil.tz
original_gettz = dateutil.tz.gettz
from odoo.tools import safe_eval
assert dateutil.tz.gettz is original_gettz
assert safe_eval.dateutil.tz is not dateutil.tz
assert safe_eval.dateutil.tz.gettz is safe_eval.pytz.timezone
assert safe_eval.safe_eval(
    "dateutil.tz.gettz('UTC')", {'dateutil': safe_eval.dateutil}
) is safe_eval.pytz.timezone('UTC')
""",
            ],
            cwd=_CORE.parent,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_every_patch_outside_monkeypatches_is_acknowledged(self):
        found = {(rel, target) for rel, target, _ in find_patches()}
        detectable_known = {
            k for k in KNOWN_PATCHES if "LAUNDERED" not in KNOWN_PATCHES[k]
        }
        new = sorted(found - detectable_known)
        gone = sorted(detectable_known - found)
        self.assertFalse(
            new,
            f"third-party module patched at import time outside _monkeypatches/: "
            f"{new}. ARCHITECTURE.md says these belong in "
            f"odoo/_monkeypatches/<module>.py. If this one genuinely cannot "
            f"move, add it to KNOWN_PATCHES with the reason.",
        )
        self.assertFalse(
            gone,
            f"KNOWN_PATCHES lists patches that no longer exist: {gone}. Good "
            f"news -- delete the entries so the pin cannot silently bless a new "
            f"patch in the same place.",
        )

    def test_the_framework_package_is_in_scope(self):
        scanned = {rel for rel, _, _ in find_patches()}
        self.assertIn(
            "tests/common.py",
            scanned,
            "odoo/tests/ has dropped out of scope again — that is 6k lines of "
            "framework code, imported by every integration run, unscanned.",
        )

    def test_package_test_suites_stay_out_of_scope(self):
        parts_suite = ("db", "tests", "conftest.py")
        parts_framework = ("tests", "common.py")
        self.assertTrue(_is_test_suite(parts_suite))
        self.assertFalse(_is_test_suite(parts_framework))

    def test_scan_is_not_vacuous(self):
        self.assertGreaterEqual(len(find_patches()), 4)

    def test_nested_module_level_blocks_are_walked(self):
        tree = ast.parse(
            "import optparse\n"
            "if True:\n"
            "    try:\n"
            "        optparse.something = 1\n"
            "    except Exception:\n"
            "        pass\n"
        )
        targets = [
            ast.unparse(t)
            for stmt in _module_level_statements(tree)
            if isinstance(stmt, ast.Assign)
            for t in stmt.targets
        ]
        self.assertIn("optparse.something", targets)

    def test_function_bodies_are_out_of_scope(self):
        tree = ast.parse("import optparse\ndef f():\n    optparse.patched_here = 1\n")
        assigns = [
            s for s in _module_level_statements(tree) if isinstance(s, ast.Assign)
        ]
        self.assertEqual(assigns, [])

    def test_the_pdf_patches_moved_to_monkeypatches_and_stay_there(self):
        src = (_CORE / "tools" / "pdf" / "__init__.py").read_text(encoding="utf-8")
        for gone in (
            "pypdf.filters.decompress =",
            "DictionaryObject.get =",
            "NameObject.renumber_table.update",
        ):
            with self.subTest(patch=gone):
                self.assertNotIn(gone, src)

        patches = (_CORE / "_monkeypatches" / "pypdf.py").read_text(encoding="utf-8")
        for present in (
            "DictionaryObject.get =",
            "NameObject.renumber_table.update",
        ):
            with self.subTest(patch=present):
                self.assertIn(present, patches)
        self.assertNotIn(
            "pypdf.filters.decompress =",
            patches,
            "e20f37408ad deleted the decompress override as a DoS: it dropped "
            "pypdf's ZLIB_MAX_OUTPUT_LENGTH cap on a FlateDecode stream reachable "
            "from PdfReader(). It belongs in neither file.",
        )

    def test_the_pdf_patches_are_actually_applied(self):
        from pypdf.generic import DictionaryObject, NameObject

        import odoo.init  # noqa: F401  registers the import hooks
        import odoo.tools.pdf  # noqa: F401  pulls pypdf in, firing the hook
        from odoo._monkeypatches import applied

        self.assertIn("pypdf", applied())
        self.assertEqual(DictionaryObject.get.__name__, "_unwrapping_get")
        self.assertIn("\n", NameObject.renumber_table)


if __name__ == "__main__":
    unittest.main()
