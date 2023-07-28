# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.addons.account.controllers.download_edi_docs import AccountEdiDocumentDownloadController

class EdiDocumentDownloadController(AccountEdiDocumentDownloadController):
    @http.route('/account_edi/download_edi_documents', type='http', auth='user')
    def download_edi_documents(self, **args):
        return super().export_edi_documents()
