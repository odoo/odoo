# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestCustomSnippet(HttpCase):
    def test_editable_root_as_custom_snippet(self):
        View = self.env['ir.ui.view']
        Page = self.env['website.page']

        custom_page_view = View.create({
            'name': 'Custom Page View',
            'type': 'qweb',
            'key': 'test.custom_page_view',
            'arch': """
                <t t-call="website.layout">
                    <section class="s_title custom" data-snippet="s_title">
                        <div class="container">
                            Some section in a snippet which is an editable root
                            (holds the branding).
                        </div>
                    </section>
                </t>
            """,
        })
        custom_page = Page.create({
            'view_id': custom_page_view.id,
            'url': '/custom-page',
        })

        self.start_tour(f'{custom_page.url}?enable_editor=1', 'editable_root_as_custom_snippet', login='admin')
