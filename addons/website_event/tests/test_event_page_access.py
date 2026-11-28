# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import JsonRpcException
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_event.tests.common import OnlineEventCase


@tagged('post_install', '-at_install')
class TestEventPageAccess(OnlineEventCase):
    """ Event managers, as restricted editors, can edit the pages and sub-menus of the events they
    can write on, without designer rights. Shared templates, the event menu itself and
    the pages and menus of other events stay out of reach. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.company_other = cls.env['res.company'].create({'name': 'Other Company'})
        event_values = {
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
        }
        cls.event = cls.env['event.event'].create({**event_values, 'name': 'Event', 'company_id': cls.company_admin.id})
        cls.event_other = cls.env['event.event'].create({**event_values, 'name': 'Other Event', 'company_id': cls.company_other.id})
        cls.event_page = cls.event.introduction_menu_ids.view_id

        cls.user_event_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            groups='base.group_user,event.group_event_manager',
            login='user_event_page_manager',
        )
        cls.user_event_editor = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            groups='base.group_user,event.group_event_user,website.group_website_restricted_editor',
            login='user_event_page_editor',
        )
        cls.user_event_desk = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            groups='base.group_user,event.group_event_registration_desk,website.group_website_restricted_editor',
            login='user_event_page_desk',
        )

        cls.div_edited_content = '<div class="oe_structure oe_structure_solo"><p>Edited content</p></div>'
        cls.div_dropped_block = '<div class="oe_structure oe_empty" id="oe_structure_website_event_intro_1"><p>Dropped block</p></div>'
        cls.div_specific_block = '<div class="oe_structure oe_empty" id="oe_structure_website_event_intro_2"><p>Specific block</p></div>'

    def _save_as_user(self, view, value, user=None, xpath='/t/t/div[2]'):
        view.with_user(user).with_context(website_id=self.website.id).save(value, xpath=xpath)

    def _get_page_view(self, view):
        return self.env['ir.ui.view'].search([('key', '=', view.key), ('website_id', '=', self.website.id)])

    def _save_menus(self, menus_data, user=None):
        return self.env['website.menu'].with_user(user or self.user_event_manager).save(
            self.website.id, {'data': menus_data})

    def test_event_page_edit(self):

        # Simple content edit
        self._save_as_user(self.event_page, self.div_edited_content, user=self.user_event_manager)
        self.assertIn('Edited content', self._get_page_view(self.event_page).arch)

        # Blocks dropped in an 'oe_structure'
        self._save_as_user(self.event_page, self.div_dropped_block, user=self.user_event_manager, xpath='/t/t/div[1]')
        self.assertIn('Dropped block', self._get_page_view(self.event_page).inherit_children_ids.arch)

        # Translations of the page content
        self.env['res.lang']._activate_lang('fr_FR')
        self.event_page.with_user(self.user_event_manager).update_field_translations(
            'arch_db', {'fr_FR': {'Introduction': 'Présentation'}})
        self.assertIn('Présentation', self.event_page.with_context(lang='fr_FR').arch_db)

        # Pages of a duplicated event
        page_view_copy = self.event.copy().introduction_menu_ids.view_id
        self._save_as_user(page_view_copy, self.div_edited_content, user=self.user_event_manager)
        self.assertIn('Edited content', self._get_page_view(page_view_copy).arch)

    def test_event_page_edit_website_specific(self):
        page_copy = self.event_page.copy({'website_id': self.website.id, 'key': self.event_page.key})
        self._save_as_user(page_copy, self.div_specific_block, user=self.user_event_manager, xpath='/t/t/div[3]')
        self.assertIn('Specific block', page_copy.inherit_children_ids.arch)

    def test_event_page_edit_forbidden(self):

        event_other_page = self.event_other.introduction_menu_ids.view_id
        layout = self.env.ref('website_event.layout')
        layout_specific = layout.copy({'website_id': self.website.id, 'key': layout.key})
        register_page = self.env.ref('website_event.event_description_full')

        for user, view, xpath in (
            (self.user_event_manager, event_other_page, '/t/t/div[2]'),     # Other company
            (self.user_event_manager, layout, '/t/t/div'),                  # Template shared by all events
            (self.user_event_manager, layout_specific, '/t/t/div'),         # Website-specific copy of the shared template
            (self.user_event_manager, register_page, '/t'),                 # Standard page shared by all events
            (self.user_event_editor, self.event_page, '/t/t/div[2]'),       # Restricted editor, but not event manager
            (self.user_event_desk, self.event_page, '/t/t/div[2]'),         # No write access on the event
        ):
            with self.subTest(user=user.login, view=view.key), self.assertRaises(AccessError):
                self._save_as_user(view, self.div_edited_content, user=user, xpath=xpath)

        # Only the website builder flow is allowed, not a direct write
        with self.assertRaises(AccessError):
            self.event_page.with_user(self.user_event_manager).write({'arch': self.event_page.arch})

        # fields embedded in the page are saved with the rights of the user
        company_name_value = (
            '<div class="oe_structure oe_structure_solo">'
            f'<span data-oe-model="res.company" data-oe-id="{self.company_other.id}" data-oe-field="name"'
            ' data-oe-type="char" data-oe-expression="company.name">Renamed</span></div>'
        )
        with self.assertRaises(AccessError):
            self._save_as_user(self.event_page, company_name_value, user=self.user_event_manager)
        self.assertEqual(self.company_other.name, 'Other Company')

        with self.assertRaises(AccessError):
            event_other_page.with_user(self.user_event_manager).update_field_translations(
                'arch_db', {'fr_FR': {'Introduction': 'Présentation'}})

    def test_event_menu_edit(self):
        root_menu = self.event.menu_id
        self._save_menus([{'id': 'new-1', 'name': 'Sponsors', 'url': '/sponsors', 'parent_id': root_menu.id}])
        new_menu = root_menu.child_id.filtered(lambda menu: menu.name == 'Sponsors')
        self.assertTrue(new_menu.url.endswith('/page/sponsors'))

        self._save_menus([{'id': new_menu.id, 'name': 'Our Sponsors', 'url': new_menu.url}])
        self.assertEqual(new_menu.name, 'Our Sponsors')

        # the event manager cannot write to website.menu directly (no ACL),
        # but save() uses sudo for authorized operations
        with self.assertRaises(AccessError):
            new_menu.with_user(self.user_event_manager).write({'name': 'Direct write'})

        # creating the page of the new menu stays reserved to designers
        with self.assertRaises(AccessError):
            self.env['website'].with_user(self.user_event_manager).new_page(name=new_menu.url.lstrip('/'))

    def test_event_menu_inline_rename(self):
        # menu labels are 't-field's: renaming them inline is saved as an embedded field
        sub_menu = self.event.introduction_menu_ids.menu_id
        self._save_as_user(self.event_page, self._menu_name_span(sub_menu, 'Welcome'), user=self.user_event_manager, xpath=None)
        self.assertEqual(sub_menu.name, 'Welcome')

        # the menu dialog checks whether the typed url exists (reads website.rewrite)
        self.assertFalse(self.website.with_user(self.user_event_manager).check_existing_page('/no-such-page'))

    def test_event_menu_inline_rename_forbidden(self):
        sub_menu = self.event.introduction_menu_ids.menu_id
        for user, menu in (
            (self.user_event_manager, self.event.menu_id),  # event menu itself
            (self.user_event_manager, self.event_other.introduction_menu_ids.menu_id),  # other company
            (self.user_event_manager, self.website.menu_id.child_id[:1]),  # website menu
            (self.user_event_editor, sub_menu),  # restricted editor, but not event manager
            (self.user_event_desk, sub_menu),  # no write access on the event
        ):
            with self.subTest(user=user.login, menu=menu.name), self.assertRaises(AccessError):
                self._save_as_user(self.event_page, self._menu_name_span(menu, 'Renamed'), user=user, xpath=None)

    def _menu_name_span(self, menu, name):
        return (
            f'<span data-oe-model="website.menu" data-oe-id="{menu.id}" data-oe-field="name"'
            f' data-oe-type="char" data-oe-expression="submenu.name">{name}</span>'
        )

    def test_event_menu_edit_forbidden(self):
        root_menu = self.event.menu_id
        new_menu_values = {'id': 'new-1', 'name': 'New', 'url': '/new', 'parent_id': root_menu.id}
        website_menu = self.website.menu_id.child_id[:1]
        sub_menu = self.event.introduction_menu_ids.menu_id
        for user, menus_data in (
            (self.user_event_manager, [{'id': root_menu.id, 'name': 'Renamed event menu', 'url': root_menu.url}]),
            (self.user_event_manager, [{**new_menu_values, 'parent_id': False}]),
            (self.user_event_manager, [{'id': sub_menu.id, 'name': sub_menu.name, 'url': '#', 'parent_id': False}]),
            (self.user_event_manager, [{**new_menu_values, 'parent_id': self.event_other.menu_id.id}]),
            (self.user_event_manager, [{'id': website_menu.id, 'name': 'Website menu', 'url': '#'}]),
            (self.user_event_editor, [new_menu_values]),
            (self.user_event_desk, [new_menu_values]),
        ):
            with self.subTest(user=user.login, menus_data=menus_data), self.assertRaises(AccessError):
                self._save_menus(menus_data, user=user)


@tagged('post_install', '-at_install')
class TestEventPageImage(HttpCase):
    """ Images modified in the website builder (replaced, cropped, filtered, etc) are
    saved through `/html_editor/modify_image/`, as copies linked to views. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_other = cls.env['res.company'].create({'name': 'Other Company'})
        cls.event = cls.env['event.event'].create({'name': 'Event', 'website_menu': True})
        cls.event_other = cls.env['event.event'].create({
            'name': 'Other Event', 'website_menu': True, 'company_id': cls.company_other.id,
        })
        cls.user_event_manager = new_test_user(
            cls.env, login='user_event_image_manager', password='user_event_image_manager',
            groups='base.group_user,event.group_event_manager',
        )

        cls.image_b64 = 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='  # 1x1 Pixel gif
        cls.image = cls.env['ir.attachment'].create({
            'name': 'image.gif', 'raw': base64.b64decode(cls.image_b64), 'public': True, 'res_model': 'ir.ui.view',
        })

    def _modify_image(self, view, image=None):
        return self.make_jsonrpc_request(f'/html_editor/modify_image/{(image or self.image).id}', {
            'res_model': 'ir.ui.view',
            'res_id': view.id,
            'data': self.image_b64,
            'mimetype': 'image/gif',
            'name': 'modified.gif',
        })

    def test_event_page_image_modify(self):
        self.authenticate(self.user_event_manager.login, self.user_event_manager.login)
        modified_url = self._modify_image(self.event.introduction_menu_ids.view_id)['original']
        modified_image = self.env['ir.attachment'].search([('original_id', '=', self.image.id)])
        self.assertEqual(modified_image.image_src, modified_url)

    def test_event_page_image_modify_forbidden(self):
        self.authenticate(self.user_event_manager.login, self.user_event_manager.login)
        for view in (self.event_other.introduction_menu_ids.view_id, self.env.ref('website_event.layout')):
            with self.subTest(view=view.key), self.assertRaises(JsonRpcException), mute_logger('odoo.http'):
                self._modify_image(view)

        private_image = self.image.copy({'public': False, 'res_model': 'event.event', 'res_id': self.event_other.id})
        with self.assertRaises(JsonRpcException), mute_logger('odoo.http'):
            self._modify_image(self.event.introduction_menu_ids.view_id, image=private_image)
