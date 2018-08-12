# coding: utf-8
from odoo.tests import common


class TestPage(common.TransactionCase):
    def setUp(self):
        super(TestPage, self).setUp()
        View = self.env['ir.ui.view']
        Page = self.env['website.page']
        Menu = self.env['website.menu']

        self.base_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>content</div>',
            'key': 'test.base_view',
        })

        self.extension_view = View.create({
            'name': 'Extension',
            'mode': 'extension',
            'inherit_id': self.base_view.id,
            'arch': '<div position="inside">, extended content</div>',
        })

        self.page_1 = Page.create({
            'view_id': self.base_view.id,
            'url': '/page_1',
        })

        self.page_1_menu = Menu.create({
            'name': 'Page 1 menu',
            'page_id': self.page_1.id,
        })

    def test_cow_page(self):
        Menu = self.env['website.menu']
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        # backend write, no COW
        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])
        total_views = View.search_count([])
        self.page_1.write({'arch': '<div>modified base content</div>'})
        self.assertEqual(total_pages, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views, View.search_count([]))

        # edit through frontend
        self.page_1.with_context(website_id=1).write({'arch': '<div>website 1 content</div>'})

        # should have created website-specific copies for:
        # - page
        # - menu
        # - view x2 (base view + extension view)
        # and shouldn't have touched original records
        self.assertEqual(total_pages + 1, Page.search_count([]))
        self.assertEqual(total_menus + 1, Menu.search_count([]))
        self.assertEqual(total_views + 2, View.search_count([]))

        self.assertEqual(self.page_1.arch, '<div>modified base content</div>')
        self.assertEqual(bool(self.page_1.website_id), False)
        self.assertEqual(bool(self.page_1_menu.website_id), False)

        new_page = Page.search([('url', '=', '/page_1'), ('id', '!=', self.page_1.id)])
        self.assertEqual(new_page.website_id.id, 1)
        self.assertEqual(new_page.view_id.inherit_children_ids[0].website_id.id, 1)
        self.assertEqual(new_page.arch, '<div>website 1 content</div>')

        new_menu = new_page.menu_ids[0]
        self.assertEqual(new_menu.website_id.id, 1)

    def test_cow_extension_view(self):
        ''' test cow on extension view itself (like web_editor would do in the frontend) '''
        Menu = self.env['website.menu']
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        # nothing special should happen when editing through the backend
        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])
        total_views = View.search_count([])
        self.extension_view.write({'arch': '<div>modified extension content</div>'})
        self.assertEqual(self.extension_view.arch, '<div>modified extension content</div>')
        self.assertEqual(total_pages, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views, View.search_count([]))

        # When editing through the frontend a website-specific copy
        # for the extension view should be created. When rendering the
        # original website.page on website 1 it will look differently
        # due to this new extension view.
        self.extension_view.with_context(website_id=1).write({'arch': '<div>website 1 content</div>'})
        self.assertEqual(total_pages, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views + 1, View.search_count([]))

        self.assertEqual(self.extension_view.arch, '<div>modified extension content</div>')
        self.assertEqual(bool(self.page_1.website_id), False)
        self.assertEqual(bool(self.page_1_menu.website_id), False)

        new_view = View.search([('name', '=', 'Extension'), ('website_id', '=', 1)])
        self.assertEqual(new_view.arch, '<div>website 1 content</div>')
        self.assertEqual(new_view.website_id.id, 1)

    def test_cou_page_backend(self):
        Menu = self.env['website.menu']
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        # currently the view unlink of website.page can't handle views with inherited views
        self.extension_view.unlink()

        self.page_1.unlink()
        self.assertEqual(Menu.search_count([('name', '=', 'Page 1 menu')]), 0)
        self.assertEqual(Page.search_count([('url', '=', '/page_1')]), 0)
        self.assertEqual(View.search_count([('name', 'in', ('Base', 'Extension'))]), 0)

    def test_cou_page_frontend(self):
        Menu = self.env['website.menu']
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        # currently the view unlink of website.page can't handle views with inherited views
        self.extension_view.unlink()

        self.page_1.with_context(website_id=1).unlink()

        self.assertEqual(bool(self.base_view.exists()), False)
        self.assertEqual(bool(self.page_1.exists()), False)
        self.assertEqual(bool(self.page_1_menu.exists()), False)

        self.assertEqual(Menu.search([('name', '=', 'Page 1 menu')]).website_id.id, 2)
        self.assertEqual(Page.search([('url', '=', '/page_1')]).website_id.id, 2)
        self.assertEqual(View.search([('name', 'in', ('Base', 'Extension'))]).mapped('website_id').id, 2)
