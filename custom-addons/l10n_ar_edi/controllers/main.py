# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http


class DownloadCertificateRequst(http.Controller):

    @http.route('/l10n_ar_edi/download_csr/<int:company_id>', type='http', auth="user")
    def download_csr(self, company_id, **kw):
        """ Download the certificate request file to upload in AFIP """
        company = http.request.env['res.company'].sudo().browse(company_id)
        content = company._l10n_ar_create_certificate_request()
        if not content:
            return http.request.not_found()
        return http.request.make_response(content, headers=[('Content-Type', 'text/plain'), ('Content-Disposition', http.content_disposition('request.csr'))])
