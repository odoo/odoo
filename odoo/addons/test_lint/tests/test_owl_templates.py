import functools
import re
from pathlib import Path

from lxml import etree

from odoo.modules import Manifest
from odoo.tests.common import BaseCase, no_retry

from . import _js_sources, lint_case

_PARSER = etree.XMLParser(remove_comments=True, resolve_entities=False)
_TAGGED = re.compile(r"\bxml`(.*?)`", re.DOTALL)
_T_ESC = re.compile(r"(?<=\s)t-esc(?=\s*=)|@t-esc\b|<attribute\s+name=[\"']t-esc[\"']")
_VENDORED = ("/static/lib/", "/static/src/o_spreadsheet/")


def _vendored(path: Path) -> bool:
    return any(part in path.as_posix() for part in _VENDORED)


def t_esc_in_xml(source: bytes) -> list[int]:
    root = etree.fromstring(source, _PARSER)
    lines = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        refs_old_name = "t-esc" in element.attrib or any(
            "@t-esc" in value for value in element.attrib.values()
        )
        if element.tag == "attribute" and element.get("name") == "t-esc":
            refs_old_name = True
        if refs_old_name:
            lines.append(element.sourceline)
    return lines


def t_esc_in_js(source: str) -> list[int]:
    return [
        source.count("\n", 0, template.start(1) + hit.start()) + 1
        for template in _TAGGED.finditer(source)
        for hit in _T_ESC.finditer(template.group(1))
    ]


@functools.cache
def _owl_template_findings() -> tuple[str, ...]:
    findings = []
    for manifest in Manifest.get_all_addon_manifests():
        static_root = Path(manifest.path) / "static"
        if not static_root.is_dir():
            continue
        for path in sorted(static_root.rglob("*.xml")):
            if _vendored(path):
                continue
            source = path.read_bytes()
            if b"t-esc" in source:
                findings += [f"{path}:{line}" for line in t_esc_in_xml(source)]
    for _addon, path, source in _js_sources.addon_js_outside_lib():
        if "t-esc" in source and not _vendored(path):
            findings += [f"{path}:{line}" for line in t_esc_in_js(source)]
    return tuple(findings)


class TestOwlTemplates(lint_case.LintCase):
    def test_no_owl_template_uses_t_esc(self):
        self.assert_ratchet(
            _owl_template_findings(),
            "owl_t_esc",
            "t-esc in OWL templates (static XML and xml`` in JS)",
            "Write t-out: OWL 3 removes t-esc, and the vendored OWL 2 renders a "
            "non-block object through t-out as its string, exactly like t-esc. "
            "Inheritance locators, <attribute name=...> and @t-esc XPaths follow "
            "the parent template's attribute name",
        )


@no_retry
class TestOwlTemplateScan(BaseCase):
    def test_every_way_of_naming_t_esc_in_a_static_template_is_found(self):
        source = b"""<templates>
            <t t-name="a"><span t-esc="x"/><span t-out="y"/></t>
            <t t-inherit="a" t-inherit-mode="extension">
                <xpath expr="//span[@t-esc='x']" position="attributes">
                    <attribute name="t-esc">z</attribute>
                </xpath>
            </t>
        </templates>"""
        self.assertEqual(t_esc_in_xml(source), [2, 4, 5])

    def test_a_t_out_template_is_clean(self):
        source = b"""<templates><t t-name="a"><span t-out="x">default</span>
            <xpath expr="//span[@t-out='x']" position="replace"/></t></templates>"""
        self.assertEqual(t_esc_in_xml(source), [])

    def test_only_tagged_templates_in_js_are_scanned(self):
        source = (
            'const arch = `<kanban><t t-esc="record.a.value"/></kanban>`;\n'
            "class A {\n"
            '    static template = xml`<div t-esc="this.x"/>`;\n'
            "}\n"
            'const names = ["t-esc", "t-out"];\n'
        )
        self.assertEqual(t_esc_in_js(source), [3])
