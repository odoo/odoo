# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.addons.account.tools.certificate import crypto_load_certificate
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import file_open
from datetime import datetime
import base64
import random
import logging


_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
except ImportError:
    _logger.warning('OpenSSL library not found. If you plan to use l10n_ar_edi, please install the library from https://pypi.python.org/pypi/pyOpenSSL')


class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_ar_afip_verification_type = fields.Selection([('not_available', 'Not Available'), ('available', 'Available'), ('required', 'Required')], required=True,
        default='not_available', string='AFIP Invoice Verification', help='It adds an option on invoices to'
        ' verify the invoices in AFIP if the invoices has CAE, CAI or CAEA numbers.\n\n'
        '* Not Available: Will NOT show "Verify on AFIP" button in the invoices\n'
        '* Available: Will show "Verify on AFIP" button in the invoices so the user can manually check the vendor'
        ' bills\n'
        '* Required: The vendor bills will be automatically verified on AFIP before been posted in Odoo. This is to'
        ' ensure that you have verified all the vendor bills that you are reporting in your Purchase VAT Book. NOTE:'
        ' Not all the document types can be validated in AFIP, only the ones defined in this link are the ones that '
        ' we are automatically validating https://serviciosweb.afip.gob.ar/genericos/comprobantes/Default.aspx')

    l10n_ar_connection_ids = fields.One2many('l10n_ar.afipws.connection', 'company_id', 'Connections')

    # Certificate fields
    l10n_ar_afip_ws_environment = fields.Selection([('testing', 'Testing'), ('production', 'Production')], string="AFIP Environment", default='production',
        help="Environment used to connect to AFIP webservices. Production is to create real fiscal invoices in AFIP,"
        " Testing is for testing invoice creation in AFIP (commonly named in AFIP as Homologation environment).")
    l10n_ar_afip_ws_key = fields.Binary('Private Key', groups="base.group_system", help="This private key is required because is sent to the AFIP when"
        " trying to create a connection to validate that you are you\n\n * If you have one you can upload it here (In"
        " order to be valid the private key should be in PEM format)\n * if you have not then Odoo will automatically"
        " create a new one when you click in 'Generate Request' or 'Generate Renewal Request' button")
    l10n_ar_afip_ws_crt = fields.Binary('Certificate', groups="base.group_system", help="This certificate lets us connect to AFIP to validate electronic invoice."
        " Please upload here the AFIP certificate in PEM format. You can get your certificate from your AFIP Portal")
    l10n_ar_afip_ws_crt_fname = fields.Char('Certificate name', compute="_compute_l10n_ar_afip_ws_crt_fname", store=True)

    l10n_ar_fce_transmission_type = fields.Selection(
        [('SCA', 'SCA - TRANSFERENCIA AL SISTEMA DE CIRCULACION ABIERTA'), ('ADC', 'ADC - AGENTE DE DEPOSITO COLECTIVO')],
        'FCE: Transmission Option Default',
        help='Default value for "FCE: Transmission Option" on electronic invoices')

    @api.depends('l10n_ar_afip_ws_crt')
    def _compute_l10n_ar_afip_ws_crt_fname(self):
        """ Set the certificate name in the company. Needed in unit tests, solved by a similar onchange method in res.config.settings while setting the certificate via web interface """
        with_crt = self.filtered(lambda x: x.l10n_ar_afip_ws_crt)
        remaining = self - with_crt
        for rec in with_crt:
            certificate = self._l10n_ar_get_certificate_object(rec.with_context(bin_size=False).l10n_ar_afip_ws_crt)
            rec.l10n_ar_afip_ws_crt_fname = certificate.get_subject().CN
        remaining.l10n_ar_afip_ws_crt_fname = ''

    @api.constrains('l10n_ar_afip_ws_crt')
    def _l10n_ar_check_afip_certificate(self):
        """ Verify if certificate uploaded is well formed before saving """
        for rec in self.filtered('l10n_ar_afip_ws_crt'):
            error = False
            try:
                content = base64.decodebytes(rec.with_context(bin_size=False).l10n_ar_afip_ws_crt).decode('ascii')
                crypto.load_certificate(crypto.FILETYPE_PEM, content)
            except Exception as exc:
                if 'Expecting: CERTIFICATE' in repr(exc) or "('PEM routines', 'get_name', 'no start line')" in repr(exc):
                    error = _('Wrong certificate file format.\nPlease upload a valid PEM certificate.')
                else:
                    error = _('Not a valid certificate file')
                _logger.warning('%s %s' % (error, repr(exc)))
            if error:
                raise ValidationError('\n'.join([_('The certificate can not be uploaded!'), error]))

    @api.constrains('l10n_ar_afip_ws_key')
    def _l10n_ar_check_afip_private_key(self):
        """ Verify if private key uploaded is well formed before saving """
        for rec in self.filtered('l10n_ar_afip_ws_key'):
            error = False
            try:
                content = base64.decodebytes(rec.with_context(bin_size=False).l10n_ar_afip_ws_key).decode('ascii').strip()
                crypto.load_privatekey(crypto.FILETYPE_PEM, content)
            except Exception as exc:
                error = _('Not a valid private key file')
                _logger.warning('%s %s' % (error, repr(exc)))
            if error:
                raise ValidationError('\n'.join([_('The private key can not be uploaded!'), error]))

    def _l10n_ar_get_certificate_object(self, cert):
        crt_str = base64.decodebytes(cert).decode('ascii')
        return crypto_load_certificate(crt_str)

    def _l10n_ar_get_afip_crt_expire_date(self):
        """ return afip certificate expire date in datetime.date() """
        self.ensure_one()
        crt = self.with_context(bin_size=False).l10n_ar_afip_ws_crt
        if crt:
            certificate = self._l10n_ar_get_certificate_object(crt)
            datestring = certificate.get_notAfter().decode()
            return datetime.strptime(datestring, '%Y%m%d%H%M%SZ').date()

    def _l10n_ar_is_afip_crt_expire(self):
        """ Raise exception if the AFIP certificate is expired """
        self.ensure_one()
        expire_date = self._l10n_ar_get_afip_crt_expire_date()
        if expire_date and expire_date < fields.Date.today():
            raise UserError(_('The AFIP certificate is expired, please renew in order to continue'))

    def _get_environment_type(self):
        """ This method is used to return the environment type of the company (testing or production) and will raise an
        exception when it has not been defined yet """
        self.ensure_one()
        if not self.l10n_ar_afip_ws_environment:
            raise UserError(_('AFIP environment not configured for company %r, please check accounting settings', self.name))
        return self.l10n_ar_afip_ws_environment

    def _l10n_ar_get_connection(self, afip_ws):
        """ Returns the last existing connection with AFIP web service, or creates a new one  (which means login to AFIP
        and save token information in a new connection record in Odoo)

        IMPORTANT WARNING: Be careful using this method, when a new connection is created, it will do a cr.commit() """
        self.ensure_one()
        if not afip_ws:
            raise UserError(_('No AFIP WS selected'))

        env_type = self._get_environment_type()
        connection = self.l10n_ar_connection_ids.search([('type', '=', env_type), ('l10n_ar_afip_ws', '=', afip_ws), ('company_id', '=', self.id)], limit=1)

        if connection and connection.expiration_time > fields.Datetime.now():
            return connection

        token_data = connection._l10n_ar_get_token_data(self, afip_ws)
        if connection:
            connection.sudo().write(token_data)
        else:
            values = {'company_id': self.id, 'l10n_ar_afip_ws': afip_ws, 'type': env_type}
            values.update(token_data)
            _logger.info('Connection created for company %s %s (%s)' % (self.name, afip_ws, env_type))
            connection = connection.sudo().create(values)

        # This commit is needed because we need to maintain the connection information no matter if the invoices have
        # been validated or not. This because when we request a token we can not generate a new one until the last
        # one expires.
        if not self.env.context.get('l10n_ar_invoice_skip_commit'):
            self._cr.commit()
        _logger.info("Successful Authenticated with AFIP.")

        return connection

    def _get_key_and_certificate(self):
        """ Return the pkey and certificate string representations in order to be used. Also raise exception if any key or certificate is not defined """
        self.ensure_one()
        pkey = base64.decodebytes(self.with_context(bin_size=False).l10n_ar_afip_ws_key) if self.l10n_ar_afip_ws_key else ''
        cert = base64.decodebytes(self.with_context(bin_size=False).l10n_ar_afip_ws_crt) if self.l10n_ar_afip_ws_crt else ''
        res = (pkey, cert)
        if not all(res):
            error = '\n * ' + _(' Missing private key.') if not pkey else ''
            error += '\n * ' + _(' Missing certificate.') if not cert else ''
            raise UserError(_('Missing configuration to connect to AFIP:') + error)
        self._l10n_ar_is_afip_crt_expire()
        return res

    def _generate_afip_private_key(self, key_length=2048):
        """ Generate private key to use in so sign AFIP Certificate"""
        for rec in self:
            key_obj = crypto.PKey()
            key_obj.generate_key(crypto.TYPE_RSA, key_length)
            key = crypto.dump_privatekey(crypto.FILETYPE_PEM, key_obj)
            key = base64.b64encode(key)
            rec.l10n_ar_afip_ws_key = key

    def _l10n_ar_create_certificate_request(self):
        """ Create Certificate Request """
        self.ensure_one()
        req = crypto.X509Req()
        req_subject = req.get_subject()
        req_subject.C = self.partner_id.country_id.code.encode('ascii', 'ignore')

        if self.partner_id.state_id:
            req_subject.ST = self.partner_id.state_id.name.encode('ascii', 'ignore')

        common_name = 'AFIP WS %s - %s' % (self._get_environment_type(), self.name)
        common_name = common_name[:50]

        req_subject.L = self.partner_id.city.encode('ascii', 'ignore')
        req_subject.O = self.name.encode('ascii', 'ignore')
        req_subject.OU = 'IT'.encode('ascii', 'ignore')
        req_subject.CN = common_name.encode('ascii', 'ignore')
        req_subject.serialNumber = ('CUIT %s' % self.partner_id.ensure_vat()).encode('ascii', 'ignore')

        if not self.l10n_ar_afip_ws_key:
            self._generate_afip_private_key()
        pkey = base64.decodebytes(self.with_context(bin_size=False).l10n_ar_afip_ws_key)

        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, pkey)
        req.set_pubkey(private_key)
        req.sign(private_key, 'sha256')
        csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        return csr

    def set_demo_random_cert(self):
        """ Method used to assign a random certificate to the company. This method is called when loading demo data to
        assign a random certificate to the demo companies. It is also available as button in the res.config.settings
        wizard to let the user change the certificate randomly if the one been set is blocked (because someone else
        is using the same certificate in another database) """
        for rec in self:
            old = rec.l10n_ar_afip_ws_crt_fname
            cert_file = 'l10n_ar_edi/demo/cert%d.crt' % random.randint(1, 10)
            rec.l10n_ar_afip_ws_crt = base64.b64encode(file_open(cert_file, 'rb').read())
            _logger.log(25, 'Setting demo certificate from %s to %s in %s company' % (old, rec.l10n_ar_afip_ws_crt_fname, rec.name))
