import base64
from cryptography import x509

from odoo import models, fields, api


class Certificate(models.Model):
    _inherit = "certificate.certificate"

    user_id = fields.Many2one('res.users', 'Certificate Owner',
                              help='If this certificate has an owner, he will be the only user authorized to use it, '
                                   'otherwise, the certificate will be shared with other users of the current company')
    last_token = fields.Char('Last Token', readonly=True)
    token_time = fields.Datetime('Token Time')
    l10n_cl_is_there_shared_certificate = fields.Boolean(related='company_id.l10n_cl_is_there_shared_certificate')
    last_rest_token = fields.Char('Last REST Token')
    subject_serial_number = fields.Char(
        compute='_compute_subject_serial_number', string='Subject Serial Number', store=True, readonly=False, copy=False,
        help='This is the document of the owner of this certificate.'
             'Some certificates do not provide this number and you must fill it by hand'
    )

    @api.depends('pem_certificate')
    def _compute_subject_serial_number(self):
        ''' Compute the subject serial number when it is not manually input by the user. '''
        for certificate in self:
            pem_certificate = certificate.with_context(bin_size=False).pem_certificate
            if not certificate.subject_serial_number and pem_certificate:
                cert = x509.load_pem_x509_certificate(base64.b64decode(pem_certificate))
                subject_serial_number = cert.subject.get_attributes_for_oid(x509.oid.NameOID.SERIAL_NUMBER)
                if subject_serial_number:
                    certificate.subject_serial_number = subject_serial_number[0].value
