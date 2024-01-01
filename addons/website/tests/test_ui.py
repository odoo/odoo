# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from werkzeug.urls import url_encode

import odoo
import odoo.tests
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiCustomizeTheme(odoo.tests.HttpCase):
    def test_01_attachment_website_unlink(self):
        ''' Some ir.attachment needs to be unlinked when a website is unlink,
            otherwise some flows will just crash. That's the case when 2 website
            have their theme color customized. Removing a website will make its
            customized attachment generic, thus having 2 attachments with the
            same URL available for other websites, leading to singleton errors
            (among other).

            But no all attachment should be deleted, eg we don't want to delete
            a SO or invoice PDF coming from an ecommerce order.
        '''
        Website = self.env['website']
        Page = self.env['website.page']
        Attachment = self.env['ir.attachment']

        website_default = Website.browse(1)
        website_test = Website.create({'name': 'Website Test'})

        # simulate attachment state when editing 2 theme through customize
        custom_url = '/TEST/website/static/src/scss/options/colors/user_theme_color_palette.custom.web.assets_frontend.scss'
        scss_attachment = Attachment.create({
            'name': custom_url,
            'type': 'binary',
            'mimetype': 'text/scss',
            'datas': '',
            'url': custom_url,
            'website_id': website_default.id
        })
        scss_attachment.copy({'website_id': website_test.id})

        # simulate PDF from ecommerce order
        # Note: it will only have its website_id flag if the website has a domain
        # equal to the current URL (fallback or get_current_website())
        so_attachment = Attachment.create({
            'name': 'SO036.pdf',
            'type': 'binary',
            'mimetype': 'application/pdf',
            'datas': '',
            'website_id': website_test.id
        })

        # avoid sql error on page website_id restrict
        Page.search([('website_id', '=', website_test.id)]).unlink()
        website_test.unlink()
        self.assertEqual(Attachment.search_count([('url', '=', custom_url)]), 1, 'Should not left duplicates when deleting a website')
        self.assertTrue(so_attachment.exists(), 'Most attachment should not be deleted')
        self.assertFalse(so_attachment.website_id, 'Website should be removed')


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiHtmlEditor(HttpCaseWithUserDemo):

    def test_html_editor_language(self):
        Page = self.env['website.page']

        default_website = self.env.ref('website.default_website')
        parseltongue = self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.env['res.lang']._activate_lang(parseltongue.code)
        default_website.language_ids += parseltongue
        default_website.default_lang_id = parseltongue.id

        page = Page.create({
            'name': 'Test page',
            'type': 'qweb',
            'arch': '''
                <t t-call="website.layout">
                    <div>rumbler</div>
                </t>
            ''',
            'key': 'test.generic_view',
            'website_id': default_website.id,
            'is_published': True,
            'url': '/test_page',
        })

        page.view_id.update_field_translations('arch_db', {
            parseltongue.code: {
                'rumbler': 'rommelpot',
            }
        })
        self.env.ref('base.user_admin').lang = parseltongue.code
        self.start_tour(self.env['website'].get_client_action_url('/test_page'), 'html_editor_language', login='admin')
        self.assertIn("rumbler", page.view_id.with_context(lang='en_US').arch)
        self.assertIn("rommelpot", page.view_id.with_context(lang='pa_GB').arch)

    def test_html_editor_multiple_templates(self):
        Website = self.env['website']
        View = self.env['ir.ui.view']
        Page = self.env['website.page']

        self.generic_view = View.create({
            'name': 'Generic',
            'type': 'qweb',
            'arch': '''
                <div>content</div>
            ''',
            'key': 'test.generic_view',
        })

        self.generic_page = Page.create({
            'view_id': self.generic_view.id,
            'url': '/generic',
        })

        generic_page = Website.viewref('test.generic_view')
        # Use an empty page layout with oe_structure id for this test
        oe_structure_layout = '''
            <t name="Generic" t-name="test.generic_view">
                <t t-call="website.layout">
                    <div id="oe_structure_test_ui" class="oe_structure oe_empty"/>
                </t>
            </t>
        '''
        generic_page.arch = oe_structure_layout
        oe_structure_layout = generic_page.arch
        self.start_tour(self.env['website'].get_client_action_url('/generic'), 'html_editor_multiple_templates', login='admin')
        self.assertEqual(View.search_count([('key', '=', 'test.generic_view')]), 2, "homepage view should have been COW'd")
        self.assertTrue(generic_page.arch == oe_structure_layout, "Generic homepage view should be untouched")
        self.assertEqual(len(generic_page.inherit_children_ids.filtered(lambda v: 'oe_structure' in v.name)), 0, "oe_structure view should have been deleted when aboutus was COW")
        specific_page = Website.with_context(website_id=1).viewref('test.generic_view')
        self.assertTrue(specific_page.arch != oe_structure_layout, "Specific homepage view should have been changed")
        self.assertEqual(len(specific_page.inherit_children_ids.filtered(lambda v: 'oe_structure' in v.name)), 1, "oe_structure view should have been created on the specific tree")

    def test_html_editor_scss(self):
        self.user_demo.write({
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('website.group_website_designer').id
            ])]
        })
        self.start_tour(self.env['website'].get_client_action_url('/contactus'), 'test_html_editor_scss', login='admin')
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_html_editor_scss_2', login='demo')

    def media_dialog_undraw(self):
        self.start_tour("/", 'website_media_dialog_undraw', login='admin')


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiTranslate(odoo.tests.HttpCase):
    def test_admin_tour_rte_translator(self):
        self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'rte_translator', login='admin', timeout=120)

    def test_translate_menu_name(self):
        lang_en = self.env.ref('base.lang_en')
        parseltongue = self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.env['res.lang']._activate_lang(parseltongue.code)
        default_website = self.env.ref('website.default_website')
        default_website.write({
            'default_lang_id': lang_en.id,
            'language_ids': [(6, 0, (lang_en + parseltongue).ids)],
        })
        new_menu = self.env['website.menu'].create({
            'name': 'Menu to edit',
            'parent_id': default_website.menu_id.id,
            'website_id': default_website.id,
            'url': '/englishURL',
        })

        self.start_tour(self.env['website'].get_client_action_url('/'), 'translate_menu_name', login='admin')

        self.assertNotEqual(new_menu.name, 'value pa-GB', msg="The new menu should not have its value edited, only its translation")
        self.assertEqual(new_menu.with_context(lang=parseltongue.code).name, 'value pa-GB', msg="The new translation should be set")

    def test_snippet_translation(self):
        ResLang = self.env['res.lang']
        parseltongue, fake_user_lang = ResLang.create([{
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        }, {
            'name': 'Fake User Lang',
            'code': 'fu_GB',
            'iso_code': 'fu_GB',
            'url_code': 'fu_GB',
        }])
        ResLang._activate_lang(parseltongue.code)
        ResLang._activate_lang(fake_user_lang.code)
        self.env.ref('base.user_admin').lang = fake_user_lang.code
        self.env.ref('website.s_cover').update_field_translations('arch_db', {
            parseltongue.code: {
                'Contact us': 'Contact us in Parseltongue'
            }
        })
        self.env.ref('web_editor.snippets').update_field_translations('arch_db', {
            fake_user_lang.code: {
                'Save': 'Save in fu_GB',
            }
        })
        website = self.env['website'].create({
            'name': 'website pa_GB',
            'language_ids': [(6, 0, [parseltongue.id])],
            'default_lang_id': parseltongue.id,
        })
        website_2 = self.env['website'].create({
            'name': 'website en_US',
            'language_ids': [(6, 0, [self.env.ref('base.lang_en').id, parseltongue.id])],
            'default_lang_id': parseltongue.id,
        })

        self.start_tour(f"/website/force/{website.id}", 'snippet_translation', login='admin')
        self.start_tour(f"/website/force/{website_2.id}", 'snippet_translation_changing_lang', login='admin')


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_tour_homepage(self):
        self.start_tour("/web", 'homepage', login='admin')

    def test_02_restricted_editor(self):
        self.restricted_editor = self.env['res.users'].create({
            'name': 'Restricted Editor',
            'login': 'restricted',
            'password': 'restricted',
            'groups_id': [(6, 0, [
                self.ref('base.group_user'),
                self.ref('website.group_website_restricted_editor')
            ])]
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'restricted_editor', login='restricted')

    def test_04_website_navbar_menu(self):
        website = self.env['website'].search([], limit=1)
        self.env['website.menu'].create({
            'name': 'Test Tour Menu',
            'url': '/test-tour-menu',
            'parent_id': website.menu_id.id,
            'sequence': 0,
            'website_id': website.id,
        })
        self.start_tour("/", 'website_navbar_menu')

    def test_05_specific_website_editor(self):
        website_default = self.env['website'].search([], limit=1)
        new_website = self.env['website'].create({'name': 'New Website'})

        code = b"document.body.dataset.hello = 'world';"
        attach = self.env['ir.attachment'].create({
            'name': 'EditorExtension.js',
            'mimetype': 'text/javascript',
            'datas': base64.b64encode(code),
        })
        custom_url = '/web/content/%s/%s' % (attach.id, attach.name)
        attach.url = custom_url

        self.env['ir.asset'].create({
            'name': 'EditorExtension',
            'bundle': 'website.assets_wysiwyg',
            'path': custom_url,
            'website_id': new_website.id,
        })
        url_params = url_encode({'path': '/@/'})
        self.start_tour(f'/website/force/{website_default.id}?{url_params}', "generic_website_editor", login='admin')
        self.start_tour(f'/website/force/{new_website.id}?{url_params}', "specific_website_editor", login='admin')

    def test_06_public_user_editor(self):
        website_default = self.env['website'].search([], limit=1)
        self.env['website.page'].search([
            ('url', '=', '/'), ('website_id', '=', website_default.id)
        ], limit=1).arch = """
            <t name="Homepage" t-name="website.homepage">
                <t t-call="website.layout">
                    <textarea class="o_public_user_editor_test_textarea o_wysiwyg_loader"/>
                </t>
            </t>
        """
        self.start_tour("/", "public_user_editor", login=None)

    def test_07_snippet_version(self):
        website_snippets = self.env.ref('website.snippets')
        self.env['ir.ui.view'].create([{
            'name': 'Test snip',
            'type': 'qweb',
            'key': 'website.s_test_snip',
            'arch': """
                <section class="s_test_snip">
                    <t t-snippet-call="website.s_share"/>
                </section>
            """,
        }, {
            'type': 'qweb',
            'inherit_id': website_snippets.id,
            'arch': """
                <xpath expr="//t[@t-snippet='website.s_parallax']" position="after">
                    <t t-snippet="website.s_test_snip" t-thumbnail="/website/static/src/img/snippets_thumbs/s_website_form.svg"/>
                </xpath>
            """,
        }])
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_version', login='admin')

    def test_08_website_style_custo(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_style_edition', login='admin')

    def test_09_website_edit_link_popover(self):
        self.start_tour('/@/', 'edit_link_popover', login='admin')

    def test_10_website_conditional_visibility(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'conditional_visibility_1', login='admin')
        self.start_tour('/web', 'conditional_visibility_2', login='admin')
        self.start_tour(self.env['website'].get_client_action_url('/'), 'conditional_visibility_3', login='admin')
        self.start_tour(self.env['website'].get_client_action_url('/'), 'conditional_visibility_4', login='admin')

    def test_11_website_snippet_background_edition(self):
        self.env['ir.attachment'].create({
            'public': True,
            'type': 'url',
            'url': '/web/image/123/test.png',
            'name': 'test.png',
            'mimetype': 'image/png',
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_background_edition', login='admin')

    def test_12_edit_translated_page_redirect(self):
        lang = self.env['res.lang']._activate_lang('nl_NL')
        self.env['website'].browse(1).write({'language_ids': [(4, lang.id, 0)]})
        self.start_tour("/nl/contactus", 'edit_translated_page_redirect', login='admin')

    def test_13_editor_focus_blur_unit_test(self):
        # TODO this should definitely not be a website python tour test but
        # while waiting for a proper web_editor qunit JS test suite for the
        # editor, it is better than no test at all as this was broken multiple
        # times already.
        self.env["ir.ui.view"].create([{
            'name': 's_focusblur',
            'key': 'website.s_focusblur',
            'type': 'qweb',
            'arch': """
                <section class="s_focusblur bg-success py-5">
                    <div class="container">
                        <div class="row">
                            <div class="col-lg-6 s_focusblur_child1 bg-warning py-5"></div>
                            <div class="col-lg-6 s_focusblur_child2 bg-danger py-5"></div>
                        </div>
                    </div>
                </section>
            """,
        }, {
            'name': 's_focusblur_snippets',
            'mode': 'extension',
            'inherit_id': self.env.ref('website.snippets').id,
            'key': 'website.s_focusblur_snippets',
            'type': 'qweb',
            'arch': """
                <data>
                    <xpath expr="//*[@id='snippet_structure']//t[@t-snippet]" position="before">
                        <t t-snippet="website.s_focusblur"/>
                    </xpath>
                </data>
            """,
        }, {
            'name': 's_focusblur_options',
            'mode': 'extension',
            'inherit_id': self.env.ref('web_editor.snippet_options').id,
            'key': 'website.s_focusblur_options',
            'type': 'qweb',
            'arch': """
                <data>
                    <xpath expr=".">
                        <div data-js="FocusBlurParent" data-selector=".s_focusblur"/>
                        <div data-js="FocusBlurChild1" data-selector=".s_focusblur_child1"/>
                        <div data-js="FocusBlurChild2" data-selector=".s_focusblur_child2"/>
                    </xpath>
                </data>
            """,
        }])

        self.start_tour('/', 'focus_blur_snippets', login='admin')

    def test_14_carousel_snippet_content_removal(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'carousel_content_removal', login='admin')

    def test_15_website_link_tools(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'link_tools', login="admin")

    def test_16_website_edit_megamenu(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'edit_megamenu', login='admin')

    def test_17_website_edit_menus(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'edit_menus', login='admin')

    def test_18_website_snippets_menu_tabs(self):
        self.start_tour('/', 'website_snippets_menu_tabs', login='admin')

    def test_19_website_page_options(self):
        self.start_tour("/web", "website_page_options", login="admin")

    def test_20_snippet_editor_panel_options(self):
        self.start_tour('/@/', 'snippet_editor_panel_options', login='admin')

    def test_21_website_start_cloned_snippet(self):
        self.start_tour('/web', 'website_start_cloned_snippet', login='admin')

    def test_22_website_gray_color_palette(self):
        self.start_tour('/web', 'website_gray_color_palette', login='admin')

    def test_23_website_multi_edition(self):
        self.start_tour('/@/', 'website_multi_edition', login='admin')

    def test_24_snippet_cache_across_websites(self):
        default_website = self.env.ref('website.default_website')
        if self.env['website'].search_count([]) == 1:
            self.env['website'].create({
                'name': 'My Website 2',
                'domain': '',
                'sequence': 20,
            })
        self.env['ir.ui.view'].with_context(website_id=default_website.id).save_snippet(
            name='custom_snippet_test',
            arch="""
                <section class="s_text_block">
                    <div class="custom_snippet_website_1">Custom Snippet Website 1</div>
                </section>
            """,
            thumbnail_url='/website/static/src/img/snippets_thumbs/s_text_block.svg',
            snippet_key='s_text_block',
            template_key='website.snippets')
        self.start_tour('/@/', 'snippet_cache_across_websites', login='admin')

    def test_25_website_edit_discard(self):
        self.start_tour('/web', 'homepage_edit_discard', login='admin')

    def test_26_website_media_dialog_icons(self):
        self.start_tour("/", 'website_media_dialog_icons', login='admin')

    def test_27_website_clicks(self):
        self.start_tour('/web', 'website_click_tour', login='admin')

    def test_28_website_text_edition(self):
        self.start_tour('/@/', 'website_text_edition', login='admin')

    def test_29_website_backend_menus_redirect(self):
        Menu = self.env['ir.ui.menu']
        menu_root = Menu.create({'name': 'Test Root'})
        Menu.create({
            'name': 'Test Child',
            'parent_id': menu_root.id,
            'action': 'ir.actions.act_window,%d' % (self.env.ref('base.open_module_tree').id,),
        })
        self.env.ref('base.user_admin').action_id = self.env.ref('base.menu_administration').id
        self.assertFalse(menu_root.action, 'The top menu should not have an action (or the test/tour will not test anything).')
        self.start_tour('/', 'website_backend_menus_redirect', login='admin')

    def test_30_website_text_animations(self):
        self.start_tour("/", 'text_animations', login='admin')

    def test_website_media_dialog_image_shape(self):
        self.start_tour("/", 'website_media_dialog_image_shape', login='admin')
