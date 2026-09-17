import json
import unittest
from hashlib import sha256
from itertools import zip_longest
from unittest.mock import patch

from lxml import etree as ET
from lxml import html
from lxml.html import builder as h

from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.modules.module import _DEFAULT_MANIFEST, Manifest
from odoo.tests import HttpCase, common, tagged


def attrs(**kwargs):
    return {"data-oe-%s" % key: str(value) for key, value in kwargs.items()}


class TestViewSavingCommon(common.TransactionCase):
    def _create_imd(self, view):
        xml_id = view.key.split(".")
        return self.env["ir.model.data"].create(
            {
                "module": xml_id[0],
                "name": xml_id[1],
                "model": view._name,
                "res_id": view.id,
            }
        )


@tagged("-at_install", "post_install")
class TestCustomizeView(common.HttpCase):
    def url_open_authenticate(self, url, data, login="admin", password="admin"):
        self.authenticate(login, password)
        response = self.url_open(
            url,
            json={"params": {**data, "is_view_data": True}},
            headers={"Content-Type": "application/json"},
        )
        data = json.loads(response.text)
        self.logout()
        return data.get("result")

    def test_disabled_optional_template_t_call(self):
        website = self.env["website"].search([], limit=1)
        View = self.env["ir.ui.view"]
        default = View.create(
            {
                "name": "test_view",
                "type": "qweb",
                "key": "website.test_view",
                "arch_db": "<span>Default</span>",
            }
        )
        custo = View.create(
            {
                "name": "test_view",
                "type": "qweb",
                "key": "website.test_view",
                "website_id": website.id,
                "arch_db": "<span>Customized</span>",
            }
        )
        template = View.create(
            {
                "name": "test_root",
                "type": "qweb",
                "key": "website.test_root",
                "arch_db": """<div><t t-if="is_view_active('website.test_view')"> is active </t><t t-call="website.test_view"/></div>""",
            }
        )
        page = self.env["website.page"].create(
            {
                "view_id": template.id,
                "url": "/test_root",
                "is_published": True,
            }
        )

        website._force()

        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get",
            {"keys": ["website.test_root", "website.test_view"]},
        )
        self.assertEqual(set(actives), {"website.test_root", "website.test_view"})
        self.assertEqual([custo.active, default.active], [True, True])
        self.assertEqual(
            self.url_open(page.url).text,
            "<div> is active <span>Customized</span></div>",
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": [], "disable": ["website.test_view"]},
        )

        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get",
            {"keys": ["website.test_root", "website.test_view"]},
        )
        self.assertEqual(set(actives), {"website.test_root"})
        self.assertEqual([custo.active, default.active], [False, True])
        self.assertEqual(
            self.url_open(page.url).text, "<div><span>Default</span></div>"
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": ["website.test_view"], "disable": []},
        )

        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get",
            {"keys": ["website.test_root", "website.test_view"]},
        )
        self.assertEqual(set(actives), {"website.test_root", "website.test_view"})
        self.assertEqual([custo.active, default.active], [True, True])
        self.assertEqual(
            self.url_open(page.url).text,
            "<div> is active <span>Customized</span></div>",
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": [], "disable": ["website.test_view"]},
        )
        custo.unlink()
        self.assertEqual(
            self.url_open(page.url).text, "<div> is active <span>Default</span></div>"
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": [], "disable": ["website.test_view"]},
        )
        new_custo = View.with_context(active_test=False).search(
            [("key", "=", "website.test_view"), ("website_id", "=", website.id)]
        )
        self.assertEqual(bool(new_custo), True)
        self.assertNotEqual(custo.id, new_custo.id)
        self.assertEqual([new_custo.active, default.active], [False, True])
        self.assertEqual(
            self.url_open(page.url).text, "<div><span>Default</span></div>"
        )

    def test_disabled_optional_template_xpath(self):
        website = self.env.ref("website.default_website")
        View = self.env["ir.ui.view"]
        template = View.create(
            {
                "name": "test_root",
                "type": "qweb",
                "key": "website.test_root",
                "arch_db": """<div><t t-if="is_view_active('website.test_view')"> is active </t></div>""",
            }
        )

        default = View.create(
            {
                "name": "test_view",
                "mode": "extension",
                "inherit_id": template.id,
                "arch_db": '<div position="inside"><span>Default</span></div>',
                "key": "website.test_view",
            }
        )
        custo = View.create(
            {
                "name": "test_view",
                "mode": "extension",
                "inherit_id": template.id,
                "arch_db": '<div position="inside"><span>Customized</span></div>',
                "key": "website.test_view",
                "website_id": website.id,
            }
        )
        page = self.env["website.page"].create(
            {
                "view_id": template.id,
                "url": "/test_root",
                "is_published": True,
            }
        )

        website._force()

        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get",
            {"keys": ["website.test_root", "website.test_view"]},
        )
        self.assertEqual(set(actives), {"website.test_root", "website.test_view"})
        self.assertEqual([custo.active, default.active], [True, True])
        self.assertEqual(
            self.url_open(page.url).text,
            "<div> is active <span>Customized</span></div>",
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": [], "disable": ["website.test_view"]},
        )

        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get",
            {"keys": ["website.test_root", "website.test_view"]},
        )
        self.assertEqual(set(actives), {"website.test_root"})
        self.assertEqual([custo.active, default.active], [False, True])
        self.assertEqual(self.url_open(page.url).text, "<div></div>")

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": ["website.test_view"], "disable": []},
        )

        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get",
            {"keys": ["website.test_root", "website.test_view"]},
        )
        self.assertEqual(set(actives), {"website.test_root", "website.test_view"})
        self.assertEqual([custo.active, default.active], [True, True])
        self.assertEqual(
            self.url_open(page.url).text,
            "<div> is active <span>Customized</span></div>",
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": [], "disable": ["website.test_view"]},
        )
        custo.unlink()
        self.assertEqual(
            self.url_open(page.url).text, "<div> is active <span>Default</span></div>"
        )

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": [], "disable": ["website.test_view"]},
        )
        new_custo = View.with_context(active_test=False).search(
            [("key", "=", "website.test_view"), ("website_id", "=", website.id)]
        )
        self.assertEqual(bool(new_custo), True)
        self.assertNotEqual(custo.id, new_custo.id)
        self.assertEqual([new_custo.active, default.active], [False, True])
        self.assertEqual(self.url_open(page.url).text, "<div></div>")

    def test_enabling_optional_template_with_editor(self):
        website = self.env["website"].search([], limit=1)
        auth = {"login": "test", "password": "testtest"}
        user = self.env["res.users"].create({"name": "test", **auth})
        user.group_ids += self.env.ref("website.group_website_designer")
        View = self.env["ir.ui.view"]
        default = View.create(
            {
                "name": "test_view",
                "type": "qweb",
                "key": "website.test_view",
                "arch_db": "<span>Default</span>",
            }
        )
        custo = View.create(
            {
                "active": False,
                "name": "test_view",
                "type": "qweb",
                "key": "website.test_view",
                "website_id": website.id,
                "arch_db": "<span>Customized</span>",
            }
        )
        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get", {"keys": ["website.test_view"]}, **auth
        )
        self.assertEqual(set(actives), set())
        self.assertEqual([custo.active, default.active], [False, True])

        self.url_open_authenticate(
            "/website/theme_customize_data",
            {"enable": ["website.test_view"], "disable": []},
            **auth,
        )
        actives = self.url_open_authenticate(
            "/website/theme_customize_data_get", {"keys": ["website.test_view"]}, **auth
        )
        self.assertEqual(set(actives), {"website.test_view"})
        self.assertEqual([custo.active, default.active], [True, True])


class TestViewSaving(TestViewSavingCommon):
    def eq(self, a, b):
        self.assertEqual(a.tag, b.tag)
        self.assertEqual(a.attrib, b.attrib)
        self.assertEqual((a.text or "").strip(), (b.text or "").strip())
        self.assertEqual((a.tail or "").strip(), (b.tail or "").strip())
        for ca, cb in zip_longest(a, b):
            self.eq(ca, cb)

    def setUp(self):
        super().setUp()
        self.arch = h.DIV(
            h.DIV(
                h.H3("Column 1"), h.UL(h.LI("Item 1"), h.LI("Item 2"), h.LI("Item 3"))
            ),
            h.DIV(
                h.H3("Column 2"),
                h.UL(
                    h.LI("Item 1"),
                    h.LI(
                        h.SPAN(
                            "My Company",
                            attrs(model="res.company", id=1, field="name", type="char"),
                        )
                    ),
                    h.LI(
                        h.SPAN(
                            "+00 00 000 00 0 000",
                            attrs(
                                model="res.company", id=1, field="website", type="char"
                            ),
                        )
                    ),
                ),
            ),
        )
        self.view_id = self.env["ir.ui.view"].create(
            {
                "name": "Test View",
                "type": "qweb",
                "key": "website.test_view",
                "arch": ET.tostring(self.arch, encoding="unicode"),
            }
        )

    def test_embedded_extraction(self):
        fields = self.env["ir.ui.view"].extract_embedded_fields(self.arch)

        expect = [
            h.SPAN(
                "My Company",
                attrs(model="res.company", id=1, field="name", type="char"),
            ),
            h.SPAN(
                "+00 00 000 00 0 000",
                attrs(model="res.company", id=1, field="website", type="char"),
            ),
        ]
        for actual, expected in zip_longest(fields, expect):
            self.eq(actual, expected)

    def test_embedded_save(self):
        embedded = h.SPAN(
            "+00 00 000 00 0 000",
            attrs(model="res.company", id=1, field="website", type="char"),
        )

        self.env["ir.ui.view"].save_embedded_field(embedded)

        company = self.env["res.company"].browse(1)
        self.assertEqual(company.website, "+00 00 000 00 0 000")

    @unittest.skip(
        "save conflict for embedded (saved by third party or previous version in "
        "page) not implemented - tracked in task 32036"
    )
    def test_embedded_conflict(self):
        e1 = h.SPAN("My Company", attrs(model="res.company", id=1, field="name"))
        e2 = h.SPAN("Leeroy Jenkins", attrs(model="res.company", id=1, field="name"))

        View = self.env["ir.ui.view"]

        View.save_embedded_field(e1)
        with self.assertRaises(Exception):
            View.save_embedded_field(e2)

    def test_embedded_to_field_ref(self):
        View = self.env["ir.ui.view"]
        embedded = h.SPAN("My Company", attrs(expression="bob"))
        self.eq(View.to_field_ref(embedded), h.SPAN({"t-field": "bob"}))

    def test_to_field_ref_keep_attributes(self):
        View = self.env["ir.ui.view"]

        att = attrs(expression="bob", model="res.company", id=1, field="name")
        att["id"] = "whop"
        att["class"] = "foo bar"
        embedded = h.SPAN("My Company", att)

        self.eq(
            View.to_field_ref(embedded),
            h.SPAN({"t-field": "bob", "class": "foo bar", "id": "whop"}),
        )

    def test_replace_arch(self):
        replacement = h.P("Wheee")

        result = self.view_id.replace_arch_section(None, replacement)

        self.eq(result, h.DIV("Wheee"))

    def test_replace_arch_2(self):
        replacement = h.DIV(h.P("Wheee"))

        result = self.view_id.replace_arch_section(None, replacement)

        self.eq(result, replacement)

    def test_fixup_arch(self):
        replacement = h.H1("I am the greatest title alive!")

        result = self.view_id.replace_arch_section("/div/div[1]/h3", replacement)

        self.eq(
            result,
            h.DIV(
                h.DIV(
                    h.H3("I am the greatest title alive!"),
                    h.UL(h.LI("Item 1"), h.LI("Item 2"), h.LI("Item 3")),
                ),
                h.DIV(
                    h.H3("Column 2"),
                    h.UL(
                        h.LI("Item 1"),
                        h.LI(
                            h.SPAN(
                                "My Company",
                                attrs(
                                    model="res.company", id=1, field="name", type="char"
                                ),
                            )
                        ),
                        h.LI(
                            h.SPAN(
                                "+00 00 000 00 0 000",
                                attrs(
                                    model="res.company",
                                    id=1,
                                    field="website",
                                    type="char",
                                ),
                            )
                        ),
                    ),
                ),
            ),
        )

    def test_multiple_xpath_matches(self):
        with self.assertRaises(UserError):
            self.view_id.replace_arch_section("/div/div/h3", h.H6("Lol nope"))

    def test_save(self):
        Company = self.env["res.company"]

        imd = self._create_imd(self.view_id)
        self.assertEqual(self.view_id.model_data_id, imd)
        self.assertFalse(imd.noupdate)

        replacement = ET.tostring(
            h.DIV(
                h.H3("Column 2"),
                h.UL(
                    h.LI("wob wob wob"),
                    h.LI(
                        h.SPAN(
                            "Acme Corporation",
                            attrs(
                                model="res.company",
                                id=1,
                                field="name",
                                expression="bob",
                                type="char",
                            ),
                        )
                    ),
                    h.LI(
                        h.SPAN(
                            "+12 3456789",
                            attrs(
                                model="res.company",
                                id=1,
                                field="website",
                                expression="edmund",
                                type="char",
                            ),
                        )
                    ),
                ),
            ),
            encoding="unicode",
        )

        self.view_id.with_context(website_id=1).save(
            value=replacement, xpath="/div/div[2]"
        )
        self.assertFalse(
            imd.noupdate,
            "view's xml_id shouldn't be set to 'noupdate' in a website context as `save` method will COW",
        )
        self.env["website"].with_context(website_id=1).viewref(
            self.view_id.key
        ).unlink()

        self.view_id.save(value=replacement, xpath="/div/div[2]")

        self.assertTrue(imd.noupdate)

        company = Company.browse(1)
        self.assertEqual(company.name, "Acme Corporation")
        self.assertEqual(company.website, "+12 3456789")
        self.eq(
            ET.fromstring(self.view_id.arch),
            h.DIV(
                h.DIV(
                    h.H3("Column 1"),
                    h.UL(h.LI("Item 1"), h.LI("Item 2"), h.LI("Item 3")),
                ),
                h.DIV(
                    h.H3("Column 2"),
                    h.UL(
                        h.LI("wob wob wob"),
                        h.LI(h.SPAN({"t-field": "bob"})),
                        h.LI(h.SPAN({"t-field": "edmund"})),
                    ),
                ),
            ),
        )

    def test_save_escaped_text(self):
        view = self.env["ir.ui.view"].create(
            {
                "arch": '<t t-name="dummy"><p><h1>hello world</h1></p></t>',
                "type": "qweb",
            }
        )
        replacement = '<script>1 && "hello & world"</script>'
        view.save(replacement, xpath="/t/p/h1")
        self.assertIn(
            replacement.replace("&", "&amp;"),
            view.arch,
            "inline script should be escaped server side",
        )
        self.assertIn(
            replacement,
            self.env["ir.qweb"]._render(view.id),
            "inline script should not be escaped when rendering",
        )
        replacement = "world &amp;amp; &amp;lt;b&amp;gt;cie"
        view.save(replacement, xpath="/t/p")
        self.assertIn(
            replacement, view.arch, "common text node should not be escaped server side"
        )
        self.assertIn(
            replacement,
            str(self.env["ir.qweb"]._render(view.id)).replace("&", "&amp;"),
            "text node characters wrongly unescaped when rendering",
        )

    def test_save_oe_structure_with_attr(self):
        view = (
            self.env["ir.ui.view"]
            .create(
                {
                    "arch": '<t t-name="dummy"><div class="oe_structure" t-att-test="1" data-test="1" id="oe_structure_test"/></t>',
                    "type": "qweb",
                }
            )
            .with_context(website_id=1, load_all_views=True)
        )
        replacement = '<div class="oe_structure" data-test="1" id="oe_structure_test" data-oe-id="55" test="2">hello</div>'
        view.save(replacement, xpath="/t/div")
        self.assertIn(
            '<div class="oe_structure" data-test="1" id="oe_structure_test" test="2">hello</div>',
            view.get_combined_arch(),
            "saved element attributes are saved excluding branding ones",
        )

    def test_save_only_embedded(self):
        Company = self.env["res.company"]
        company_id = 1
        company = Company.browse(company_id)
        company.write({"name": "Foo Corporation"})

        node = html.tostring(
            h.SPAN(
                "Acme Corporation",
                attrs(
                    model="res.company",
                    id=company_id,
                    field="name",
                    expression="bob",
                    type="char",
                ),
            ),
            encoding="unicode",
        )
        View = self.env["ir.ui.view"]
        View.browse(company_id).save(value=node)
        self.assertEqual(company.name, "Acme Corporation")

    def test_cow_of_a_parentless_primary_given_a_parent_is_an_extension(self):
        View = self.env["ir.ui.view"]
        website = self.env.ref("website.default_website")
        base = View.create(
            {
                "name": "cow mode base",
                "type": "qweb",
                "key": "website.cow_mode_base",
                "arch": "<t t-name='website.cow_mode_base'><div/></t>",
            }
        )
        fresh = View.create(
            {
                "name": "cow mode fresh",
                "type": "qweb",
                "key": "website.cow_mode_fresh",
                "arch": "<data/>",
            }
        )
        child = View.create(
            {
                "name": "cow mode child",
                "type": "qweb",
                "key": "website.cow_mode_child",
                "mode": "primary",
                "inherit_id": fresh.id,
                "arch": "<data/>",
            }
        )
        (fresh + child).with_context(website_id=website.id).write(
            {"inherit_id": base.id}
        )
        specific = View.search([("website_id", "=", website.id)])
        by_key = {view.key: view for view in specific}
        self.assertEqual(by_key["website.cow_mode_fresh"].mode, "extension")
        self.assertEqual(by_key["website.cow_mode_child"].mode, "primary")
        self.assertEqual(fresh.mode, "primary", "the generic is untouched")

    def test_field_tail(self):
        replacement = ET.tostring(
            h.LI(
                h.SPAN(
                    "+12 3456789",
                    attrs(
                        model="res.company",
                        id=1,
                        type="char",
                        field="website",
                        expression="edmund",
                    ),
                ),
                "whop whop",
            ),
            encoding="utf-8",
        )
        self.view_id.save(value=replacement, xpath="/div/div[2]/ul/li[3]")

        self.eq(
            ET.fromstring(self.view_id.arch.encode("utf-8")),
            h.DIV(
                h.DIV(
                    h.H3("Column 1"),
                    h.UL(h.LI("Item 1"), h.LI("Item 2"), h.LI("Item 3")),
                ),
                h.DIV(
                    h.H3("Column 2"),
                    h.UL(
                        h.LI("Item 1"),
                        h.LI(
                            h.SPAN(
                                "My Company",
                                attrs(
                                    model="res.company", id=1, field="name", type="char"
                                ),
                            )
                        ),
                        h.LI(h.SPAN({"t-field": "edmund"}), "whop whop"),
                    ),
                ),
            ),
        )


@tagged("-at_install", "post_install")
class TestCowViewSaving(TestViewSavingCommon, HttpCase):
    def setUp(self):
        super().setUp()
        View = self.env["ir.ui.view"]

        self.base_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": "<div>base content</div>",
                "key": "website.base_view",
            }
        ).with_context(load_all_views=True)

        self.inherit_view = View.create(
            {
                "name": "Extension",
                "mode": "extension",
                "inherit_id": self.base_view.id,
                "arch": '<div position="inside">, extended content</div>',
                "key": "website.extension_view",
            }
        )
        self.headers = {"Content-Type": "application/json"}

    def test_cow_on_base_after_extension(self):
        View = self.env["ir.ui.view"]
        self.inherit_view.with_context(website_id=1).write(
            {"name": "Extension Specific"}
        )
        v1 = self.base_view
        v2 = self.inherit_view
        v3 = View.search([("website_id", "=", 1), ("name", "=", "Extension Specific")])
        v4 = self.inherit_view.copy({"name": "Second Extension"})
        v5 = self.inherit_view.copy({"name": "Third Extension (Specific)"})
        v5.write({"website_id": 1})

        self.assertEqual(
            v2.key == v3.key,
            True,
            "Making specific a generic inherited view should copy it's key (just change the website_id)",
        )
        self.assertEqual(
            v3.key != v4.key != v5.key,
            True,
            "Copying a view should generate a new key for the new view (not the case when triggering COW)",
        )
        self.assertEqual(
            "website.extension_view" in v3.key
            and "website.extension_view" in v4.key
            and "website.extension_view" in v5.key,
            True,
            "The copied views should have the key from the view it was copied from but with an unique suffix",
        )

        total_views = View.search_count([])
        v1.with_context(website_id=1).write({"name": "Base Specific"})

        v6 = View.search([("website_id", "=", 1), ("name", "=", "Base Specific")])
        v7 = View.search([("website_id", "=", 1), ("name", "=", "Extension Specific")])
        v8 = View.search([("website_id", "=", 1), ("name", "=", "Second Extension")])
        v9 = View.search(
            [("website_id", "=", 1), ("name", "=", "Third Extension (Specific)")]
        )

        self.assertEqual(
            total_views + 4 - 2,
            View.search_count([]),
            "It should have duplicated the view tree with a website_id, taking only most specific (only specific `b` key), and removing website_specific from generic tree",
        )
        self.assertEqual(
            len((v3 + v5).exists()),
            0,
            "v3 and v5 should have been deleted as they were already specific and copied to the new specific base",
        )
        self.assertEqual((v1 + v2 + v4).mapped("website_id").ids, [])
        self.assertEqual((v2 + v4).mapped("inherit_id"), v1)
        self.assertEqual((v6 + v7 + v8 + v9).mapped("website_id").ids, [1])
        self.assertEqual((v7 + v8 + v9).mapped("inherit_id"), v6)
        self.assertEqual(v6.key == v1.key, True)
        self.assertEqual(v7.key == v2.key, True)
        self.assertEqual(v4.key == v8.key, True)
        self.assertEqual(View.search_count([("key", "=", v9.key)]), 1)

    def test_cow_leaf(self):
        View = self.env["ir.ui.view"]

        self.inherit_view.write(
            {"arch": '<div position="replace"><div>modified content</div></div>'}
        )
        self.assertEqual(View.search_count([("key", "=", "website.base_view")]), 1)
        self.assertEqual(View.search_count([("key", "=", "website.extension_view")]), 1)

        arch = self.base_view.get_combined_arch()
        self.assertEqual(arch, "<div>modified content</div>")

        self.inherit_view.with_context(website_id=1).write(
            {"arch": '<div position="replace"><div>website 1 content</div></div>'}
        )
        inherit_views = View.search([("key", "=", "website.extension_view")])
        self.assertEqual(View.search_count([("key", "=", "website.base_view")]), 1)
        self.assertEqual(len(inherit_views), 2)
        self.assertEqual(len(inherit_views.filtered(lambda v: v.website_id.id == 1)), 1)

        arch = self.base_view.get_combined_arch()
        self.assertEqual(arch, "<div>modified content</div>")
        arch = self.base_view.with_context(website_id=1).get_combined_arch()
        self.assertEqual(arch, "<div>website 1 content</div>")

        inherit_views.filtered(lambda v: v.website_id.id == 1).write({"active": False})
        arch = self.base_view.with_context(website_id=1).get_combined_arch()
        self.assertEqual(arch, "<div>base content</div>")

    def test_cow_root(self):
        View = self.env["ir.ui.view"]

        self.base_view.write({"arch": "<div>modified base content</div>"})
        self.assertEqual(View.search_count([("key", "=", "website.base_view")]), 1)
        self.assertEqual(View.search_count([("key", "=", "website.extension_view")]), 1)

        self.base_view.with_context(website_id=1).write(
            {"arch": "<div>website 1 content</div>"}
        )

        generic_base_view = View.search(
            [("key", "=", "website.base_view"), ("website_id", "=", False)]
        )
        website_specific_base_view = View.search(
            [("key", "=", "website.base_view"), ("website_id", "=", 1)]
        )
        self.assertEqual(len(generic_base_view), 1)
        self.assertEqual(len(website_specific_base_view), 1)

        inherit_views = View.search([("key", "=", "website.extension_view")])
        self.assertEqual(len(inherit_views), 2)
        self.assertEqual(len(inherit_views.filtered(lambda v: v.website_id.id == 1)), 1)

        arch = generic_base_view.with_context(load_all_views=True).get_combined_arch()
        self.assertEqual(arch, "<div>modified base content, extended content</div>")

        arch = website_specific_base_view.with_context(
            load_all_views=True, website_id=1
        ).get_combined_arch()
        self.assertEqual(arch, "<div>website 1 content, extended content</div>")

    def test_cow_generic_view_with_already_existing_specific(self):
        View = self.env["ir.ui.view"]

        base_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": "<div>content</div>",
            }
        )

        total_views = View.with_context(active_test=False).search_count([])
        base_view.with_context(website_id=1).write({"name": "New Name"})
        specific_view = View.search([["name", "=", "New Name"], ["website_id", "=", 1]])
        base_view.with_context(website_id=1).write({"name": "Another New Name"})
        specific_view.active = False
        base_view.with_context(website_id=1).write({"name": "Yet Another New Name"})
        self.assertEqual(
            total_views + 1,
            View.with_context(active_test=False).search_count([]),
            "Subsequent writes should have written on the view copied during first write",
        )

        view_arch = """<t name="Second View" t-name="website.second_view">
                          <t t-call="website.layout">
                            <div id="wrap">
                              <div class="editable_part"/>
                              <div class="container">
                                  <h1>Second View</h1>
                              </div>
                              <div class="editable_part"/>
                            </div>
                          </t>
                       </t>"""
        second_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": view_arch,
            }
        )

        total_views = View.with_context(active_test=False).search_count([])
        second_view.with_context(website_id=1).save(
            '<div class="editable_part" data-oe-id="%s" data-oe-xpath="/t[1]/t[1]/div[1]/div[1]" data-oe-field="arch" data-oe-model="ir.ui.view">First editable_part</div>'
            % second_view.id,
            "/t[1]/t[1]/div[1]/div[1]",
        )
        second_view.with_context(website_id=1).save(
            '<div class="editable_part" data-oe-id="%s" data-oe-xpath="/t[1]/t[1]/div[1]/div[3]" data-oe-field="arch" data-oe-model="ir.ui.view">Second editable_part</div>'
            % second_view.id,
            "/t[1]/t[1]/div[1]/div[3]",
        )
        self.assertEqual(
            total_views + 1,
            View.with_context(active_test=False).search_count([]),
            "Second save should have written on the view copied during first save",
        )

        total_specific_view = View.with_context(active_test=False).search_count(
            [
                ("arch_db", "like", "First editable_part"),
                ("arch_db", "like", "Second editable_part"),
            ]
        )
        self.assertEqual(
            total_specific_view,
            1,
            "both editable_part should have been replaced on a created specific view",
        )

    def test_cow_complete_flow(self):
        View = self.env["ir.ui.view"]
        total_views = View.search_count([])

        self.base_view.write({"arch": "<div>Hi</div>"})
        self.inherit_view.write({"arch": '<div position="inside"> World</div>'})

        arch = self.base_view.with_context(website_id=1).get_combined_arch()
        self.assertIn("Hi World", arch)

        self.base_view.write({"arch": "<div>Hello</div>"})

        arch = self.base_view.with_context(website_id=1).get_combined_arch()
        self.assertIn("Hello World", arch)

        self.base_view.with_context(website_id=1).write({"arch": "<div>Bye</div>"})

        base_specific = View.search(
            [("key", "=", self.base_view.key), ("website_id", "=", 1)]
        ).with_context(load_all_views=True)
        extend_specific = View.search(
            [("key", "=", self.inherit_view.key), ("website_id", "=", 1)]
        )
        self.assertEqual(
            total_views + 2,
            View.search_count([]),
            "Should have copied Base & Extension with a website_id",
        )
        self.assertEqual(self.base_view.key, base_specific.key)
        self.assertEqual(self.inherit_view.key, extend_specific.key)

        extend_specific.write({"arch": '<div position="inside"> All</div>'})

        arch = base_specific.with_context(website_id=1).get_combined_arch()
        self.assertEqual("Bye All" in arch, True)

        self.inherit_view.with_context(website_id=1).write(
            {"arch": '<div position="inside"> Nobody</div>'}
        )

        arch = base_specific.with_context(website_id=1).get_combined_arch()
        self.assertEqual(
            "Bye Nobody" in arch,
            True,
            "Write on generic `inherit_view` should have been diverted to already existing specific view",
        )

        base_arch = self.base_view.get_combined_arch()
        base_arch_w1 = self.base_view.with_context(website_id=1).get_combined_arch()
        self.assertEqual("Hello World" in base_arch, True)
        self.assertEqual(
            base_arch,
            base_arch_w1,
            "Reading a top level view with or without a website_id in the context should render that exact view..",
        )

    def test_cow_cross_inherit(self):
        View = self.env["ir.ui.view"]
        total_views = View.search_count([])

        main_view = View.create(
            {
                "name": "Main View",
                "type": "qweb",
                "arch": "<body>GENERIC<div>A</div></body>",
                "key": "website.main_view",
            }
        ).with_context(load_all_views=True)

        View.create(
            {
                "name": "Child View",
                "mode": "extension",
                "inherit_id": main_view.id,
                "arch": '<xpath expr="//div" position="replace"><div>VIEW<p>B</p></div></xpath>',
                "key": "website.child_view",
            }
        )

        child_view_2 = View.with_context(load_all_views=True).create(
            {
                "name": "Child View 2",
                "mode": "extension",
                "inherit_id": main_view.id,
                "arch": '<xpath expr="//p" position="replace"><span>C</span></xpath>',
                "key": "website.child_view_2",
            }
        )

        child_view_2.with_context(website_id=1).write(
            {"arch": '<xpath expr="//p" position="replace"><span>D</span></xpath>'}
        )
        self.assertEqual(
            total_views + 3 + 1,
            View.search_count([]),
            "It should have created the 3 initial generic views and created a child_view_2 specific view",
        )
        main_view.with_context(website_id=1).write(
            {"arch": "<body>SPECIFIC<div>Z</div></body>"}
        )
        self.assertEqual(
            total_views + 3 + 3,
            View.search_count([]),
            "It should have duplicated the Main View tree as a specific tree and then removed the specific view from the generic tree as no more needed",
        )

        generic_view = View.with_context(website_id=None)._get_template_view(
            "website.main_view"
        )
        specific_view = View.with_context(website_id=1)._get_template_view(
            "website.main_view"
        )
        generic_view_arch = generic_view.with_context(
            load_all_views=True
        ).get_combined_arch()
        specific_view_arch = specific_view.with_context(
            load_all_views=True, website_id=1
        ).get_combined_arch()
        self.assertEqual(
            generic_view_arch, "<body>GENERIC<div>VIEW<span>C</span></div></body>"
        )
        self.assertEqual(
            specific_view_arch,
            "<body>SPECIFIC<div>VIEW<span>D</span></div></body>",
            "Writing on top level view hierarchy with a website in context should write on the view and clone it's inherited views",
        )

    def test_multi_website_view_active(self):
        View = self.env["ir.ui.view"].with_context(active_test=False)
        self.inherit_view.with_context(website_id=1).write({"active": False})

        inherit_view = View._get_template_view(self.inherit_view.key)
        self.assertEqual(
            inherit_view.active,
            True,
            "_get_template_view should return the generic one",
        )
        inherit_view = View.with_context(website_id=1)._get_template_view(
            self.inherit_view.key
        )
        self.assertEqual(
            inherit_view.active,
            False,
            "_get_template_view should return the specific one",
        )

        views = View.with_context(website_id=1).get_related_views(self.base_view.key)
        self.assertEqual(
            views.mapped("active"),
            [True, False],
            "get_related_views should return the specific child",
        )

        view = (
            View.with_context(active_test=False)
            .search([("key", "=", self.inherit_view.key)])
            ._filtered_most_specific()
        )
        self.assertEqual(
            view.active, True, "_filtered_most_specific should return the generic one"
        )
        view = (
            View.with_context(active_test=False, website_id=1)
            .search([("key", "=", self.inherit_view.key)])
            ._filtered_most_specific()
        )
        self.assertEqual(
            view.active, False, "_filtered_most_specific should return the specific one"
        )

    def test_get_related_views_tree(self):
        View = self.env["ir.ui.view"]

        self.base_view.write({"name": "B", "key": "B"})
        self.inherit_view.write({"name": "I", "key": "I"})
        View.create(
            {
                "name": "II",
                "mode": "extension",
                "inherit_id": self.inherit_view.id,
                "arch": '<div position="inside">, sub ext</div>',
                "key": "II",
            }
        )

        self.inherit_view.active = False
        views = View.get_related_views("B")
        self.assertEqual(
            views.mapped("key"),
            ["B", "I"],
            "As 'I' is inactive, 'II' (its own child) should not be returned.",
        )
        self.inherit_view.active = True

        self.inherit_view.with_context(website_id=1).write({"name": "Extension"})
        View.create(
            {
                "name": "II2",
                "mode": "extension",
                "inherit_id": self.inherit_view.id,
                "arch": '<div position="inside">, sub sibling specific</div>',
                "key": "II2",
            }
        )

        views = View.with_context(website_id=1).get_related_views("B")
        self.assertEqual(
            views.mapped("key"),
            ["B", "I", "II"],
            "Should only return the specific tree",
        )

    def test_get_related_views_tree_recursive_t_call_and_inherit_inactive(self):
        View = self.env["ir.ui.view"]
        Website = self.env["website"]

        products = View.create(
            {
                "name": "Products",
                "type": "qweb",
                "key": "_website_sale.products",
                "arch": """
                <div id="products_grid">
                    <t t-call="_website_sale.products_item"/>
                </div>
        """,
            }
        )

        products_item = View.create(
            {
                "name": "Products item",
                "type": "qweb",
                "key": "_website_sale.products_item",
                "arch": """
                <div class="product_price"/>
            """,
            }
        )

        add_to_wishlist = View.create(
            {
                "name": "Wishlist",
                "active": True,
                "customize_show": True,
                "inherit_id": products_item.id,
                "key": "_website_sale_wishlist.add_to_wishlist",
                "arch": """
                <xpath expr="//div[hasclass('product_price')]" position="inside"></xpath>
            """,
            }
        )

        products_list_view = View.create(
            {
                "name": "List View",
                "active": False,
                "customize_show": True,
                "inherit_id": products.id,
                "key": "_website_sale.products_list_view",
                "arch": """
                <div id="products_grid" position="replace">
                    <t t-call="_website_sale.products_item"/>
                </div>
            """,
            }
        )

        views = View.with_context(website_id=1).get_related_views(
            "_website_sale.products"
        )
        self.assertEqual(
            views,
            products + products_item + add_to_wishlist + products_list_view,
            "The four views should be returned.",
        )
        add_to_wishlist.with_context(website_id=1).write({"active": False})
        add_to_wishlist_cow = Website.with_context(website_id=1).viewref(
            add_to_wishlist.key
        )
        views = View.with_context(website_id=1).get_related_views(
            "_website_sale.products"
        )
        self.assertEqual(
            views,
            products + products_item + add_to_wishlist_cow + products_list_view,
            "The generic wishlist view should have been replaced by the COW one.",
        )

    def test_cow_inherit_children_order(self):
        self.inherit_view.copy(
            {
                "name": 'alphabetically before "Extension"',
                "key": "_test.alphabetically_first",
                "arch": '<div position="replace"><p>COMPARE</p></div>',
            }
        )
        self.base_view.with_context(website_id=1).write({"name": "Product (W1)"})

    def test_write_order_vs_cow_inherit_children_order(self):
        View = self.env["ir.ui.view"]
        self.inherit_view.with_context(website_id=1).write(
            {"name": "Specific Inherited View Changed First"}
        )
        specific_view = View.search(
            [("name", "=", "Specific Inherited View Changed First")]
        )
        views = View.browse([self.base_view.id, specific_view.id])
        views.with_context(website_id=1).write({"active": False})
        new_specific_view = View.search(
            [("name", "=", "Specific Inherited View Changed First")]
        )
        self.assertTrue(
            specific_view.id != new_specific_view.id, "Should have a new id"
        )
        self.assertFalse(new_specific_view.active, "Should have been deactivated")

    def test_write_order_vs_cow_inherit_children_order_alt(self):
        View = self.env["ir.ui.view"]
        self.inherit_view.with_context(website_id=1).write(
            {"name": "Specific Inherited View Changed First"}
        )
        specific_view = View.search(
            [("name", "=", "Specific Inherited View Changed First")]
        )
        views = View.browse([specific_view.id, self.base_view.id])
        views.with_context(website_id=1).write({"active": False})
        new_specific_view = View.search(
            [("name", "=", "Specific Inherited View Changed First")]
        )
        self.assertTrue(
            specific_view.id != new_specific_view.id, "Should have a new id"
        )
        self.assertFalse(new_specific_view.active, "Should have been deactivated")

    def test_module_new_inherit_view_on_parent_already_forked(self):
        Website = self.env["website"]
        View = self.env["ir.ui.view"]

        self.base_view.write({"name": "Product", "key": "_website_sale.product"})
        self.base_view.with_context(website_id=1).write({"name": "Product (W1)"})

        View._load_records(
            [
                {
                    "xml_id": "_website_sale_comparison.product_add_to_compare",
                    "values": {
                        "name": "Add to comparison in product page",
                        "mode": "extension",
                        "inherit_id": self.base_view.id,
                        "arch": '<div position="replace"><p>COMPARE</p></div>',
                        "key": "_website_sale_comparison.product_add_to_compare",
                    },
                }
            ]
        )
        View.invalidate_model()

        View._create_all_specific_views(["_website_sale_comparison"])

        specific_view = Website.with_context(load_all_views=True, website_id=1).viewref(
            "_website_sale.product"
        )
        self.assertEqual(
            self.base_view.key,
            specific_view.key,
            "Ensure it is equal as it should be for the rest of the test so we test the expected behaviors",
        )
        specific_view_arch = specific_view.get_combined_arch()
        self.assertEqual(
            specific_view.website_id.id,
            1,
            "Ensure we got specific view to perform the checks against",
        )
        self.assertEqual(
            specific_view_arch,
            "<p>COMPARE</p>",
            "When a module creates an inherited view (on a generic tree), it should also create that view in the specific COW'd tree.",
        )

        View._load_records(
            [
                {
                    "xml_id": "_website_sale_comparison.product_add_to_compare",
                    "values": {
                        "arch": '<div position="replace"><p>COMPARE EDITED</p></div>',
                    },
                }
            ]
        )
        specific_view_arch = (
            Website.with_context(load_all_views=True, website_id=1)
            .viewref("_website_sale.product")
            .get_combined_arch()
        )
        self.assertEqual(
            specific_view_arch,
            "<p>COMPARE EDITED</p>",
            "When a module updates an inherited view (on a generic tree), it should also update the copies of that view (COW).",
        )

        random_views = self.env.ref("website.s_accordion_image") + self.env.ref(
            "website.s_accordion"
        )
        View._load_records(
            [
                {
                    "xml_id": "_website_sale_comparison.product_add_to_compare",
                    "values": {
                        "website_id": None,
                        "inherit_id": random_views[0].id,
                    },
                }
            ]
        )

        w1_specific_child_view = Website.with_context(
            load_all_views=True, website_id=1
        ).viewref("_website_sale_comparison.product_add_to_compare")
        generic_child_view = Website.with_context(load_all_views=True).viewref(
            "_website_sale_comparison.product_add_to_compare"
        )
        self.assertEqual(
            w1_specific_child_view.website_id.id,
            1,
            "website_id is a prohibited field when COWing views during _load_records",
        )
        self.assertEqual(
            generic_child_view.inherit_id,
            random_views[0],
            "prohibited fields only concerned write on COW'd view. Generic should still considere these fields",
        )
        self.assertEqual(
            w1_specific_child_view.inherit_id,
            random_views[0],
            "inherit_id update should be repliacated on cow views during _load_records",
        )

        generic_child_view.inherit_id = self.base_view
        w1_specific_child_view.inherit_id = specific_view

        w1_specific_child_view.inherit_id = random_views[1].id
        View._load_records(
            [
                {
                    "xml_id": "_website_sale_comparison.product_add_to_compare",
                    "values": {
                        "inherit_id": random_views[0].id,
                    },
                }
            ]
        )
        self.assertEqual(
            w1_specific_child_view.inherit_id,
            random_views[1],
            "inherit_id update should not be repliacated on cow views during _load_records if it was manually updated before",
        )

        generic_child_view.inherit_id = self.base_view
        w1_specific_child_view.inherit_id = specific_view

        new_website = Website.create({"name": "New Website"})
        self.base_view.with_context(website_id=new_website.id).write(
            {"name": "Product (new_website)"}
        )
        new_website_specific_child_view = Website.with_context(
            load_all_views=True, website_id=new_website.id
        ).viewref("_website_sale_comparison.product_add_to_compare")
        new_website_specific_child_view.priority = 26
        View._load_records(
            [
                {
                    "xml_id": "_website_sale_comparison.product_add_to_compare",
                    "values": {
                        "priority": 3,
                    },
                }
            ]
        )
        self.assertEqual(
            generic_child_view.priority,
            3,
            "XML update should be written on the Generic View",
        )
        self.assertEqual(
            w1_specific_child_view.priority,
            3,
            "XML update should be written on the specific view if the fields have not been modified on that specific view",
        )
        self.assertEqual(
            new_website_specific_child_view.priority,
            26,
            "XML update should NOT be written on the specific view if the fields have been modified on that specific view",
        )

        self._create_imd(self.base_view)
        self.base_view.invalidate_model()
        View._load_records(
            [
                {
                    "xml_id": "_website_sale.product",
                    "values": {
                        "website_meta_title": "A bug got fixed by updating this field",
                    },
                }
            ]
        )
        all_title_updated = (
            specific_view.website_meta_title
            == self.base_view.website_meta_title
            == "A bug got fixed by updating this field"
        )
        self.assertEqual(
            all_title_updated,
            True,
            "Update on top level generic views should also be applied on specific views",
        )

    def test_module_new_inherit_view_on_parent_already_forked_xpath_replace(self):
        View = self.env["ir.ui.view"]

        base_view = View.create(
            {
                "name": "Main Frontend Layout",
                "type": "qweb",
                "arch": '<t t-call="web.layout"><t t-set="head_website"/></t>',
                "key": "_portal.frontend_layout",
            }
        ).with_context(load_all_views=True)

        inherit_view = View.create(
            {
                "name": "Main layout",
                "mode": "extension",
                "inherit_id": base_view.id,
                "arch": '<xpath expr="//t[@t-set=\'head_website\']" position="replace"><t t-call-assets="assets_summernote" t-js="false" groups="website.group_website_restricted_editor"/></xpath>',
                "key": "_website.layout",
            }
        )

        base_view.with_context(website_id=1).write(
            {"name": "Main Frontend Layout (W1)"}
        )

        View._load_records(
            [
                {
                    "xml_id": "_website_forum.layout",
                    "values": {
                        "name": "Forum Layout",
                        "mode": "primary",
                        "inherit_id": inherit_view.id,
                        "arch": '<xpath expr="//t[@t-call-assets=\'assets_summernote\'][@t-js=\'false\']" position="attributes"><attribute name="groups"/></xpath>',
                        "key": "_website_forum.layout",
                    },
                }
            ]
        )

    def test_multiple_inherit_level(self):
        View = self.env["ir.ui.view"]

        self.inherit_view.website_id = 1
        inherit_view_2 = View.create(
            {
                "name": "Extension 2",
                "mode": "extension",
                "inherit_id": self.inherit_view.id,
                "arch": '<div position="inside">, extended content 2</div>',
                "key": "website.extension_view_2",
                "website_id": 1,
            }
        )

        total_views = View.search_count([])

        self.base_view.with_context(website_id=1).write(
            {"arch": "<div>modified content</div>"}
        )

        self.assertEqual(View.search_count([]), total_views + 1)
        self.assertFalse(self.inherit_view.exists())
        self.assertTrue(inherit_view_2.exists())

        base_specific = View.search(
            [("key", "=", self.base_view.key), ("website_id", "=", 1)]
        ).with_context(load_all_views=True)
        extend_specific = View.search(
            [("key", "=", "website.extension_view"), ("website_id", "=", 1)]
        )
        self.assertEqual(extend_specific.inherit_id, base_specific)
        self.assertEqual(inherit_view_2.inherit_id, extend_specific)

    def test_cow_extension_with_install(self):
        View = self.env["ir.ui.view"]
        v1 = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": "<div>base content</div>",
                "key": "website.base_view_v1",
            }
        ).with_context(load_all_views=True)
        self._create_imd(v1)

        v2 = View.create(
            {
                "name": "Extension",
                "mode": "extension",
                "inherit_id": v1.id,
                "arch": '<div position="inside"><ooo>extended content</ooo></div>',
                "key": "website.extension_view_v2",
            }
        )
        self._create_imd(v2)

        v1.with_context(website_id=1).write({"name": "Extension Specific"})

        original_ready = View.pool.ready
        View.pool.ready = False

        try:
            View._load_records(
                [
                    {
                        "xml_id": "website.extension2_view",
                        "values": {
                            "name": " ---",
                            "mode": "extension",
                            "inherit_id": v1.id,
                            "arch": '<ooo position="replace"><p>EXTENSION</p></ooo>',
                            "key": "website.extension2_view",
                        },
                    }
                ]
            )
        finally:
            View.pool.ready = original_ready

    def test_specific_view_translation(self):
        self.env["res.lang"]._activate_lang("fr_BE")
        self.base_view.with_context(lang="en_US").arch_db = "<div>hello</div>"
        self.base_view.update_field_translations(
            "arch_db", {"fr_BE": {"hello": "bonjour"}}
        )
        self.assertEqual(
            self.base_view.with_context(lang="fr_BE").arch, "<div>bonjour</div>"
        )
        self.base_view.with_context(website_id=1).write({"active": True})
        specific_view = self.base_view._get_views_specific() - self.base_view

        self.assertEqual(
            specific_view.with_context(lang="fr_BE").arch,
            "<div>bonjour</div>",
            "copy on write (COW) also copy existing translations",
        )

        self.base_view.update_field_translations(
            "arch_db", {"fr_BE": {"hello": "salut"}}
        )
        self.assertEqual(
            self.base_view.with_context(lang="fr_BE").arch, "<div>salut</div>"
        )
        self.assertEqual(
            specific_view.with_context(lang="fr_BE").arch,
            "<div>bonjour</div>",
            "updating translation of base view doesn't update specific view",
        )

        self.env["res.lang"]._activate_lang("es_ES")
        specific_view.update_field_translations("arch_db", {"es_ES": {"hello": "hola"}})
        self.assertEqual(
            specific_view.with_context(lang="es_ES").arch, "<div>hola</div>"
        )

        self.env["ir.module.module"]._load_module_terms(
            ["website"], ["en_US", "fr_BE", "es_ES"], overwrite=True
        )

        specific_view.invalidate_model(["arch_db", "arch"])
        self.assertEqual(
            specific_view.with_context(lang="fr_BE").arch,
            "<div>salut</div>",
            "loading module translation copy translation from base to specific view",
        )

        self.assertEqual(
            specific_view.with_context(lang="es_ES").arch,
            "<div>hola</div>",
            "loading module translation should not remove specific translations that are not available on base view",
        )

        self.env["res.lang"]._activate_lang("nl_NL")

        self.env["ir.module.module"]._load_module_terms(
            ["website"], ["nl_NL"], overwrite=True
        )

        specific_view.invalidate_model(["arch_db", "arch"])
        self.assertEqual(
            specific_view.with_context(lang="fr_BE").arch,
            "<div>salut</div>",
            "loading module translation for a specific language should not remove existing translations for other languages",
        )

        self.assertEqual(
            specific_view.with_context(lang="es_ES").arch,
            "<div>hola</div>",
            "loading module translation for a specific language should not remove existing translations for other languages",
        )

    def test_view_to_translate_tag(self):
        fr_BE = self.env["res.lang"]._activate_lang("fr_BE")
        self.base_view.with_context(lang="en_US").arch_db = "<div>hello</div>"
        self.assertFalse(self.base_view.website_id)
        website = self.env["website"].browse(1)
        website.default_lang_id = fr_BE
        self.base_view.with_context(website_id=1).write({"active": True})
        specific_view = self.base_view._get_views_specific() - self.base_view

        with patch(
            "odoo.addons.website.models.ir_http.get_request_website", lambda: website
        ):
            self.base_view.invalidate_recordset()
            self.assertIn(
                "to_translate",
                self.base_view.with_context(lang="en_US", edit_translations=True).arch,
            )
            self.assertIn(
                "translated",
                self.base_view.with_context(lang="fr_BE", edit_translations=True).arch,
            )
            self.base_view.invalidate_recordset()

        self.assertIn(
            "translated",
            self.base_view.with_context(lang="en_US", edit_translations=True).arch,
        )
        self.assertIn(
            "to_translate",
            self.base_view.with_context(lang="fr_BE", edit_translations=True).arch,
        )
        self.base_view.update_field_translations(
            "arch_db", {"fr_BE": {"hello": "bonjour"}}
        )
        self.assertIn(
            "translated",
            self.base_view.with_context(lang="en_US", edit_translations=True).arch,
        )
        self.assertIn(
            "translated",
            self.base_view.with_context(lang="fr_BE", edit_translations=True).arch,
        )

        self.assertIn(
            "to_translate",
            specific_view.with_context(lang="en_US", edit_translations=True).arch,
        )
        self.assertIn(
            "translated",
            specific_view.with_context(lang="fr_BE", edit_translations=True).arch,
        )

    def test_load_module_terms_preserve_delayed_translation(self):
        self.env["res.lang"]._activate_lang("fr_BE")
        base_footer = self.env["ir.ui.view"].search(
            [
                ("key", "=", "website.footer_custom"),
                ("website_id", "=", False),
            ],
            limit=1,
        )
        base_footer.with_context(website_id=1).write({"active": True})
        specific_footer = base_footer._get_views_specific()
        # the specific view is an extension of website.layout and validates
        # against it, website context or not: its arch is a spec
        footer = '<xpath expr="//div[@id=\'footer\']" position="replace">%s</xpath>'
        specific_footer.with_context(lang="en_US").arch_db = footer % "<div>hello</div>"
        specific_footer.update_field_translations(
            "arch_db", {"fr_BE": {"hello": "bonjour"}}
        )

        self.assertEqual(
            specific_footer.with_context(lang="en_US").arch, footer % "<div>hello</div>"
        )
        self.assertEqual(
            specific_footer.with_context(lang="fr_BE").arch,
            footer % "<div>bonjour</div>",
        )

        specific_footer.with_context(delay_translations=True, lang="en_US").arch_db = (
            footer % "<h1>hello</h1>"
        )

        self.assertEqual(
            specific_footer.with_context(lang="en_US").arch, footer % "<h1>hello</h1>"
        )
        self.assertEqual(
            specific_footer.with_context(lang="fr_BE").arch,
            footer % "<div>bonjour</div>",
        )

        self.env["ir.module.module"]._load_module_terms(["website"], ["en_US", "fr_BE"])

        self.assertEqual(
            specific_footer.with_context(lang="en_US").arch, footer % "<h1>hello</h1>"
        )
        self.assertEqual(
            specific_footer.with_context(lang="fr_BE").arch,
            footer % "<div>bonjour</div>",
        )

    def test_soc_complete_flow(self):
        View = self.env["ir.ui.view"]

        View.with_context(website_id=1).create(
            {
                "name": "Name",
                "key": "website.no_website_id",
                "type": "qweb",
                "arch": "<data></data>",
            }
        )
        created_views = View.search([("key", "=", "website.no_website_id")])
        self.assertEqual(len(created_views), 1, "Should only have created one view")
        self.assertEqual(
            created_views.website_id.id,
            1,
            "The created view should be specific to website 1",
        )

        with self.assertRaises(
            ValueError,
            msg="Should not allow to create generic view explicitely from website 1 specific context",
        ):
            View.with_context(website_id=1).create(
                {
                    "name": "Name",
                    "key": "website.explicit_no_website_id",
                    "type": "qweb",
                    "arch": "<data></data>",
                    "website_id": False,
                }
            )

        with self.assertRaises(
            ValueError,
            msg="Should not allow to create specific view for website 2 from website 1 specific context",
        ):
            View.with_context(website_id=1).create(
                {
                    "name": "Name",
                    "key": "website.different_website_id",
                    "type": "qweb",
                    "arch": "<data></data>",
                    "website_id": 2,
                }
            )

    def test_specific_view_module_update_inherit_change(self):
        View = self.env["ir.ui.view"]
        Website = self.env["website"]
        self._create_imd(self.inherit_view)
        self.inherit_view.invalidate_model()
        base_view_2 = self.base_view.copy(
            {"key": "website.base_view2", "arch": "<div>base2 content</div>"}
        )
        self.base_view.with_context(website_id=1).write(
            {"arch": "<div>website 1 content</div>"}
        )
        specific_view = Website.with_context(load_all_views=True, website_id=1).viewref(
            self.base_view.key
        )
        specific_view.inherit_children_ids.with_context(website_id=1).write(
            {"arch": '<div position="inside">, extended content website 1</div>'}
        )
        specific_child_view = Website.with_context(
            load_all_views=True, website_id=1
        ).viewref(self.inherit_view.key)
        self.assertEqual(
            self.base_view.inherit_children_ids,
            self.inherit_view,
            "D should be under A",
        )
        self.assertEqual(
            specific_view.inherit_children_ids,
            specific_child_view,
            "D' should be under A'",
        )
        self.assertFalse(base_view_2.inherit_children_ids, "B should have no child")

        View._load_records(
            [
                {
                    "xml_id": self.inherit_view.key,
                    "values": {
                        "inherit_id": base_view_2.id,
                    },
                }
            ]
        )

        self.assertTrue(
            len(self.base_view.inherit_children_ids)
            == len(specific_view.inherit_children_ids)
            == 0,
            "Child views should now be under view B",
        )
        self.assertEqual(
            len(base_view_2.inherit_children_ids), 2, "D and D' should be under B"
        )
        self.assertTrue(
            self.inherit_view in base_view_2.inherit_children_ids, "D should be under B"
        )
        self.assertTrue(
            specific_child_view in base_view_2.inherit_children_ids,
            "D' should be under B",
        )

    def test_no_cow_on_translate(self):
        self.authenticate("admin", "admin")
        french = self.env["res.lang"]._activate_lang("fr_FR")
        self.env["ir.module.module"]._load_module_terms(["website"], [french.code])
        self.env.registry.clear_cache()

        View = self.env["ir.ui.view"].with_context(lang=french.code, website_id=1)
        old_specific_views = View.search([("website_id", "!=", None)])
        view = self.base_view.with_context(lang=french.code, website_id=1)

        root = html.fromstring(
            self.base_view.arch, parser=html.HTMLParser(encoding="utf-8")
        )
        to_translate = root.text_content()
        sha = sha256(to_translate.encode()).hexdigest()
        payload = self.prepare_rpc_payload(
            {
                "model": view._name,
                "record_id": view.id,
                "field_name": "arch_db",
                "translations": {french.code: {sha: "contenu de base"}},
            }
        )
        self.url_open(
            "/website/field/translation/update",
            data=json.dumps(payload),
            headers=self.headers,
        )
        new_specific_views = View.search([("website_id", "!=", None)])
        self.assertEqual(
            len(old_specific_views),
            len(new_specific_views),
            "No additional specific view must have been created",
        )
        self.assertTrue(
            view.arch.index("contenu de base") > 0,
            "New translation must appear in view",
        )


@tagged("-at_install", "post_install")
class Crawler(HttpCase):
    def setUp(self):
        super().setUp()
        View = self.env["ir.ui.view"]

        self.base_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": "<div>base content</div>",
                "key": "website.base_view",
            }
        ).with_context(load_all_views=True)

        self.inherit_view = View.create(
            {
                "name": "Extension",
                "mode": "extension",
                "inherit_id": self.base_view.id,
                "arch": '<div position="inside">, extended content</div>',
                "key": "website.extension_view",
            }
        )

    def test_get_switchable_related_views(self):
        Website = self.env["website"]

        website_1 = Website.create({"name": "Website 1"})
        website_2 = Website.create({"name": "Website 2"})

        self.base_view.write(
            {"name": "Main Frontend Layout", "key": "_portal.frontend_layout"}
        )
        event_main_view = self.base_view.copy(
            {
                "name": "Events",
                "key": "_website_event.index",
                "arch": '<t t-call="_website.layout"><div>Arch is not important in this test</div></t>',
            }
        )
        self.inherit_view.write({"name": "Main layout", "key": "_website.layout"})

        self.inherit_view.copy(
            {"name": "Sign In", "customize_show": True, "key": "_portal.user_sign_in"}
        )
        view_logo = self.inherit_view.copy(
            {
                "name": "Show Logo",
                "inherit_id": self.inherit_view.id,
                "customize_show": True,
                "key": "_website.layout_logo_show",
            }
        )
        view_logo.copy({"name": "Affix Top Menu", "key": "_website.affix_top_menu"})

        event_child_view = self.inherit_view.copy(
            {
                "name": "Filters",
                "customize_show": True,
                "inherit_id": event_main_view.id,
                "key": "_website_event.event_left_column",
                "priority": 30,
            }
        )
        view_photos = event_child_view.copy(
            {"name": "Photos", "key": "_website_event.event_right_photos"}
        )
        event_child_view.copy(
            {
                "name": "Quotes",
                "key": "_website_event.event_right_quotes",
                "priority": 30,
            }
        )

        event_child_view.copy(
            {
                "name": "Filter by Category",
                "inherit_id": event_child_view.id,
                "key": "_website_event.event_category",
            }
        )
        event_child_view.copy(
            {
                "name": "Filter by Country",
                "inherit_id": event_child_view.id,
                "key": "_website_event.event_location",
            }
        )

        self.env.flush_all()

        self.authenticate("admin", "admin")
        base_url = website_1.get_base_url()

        self.url_open(base_url + "/website/force/%s" % website_2.id)

        url = base_url + "/website/get_switchable_related_views"
        json = {"params": {"key": "_website_event.index"}}
        response = self.url_open(url=url, json=json)
        res = response.json()["result"]

        self.assertEqual(
            [v["name"] for v in res],
            [
                "Sign In",
                "Affix Top Menu",
                "Show Logo",
                "Filters",
                "Photos",
                "Quotes",
                "Filter by Category",
                "Filter by Country",
            ],
            "Sequence should not be taken into account for customize menu",
        )
        self.assertEqual(
            [v["inherit_id"][1] for v in res],
            [
                "Main Frontend Layout",
                "Main layout",
                "Main layout",
                "Events",
                "Events",
                "Events",
                "Filters",
                "Filters",
            ],
            "Sequence should not be taken into account for customize menu (Checking Customize headers)",
        )

        view_logo.with_context(website_id=website_1.id).write(
            {
                "arch": '<div position="inside">, trigger COW, arch is not relevant in this test</div>'
            }
        )

        self.url_open(base_url + "/website/force/%s" % website_1.id)

        url = base_url + "/website/get_switchable_related_views"
        json = {"params": {"key": "_website_event.index"}}
        response = self.url_open(url=url, json=json)
        res = response.json()["result"]
        self.assertEqual(
            [v["name"] for v in res],
            [
                "Sign In",
                "Affix Top Menu",
                "Show Logo",
                "Filters",
                "Photos",
                "Quotes",
                "Filter by Category",
                "Filter by Country",
            ],
            "multi-website COW should not impact customize views order (COW view will have a bigger ID and should not be last)",
        )
        self.assertEqual(
            [v["inherit_id"][1] for v in res],
            [
                "Main Frontend Layout",
                "Main layout",
                "Main layout",
                "Events",
                "Events",
                "Events",
                "Filters",
                "Filters",
            ],
            "multi-website COW should not impact customize views menu header position or split (COW view will have a bigger ID and should not be last)",
        )

        view_photos.with_context(website_id=website_1.id).write(
            {
                "arch": '<div position="inside">, trigger COW, arch is not relevant in this test</div>'
            }
        )

        url = base_url + "/website/get_switchable_related_views"
        json = {"params": {"key": "_website_event.index"}}
        response = self.url_open(url=url, json=json)
        res = response.json()["result"]
        self.assertEqual(
            [v["name"] for v in res],
            [
                "Sign In",
                "Affix Top Menu",
                "Show Logo",
                "Filters",
                "Photos",
                "Quotes",
                "Filter by Category",
                "Filter by Country",
            ],
            "multi-website COW should not impact customize views order (COW view will have a bigger ID and should not be last) (2)",
        )
        self.assertEqual(
            [v["inherit_id"][1] for v in res],
            [
                "Main Frontend Layout",
                "Main layout",
                "Main layout",
                "Events",
                "Events",
                "Events",
                "Filters",
                "Filters",
            ],
            "multi-website COW should not impact customize views menu header position or split (COW view will have a bigger ID and should not be last) (2)",
        )

    def test_multi_website_views_retrieving(self):
        View = self.env["ir.ui.view"]
        Website = self.env["website"]

        website_1 = Website.create({"name": "Website 1"})
        website_2 = Website.create({"name": "Website 2"})

        main_view = View.create(
            {
                "name": "Products",
                "type": "qweb",
                "arch": "<body>Arch is not relevant for this test</body>",
                "key": "_website_sale.products",
            }
        ).with_context(load_all_views=True)

        View.with_context(load_all_views=True).create(
            {
                "name": "Child View W1",
                "mode": "extension",
                "inherit_id": main_view.id,
                "arch": '<xpath expr="//body" position="replace"><body>It is really not relevant!</body></xpath>',
                "key": "_website_sale.child_view_w1",
                "website_id": website_1.id,
                "active": False,
                "customize_show": True,
            }
        )

        theme_view = (
            self.env["theme.ir.ui.view"]
            .with_context(install_filename="/testviews")
            .create(
                {
                    "name": "Products Theme Kea",
                    "mode": "extension",
                    "inherit_id": main_view,
                    "arch": '<xpath expr="//p" position="replace"><span>C</span></xpath>',
                    "key": "_theme_kea_sale.products",
                }
            )
        )
        view_from_theme_view_on_w2 = View.with_context(load_all_views=True).create(
            {
                "name": "Products Theme Kea",
                "mode": "extension",
                "inherit_id": main_view.id,
                "arch": '<xpath expr="//body" position="replace"><body>Really really not important for this test</body></xpath>',
                "key": "_theme_kea_sale.products",
                "website_id": website_2.id,
                "customize_show": True,
            }
        )
        self.env["ir.model.data"].create(
            {
                "module": "_theme_kea_sale",
                "name": "products",
                "model": "theme.ir.ui.view",
                "res_id": theme_view.id,
            }
        )

        with self.assertRaises(MissingError):
            view = View.with_context(website_id=website_1.id)._get_template_view(
                "_theme_kea_sale.products"
            )
        view = View.with_context(website_id=website_2.id)._get_template_view(
            "_theme_kea_sale.products"
        )
        self.assertEqual(
            len(view),
            1,
            "It should find the ir.ui.view with key '_theme_kea_sale.products' on website 2..",
        )
        self.assertEqual(view._name, "ir.ui.view", "..and not a theme.ir.ui.view")

        views = View.with_context(website_id=website_1.id).get_related_views(
            "_website_sale.products"
        )
        self.assertEqual(
            len(views),
            2,
            "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_website_sale.child_view_w1'] should be returned",
        )
        views = View.with_context(website_id=website_2.id).get_related_views(
            "_website_sale.products"
        )
        self.assertEqual(
            len(views),
            2,
            "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_theme_kea_sale.products'] should be returned",
        )

        called_theme_view = (
            self.env["theme.ir.ui.view"]
            .with_context(install_filename="/testviews")
            .create(
                {
                    "name": "Called View Kea",
                    "arch": "<div></div>",
                    "key": "_theme_kea_sale.t_called_view",
                }
            )
        )
        View.create(
            {
                "name": "Called View Kea",
                "type": "qweb",
                "arch": "<div></div>",
                "key": "_theme_kea_sale.t_called_view",
                "website_id": website_2.id,
            }
        ).with_context(load_all_views=True)
        self.env["ir.model.data"].create(
            {
                "module": "_theme_kea_sale",
                "name": "t_called_view",
                "model": "theme.ir.ui.view",
                "res_id": called_theme_view.id,
            }
        )
        view_from_theme_view_on_w2.write(
            {
                "arch": '<xpath expr="//body" position="inside">'
                '<t t-call="_theme_kea_sale.t_called_view"/></xpath>'
            }
        )

        views = View.with_context(website_id=website_1.id).get_related_views(
            "_website_sale.products"
        )
        self.assertEqual(
            len(views),
            2,
            "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_website_sale.child_view_w1'] should be returned (2)",
        )
        views = View.with_context(website_id=website_2.id).get_related_views(
            "_website_sale.products"
        )
        self.assertEqual(
            len(views),
            3,
            "It should not mix apples and oranges, only ir.ui.view ['_website_sale.products', '_theme_kea_sale.products', '_theme_kea_sale.t_called_view'] should be returned",
        )

        self.authenticate("admin", "admin")
        base_url = website_1.get_base_url()

        self.url_open(base_url + "/website/force/%s" % website_2.id)

        url = base_url + "/website/get_switchable_related_views"
        json = {"params": {"key": "_website_sale.products"}}
        response = self.url_open(url=url, json=json)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["result"]),
            1,
            "Only '_theme_kea_sale.products' should be returned as it is the only customize_show related view in website 2 context",
        )
        self.assertEqual(
            response.json()["result"][0]["key"],
            "_theme_kea_sale.products",
            "Only '_theme_kea_sale.products' should be returned",
        )

        self.url_open(base_url + "/website/force/%s" % website_1.id)

        url = base_url + "/website/get_switchable_related_views"
        json = {"params": {"key": "_website_sale.products"}}
        response = self.url_open(url=url, json=json)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["result"]),
            1,
            "Only '_website_sale.child_view_w1' should be returned as it is the only customize_show related view in website 1 context",
        )
        self.assertEqual(
            response.json()["result"][0]["key"],
            "_website_sale.child_view_w1",
            "Only '_website_sale.child_view_w1' should be returned",
        )


@tagged("post_install", "-at_install")
class TestThemeViews(common.TransactionCase):
    def test_inherit_specific(self):
        View = self.env["ir.ui.view"]
        Website = self.env["website"]

        website_1 = Website.create({"name": "Website 1"})

        main_view = View.create(
            {
                "name": "Test Main View",
                "type": "qweb",
                "arch": "<body>Arch is not relevant for this test</body>",
                "key": "_test.main_view",
            }
        ).with_context(load_all_views=True)
        main_view.with_context(website_id=website_1.id).arch = "<body>specific</body>"

        patcher = patch(
            "odoo.modules.Manifest.for_addon",
            return_value=Manifest(
                path="/dummy/test_theme", manifest_content=_DEFAULT_MANIFEST
            ),
        )
        self.startPatcher(patcher)
        test_theme_module = self.env["ir.module.module"].create({"name": "test_theme"})
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "module_test_theme_module",
                "model": "ir.module.module",
                "res_id": test_theme_module.id,
            }
        )
        theme_view = (
            self.env["theme.ir.ui.view"]
            .with_context(install_filename="/testviews")
            .create(
                {
                    "name": "Test Child View",
                    "mode": "extension",
                    "inherit_id": "ir.ui.view,%s" % main_view.id,
                    "arch": '<xpath expr="//body" position="replace"><span>C</span></xpath>',
                    "key": "test_theme.test_child_view",
                }
            )
        )
        self.env["ir.model.data"].create(
            {
                "module": "test_theme",
                "name": "products",
                "model": "theme.ir.ui.view",
                "res_id": theme_view.id,
            }
        )
        test_theme_module.with_context(load_all_views=True)._theme_load(website_1)

        main_views = View.search([("key", "=", "_test.main_view")])
        self.assertEqual(
            len(main_views),
            2,
            "View should have been COWd when writing on its arch in a website context",
        )
        specific_main_view = main_views.filtered(lambda v: v.website_id == website_1)
        specific_main_view_children = specific_main_view.inherit_children_ids
        self.assertEqual(
            specific_main_view_children.name,
            "Test Child View",
            "Ensure theme.ir.ui.view has been loaded as an ir.ui.view into the website..",
        )
        self.assertEqual(
            specific_main_view_children.website_id,
            website_1,
            "..and the website is the correct one.",
        )

        new_arch = (
            '<xpath expr="//body" position="replace"><span>Odoo Change01</span></xpath>'
        )
        theme_view.arch = new_arch
        test_theme_module.with_context(load_all_views=True)._theme_load(website_1)
        self.assertEqual(
            specific_main_view_children.arch,
            new_arch,
            "First time: View arch should receive theme updates.",
        )
        self.assertFalse(specific_main_view_children.arch_updated)
        new_arch = (
            '<xpath expr="//body" position="replace"><span>Odoo Change02</span></xpath>'
        )
        theme_view.arch = new_arch
        test_theme_module.with_context(load_all_views=True)._theme_load(website_1)
        self.assertEqual(
            specific_main_view_children.arch,
            new_arch,
            "Second time: View arch should still receive theme updates.",
        )

        new_arch = '<xpath expr="//body" position="replace"><span>Odoo</span></xpath>'
        specific_main_view_children.arch = new_arch
        theme_view.name = "Test Child View modified"
        test_theme_module.with_context(load_all_views=True)._theme_load(website_1)
        self.assertEqual(
            specific_main_view_children.arch,
            new_arch,
            "View arch shouldn't have been overrided on theme update as it was modified by user.",
        )
        self.assertEqual(
            specific_main_view_children.name,
            "Test Child View modified",
            "View should receive modification on theme update.",
        )


@tagged("post_install", "-at_install")
class TestFirstPageIdBatchCost(common.TransactionCase):
    def test_first_page_id_does_not_query_per_view(self):
        website = self.env["website"].search([], limit=1)
        pages = self.env["website.page"].create(
            [
                {
                    "name": f"batch cost {i}",
                    "url": f"/batch-cost-{i}",
                    "website_id": website.id,
                    "view_id": self.env["ir.ui.view"]
                    .create(
                        {
                            "name": f"batch cost view {i}",
                            "type": "qweb",
                            "key": f"website.batch_cost_view_{i}",
                            "arch": "<t t-name='website.batch_cost'><div/></t>",
                        }
                    )
                    .id,
                }
                for i in range(20)
            ]
        )
        self.env.flush_all()
        views = pages.view_id

        def queries_for(count):
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            views[:count].mapped("first_page_id")
            return self.env.cr.sql_statement_count - before

        small = queries_for(2)
        large = queries_for(20)
        self.assertLessEqual(
            large,
            small,
            f"_compute_first_page_id costs {large} queries for 20 views against "
            f"{small} for 2: it is searching per view. Two sizes rather than one, "
            f"and 2 rather than 1 so a warm cache cannot make it vacuous.",
        )


@tagged("post_install", "-at_install")
class TestSpecificViewResolution(common.TransactionCase):
    """A website-specific view is combined in its own website when the
    context names none: outside one, the generic domain dropped it from its
    own tree, so it resolved without itself and was written unvalidated."""

    def setUp(self):
        super().setUp()
        View = self.env["ir.ui.view"]
        self.base = View.create(
            {
                "name": "resolution base",
                "type": "qweb",
                "key": "website.probe_resolution_base",
                "arch": "<div><span>base</span></div>",
            }
        )
        self.specific = View.create(
            {
                "name": "resolution specific",
                "type": "qweb",
                "key": "website.probe_resolution_specific",
                "inherit_id": self.base.id,
                "website_id": self.env.ref("website.default_website").id,
                "arch": '<xpath expr="//span" position="after"><b>specific</b></xpath>',
            }
        )

    def test_a_specific_view_resolves_in_its_own_website(self):
        self.assertIn("<b>specific</b>", self.specific.get_combined_arch())
        self.assertNotIn("<b>specific</b>", self.base.get_combined_arch())

    def test_a_generic_resolution_pays_no_query_for_the_website(self):
        self.env.invalidate_all()
        with self.assertQueryCount(2):
            self.base.get_combined_arch()

    def test_a_specific_view_is_validated_against_its_tree(self):
        with self.assertRaises(ValidationError):
            self.specific.write(
                {"arch": '<xpath expr="//nope" position="after"><b/></xpath>'}
            )
