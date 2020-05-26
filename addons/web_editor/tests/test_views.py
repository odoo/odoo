# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import deepcopy

from lxml import etree

from odoo.tests import TransactionCase


class TestViews(TransactionCase):
    def test_infinite_inherit_loop(self):
        # Creates an infinite loop: A t-call B and A inherit from B
        View = self.env['ir.ui.view']
        first_view = View.create({
            'name': 'Test View 1',
            'type': 'qweb',
            'arch': '<div>Hello World</div>',
            'key': 'web_editor.test_first_view',
        })
        second_view = View.create({
            'name': 'Test View 2',
            'type': 'qweb',
            'arch': '<t t-call="web_editor.test_first_view"/>',
            'key': 'web_editor.test_second_view',
        })
        second_view.write({
            'inherit_id': first_view.id,
        })
        # Test for RecursionError: maximum recursion depth exceeded in this function
        View._views_get(first_view)

    def test_oe_structure_specific_inheritance(self):
        """Check oe_structure nodes can be correctly found."""
        self.patch(self.registry, "_init", False)
        View = self.env["ir.ui.view"].with_context(inherit_branding=True)
        # A base view with editable sections
        base = View.create(
            {
                "name": "Base view",
                "type": "qweb",
                "key": "web_editor.test_base",
                "arch": """
                    <t t-name="web_editor.test_base">
                        <div id="wrap">
                            <div id="oe_structure_first" class="oe_structure"/>
                            <div>Random middle content</div>
                            <div id="oe_structure_second" class="oe_structure"/>
                        </div>
                    </t>
                    """,
            },
        )
        # Some submodule extends above view and would make original xpath
        # for #oe_structure_second fail
        View.create(
            {
                "name": "Extension view",
                "type": "qweb",
                "inherit_id": base.id,
                "key": "web_editor.test_extension",
                "arch": """
                    <xpath expr="//*[@id='oe_structure_first']" position="after">
                        <div t-field="user.name"/>
                    </xpath>
                    """,
            }
        )
        # User browses that site
        before = etree.fromstring(
            View.render_template(base.id, {"user": self.env.user})
        )
        # User changes each oe_structure
        for n, section in enumerate(before.xpath("//*[hasclass('oe_structure')]")):
            view = self.env[section.get("data-oe-model")].browse(
                int(section.get("data-oe-id"))
            )
            new_section = deepcopy(section)
            new_section.text = "Modified content {}".format(n)
            view.save(etree.tostring(new_section), section.get("data-oe-xpath"))
        # User browses again
        after = etree.fromstring(View.render_template(base.id, {"user": self.env.user}))
        # Assert modifications are saved correctly
        for n, section in enumerate(after.xpath("//*[hasclass('oe_structure')]")):
            self.assertEqual(section.text, "Modified content {}".format(n))
