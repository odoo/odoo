from requests.exceptions import HTTPError
import base64
import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_nl_reports_sbr_cert_id = fields.Many2one(
        string='Digipoort Certificate',
        comodel_name='certificate.certificate',
        domain=[('is_valid', "=", True)],
        help="Select the certificate that will be used to connect to the Digipoort infrastructure. "
             "The private key from this certificate will be used if one is included.",
    )
    l10n_nl_reports_sbr_server_root_cert_id = fields.Many2one(
        string='SBR Root Certificate',
        comodel_name='certificate.certificate',
        domain=[('is_valid', "=", True)],
        help="The SBR Tax Service Server Root Certificate is used to verifiy the connection with the Tax services server of the SBR."
        "It is used in order to make the connection library trust the server.",
    )
    l10n_nl_reports_sbr_last_sent_date_to = fields.Date(
        string='Last Date Sent',
        help="Stores the date of the end of the last period submitted to the Tax Services",
        readonly=True,
    )

    def _l10n_nl_get_server_root_certificate_bytes(self):
        """ Return the tax service server root certificate as PEM encoded bytes.
            Throws a UserError if the services are not reachable.
        """
        if not self.sudo().l10n_nl_reports_sbr_server_root_cert_id or not self.sudo().l10n_nl_reports_sbr_server_root_cert_id.is_valid:
            try:
                req_root = requests.get('https://cert.pkioverheid.nl/PrivateRootCA-G1.cer', timeout=30)
                req_root.raise_for_status()

                # This certificate is a .cer and is in DER format
                cert = self.env['certificate.certificate'].sudo().create({
                    'name': 'SBR Root Certificate',
                    'content': base64.b64encode(req_root.content),
                })
                self.write({'l10n_nl_reports_sbr_server_root_cert_id': cert.id})
            except HTTPError:
                raise UserError(_("The server root certificate is not accessible at the moment. Please try again later."))

        return base64.b64decode(self.sudo().l10n_nl_reports_sbr_server_root_cert_id.pem_certificate)
