# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
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
        """ Method that checks that a visitor has been de-activated / merged
        with other visitor, notably in case of login (see User.authenticate() as
        well as Visitor._merge_visitor() ). """
        self.assertFalse(visitor.exists(), "The anonymous visitor should be deleted")
        self.assertTrue(visitor.website_track_ids < main_visitor.website_track_ids)

    def test_visitor_creation_on_tracked_page(self):
        """ Test various flows involving visitor creation and update. """

        def authenticate(login, pwd):
            # We can't call `self.authenticate` because that tour util is
            # regenerating a new session.id before calling the real
            # `authenticate` method.
            # But we need the session id in the `authenticate` method because
            # we need to retrieve the visitor before the authentication, which
            # require the session id.
            res = self.url_open('/web/login')
            csrf_anchor = '<input type="hidden" name="csrf_token" value="'
            self.url_open('/web/login', timeout=200, data={
                'login': login,
                'password': pwd,
                'csrf_token': res.text.partition(csrf_anchor)[2].partition('"')[0],
            })

        existing_visitors = self.env['website.visitor'].search([])
        existing_tracks = self.env['website.track'].search([])
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page.url)
        self.url_open(self.tracked_page.url)

        new_visitor = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        new_track = self.env['website.track'].search([('id', 'not in', existing_tracks.ids)])
        self.assertEqual(len(new_visitor), 1, "1 visitor should be created")
        self.assertEqual(len(new_track), 2, "There should be 2 tracked page")
        self.assertEqual(new_visitor.visit_count, 1)
        self.assertEqual(new_visitor.website_track_ids, new_track)
        self.assertVisitorTracking(new_visitor, self.tracked_page + self.tracked_page)

        # ------------------------------------------------------------
        # Admin connects
        # ------------------------------------------------------------

        authenticate(self.user_admin.login, 'admin')

        visitor_admin = new_visitor
        # visit a page
        self.url_open(self.tracked_page_2.url)

        # check tracking and visitor / user sync
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(len(new_visitors), 1, "There should still be only one visitor.")
        self.assertVisitorTracking(visitor_admin, self.tracked_page + self.tracked_page + self.tracked_page_2)
        self.assertEqual(visitor_admin.partner_id, self.partner_admin)
        self.assertEqual(visitor_admin.name, self.partner_admin.name)

        # ------------------------------------------------------------
        # Portal connects
        # ------------------------------------------------------------

        self.url_open('/web/session/logout')
        authenticate(self.user_portal.login, 'portal')

        self.assertFalse(
            self.env['website.visitor'].search([('id', 'not in', (existing_visitors | visitor_admin).ids)]),
            "No extra visitor should be created")

        # visit a page
        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)

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
        self.url_open('/web/session/logout')

        # visit some pages
        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)

        # new visitor is created
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(len(new_visitors), 3, "One extra visitor should be created")
        visitor_anonymous = new_visitors[0]
        self.assertFalse(visitor_anonymous.name)
        self.assertFalse(visitor_anonymous.partner_id)
        self.assertVisitorTracking(visitor_anonymous, self.tracked_page | self.tracked_page_2)
        visitor_anonymous_tracks = visitor_anonymous.website_track_ids

        # ------------------------------------------------------------
        # Admin connects again
        # ------------------------------------------------------------

        authenticate(self.user_admin.login, 'admin')

        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(new_visitors, visitor_admin | visitor_portal)
        visitor_admin = self.env['website.visitor'].search([('partner_id', '=', self.partner_admin.id)])
        # tracks are linked
        self.assertTrue(visitor_anonymous_tracks < visitor_admin.website_track_ids)
        self.assertEqual(len(visitor_admin.website_track_ids), 5, "There should be 5 tracked page for the admin")

        # ------------------------------------------------------------
        # Back to anonymous
        # ------------------------------------------------------------

        # admin disconnects
        self.url_open('/web/session/logout')

        # visit some pages
        self.url_open(self.tracked_page.url)
        self.url_open(self.untracked_page.url)
        self.url_open(self.tracked_page_2.url)

        # new visitor created
        new_visitors = self.env['website.visitor'].search([('id', 'not in', existing_visitors.ids)])
        self.assertEqual(len(new_visitors), 3, "One extra visitor should be created")
        visitor_anonymous_2 = new_visitors[0]
        self.assertFalse(visitor_anonymous_2.name)
        self.assertFalse(visitor_anonymous_2.partner_id)
        self.assertVisitorTracking(visitor_anonymous_2, self.tracked_page | self.tracked_page_2)
        visitor_anonymous_2_tracks = visitor_anonymous_2.website_track_ids

        # ------------------------------------------------------------
        # Portal connects again
        # ------------------------------------------------------------
        authenticate(self.user_portal.login, 'portal')

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
        visitor_portal.invalidate_model(['website_track_ids'])
        # tracks are created
        self.assertEqual(len(visitor_portal.website_track_ids), 5, "There should be 5 tracked page for the portal user")

        # simulate the portal user comes back 8hours later
        visitor_portal.write({'last_connection_datetime': visitor_portal.last_connection_datetime - timedelta(hours=9)})
        self.url_open(self.tracked_page.url)
        visitor_portal.invalidate_model(['visit_count'])
        # check number of visits
        self.assertEqual(visitor_portal.visit_count, 2, "There should be 2 visits for the portal user")

    def test_clean_inactive_visitors(self):
        inactive_visitors = self.env['website.visitor'].create([{
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'last_connection_datetime': datetime.now() - timedelta(days=8),
            'access_token': 'f9d2b14b21be669518b14a9590cb62ed',
        }, {
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'last_connection_datetime': datetime.now() - timedelta(days=15),
            'access_token': 'f9d2d261a725da7f596574ca84e52f47',
        }])

        active_visitors = self.env['website.visitor'].create([{
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'last_connection_datetime': datetime.now() - timedelta(days=1),
            'access_token': 'f9d2526d9c15658bdc91d2119e54b554',
        }, {
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'partner_id': self.partner_demo.id,
            'last_connection_datetime': datetime.now() - timedelta(days=15),
            'access_token': self.partner_demo.id,
        }])

        self._test_unlink_old_visitors(inactive_visitors, active_visitors)

    def _test_unlink_old_visitors(self, inactive_visitors, active_visitors):
        """ This method will test that the visitors are correctly deleted when inactive.

        - inactive_visitors: all visitors that should be unlinked by the CRON
          '_cron_unlink_old_visitors'
        - active_visitors: all visitors that should NOT be cleaned because they are either active
          or have some important data linked to them (partner, ...) and we want to keep them.

        We use this method as a private tool so that sub-module can also test the cleaning of visitors
        based on their own sets of conditions. """

        WebsiteVisitor = self.env['website.visitor']

        self.env['ir.config_parameter'].sudo().set_param('website.visitor.live.days', 7)

        # ensure we keep a single query by correct usage of "not inselect"
        # (+1 query to fetch the 'ir.config_parameter')
        with self.assertQueryCount(2):
            WebsiteVisitor.search(WebsiteVisitor._inactive_visitors_domain())

        inactive_visitor_ids = inactive_visitors.ids
        active_visitor_ids = active_visitors.ids

        WebsiteVisitor._cron_unlink_old_visitors()
        if inactive_visitor_ids:
            # all inactive visitors should be deleted
            self.assertFalse(bool(WebsiteVisitor.search([('id', 'in', inactive_visitor_ids)])))
        if active_visitor_ids:
            # all active visitors should be kept
            self.assertEqual(active_visitors, WebsiteVisitor.search([('id', 'in', active_visitor_ids)]))

    def test_link_to_visitor(self):
        """ Visitors are 'linked' together when the user, previously not connected, authenticates
        and the system detects it already had a website.visitor for that partner_id.
        This can happen quite often if the user switches browsers / hardwares.

        When 'linking' visitors together, the new visitor is archived and all its relevant data is
        merged within the main visitor. See 'website.visitor#_merge_visitor' for more details.

        This test ensures that all the relevant data are properly merged.

        We build this logic with sub-methods so that sub-modules can easily add their own data and
        test that they are correctly merged."""

        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

    def _prepare_main_visitor_data(self):
        return {
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'access_token': self.partner_admin.id,
            'website_track_ids': [(0, 0, {
                'page_id': self.tracked_page.id,
                'url': self.tracked_page.url
            })]
        }

    def _prepare_linked_visitor_data(self):
        return {
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'access_token': '%032x' % random.randrange(16**32),
            'website_track_ids': [(0, 0, {
                'page_id': self.tracked_page_2.id,
                'url': self.tracked_page_2.url
            })]
        }

    def test_merge_partner_with_visitor_both(self):
        """ See :meth:`test_merge_partner_with_visitor_single` """
        # Setup a visitor for demo and none for admin
        Visitor = self.env['website.visitor']
        (self.partner_demo + self.partner_admin).visitor_ids.unlink()
        [visitor_demo, visitor_admin] = Visitor.create([{
            'partner_id': self.partner_demo.id,
            'access_token': self.partner_demo.id,
        }, {
            'partner_id': self.partner_admin.id,
            'access_token': self.partner_admin.id,
        }])
        # | id | access_token | partner_id |
        # | -- | ------------ | ---------- |
        # |  1 |      demo_id |    demo_id |
        # |    |      1062141 |    1062141 |
        # |  2 |     admin_id |   admin_id |
        # |    |      5013266 |    5013266 |
        self.assertTrue(visitor_demo.partner_id.id == int(visitor_demo.access_token) == self.partner_demo.id)
        self.assertTrue(visitor_admin.partner_id.id == int(visitor_admin.access_token) == self.partner_admin.id)

        self.env['website.track'].create([{
            'visitor_id': visitor_demo.id,
            'url': '/demo'
        }, {
            'visitor_id': visitor_admin.id,
            'url': '/admin'
        }])
        self.assertEqual(visitor_demo.website_track_ids.url, '/demo')
        self.assertEqual(visitor_admin.website_track_ids.url, '/admin')

        # Merge demo partner in admin partner
        self.env['base.partner.merge.automatic.wizard']._merge(
            (self.partner_admin + self.partner_demo).ids,
            self.partner_admin
        )
        # Should be
        # | id | access_token | partner_id |
        # | -- | ------------ | ---------- |
        # |  2 |     admin_id |   admin_id |
        # |    |      5013266 |    5013266 |
        self.assertTrue(visitor_admin.exists())
        self.assertFalse(visitor_demo.exists())
        self.assertFalse(Visitor.search_count([('partner_id', '=', self.partner_demo.id)]),
                         "The demo visitor should've been merged (and deleted) with the admin one.")
        # Track check
        self.assertEqual(visitor_admin.website_track_ids.sorted('url').mapped('url'), ['/admin', '/demo'])

    def test_merge_partner_with_visitor_single(self):
        """ The partner merge feature of Odoo is auto discovering relations to
        ``res_partner`` to change the field value, in raw SQL.
        It will change the ``partner_id`` field of visitor without changing the
        ``access_token``, which is supposed to be the same value (``partner_id``
        is just a stored computed field holding the ``access_token`` value if it
        is an integer value).
        This partner_id/access_token "de-sync" need to be handled, this is done
        in ``_update_foreign_keys()`` website override.
        This test is ensuring that it works as it should.

        There is 2 possible cases:

        1. There is a visitor for partner 1, none for partner 2. Partner 1 is
           merged into partner 2, making partner_id of visitor from partner 1
           becoming partner 2.
           -> The ``access_token`` value should also be updated from 1 to 2.
        2. There is a visitor for both partners and partner 1 is merged into
           partner 2.
           -> Both visitor should be merged too, so data are aggregated into a
              single visitor.

        Case 1 is tested here.
        Cade 2 is tested in :meth:`test_merge_partner_with_visitor_both`.
        """
        # Setup a visitor for demo and none for admin
        Visitor = self.env['website.visitor']
        (self.partner_demo + self.partner_admin).visitor_ids.unlink()
        visitor_demo = Visitor.create({
            'partner_id': self.partner_demo.id,
            'access_token': self.partner_demo.id,
        })
        # | id | access_token | partner_id |
        # | -- | ------------ | ---------- |
        # |  1 |      demo_id |    demo_id |
        # |    |      1062141 |    1062141 |
        self.assertTrue(visitor_demo.partner_id.id == int(visitor_demo.access_token) == self.partner_demo.id)

        # Merge demo partner in admin partner
        self.env['base.partner.merge.automatic.wizard']._merge(
            (self.partner_admin + self.partner_demo).ids,
            self.partner_admin
        )
        # This should not happen..
        # | id | access_token | partner_id |
        # | -- | ------------ | ---------- |
        # |  1 |      demo_id |   admin_id | <-- Mismatch
        # |    |      1062141 |    5013266 |
        # .. it should be:
        # | id | access_token | partner_id |
        # | -- | ------------ | ---------- |
        # |  1 |     admin_id |   admin_id | <-- No mismatch, became admin_id
        # |    |      5013266 |    5013266 |
        self.assertTrue(visitor_demo.partner_id.id == int(visitor_demo.access_token) == self.partner_admin.id,
                        "The demo visitor should now be linked to the admin partner.")
        self.assertFalse(Visitor.search_count([('partner_id', '=', self.partner_demo.id)]),
                         "The demo visitor should've been merged (and deleted) with the admin one.")
