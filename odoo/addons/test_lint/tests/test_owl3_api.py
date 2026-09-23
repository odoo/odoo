import functools
import re

from odoo.tests.common import BaseCase, no_retry

from . import _js_sources, lint_case

_VENDORED = ("/static/lib/", "/static/src/o_spreadsheet/")
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_OWN_RENDER = re.compile(r"^\s+render\s*\([^)]*\)\s*\{", re.MULTILINE)
REMOVED_IN_OWL3 = {
    "owl_on_rendered": re.compile(r"(?<![\w.$])onRendered\s*\("),
    "owl_on_will_render": re.compile(r"(?<![\w.$])onWillRender\s*\("),
    "owl_this_render": re.compile(r"\bthis\.render\s*\("),
    "owl_use_component": re.compile(r"(?<![\w.$])useComponent\s*\("),
}


def calls(pattern: re.Pattern, source: str) -> list[int]:
    code = _COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), source)
    if pattern is REMOVED_IN_OWL3["owl_this_render"] and _OWN_RENDER.search(code):
        return []
    return [code.count("\n", 0, m.start()) + 1 for m in pattern.finditer(code)]


@functools.cache
def _findings(gate: str) -> tuple[str, ...]:
    pattern = REMOVED_IN_OWL3[gate]
    return tuple(
        f"{path}:{line}"
        for _addon, path, source in _js_sources.addon_js_outside_lib()
        if "/static/src/" in path.as_posix()
        and not any(part in path.as_posix() for part in _VENDORED)
        for line in calls(pattern, source)
    )


class TestOwl3Api(lint_case.LintCase):
    def _assert_removed(self, gate: str, api: str, fix: str) -> None:
        self.assert_ratchet(
            _findings(gate), gate, f"{api} calls (removed in OWL 3)", fix
        )

    def test_no_on_rendered(self):
        self._assert_removed(
            "owl_on_rendered",
            "onRendered",
            "Work that must follow a render reacts to the data instead: a value "
            "the render shows is a template binding or a useEffect on it, DOM "
            "work is onMounted/onPatched",
        )

    def test_no_on_will_render(self):
        self._assert_removed(
            "owl_on_will_render",
            "onWillRender",
            "Derive the value where it is read (a getter, or a useEffect keyed "
            "on its inputs); OWL 3 has no render hook",
        )

    def test_no_this_render(self):
        self._assert_removed(
            "owl_this_render",
            "this.render()",
            "Make the data the template reads reactive, so writing it re-renders; "
            "OWL 3 components have no render()",
        )

    def test_no_use_component(self):
        self._assert_removed(
            "owl_use_component",
            "useComponent()",
            "A hook takes what it needs as arguments or reads it through its "
            "own hooks; OWL 3 has no useComponent",
        )


@no_retry
class TestOwl3ApiScan(BaseCase):
    def test_a_bare_call_is_found_and_a_method_of_that_name_is_not(self):
        source = (
            "onRendered(() => {});\n"
            "this.props.comp.onRendered(el);\n"
            "// onRendered(() => {});\n"
            "/* this.render() */ this.render(true);\n"
            "this.renderer();\n"
        )
        self.assertEqual(calls(REMOVED_IN_OWL3["owl_on_rendered"], source), [1])
        self.assertEqual(calls(REMOVED_IN_OWL3["owl_this_render"], source), [4])

    def test_a_class_with_its_own_render_calls_that_render(self):
        interaction = (
            "export class Countdown extends Interaction {\n"
            "    start() { this.render(); }\n"
            "    render() { draw(); }\n"
            "}\n"
        )
        self.assertEqual(calls(REMOVED_IN_OWL3["owl_this_render"], interaction), [])
