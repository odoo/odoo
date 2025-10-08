import lxml.html

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestMultiWebsite(HttpCase):
    def test_multi_website_switch(self):
        Website = self.env['website']

        website_1 = Website.create({'name': 'Website 1'})
        website_2 = Website.create({'name': 'Website 2'})

        self.authenticate("admin", "admin")
        base_url = website_1.get_base_url()

        res1 = self.url_open(base_url + '/website/force/%s' % website_2.id)
        res2 = self.url_open(base_url + '/website/force/%s' % website_1.id)
        website_2_tree = lxml.html.fromstring(res1.content)
        website_1_tree = lxml.html.fromstring(res2.content)

        data_obj_1 = website_1_tree.xpath('//html/@data-main-object')[0]
        data_obj_2 = website_2_tree.xpath('//html/@data-main-object')[0]

        website_id_1 = website_1_tree.xpath('//html/@data-website-id')[0]
        website_id_2 = website_2_tree.xpath('//html/@data-website-id')[0]

        self.assertNotEqual(data_obj_1, data_obj_2)
        self.assertNotEqual(website_id_1, website_id_2)
