# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website.tools import MockRequest
from odoo.addons.website.models.website_visitor import WebsiteVisitor
from odoo.tests import common, tagged


class MockVisitor(common.BaseCase):

    @contextmanager
    def mock_visitor_from_request(self, force_visitor=False):

        def _get_visitor_from_request(model, *args, **kwargs):
            return force_visitor

        with patch.object(WebsiteVisitor, '_get_visitor_from_request',
                          autospec=True, wraps=WebsiteVisitor,
                          side_effect=_get_visitor_from_request) as _get_visitor_from_request_mock:
            yield


@tagged('-at_install', 'post_install', 'website_visitor')
class WebsiteVisitorTests(MockVisitor, HttpCaseWithUserDemo):

    def setUp(self):
        super(WebsiteVisitorTests, self).setUp()

        self.website = self.env['website'].search([
            ('company_id', '=', self.env.user.company_id.id)
        ], limit=1)
        self.cookies = {}

        untracked_view = self.env['ir.ui.view'].create({
            'name': 'UntackedView',
            'type': 'qweb',
            'arch': '''<t name="Homepage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic page²
                        </t>
                    </t>''',
            'key': 'test.base_view',
            'track': False,
        })
        tracked_view = self.env['ir.ui.view'].create({
            'name': 'TrackedView',
            'type': 'qweb',
            'arch': '''<t name="Homepage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>''',
            'key': 'test.base_view',
            'track': True,
        })
        tracked_view_2 = self.env['ir.ui.view'].create({
            'name': 'TrackedView2',
            'type': 'qweb',
            'arch': '''<t name="OtherPage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic second page
                        </t>
                    </t>''',
            'key': 'test.base_view',
            'track': True,
        })
        [self.untracked_page, self.tracked_page, self.tracked_page_2] = self.env['website.page'].create([
            {
                'view_id': untracked_view.id,
                'url': '/untracked_view',
                'website_published': True,
            },
            {
                'view_id': tracked_view.id,
                'url': '/tracked_view',
                'website_published': True,
            },
            {
                'view_id': tracked_view_2.id,
                'url': '/tracked_view_2',
                'website_published': True,
            },
        ])

        self.user_portal = self.env['res.users'].search([('login', '=', 'portal')])
        self.partner_portal = self.user_portal.partner_id
        if not self.user_portal:
            self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
            self.partner_portal = self.env['res.partner'].create({
                'name': 'Joel Willis',
                'email': 'joel.willis63@example.com',
            })
            self.user_portal = self.env['res.users'].create({
                'login': 'portal',
                'password': 'portal',
                'partner_id': self.partner_portal.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })

    def _get_last_visitor(self):
        return self.env['website.visitor'].search([], limit=1, order="id DESC")

    def assertPageTracked(self, visitor, page):
        """ Check a page is in visitor tracking data """
        self.assertIn(page, visitor.website_track_ids.page_id)
        self.assertIn(page, visitor.page_ids)

    def assertVisitorTracking(self, visitor, pages):
        """ Check the whole tracking history of a visitor """
        for page in pages:
            self.assertPageTracked(visitor, page)
        self.assertEqual(
            len(visitor.website_track_ids),
            len(pages)
        )

    def assertVisitorDeactivated(self, visitor, main_visitor):
        """ Temporary method to check that a visitor has been de-activated / merged
        with other visitor, notably in case of login (see User.authenticate() as
        well as Visitor._link_to_visitor() ).

        As final result depends on installed modules (see overrides) due to stable
        improvements linked to EventOnline, this method contains a hack to avoid
        doing too much overrides just for that behavior. """
        if 'parent_id' in self.env['website.visitor']:
            self.assertTrue(bool(visitor))
            self.assertFalse(visitor.active)
            self.assertTrue(main_visitor.active)
            self.assertEqual(visitor.parent_id, main_visitor)
        else:
            self.assertFalse(visitor)
            self.assertTrue(bool(main_visitor))

    def test_visitor_creation_on_tracked_page(self):
        """ Test various flows involving visitor creation and update. """
        existing_visitors = self.env['website.visitor'].search([])
        existing_tracks = self.env['website.track'].search([])
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page.url)
        self.url_open(self.tracked_page.url)

        new_visitor = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        new_track = self.env['website.track'].search([('id', 'not in', existing_tracks.ids)])
        self.assertEqual(len(new_visitor), 1, "1 visitor should be created")
        self.assertEqual(len(new_track), 1, "There should be 1 tracked page")
        self.assertEqual(new_visitor.visit_count, 1)
        self.assertEqual(new_visitor.website_track_ids, new_track)
        self.assertVisitorTracking(new_visitor, self.tracked_page)

        # ------------------------------------------------------------
        # Admin connects
        # ------------------------------------------------------------

        self.cookies = {'visitor_uuid': new_visitor.access_token}
        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.authenticate(self.user_admin.login, 'admin')

        visitor_admin = new_visitor
        # visit a page
        self.url_open(self.tracked_page_2.url)

        # check tracking and visitor / user sync
        self.assertVisitorTracking(visitor_admin, self.tracked_page | self.tracked_page_2)
        self.assertEqual(visitor_admin.partner_id, self.partner_admin)
        self.assertEqual(visitor_admin.name, self.partner_admin.name)

        # ------------------------------------------------------------
        # Portal connects
        # ------------------------------------------------------------

        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.authenticate(self.user_portal.login, 'portal')

        self.assertFalse(
            self.env['website.visitor'].search([('id', 'not in', (existing_visitors | visitor_admin).ids)]),
            "No extra visitor should be created")

        # visit a page
        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)
        self.url_open(self.tracked_page_2.url)  # 2 time to be sure it does not record twice

        # new visitor is created
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(len(new_visitors), 2, "One extra visitor should be created")
        visitor_portal = new_visitors[0]
        self.assertEqual(visitor_portal.partner_id, self.partner_portal)
        self.assertEqual(visitor_portal.name, self.partner_portal.name)
        self.assertVisitorTracking(visitor_portal, self.tracked_page | self.tracked_page_2)

        # ------------------------------------------------------------
        # Back to anonymous
        # ------------------------------------------------------------

        # portal user disconnects
        self.logout()

        # visit some pages
        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)
        self.url_open(self.tracked_page_2.url)  # 2 time to be sure it does not record twice

        # new visitor is created
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(len(new_visitors), 3, "One extra visitor should be created")
        visitor_anonymous = new_visitors[0]
        self.cookies['visitor_uuid'] = visitor_anonymous.access_token
        self.assertFalse(visitor_anonymous.name)
        self.assertFalse(visitor_anonymous.partner_id)
        self.assertVisitorTracking(visitor_anonymous, self.tracked_page | self.tracked_page_2)
        visitor_anonymous_tracks = visitor_anonymous.website_track_ids

        # ------------------------------------------------------------
        # Admin connects again
        # ------------------------------------------------------------

        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.authenticate(self.user_admin.login, 'admin')

        # one visitor is deleted
        visitor_anonymous = self.env['website.visitor'].with_context(active_test=False).search([('id', '=', visitor_anonymous.id)])
        self.assertVisitorDeactivated(visitor_anonymous, visitor_admin)
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(new_visitors, visitor_admin | visitor_portal)
        visitor_admin = self.env['website.visitor'].search([('partner_id', '=', self.partner_admin.id)])
        # tracks are linked
        self.assertTrue(visitor_anonymous_tracks < visitor_admin.website_track_ids)
        self.assertEqual(len(visitor_admin.website_track_ids), 4, "There should be 4 tracked page for the admin")

        # ------------------------------------------------------------
        # Back to anonymous
        # ------------------------------------------------------------

        # admin disconnects
        self.logout()

        # visit some pages
        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)
        self.url_open(self.tracked_page_2.url)  # 2 time to be sure it does not record twice

        # new visitor created
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(len(new_visitors), 3, "One extra visitor should be created")
        visitor_anonymous_2 = new_visitors[0]
        self.cookies['visitor_uuid'] = visitor_anonymous_2.access_token
        self.assertFalse(visitor_anonymous_2.name)
        self.assertFalse(visitor_anonymous_2.partner_id)
        self.assertVisitorTracking(visitor_anonymous_2, self.tracked_page | self.tracked_page_2)
        visitor_anonymous_2_tracks = visitor_anonymous_2.website_track_ids

        # ------------------------------------------------------------
        # Portal connects again
        # ------------------------------------------------------------
        with MockRequest(self.env, website=self.website, cookies=self.cookies):
            self.authenticate(self.user_portal.login, 'portal')

        # one visitor is deleted
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(new_visitors, visitor_admin | visitor_portal)
        # tracks are linked
        self.assertTrue(visitor_anonymous_2_tracks < visitor_portal.website_track_ids)
        self.assertEqual(len(visitor_portal.website_track_ids), 4, "There should be 4 tracked page for the portal user")

        # simulate the portal user comes back 30min later
        for track in visitor_portal.website_track_ids:
            track.write({'visit_datetime': track.visit_datetime - timedelta(minutes=30)})

        # visit a page
        self.url_open(self.tracked_page.url)
        visitor_portal.invalidate_cache(fnames=['website_track_ids'])
        # tracks are created
        self.assertEqual(len(visitor_portal.website_track_ids), 5, "There should be 5 tracked page for the portal user")

        # simulate the portal user comes back 8hours later
        visitor_portal.write({'last_connection_datetime': visitor_portal.last_connection_datetime - timedelta(hours=8)})
        self.url_open(self.tracked_page.url)
        visitor_portal.invalidate_cache(fnames=['visit_count'])
        # check number of visits
        self.assertEqual(visitor_portal.visit_count, 2, "There should be 2 visits for the portal user")

    def test_visitor_archive(self):
        """ Test cron archiving inactive visitors and their re-activation when
        authenticating an user. """
        self.env['ir.config_parameter'].sudo().set_param('website.visitor.live.days', 7)

        partner_demo = self.partner_demo
        old_visitor = self.env['website.visitor'].create({
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'partner_id': partner_demo.id,
        })
        self.assertTrue(old_visitor.active)
        self.assertEqual(partner_demo.visitor_ids, old_visitor, "Visitor and its partner should be synchronized")

        # archive old visitor
        old_visitor.last_connection_datetime = datetime.now() - timedelta(days=8)
        self.env['website.visitor']._cron_archive_visitors()
        self.assertEqual(old_visitor.active, False, "Visitor should be archived after inactivity")

        # reconnect with new visitor.
        self.url_open(self.tracked_page.url)
        new_visitor = self._get_last_visitor()
        self.assertFalse(new_visitor.partner_id)
        self.assertTrue(new_visitor.id > old_visitor.id, "A new visitor should have been created.")
        self.assertVisitorTracking(new_visitor, self.tracked_page)

        with self.mock_visitor_from_request(force_visitor=new_visitor):
            self.authenticate('demo', 'demo')
        (new_visitor | old_visitor).flush()
        partner_demo.flush()
        partner_demo.invalidate_cache(fnames=['visitor_ids'])
        self.assertEqual(partner_demo.visitor_ids, old_visitor, "The partner visitor should be back to the 'old' visitor.")

        new_visitor = self.env['website.visitor'].search([('id', '=', new_visitor.id)])
        self.assertEqual(len(new_visitor), 0, "The new visitor should be deleted when visitor authenticate once again.")
        self.assertEqual(old_visitor.active, True, "The old visitor should be reactivated when visitor authenticates once again.")
