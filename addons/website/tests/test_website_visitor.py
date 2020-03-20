# coding: utf-8
from odoo import tests
from datetime import datetime, timedelta


class WebsiteVisitorTests(tests.HttpCase):
    def setUp(self):
        super(WebsiteVisitorTests, self).setUp()
        Page = self.env['website.page']
        View = self.env['ir.ui.view']
        self.Visitor = self.env['website.visitor']
        self.Track = self.env['website.track']
        untracked_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '''<t name="Homepage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>''',
            'key': 'test.base_view',
            'track': False,
        })
        tracked_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '''<t name="Homepage" t-name="website.base_view">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>''',
            'key': 'test.base_view',
            'track': True,
        })
        [self.untracked_view, self.tracked_view] = Page.create([
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
        ])

    def test_create_visitor_on_tracked_page(self):
        self.assertEqual(len(self.Visitor.search([])), 0, "No visitor at the moment")
        self.assertEqual(len(self.Track.search([])), 0, "No track at the moment")
        self.url_open(self.untracked_view.url)
        self.assertEqual(len(self.Visitor.search([])), 0, "No visitor created after visiting an untracked view")
        self.assertEqual(len(self.Track.search([])), 0, "No track created after visiting an untracked view")
        self.url_open(self.tracked_view.url)
        self.assertEqual(len(self.Visitor.search([])), 1, "A visitor should be created after visiting a tracked view")
        self.assertEqual(len(self.Track.search([])), 1, "A track should be created after visiting a tracked view")
        self.url_open(self.tracked_view.url)
        self.assertEqual(len(self.Visitor.search([])), 1, "No visitor should be created after visiting another tracked view")
        self.assertEqual(len(self.Track.search([])), 1, "No track should be created after visiting another tracked view before 30 min")

    def test_long_period_inactivity(self):
        # link visitor to partner
        old_visitor = self.Visitor.create({
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
        })
        partner_demo = self.env.ref('base.partner_demo')
        old_visitor.partner_id = partner_demo.id
        partner_demo.visitor_ids = [(6, 0, [old_visitor.id])]  # TODO DBE : Remove this line in Master (13.1) after visitor_ids field declaration master fix
        self.assertEqual(partner_demo.visitor_ids.id, old_visitor.id, "The partner visitor should be set correctly.")

        # archive old visitor
        old_visitor.last_connection_datetime = datetime.now() - timedelta(days=8)
        self.Visitor._cron_archive_visitors()
        self.assertEqual(old_visitor.active, False, "The visitor should be archived after one week of inactivity")

        # reconnect with new visitor.
        self.url_open(self.tracked_view.url)
        new_visitor = self.Visitor.search([('id', '!=', old_visitor.id)], limit=1, order="id desc") # get the last created visitor
        new_visitor_id = new_visitor.id
        self.assertEqual(new_visitor_id > old_visitor.id, True, "A new visitor should have been created.")
        self.assertEqual(len(new_visitor), 1, "A visitor should be created after visiting a tracked view")
        self.assertEqual(len(self.Track.search([('visitor_id', '=', new_visitor.id)])), 1,
                         "A track for the new visitor should be created after visiting a tracked view")

        # override the get_visitor_from_request to mock that is new_visitor that authenticates
        def get_visitor_from_request(self_mock, force_create=False):
            return new_visitor
        self.patch(type(self.env['website.visitor']), '_get_visitor_from_request', get_visitor_from_request)

        self.authenticate('demo', 'demo')
        self.assertEqual(partner_demo.visitor_ids.id, old_visitor.id, "The partner visitor should be back to the 'old' visitor.")

        new_visitor = self.Visitor.search([('id', '=', new_visitor_id)])
        self.assertEqual(len(new_visitor), 0, "The new visitor should be deleted when visitor authenticate once again.")
        self.assertEqual(old_visitor.active, True, "The old visitor should be reactivated when visitor authenticates once again.")
