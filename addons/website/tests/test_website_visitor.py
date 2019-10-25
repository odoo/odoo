# coding: utf-8
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class WebsiteVisitorTests(HttpCase):
    def test_create_visitor_on_tracked_page(self):
        Page = self.env['website.page']
        View = self.env['ir.ui.view']
        Visitor = self.env['website.visitor']
        Track = self.env['website.track']
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
        [untracked_view, tracked_view] = Page.create([
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

        self.assertEqual(len(Visitor.search([])), 0, "No visitor at the moment")
        self.assertEqual(len(Track.search([])), 0, "No track at the moment")
        self.url_open(untracked_view.url)
        self.assertEqual(len(Visitor.search([])), 0, "No visitor created after visiting an untracked view")
        self.assertEqual(len(Track.search([])), 0, "No track created after visiting an untracked view")
        self.url_open(tracked_view.url)
        self.assertEqual(len(Visitor.search([])), 1, "A visitor should be created after visiting a tracked view")
        self.assertEqual(len(Track.search([])), 1, "A track should be created after visiting a tracked view")
        self.url_open(tracked_view.url)
        self.assertEqual(len(Visitor.search([])), 1, "No visitor should be created after visiting another tracked view")
        self.assertEqual(len(Track.search([])), 1, "No track should be created after visiting another tracked view before 30 min")
