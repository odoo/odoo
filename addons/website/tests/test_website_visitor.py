# coding: utf-8
from odoo.tests import HttpCase, tagged

@tagged('dbetest')
class WebsiteVisitorTests(HttpCase):
    def test_create_visitor_on_tracked_page(self):
        Page = self.env['website.page']
        View = self.env['ir.ui.view']
        Visitor = self.env['website.visitor']
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
        [untracked_page, tracked_page] = Page.create([
            {
                'view_id': base_view.id,
                'url': '/untracked_page_1',
                'website_published': True
            },
            {
                'view_id': base_view.id,
                'url': '/tracked_page_1',
                'website_published': True,
                'is_tracked': True
            }
        ])

        self.assertEqual(len(Visitor.search([])), 0, "No visitor at the moment")
        self.url_open(untracked_page.url)
        self.assertEqual(len(Visitor.search([])), 0, "No visitor created after visiting an untracked page")
        self.url_open(tracked_page.url)
        self.assertEqual(len(Visitor.search([])), 1, "A visitor should be created after visiting a tracked page")
