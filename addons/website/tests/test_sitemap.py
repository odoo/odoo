# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteSitemap(TransactionCase):
    def test_sitemap_page_lastmod(self):
        website = self.env['website'].search([], limit=1)
        page_url = '/test-page'
        Page = self.env['website.page']
        page = Page.create({
            'name': 'Test Page',
            'website_id': website.id,
            'url': page_url,
            'type': 'qweb',
            'arch': '<t t-call="website.layout"/>',
            'is_published': True,
        })
        View = self.env['ir.ui.view']

        def set_write_dates(page_date, view_date):
            self.env.cr.execute(
                "UPDATE website_page SET write_date = %s WHERE id = %s",
                (page_date, page.id)
            )
            self.env.cr.execute(
                "UPDATE ir_ui_view SET write_date = %s WHERE id = %s",
                (view_date, page.view_id.id)
            )
            Page.invalidate_model()
            View.invalidate_model()

        def get_sitemap_lastmod():
            pages = website._enumerate_pages()
            return next(p['lastmod'] for p in pages if p['loc'] == page_url)

        old_date = "2002-05-06 12:00:00"
        new_date = "2014-05-15 12:00:00"

        set_write_dates(new_date, old_date)
        self.assertEqual(str(get_sitemap_lastmod()), new_date[:10])

        set_write_dates(old_date, new_date)
        self.assertEqual(str(get_sitemap_lastmod()), new_date[:10])
