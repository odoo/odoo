# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebSaleDigitalResourcesDownload(HttpCase):
    def setUp(self):
        super().setUp()
        self.ir_attachment = self.env['ir.attachment'].create({'name': "test attachment"})

    def test_resources_can_be_downloaded(self):
        self.authenticate('admin', 'admin')
        res = self.url_open('/my/download', data={
            'attachment_id': self.ir_attachment.id,
            'csrf_token': http.Request.csrf_token(self),
        })
        res.raise_for_status()
