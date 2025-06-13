import odoo.tests
from ..tools import create_image_attachment


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteAttachment(odoo.tests.HttpCase):

    def test_01_type_url_301_image(self):
        IMD = self.env['ir.model.data']

        img1 = create_image_attachment(self.env, '/website/static/src/img/snippets_demo/s_banner.jpg', 's_banner_default_image.jpg')
        img2 = create_image_attachment(self.env, '/web/image/test.an_image_url', 's_banner_default_image.jpg')

        IMD.create({
            'name': 'an_image_url',
            'module': 'test',
            'model': img1._name,
            'res_id': img1.id,
        })

        IMD.create({
            'name': 'an_image_redirect_301',
            'module': 'test',
            'model': img2._name,
            'res_id': img2.id,
        })

        req = self.url_open('/web/image/test.an_image_url')
        self.assertEqual(req.status_code, 200)

        base = self.base_url()
        req = self.url_open(base + '/web/image/test.an_image_redirect_301', allow_redirects=False)
        self.assertEqual(req.status_code, 301)
        self.assertURLEqual(req.headers['Location'], '/web/image/test.an_image_url')

        req = self.url_open(base + '/web/image/test.an_image_redirect_301', allow_redirects=True)
        self.assertEqual(req.status_code, 200)

    def test_02_image_quality(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_image_quality', login="admin")

    def test_03_link_to_document(self):
        text = b'Lorem Ipsum'
        self.env['ir.attachment'].create({
            'name': 'sample.txt',
            'public': True,
            'mimetype': 'text/plain',
            'raw': text,
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_link_to_document', login="admin")
