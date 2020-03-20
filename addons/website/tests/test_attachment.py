import odoo.tests
from odoo.tests.common import HOST, PORT


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteAttachment(odoo.tests.HttpCase):

    def test_01_type_url_301_image(self):
        IMD = self.env['ir.model.data']
        IrAttachment = self.env['ir.attachment']

        img1 = IrAttachment.create({
            'public': True,
            'name': 's_banner_default_image.jpg',
            'type': 'url',
            'url': '/website/static/src/img/snippets_demo/s_banner.jpg'
        })

        img2 = IrAttachment.create({
            'public': True,
            'name': 's_banner_default_image.jpg',
            'type': 'url',
            'url': '/web/image/test.an_image_url'
        })

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
        self.assertEquals(req.status_code, 200)

        base = "http://%s:%s" % (HOST, PORT)

        req = self.opener.get(base + '/web/image/test.an_image_redirect_301', allow_redirects=False)
        self.assertEquals(req.status_code, 301)
        self.assertEquals(req.headers['Location'], base + '/web/image/test.an_image_url')

        req = self.opener.get(base + '/web/image/test.an_image_redirect_301', allow_redirects=True)
        self.assertEquals(req.status_code, 200)
