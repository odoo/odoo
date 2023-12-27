# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html
from unittest.mock import patch

from odoo.addons.website.controllers.main import Website
from odoo.addons.website.tools import MockRequest
from odoo.fields import Command
from odoo.http import root
from odoo.tests import common, HttpCase, tagged
from odoo.tests.common import HOST
from odoo.tools import config, mute_logger


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
        Page.clone_page(self.page_specific.id, clone_menu=True)
        cloned_page = Page.search([('url', '=', '/page_specific-1')])
        cloned_menu = Menu.search([('url', '=', '/page_specific-1')])
        self.assertEqual(len(cloned_page), 1, "A page with an URL /page_specific-1 should've been created")
        self.assertEqual(Page.search_count([]), total_pages + 1, "Should have cloned the page")
        # It should also copy its menu with new url/name/page_id (if the page has a menu)
        self.assertEqual(len(cloned_menu), 1, "A specific page (with a menu) being cloned should have it's menu also cloned")
        self.assertEqual(cloned_menu.page_id, cloned_page, "The new cloned menu and the new cloned page should be linked (m2o)")
        self.assertEqual(Menu.search_count([]), total_menus + 1, "Should have cloned the page menu")
        Page.clone_page(self.page_specific.id, page_name="about-us", clone_menu=True)
        cloned_page_about_us = Page.search([('url', '=', '/about-us')])
        cloned_menu_about_us = Menu.search([('url', '=', '/about-us')])
        self.assertEqual(len(cloned_page_about_us), 1, "A page with an URL /about-us should've been created")
        self.assertEqual(len(cloned_menu_about_us), 1, "A specific page (with a menu) being cloned should have it's menu also cloned")
        self.assertEqual(cloned_menu_about_us.page_id, cloned_page_about_us, "The new cloned menu and the new cloned page should be linked (m2o)")
        # It should also copy its menu with new url/name/page_id (if the page has a menu)
        self.assertEqual(Menu.search_count([]), total_menus + 2, "Should have cloned the page menu")

        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])

        # Copying a generic page should create a specific page with same URL
        Page.clone_page(self.page_1.id, clone_menu=True)
        cloned_generic_page = Page.search([('url', '=', '/page_1'), ('id', '!=', self.page_1.id), ('website_id', '!=', False)])
        self.assertEqual(len(cloned_generic_page), 1, "A generic page being cloned should create a specific one for the current website")
        self.assertEqual(cloned_generic_page.url, self.page_1.url, "The URL of the cloned specific page should be the same as the generic page it has been cloned from")
        self.assertEqual(Page.search_count([]), total_pages + 1, "Should have cloned the generic page as a specific page for this website")
        self.assertEqual(Menu.search_count([]), total_menus, "It should not create a new menu as the generic page's menu belong to another website")
        # Except if the URL already exists for this website (its the case now that we already cloned it once)
        Page.clone_page(self.page_1.id, clone_menu=True)
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
        Website = self.env['website']

        self.env['website'].create({
            'name': 'My Second Website',
        })

        # currently the view unlink of website.page can't handle views with inherited views
        self.extension_view.unlink()

        website_id = 1
        self.page_1.with_context(website_id=website_id).unlink()

        self.assertEqual(bool(self.base_view.exists()), False)
        self.assertEqual(bool(self.page_1.exists()), False)
        # Not COU but deleting a page will delete its menu (cascade)
        self.assertEqual(bool(self.page_1_menu.exists()), False)

        pages = Page.search([('url', '=', '/page_1')])
        self.assertEqual(len(pages), Website.search_count([]) - 1, "A specific page for every website should have been created, except for the one from where we deleted the generic one.")
        self.assertTrue(website_id not in pages.mapped('website_id').ids, "The website from which we deleted the generic page should not have a specific one.")
        self.assertTrue(website_id not in View.search([('name', 'in', ('Base', 'Extension'))]).mapped('website_id').ids, "Same for views")


@tagged('-at_install', 'post_install')
class WithContext(HttpCase):
    def setUp(self):
        super().setUp()
        Page = self.env['website.page']
        View = self.env['ir.ui.view']
        self.base_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '''<t name="Homepage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>''',
            'key': 'test.base_view',
        })
        self.page = Page.create({
            'view_id': self.base_view.id,
            'url': '/page_1',
            'is_published': True,
        })

    def test_unpublished_page(self):
        specific_page = self.page.copy({'website_id': self.env['website'].get_current_website().id})
        specific_page.write({'is_published': False, 'arch': self.page.arch.replace('I am a generic page', 'I am a specific page')})

        self.authenticate(None, None)
        r = self.url_open(specific_page.url)
        self.assertEqual(r.status_code, 404, "Restricted users should see a 404 and not the generic one as we unpublished the specific one")

        self.authenticate('admin', 'admin')
        r = self.url_open(specific_page.url)
        self.assertEqual(r.status_code, 200, "Admin should see the specific unpublished page")
        self.assertEqual('I am a specific page' in r.text, True, "Admin should see the specific unpublished page")

    def test_search(self):
        dbname = common.get_db_name()
        admin_uid = self.env.ref('base.user_admin').id
        website = self.env['website'].get_current_website()

        robot = self.xmlrpc_object.execute(
            dbname, admin_uid, 'admin',
            'website', 'search_pages', [website.id], 'info'
        )
        self.assertIn({'loc': '/website/info'}, robot)

        pages = self.xmlrpc_object.execute(
            dbname, admin_uid, 'admin',
            'website', 'search_pages', [website.id], 'page'
        )
        self.assertIn(
            '/page_1',
            [p['loc'] for p in pages],
        )

    @mute_logger('odoo.http')
    def test_03_error_page_debug(self):
        with MockRequest(self.env, website=self.env['website'].browse(1)):
            self.base_view.arch = self.base_view.arch.replace('I am a generic page', '<t t-esc="15/0"/>')

            # first call, no debug, traceback should not be visible
            r = self.url_open(self.page.url)
            self.assertEqual(r.status_code, 500, "15/0 raise a 500 error page")
            self.assertNotIn('ZeroDivisionError: division by zero', r.text, "Error should not be shown when not in debug.")

            # second call, enable debug, traceback should be visible
            r = self.url_open(self.page.url + '?debug=1')
            self.assertEqual(r.status_code, 500, "15/0 raise a 500 error page (2)")
            self.assertIn('ZeroDivisionError: division by zero', r.text, "Error should be shown in debug.")

            # third call, no explicit debug but it should be enabled by
            # the session, traceback should be visible
            r = self.url_open(self.page.url)
            self.assertEqual(r.status_code, 500, "15/0 raise a 500 error page (2)")
            self.assertIn('ZeroDivisionError: division by zero', r.text, "Error should be shown in debug.")

    def test_04_visitor_no_session(self):
        with patch.object(root.session_store, 'save') as session_save,\
             MockRequest(self.env, website=self.env['website'].browse(1)):
            # no session should be saved for website visitor
            self.url_open(self.page.url).raise_for_status()
            session_save.assert_not_called()

    def test_05_homepage_not_slash_url(self):
        website = self.env['website'].browse([1])
        # Set another page (/page_1) as homepage
        website.write({
            'homepage_url': self.page.url,
            'domain': f"http://{HOST}:{config['http_port']}",
        })
        assert self.page.url != '/'

        r = self.url_open('/')
        r.raise_for_status()
        self.assertEqual(r.status_code, 200,
                         "There should be no crash when a public user is accessing `/` which is rerouting to another page with a different URL.")
        root_html = html.fromstring(r.content)
        canonical_url = root_html.xpath('//link[@rel="canonical"]')[0].attrib['href']
        self.assertIn(canonical_url, [f"{website.domain}/", f"{website.domain}/page_1"])

    def test_website_homepage_url_change(self):
        website = self.env['website'].browse([1])
        self.assertFalse(website.homepage_url)

        test_page = self.env['website.page'].create({
            'name': 'HomepageUrlTest',
            'type': 'qweb',
            'arch': '<div>HomepageUrlTest</div>',
            'key': 'test.homepage_url_test',
            'url': '/homepage_url_test',
            'is_published': True,
        })
        self.assertEqual(test_page.url, '/homepage_url_test')

        # If one has set the `homepage_url` to a specific page URL..
        website.write({
            'name': 'Test Website',
            'domain': f'http://{HOST}:{config["http_port"]}',
            'homepage_url': test_page.url,
        })
        home_url_full = website.domain + '/'
        r = self.url_open('/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, home_url_full)
        self.assertIn(b"HomepageUrlTest", r.content)

        # .. and then change that page URL ..
        with MockRequest(self.env, website=website):
            test_page.url = '/url-changed'

        # .. the `homepage_url` should be changed to follow the new page URL
        self.assertEqual(website.homepage_url, '/url-changed')
        r = self.url_open('/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.url, home_url_full, """URL should still be '/', note that if this
            `assert` fail, the loaded URL will probably be the first available
            menu different from '/', see homepage controller.""")
        self.assertIn(b"HomepageUrlTest", r.content)

        # Side test: ensure `slugify` and `get_unique_path` changes are
        # correctly replicated in the synced website homepage_url
        with MockRequest(self.env, website=website):
            # `/url-changed_two` will become `/url-changed-two`
            test_page.url = '/url-changed_two'
        self.assertEqual(website.homepage_url, '/url-changed-two')
        r = self.url_open('/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, home_url_full)
        self.assertIn(b"HomepageUrlTest", r.content)

    def test_06_homepage_url(self):
        # Setup
        website = self.env['website'].browse([1])
        website.write({
            'name': 'Test Website',
            'domain': f'http://{HOST}:{config["http_port"]}',
            'homepage_url': False,
        })
        contactus_url = '/contactus'
        contactus_url_full = website.domain + contactus_url
        contactus_content = b'content="Contact Us | Test Website"'
        contactus_menu = self.env['website.menu'].search([
            ('website_id', '=', website.id),
            ('url', '=', contactus_url),
        ], limit=1)
        home_url = '/'
        home_url_full = website.domain + home_url
        home_content = b'content="Home | Test Website"'
        home_menu = self.env['website.menu'].search([
            ('website_id', '=', website.id),
            ('url', '=', home_url),
        ], limit=1)

        # Case 1: Default case
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #    yes        |     /       |     None
        # -------------------------------------------
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, home_url_full)
        self.assertIn(home_content, r.content)

        # Case 2: Another page as homepage
        website.homepage_url = contactus_url
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #    yes        |     /       |  /contactus
        # -------------------------------------------
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, home_url_full)
        self.assertIn(contactus_content, r.content)

        # Case 3: Check we don't fallback on first menu if there is a / page
        contactus_menu.sequence = 2
        website.homepage_url = False
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #    yes        | /contactus  |     None
        # -------------------------------------------
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, home_url_full)
        self.assertIn(home_content, r.content)

        # Case 6: Wrong URL should fallback on first non "/" menu
        website.homepage_url = '/unexisting'
        home_menu.sequence = 1
        self.assertEqual(website.menu_id.child_id[0], home_menu)
        self.assertEqual(website.menu_id.child_id[1], contactus_menu)
        # ----------------------------------------------------------
        # / page exists | first menu  | second menu  |  homepage_url
        # ----------------------------------------------------------
        #     no        | /           |  /contactus  | /unexisting
        # ----------------------------------------------------------
        r = self.url_open(website.homepage_url)
        self.assertEqual(r.status_code, 404, "The website homepage_url should be a 404")
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, contactus_url_full, "Menu fallback should be a redirect, not a reroute")
        self.assertIn(contactus_content, r.content)

        # Case 4: Check first menu fallback is a redirect (and not a reroute)
        self.env['website.page'].search([('url', '=', home_url)]).unlink()  # this also deletes the / home menu
        website.homepage_url = False
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #     no        | /contactus  |     None
        # -------------------------------------------
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.history[0].status_code, 303)
        self.assertEqual(r.url, contactus_url_full)
        self.assertIn(contactus_content, r.content)

        # Case 5: Check controller redirect and make sure it is a reroute
        website.homepage_url = '/website/info'
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #     no        | /contactus  | /website/info
        # -------------------------------------------
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, home_url_full)
        self.assertIn(b'o_website_info', r.content)

        # Case 6: Check controller redirect which has different `auth` method
        website.homepage_url = '/my'
        # -------------------------------------------
        # / page exists | first menu  |  homepage_url
        # -------------------------------------------
        #     no        | /contactus  | /my
        # -------------------------------------------
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'<title> My Portal', r.content)
        self.assertIn(b'<title> Contact Us', r.content)
        self.assertEqual(r.url, contactus_url_full)
        self.assertEqual(r.history[0].status_code, 303)
        # Now with /contactus which is a public content
        self.env['website.menu'].create({
            'name': '/my first menu',
            'website_id': website.id,
            'parent_id': website.menu_id.id,
            'url': '/my',
            'sequence': 1,
        })
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'<title> My Portal', r.content)
        self.assertIn(b'<title> Login', r.content)
        self.assertIn('/web/login?redirect', r.url)
        self.assertEqual(r.history[0].status_code, 303)

    def test_07_alternatives(self):
        website = self.env.ref('website.default_website')
        lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        lang_fr.write({'url_code': 'fr'})
        website.language_ids = self.env.ref('base.lang_en') + lang_fr
        website.default_lang_id = self.env.ref('base.lang_en')

        with self.subTest(url='/page_1'):
            res = self.url_open('/page_1')
            res.raise_for_status()

            root_html = html.fromstring(res.content)
            canonical_url = root_html.xpath('//link[@rel="canonical"]')[0].attrib['href']
            alternate_en_url = root_html.xpath('//link[@rel="alternate"][@hreflang="en"]')[0].attrib['href']
            alternate_fr_url = root_html.xpath('//link[@rel="alternate"][@hreflang="fr"]')[0].attrib['href']

            self.assertEqual(canonical_url, f'{self.base_url()}/page_1')
            self.assertEqual(alternate_en_url, f'{self.base_url()}/page_1')
            self.assertEqual(alternate_fr_url, f'{self.base_url()}/fr/page_1')

        with self.subTest(url='/fr/page_1'):
            res = self.url_open('/fr/page_1')
            res.raise_for_status()

            root_html = html.fromstring(res.content)
            canonical_url = root_html.xpath('//link[@rel="canonical"]')[0].attrib['href']
            alternate_en_url = root_html.xpath('//link[@rel="alternate"][@hreflang="en"]')[0].attrib['href']
            alternate_fr_url = root_html.xpath('//link[@rel="alternate"][@hreflang="fr"]')[0].attrib['href']

            self.assertEqual(canonical_url, f'{self.base_url()}/fr/page_1')
            self.assertEqual(alternate_en_url, f'{self.base_url()}/page_1')
            self.assertEqual(alternate_fr_url, f'{self.base_url()}/fr/page_1')

    def test_07_not_authorized(self):
        # Create page that requires specific user role.
        specific_page = self.page.copy({'website_id': self.env['website'].get_current_website().id})
        specific_page.write({
            'arch': self.page.arch.replace('I am a generic page', 'I am a specific page not available for visitors'),
            'is_published': True,
            'visibility': 'restricted_group',
            'groups_id': [Command.link(self.ref('website.group_website_designer'))],
        })
        # Access page as anonymous visitor.
        self.authenticate(None, None)
        r = self.url_open('/page_1')
        # Check that is is rendered as a website page.
        self.assertEqual(403, r.status_code, "Must fail with 403")
        self.assertTrue('id="wrap"' in r.text, "Must be rendered as a website page")

    def test_page_url_case_insensitive_match(self):
        r = self.url_open('/page_1')
        self.assertEqual(r.status_code, 200, "Reaching page URL, common case")
        r2 = self.url_open('/Page_1', allow_redirects=False)
        self.assertEqual(r2.status_code, 303, "URL exists only in different casing, should redirect to it")
        self.assertTrue(r2.headers.get('Location').endswith('/page_1'), "Should redirect /Page_1 to /page_1")

@tagged('-at_install', 'post_install')
class TestNewPage(common.TransactionCase):
    def test_new_page_used_key(self):
        website = self.env.ref('website.default_website')
        controller = Website()
        with MockRequest(self.env, website=website):
            controller.pagenew(path="snippets")
        pages = self.env['website.page'].search([('url', '=', '/snippets')])
        self.assertEqual(len(pages), 1, "Exactly one page should be at /snippets.")
        self.assertNotEqual(pages.key, "website.snippets", "Page's key cannot be website.snippets.")
