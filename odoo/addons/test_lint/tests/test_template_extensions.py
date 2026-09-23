"""Every Owl template extension locates its target in the template it extends.

Owl templates are inherited in the browser, lazily, the first time a template
is rendered (`@web/core/template_inheritance`). An `<xpath>` that matches
nothing is not an asset error and not a load error: it throws inside the owl
lifecycle when the component first renders, so the only thing that notices is
a tour that happens to open that screen. That is how two breaks sat in the tree
unnoticed:

* `web.KanbanView` started rendering `<ViewLayout>` instead of `<Layout>`; the
  commit moved the eight inheritors in `odoo` and `account_online_synchronization`
  kept `//Layout`, so the bank reconciliation screen failed to render whenever
  it was installed -- four account tours red.
* `social`'s post and comment menus moved from Bootstrap's `div.dropdown-menu`
  to `<Dropdown>`/`<DropdownItem>`, and `social_crm` kept inserting its
  "Create Lead" link before `div.dropdown-menu/a[1]`.

This reads every template under `static/src` of every addon on the addons path,
resolves each template with its primary parents and its extensions, and lists
the operations whose target cannot be located. Node lookup mirrors the browser
engine, not the server-side view engine: `hasclass(...)` is the same substring
test on `concat(' ', @class, ' ')`, and a non-xpath operation matches the first
descendant with that tag whose attributes all equal the operation's.

Templates are indexed across bundles, so a name defined in two bundles is
resolved against the last definition read; the gate is a superset check and
cannot see which bundle loads which file.
"""

import copy
import pathlib
import re
import tempfile
from collections import defaultdict

from lxml import etree

from odoo.libs.xml import apply_inheritance_specs
from odoo.tests import tagged
from odoo.tests.common import BaseCase

from . import lint_case

_TEMPLATE_ROOTS = frozenset({"templates", "template", "odoo"})
_HASCLASS = re.compile(r"hasclass\(([^)]*)\)")
_PARSER = etree.XMLParser(remove_comments=True)


def _browser_xpath(expr: str) -> str:
    return _HASCLASS.sub(
        lambda match: " and ".join(
            f"contains(concat(' ', @class, ' '), ' {part.strip()[1:-1]} ')"
            for part in match.group(1).split(",")
        ),
        expr,
    )


def _locate(root: etree._Element, operation: etree._Element):
    if operation.tag == "xpath":
        found = root.xpath(_browser_xpath(operation.get("expr", "")))
        return found[0] if found else None
    wanted = {
        name: value
        for name, value in operation.attrib.items()
        if name != "position" and not name.startswith("data-oe-")
    }
    for element in root.iter(operation.tag):
        if element is not root and all(
            element.get(name) == value for name, value in wanted.items()
        ):
            return element
    return None


def _apply(root: etree._Element, operation: etree._Element) -> etree._Element:
    wrapper = etree.Element("data")
    wrapper.append(copy.deepcopy(operation))
    try:
        return apply_inheritance_specs(root, wrapper)
    except Exception:
        # Located, but mutated in a way the server engine models differently:
        # not a missing target, so not this gate's finding.
        return root


def _index(paths):
    definitions = {}
    extensions = defaultdict(list)
    for path in paths:
        try:
            root = etree.parse(path, _PARSER).getroot()
        except etree.XMLSyntaxError:
            continue
        elements = (
            [el for el in root if isinstance(el.tag, str)]
            if root.tag in _TEMPLATE_ROOTS
            else [root]
        )
        for template in elements:
            parent = template.get("t-inherit")
            if parent and template.get("t-inherit-mode", "primary") == "extension":
                extensions[parent].extend(
                    (path, op) for op in template if isinstance(op.tag, str)
                )
            elif name := template.get("t-name"):
                definitions[name] = template
    return definitions, extensions


def unresolved_extensions(paths) -> list[str]:
    definitions, extensions = _index(paths)
    resolved: dict[str, etree._Element | None] = {}
    findings: list[str] = []

    def resolve(name: str, visiting: frozenset = frozenset()):
        if name in resolved:
            return resolved[name]
        template = definitions.get(name)
        if template is None or name in visiting:
            return None
        parent_name = template.get("t-inherit")
        if parent_name:
            parent = resolve(parent_name, visiting | {name})
            if parent is None:
                resolved[name] = None
                return None
            tree = copy.deepcopy(parent)
            for operation in template:
                if not isinstance(operation.tag, str):
                    continue
                if _locate(tree, operation) is None:
                    target = (
                        operation.get("expr")
                        or etree.tostring(operation).decode()[:120]
                    )
                    findings.append(
                        f"{name}: t-inherit={parent_name!r}: {target} locates nothing"
                    )
                else:
                    tree = _apply(tree, operation)
        else:
            tree = copy.deepcopy(template)
        # Extensions may target nodes another extension adds, and the browser
        # applies them in bundle order this gate cannot see; apply whatever
        # locates until nothing more does, and report only what never did.
        pending = list(extensions.get(name, ()))
        while pending:
            remaining = [(p, op) for p, op in pending if _locate(tree, op) is None]
            for _path, operation in pending:
                if (_path, operation) not in remaining:
                    tree = _apply(tree, operation)
            if len(remaining) == len(pending):
                break
            pending = remaining
        for path, operation in pending:
            target = operation.get("expr") or etree.tostring(operation).decode()[:120]
            findings.append(f"{path}: t-inherit={name!r}: {target} locates nothing")
        resolved[name] = tree
        return tree

    for name in definitions:
        resolve(name)
    for parent, operations in extensions.items():
        if parent not in definitions:
            findings.extend(
                f"{path}: t-inherit={parent!r}: no template of that name"
                for path in {path for path, _op in operations}
            )
    return findings


@tagged("post_install", "-at_install")
class TestTemplateExtensions(lint_case.LintCase):
    def test_every_extension_locates_its_target(self):
        paths = [
            path
            for path in self.iter_module_files("*/static/src/*.xml")
            if "/static/src/lib/" not in path
        ]
        self.assert_ratchet(
            unresolved_extensions(paths),
            "lint_template_extension_target",
            "Owl template extension operation(s) whose target cannot be located",
            "The parent template changed shape under the extension: point the "
            "xpath at the node the parent renders now. The browser throws on "
            "first render, so no test but a tour opening that screen would see it.",
        )


class TestTemplateExtensionLookup(BaseCase):
    def _findings(self, xml: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory, "templates.xml")
            path.write_text(xml, encoding="utf-8")
            return unresolved_extensions([str(path)])

    def test_renamed_parent_node_is_reported(self):
        findings = self._findings(
            """<templates>
                <t t-name="p.Kanban"><ViewLayout><div class="o_kanban"/></ViewLayout></t>
                <t t-inherit="p.Kanban" t-inherit-mode="extension">
                    <xpath expr="//Layout" position="before"><div/></xpath>
                </t>
            </templates>"""
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("//Layout locates nothing", findings[0])

    def test_a_primary_child_operation_that_locates_nothing_is_reported(self):
        findings = self._findings(
            """<templates>
                <t t-name="p.Base"><t t-component="this.props.Renderer" model="this.model"/></t>
                <t t-name="p.Child" t-inherit="p.Base" t-inherit-mode="primary">
                    <t model="model" position="after"><div/></t>
                </t>
            </templates>"""
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("p.Child", findings[0])

    def test_hasclass_matches_like_the_browser(self):
        self.assertFalse(
            self._findings(
                """<templates>
                    <t t-name="p.Screen"><div class="subpads d-flex flex-column"/></t>
                    <t t-inherit="p.Screen" t-inherit-mode="extension">
                        <xpath expr="//div[hasclass('subpads', 'd-flex')]" position="attributes">
                            <attribute name="t-if">ok</attribute>
                        </xpath>
                    </t>
                </templates>"""
            )
        )

    def test_extension_may_target_what_another_extension_added(self):
        self.assertFalse(
            self._findings(
                """<templates>
                    <t t-name="p.Form"><div class="o_form"/></t>
                    <t t-inherit="p.Form" t-inherit-mode="extension">
                        <xpath expr="//span[hasclass('added')]" position="inside"><b/></xpath>
                    </t>
                    <t t-inherit="p.Form" t-inherit-mode="extension">
                        <xpath expr="//div[hasclass('o_form')]" position="inside">
                            <span class="added"/>
                        </xpath>
                    </t>
                </templates>"""
            )
        )

    def test_primary_child_sees_parent_extensions(self):
        self.assertFalse(
            self._findings(
                """<templates>
                    <t t-name="p.Base"><div class="root"/></t>
                    <t t-inherit="p.Base" t-inherit-mode="extension">
                        <xpath expr="//div[hasclass('root')]" position="inside"><i class="icon"/></xpath>
                    </t>
                    <t t-name="p.Child" t-inherit="p.Base" t-inherit-mode="primary">
                        <xpath expr="//i[hasclass('icon')]" position="replace"><em/></xpath>
                    </t>
                </templates>"""
            )
        )
