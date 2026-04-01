from odoo import http
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import file_open


@tagged("-at_install", "post_install")
class TestUpload(HttpCase):

    @mute_logger("odoo.addons.sale_pdf_quote_builder.controllers.quotation_document", "odoo.http")
    def test_wrong_pdf(self):
        self.authenticate("admin", "admin")
        data = {'csrf_token': http.Request.csrf_token(self)}
        # Structurally valid but AES-encrypted PDF file (generated with PyPDF)
        with file_open('sale_pdf_quote_builder/tests/files/test_AES.pdf', 'rb') as f:
            files = [('ufile', ('test_AES.pdf', f.read(), 'application/pdf'))]
        resp = self.url_open("/sale_pdf_quote_builder/quotation_document/upload", data=data, files=files)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.headers['Content-Type'], 'application/json; charset=utf-8')
        self.assertEqual(resp.text, R'''{"error": "It seems that we're not able to process this pdf inside a quotation. It is either encrypted, or encoded in a format we do not support."}''')
