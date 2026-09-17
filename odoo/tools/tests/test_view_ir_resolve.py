import copy
import unittest

from lxml import etree

from odoo.libs.xml import apply_inheritance_specs
from odoo.tools import view_ir
from odoo.tools.view_ir.patch import Applied, AttrChange, Move, Patch
from odoo.tools.view_ir.resolve import apply_specs

from .test_view_ir_corpus import iter_view_records

BASE = """
<form>
    <header><button name="confirm" type="object"/></header>
    <sheet>
        <group name="main">
            <field name="partner_id"/>
            <field name="date" invisible="state == 'done'"/>
        </group>
        <notebook><page name="lines"><field name="line_ids"/></page></notebook>
    </sheet>
</form>
"""


def specs(xml):
    return etree.fromstring(xml)


def both_ways(base_xml, specs_xml, origin="mod"):
    """The arch the XML combine yields and the one the applied specs yield."""
    xml_result = apply_inheritance_specs(
        etree.fromstring(base_xml), copy.deepcopy(specs(specs_xml))
    )
    applied = Applied(root=view_ir.from_string(base_xml))
    translated = apply_specs(applied, specs(specs_xml), origin)
    fallbacks = [t for t in translated if not isinstance(t, Patch)]
    return xml_result, translated, applied, fallbacks


def canon(element):
    # the whitespace around text is the XML combine's business (it moves the
    # target's trailing whitespace past what it inserts), not the tree's
    element = copy.deepcopy(element)
    for el in element.iter():
        if not isinstance(el.tag, str):
            continue
        el.text = (el.text or "").strip() or None
        el.tail = (el.tail or "").strip() or None
    return view_ir.canonical(element)


class TestTranslateSpecs(unittest.TestCase):
    def test_every_position_translates_and_matches_the_xml_combine(self):
        xml_result, translated, applied, fallbacks = both_ways(
            BASE,
            """
            <data>
                <field name="partner_id" position="after"><field name="ref"/></field>
                <xpath expr="//field[@name='date']" position="attributes">
                    <attribute name="invisible" add="not ref" separator="or"/>
                    <attribute name="string">Date</attribute>
                </xpath>
                <xpath expr="//group[@name='main']" position="inside">
                    <field name="note"/>
                </xpath>
                <xpath expr="//page[@name='lines']" position="before">
                    <page name="first" string="First"/>
                </xpath>
                <xpath expr="//header" position="replace" mode="inner">
                    <button name="cancel" type="object"/>
                </xpath>
                <xpath expr="//page[@name='lines']" position="after">
                    <field name="ref" position="move"/>
                </xpath>
                <xpath expr="//field[@name='line_ids']" position="replace">
                    <div class="wrap">$0</div>
                </xpath>
            </data>
            """,
        )
        self.assertEqual(fallbacks, [])
        self.assertEqual(
            [p.op for p in translated],
            [
                "after",
                "attributes",
                "inside",
                "before",
                "replace_inner",
                "after",
                "replace",
            ],
        )
        self.assertEqual(
            [p.target for p in translated],
            [
                "field:partner_id",
                "field:date",
                "group:main",
                "page:lines",
                "header",
                "page:lines",
                "field:line_ids",
            ],
        )
        self.assertEqual(
            translated[1].attributes,
            (
                AttrChange("invisible", add="not ref", separator="or"),
                AttrChange("string", value="Date"),
            ),
        )
        self.assertEqual(translated[5].content, (Move("field:ref"),))
        self.assertTrue(all(p.origin == "mod" for p in translated))
        self.assertEqual(canon(view_ir.to_arch(applied.root)), canon(xml_result))
        ids = view_ir.identify(applied.root)
        self.assertEqual(ids["field:note"].origin, "mod")
        # `ref` was inserted by this view's first spec, then moved: still its
        self.assertEqual(ids["field:ref"].origin, "mod")
        self.assertIsNone(ids["field:partner_id"].origin)

    def test_a_spec_the_ids_cannot_name_applies_the_xml_way(self):
        specs_xml = """
            <data>
                <xpath expr="//field[@name='date']" position="replace">
                    <div>before $0 after</div>
                </xpath>
                <xpath expr="//sheet" position="after"><footer/></xpath>
                <xpath expr="//header" position="after"><div class="x"/></xpath>
            </data>
        """
        xml_result, translated, applied, _fallbacks = both_ways(BASE, specs_xml)
        # the `$0` in running text stays an element and applies the XML way;
        # what follows still translates, against the tree it left
        self.assertEqual(
            [type(t).__name__ for t in translated], ["_Element", "Patch", "Patch"]
        )
        self.assertEqual(translated[1].target, "sheet")
        self.assertEqual(canon(view_ir.to_arch(applied.root)), canon(xml_result))
        # provenance survives the XML-applied spec: the base keeps none, the
        # nodes the specs put in are the overlay's
        ids = view_ir.identify(applied.root)
        self.assertIsNone(ids["field:partner_id"].origin)
        self.assertEqual(ids["footer"].origin, "mod")
        self.assertEqual([div.origin for div in applied.root.find("div")], ["mod"] * 2)

    def test_a_spec_the_xml_combine_refuses_is_raised_as_it_reports_it(self):
        applied = Applied(root=view_ir.from_string(BASE))
        with self.assertRaisesRegex(ValueError, "cannot be located in parent view"):
            apply_specs(
                applied,
                specs(
                    """
                    <data>
                        <xpath expr="//sheet" position="after"><footer/></xpath>
                        <xpath expr="//field[@name='nope']" position="after"><div/></xpath>
                    </data>
                    """
                ),
                "mod",
            )
        # the spec before it was applied; the tree is what the XML combine
        # would have left at the refusal
        self.assertIsNotNone(next(applied.root.find("footer"), None))

    def test_the_xml_way_may_replace_the_root(self):
        xml_result, translated, applied, _fallbacks = both_ways(
            BASE,
            """
            <data>
                <xpath expr="//sheet" position="after"><footer/></xpath>
                <xpath expr="/form" position="replace">
                    <form string="wrapped">see $0 here</form>
                </xpath>
                <xpath expr="//form" position="inside"><div class="late"/></xpath>
            </data>
            """,
        )
        self.assertEqual(
            [type(t).__name__ for t in translated], ["Patch", "_Element", "Patch"]
        )
        self.assertEqual(applied.root.attrs.get("string"), "wrapped")
        self.assertEqual(canon(view_ir.to_arch(applied.root)), canon(xml_result))
        ids = view_ir.identify(applied.root)
        self.assertEqual(ids["form"].origin, "mod")
        self.assertEqual(ids["div"].origin, "mod")

    def test_the_xml_way_goes_through_the_caller(self):
        seen = []

        def apply_xml(source, spec):
            seen.append(spec.get("expr"))
            return apply_inheritance_specs(source, spec)

        applied = Applied(root=view_ir.from_string(BASE))
        translated = apply_specs(
            applied,
            specs(
                """
                <data>
                    <xpath expr="//sheet" position="after"><footer/></xpath>
                    <xpath expr="//field[@name='date']" position="replace">
                        <div>before $0 after</div>
                    </xpath>
                </data>
                """
            ),
            "mod",
            apply_xml,
        )
        self.assertEqual(seen, ["//field[@name='date']"])
        self.assertEqual([type(t).__name__ for t in translated], ["Patch", "_Element"])

    def test_later_specs_address_the_tree_the_earlier_ones_left(self):
        xml_result, translated, applied, fallbacks = both_ways(
            BASE,
            """
            <data>
                <xpath expr="//sheet" position="inside"><group name="extra"/></xpath>
                <xpath expr="//group[@name='extra']" position="inside"><field name="x"/></xpath>
                <xpath expr="//field[@name='x']" position="attributes">
                    <attribute name="readonly">1</attribute>
                </xpath>
            </data>
            """,
        )
        self.assertEqual(fallbacks, [])
        self.assertEqual(
            [p.target for p in translated], ["sheet", "group:extra", "field:x"]
        )
        self.assertEqual(canon(view_ir.to_arch(applied.root)), canon(xml_result))


class TestTranslateCorpus(unittest.TestCase):
    """Every inherited view the checkout ships, applied to its primary both
    ways — the XML combine and the translated patches — yields the same arch."""

    def test_translated_patches_match_the_xml_combine(self):
        spec = view_ir.schema()
        records = {
            xmlid: (path, top, parent)
            for path, xmlid, top, parent in iter_view_records()
        }
        primaries = {
            x for x, (_p, top, _par) in records.items() if spec.view_type_of(top.tag)
        }
        translated = matched = fallback = mismatched = 0
        problems = []
        for xmlid, (path, top, parent) in records.items():
            if parent not in primaries or spec.view_type_of(top.tag):
                continue
            _ppath, ptop, _ = records[parent]
            base_xml = etree.tostring(ptop)
            specs_tree = copy.deepcopy(top)
            try:
                xml_result = apply_inheritance_specs(
                    etree.fromstring(base_xml), copy.deepcopy(specs_tree)
                )
            except ValueError, etree.XPathError:
                continue  # not resolvable against the primary alone
            applied = Applied(root=view_ir.from_string(base_xml))
            items = apply_specs(applied, specs_tree, xmlid)
            if any(not isinstance(item, Patch) for item in items):
                fallback += 1
                continue
            translated += 1
            if canon(view_ir.to_arch(applied.root)) == canon(xml_result):
                matched += 1
            else:
                mismatched += 1
                problems.append(f"{path.relative_to(path.parents[3])}#{xmlid}")
        self.assertGreater(translated, 500, (translated, fallback))
        self.assertEqual(problems[:10], [], (translated, matched, fallback, mismatched))
        self.assertEqual(mismatched, 0)
