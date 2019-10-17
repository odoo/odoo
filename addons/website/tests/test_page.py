# coding: utf-8
from odoo.tests import common, HttpCase, tagged


@tagged('-at_install', 'post_install')
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
            'key': 'test.extension_view',
        })

        self.page_1 = Page.create({
            'view_id': self.base_view.id,
            'url': '/page_1',
        })

        self.page_1_menu = Menu.create({
            'name': 'Page 1 menu',
            'page_id': self.page_1.id,
            'website_id': 1,
        })

    def test_copy_page(self):
        View = self.env['ir.ui.view']
        Page = self.env['website.page']
        Menu = self.env['website.menu']
        # Specific page
        self.specific_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>Specific View</div>',
            'key': 'test.specific_view',
        })
        self.page_specific = Page.create({
            'view_id': self.specific_view.id,
            'url': '/page_specific',
            'website_id': 1,
        })
        self.page_specific_menu = Menu.create({
            'name': 'Page Specific menu',
            'page_id': self.page_specific.id,
            'website_id': 1,
        })
        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])
        # Copying a specific page should create a new page with an unique URL (suffixed by -X)
        Page.clone_page(self.page_specific.id, True)
        cloned_page = Page.search([('url', '=', '/page_specific-1')])
        cloned_menu = Menu.search([('url', '=', '/page_specific-1')])
        self.assertEqual(len(cloned_page), 1, "A page with an URL /page_specific-1 should've been created")
        self.assertEqual(Page.search_count([]), total_pages + 1, "Should have cloned the page")
        # It should also copy its menu with new url/name/page_id (if the page has a menu)
        self.assertEqual(len(cloned_menu), 1, "A specific page (with a menu) being cloned should have it's menu also cloned")
        self.assertEqual(cloned_menu.page_id, cloned_page, "The new cloned menu and the new cloned page should be linked (m2o)")
        self.assertEqual(Menu.search_count([]), total_menus + 1, "Should have cloned the page menu")

        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])

        # Copying a generic page should create a specific page with same URL
        Page.clone_page(self.page_1.id, True)
        cloned_generic_page = Page.search([('url', '=', '/page_1'), ('id', '!=', self.page_1.id), ('website_id', '!=', False)])
        self.assertEqual(len(cloned_generic_page), 1, "A generic page being cloned should create a specific one for the current website")
        self.assertEqual(cloned_generic_page.url, self.page_1.url, "The URL of the cloned specific page should be the same as the generic page it has been cloned from")
        self.assertEqual(Page.search_count([]), total_pages + 1, "Should have cloned the generic page as a specific page for this website")
        self.assertEqual(Menu.search_count([]), total_menus, "It should not create a new menu as the generic page's menu belong to another website")
        # Except if the URL already exists for this website (its the case now that we already cloned it once)
        Page.clone_page(self.page_1.id, True)
        cloned_generic_page_2 = Page.search([('url', '=', '/page_1-1'), ('id', '!=', self.page_1.id)])
        self.assertEqual(len(cloned_generic_page_2), 1, "A generic page being cloned should create a specific page with a new URL if there is already a specific page with that URL")

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

        # 1. should have created website-specific copies for:
        #    - page
        #    - view x2 (base view + extension view)
        # 2. should not have created menu copy as menus are not shared/COW
        # 3. and shouldn't have touched original records
        self.assertEqual(total_pages + 1, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views + 2, View.search_count([]))

        self.assertEqual(self.page_1.arch, '<div>modified base content</div>')
        self.assertEqual(bool(self.page_1.website_id), False)

        new_page = Page.search([('url', '=', '/page_1'), ('id', '!=', self.page_1.id)])
        self.assertEqual(new_page.website_id.id, 1)
        self.assertEqual(new_page.view_id.inherit_children_ids[0].website_id.id, 1)
        self.assertEqual(new_page.arch, '<div>website 1 content</div>')

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

        new_view = View.search([('name', '=', 'Extension'), ('website_id', '=', 1)])
        self.assertEqual(new_view.arch, '<div>website 1 content</div>')
        self.assertEqual(new_view.website_id.id, 1)

    def test_cou_page_backend(self):
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        # currently the view unlink of website.page can't handle views with inherited views
        self.extension_view.unlink()

        self.page_1.unlink()
        self.assertEqual(Page.search_count([('url', '=', '/page_1')]), 0)
        self.assertEqual(View.search_count([('name', 'in', ('Base', 'Extension'))]), 0)

    def test_cou_page_frontend(self):
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        # currently the view unlink of website.page can't handle views with inherited views
        self.extension_view.unlink()

        self.page_1.with_context(website_id=1).unlink()

        self.assertEqual(bool(self.base_view.exists()), False)
        self.assertEqual(bool(self.page_1.exists()), False)
        # Not COU but deleting a page will delete its menu (cascade)
        self.assertEqual(bool(self.page_1_menu.exists()), False)

        self.assertEqual(Page.search([('url', '=', '/page_1')]).website_id.id, 2)
        self.assertEqual(View.search([('name', 'in', ('Base', 'Extension'))]).mapped('website_id').id, 2)


class Crawler(HttpCase):
    def test_unpublished_page(self):
        Page = self.env['website.page']
        View = self.env['ir.ui.view']
        base_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '''<t name="Homepage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>''',
            'key': 'test.base_view',
        })
        generic_page = Page.create({
            'view_id': base_view.id,
            'url': '/page_1',
            'website_published': True,
        })

        specific_page = generic_page.copy({'website_id': self.env['website'].get_current_website().id})
        specific_page.write({'website_published': False, 'arch': generic_page.arch.replace('I am a generic page', 'I am a specific page')})

        r = self.url_open(specific_page.url)
        self.assertEqual(r.status_code, 404, "Restricted users should see a 404 and not the generic one as we unpublished the specific one")

        self.authenticate('admin', 'admin')
        r = self.url_open(specific_page.url)
        self.assertEqual(r.status_code, 200, "Admin should see the specific unpublished page")
        self.assertEqual('I am a specific page' in r.text, True, "Admin should see the specific unpublished page")
