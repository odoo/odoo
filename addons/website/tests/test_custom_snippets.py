# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCustomSnippet(TransactionCase):
    def test_translations_custom_snippet(self):
        ResLang = self.env['res.lang']
        View = self.env['ir.ui.view']

        # 1. Setup website and languages
        parseltongue = ResLang.create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        ResLang._activate_lang(parseltongue.code)
        website = self.env.ref('website.default_website')
        website.language_ids = [Command.link(parseltongue.id)]
        data_name_attr = "Custom Text Block Test Translations"
        data_name_attr2 = "Custom Title Test Translations"
        # Note that `s_custom_snippet` is supposed to be added by the JS when
        # sending a snippet arch to the `save_snippet` python method.
        # Adding it here to mimick the real flow, but at this point it really is
        # just a regular snippet.
        snippet_arch = f"""
            <section class="s_text_block s_custom_snippet" data-name="{data_name_attr}">
                <div class="custom_snippet_website_1">English Text</div>
            </section>
        """
        snippet_arch2 = f"""
            <section class="s_title s_custom_snippet" data-name="{data_name_attr2}">
                <h1 class="custom_snippet_website_1">English Title</h1>
            </section>
        """

        # 2. Create a view containing a snippet and translate it
        view1 = View.create({
            'name': 'Specific View Test Translation 1',
            'type': 'qweb',
            'arch': f'''
                <body><p>Hello</p><div>{snippet_arch}</div><h1>World</h1><div>{snippet_arch2}</div></body>
            ''',
            'key': 'test.specific_view_test_translation_1',
            'website_id': website.id,
        })
        view1.update_field_translations('arch_db', {
            parseltongue.code: {
                'English Text': 'Texte Francais',
                'English Title': 'Titre Francais',
            }
        })
        self.assertIn('Titre Francais', view1.with_context(lang=parseltongue.code).arch)
        self.assertIn('Texte Francais', view1.with_context(lang=parseltongue.code).arch)

        # 3. Save the snippet as custom snippet and ensure it is translated
        self.env['ir.ui.view'].with_context(
            website_id=website.id,
            model=view1._name,
            # `arch` is not the field in DB (it's a compute), this is also
            # testing that it works in such cases (raw sql query would fail)
            field='arch',
            resId=view1.id,
        ).save_snippet(
            name=data_name_attr,
            arch=snippet_arch,
            thumbnail_url='/website/static/src/img/snippets_thumbs/s_text_block.svg',
            snippet_key='s_text_block',
            template_key='website.snippets'
        )
        custom_snippet_view = View.search([('name', '=', data_name_attr)], limit=1)
        self.assertIn(
            'Texte Francais',
            custom_snippet_view.with_context(lang=parseltongue.code).arch)

        self.env['ir.ui.view'].with_context(
            website_id=website.id,
            model=view1._name,
            # `arch` is not the field in DB (it's a compute), this is also
            # testing that it works in such cases (raw sql query would fail)
            field='arch',
            resId=view1.id,
        ).save_snippet(
            name=data_name_attr2,
            arch=snippet_arch2,
            thumbnail_url='/website/static/src/img/snippets_thumbs/s_text_block.svg',
            snippet_key='s_text_block',
            template_key='website.snippets'
        )
        custom_snippet_view = View.search([('name', '=', data_name_attr2)], limit=1)
        self.assertIn(
            'Titre Francais',
            custom_snippet_view.with_context(lang=parseltongue.code).arch)

        # 4. Simulate snippet being dropped in another page/view and ensure
        #    it is translated
        view2 = View.create({
            'name': 'Specific View Test Translation 2',
            'type': 'qweb',
            'arch': '<body><div/><div/></body>',
            'key': 'test.specific_view_test_translation_2',
            'website_id': website.id,
        })
        view2.save(f"<div>{snippet_arch}</div>", xpath='/body[1]/div[1]')
        view2.save(f"<div>{snippet_arch2}</div>", xpath='/body[1]/div[2]')
        self.assertIn(
            'Titre Francais',
            view2.with_context(lang=parseltongue.code).arch)
        self.assertIn(
            'Texte Francais',
            view2.with_context(lang=parseltongue.code).arch)

        # 5. Simulate snippet being dropped in another model field and ensure
        #    it is translated
        mega_menu = self.env['website.menu'].create({
            'name': 'Meaga Menu Test Translation 1',
            'mega_menu_content': '<body><div/></body>',
        })
        view2.save(f'''
            <div data-oe-xpath="/body[1]/div[1]" data-oe-model="website.menu"
                 data-oe-id="{mega_menu.id}" data-oe-field="mega_menu_content" data-oe-type="html"
                 data-oe-expression="submenu.mega_menu_content">
                {snippet_arch}
            </div>
        ''', xpath='/body[1]/div[1]')
        self.assertIn(
            'English Text',
            mega_menu.mega_menu_content)

        # Side test: this is testing that saving a custom snippet from a record
        # which is not an ir.ui.view works fine.
        # Indeed, it's a more complexe case as it's basically copying
        # translations from Model1.Field1 to Model2.Field2 -> different model
        # and different field.
        mega_menu.mega_menu_content = f'<div>{snippet_arch}</div>'
        mega_menu.update_field_translations('mega_menu_content', {
            parseltongue.code: {
                'English Text': 'Texte Francais',
            }
        })

        self.env['ir.ui.view'].with_context(
            website_id=website.id,
            model=mega_menu._name,
            field='mega_menu_content',
            resId=mega_menu.id,
        ).save_snippet(
            name='Test Translation MegaMenu',
            arch=snippet_arch,
            thumbnail_url='/website/static/src/img/snippets_thumbs/s_text_block.svg',
            snippet_key='s_text_block',
            template_key='website.snippets'
        )
        custom_snippet_view = View.search([('name', '=', 'Test Translation MegaMenu')], limit=1)
        self.assertIn(
            'Texte Francais',
            custom_snippet_view.with_context(lang=parseltongue.code).arch)

        # Check that a translated page/view with a custom snippet won't copy
        # the translation from the saved custom view for the terms that are
        # "already translated".
        view = View.create({
            'name': 'Custom Snippet Test View',
            'type': 'qweb',
            'arch': """
                <body>
                    <section class="s_title">
                        <h1>English Text</h1>
                    </section>
                    <div/>
                </body>
            """,
            'key': 'test.custom_snippet_test_view',
            'website_id': website.id,
        })

        view.update_field_translations('arch_db', {
           parseltongue.code: {
                'English Text': 'Parseltongue Text',
            }
        })
        self.assertIn(
            'Parseltongue Text',
            view.with_context(lang=parseltongue.code).arch)

        view.save(f'<div>{snippet_arch}</div>', xpath='/body[1]/div[1]')
        self.assertIn(
            'Parseltongue Text',
            view.with_context(lang=parseltongue.code).arch)


@tagged('post_install', '-at_install')
class TestHttpCustomSnippet(HttpCase):
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
