# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import file_open
from datetime import datetime
import base64
import random
import logging


_logger = logging.getLogger(__name__)


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
    l10n_ar_afip_ws_key_id = fields.Many2one(string='Private Key', comodel_name='certificate.key', domain=[('public', '=', False)],
        compute="_compute_afip_key", store=True, readonly=False,
        help="This private key is required because is sent to the AFIP when"
        " trying to create a connection to validate that you are you\n\n * If you have one you can upload it here (In"
        " order to be valid the private key should be in PEM format)\n * if you have not then Odoo will automatically"
        " create a new one when you click in 'Generate Request' or 'Generate Renewal Request' button")
    l10n_ar_afip_ws_crt_id = fields.Many2one(string='AFIP Certificate', comodel_name="certificate.certificate",
        compute="_compute_afip_crt", store=True, readonly=False,
        help="This certificate lets us connect to AFIP to validate electronic invoice."
        " Please select here the AFIP certificate in PEM format. You can get your certificate from your AFIP Portal")
    l10n_ar_fce_transmission_type = fields.Selection(
        [('SCA', 'SCA - TRANSFERENCIA AL SISTEMA DE CIRCULACION ABIERTA'), ('ADC', 'ADC - AGENTE DE DEPOSITO COLECTIVO')],
        'FCE: Transmission Option Default',
        help='Default value for "FCE: Transmission Option" on electronic invoices')
    l10n_ar_payment_foreign_currency = fields.Selection(
        selection=[("Yes", "Yes"), ("No", "No"), ("account", "Account's Currency Dependant")],
        compute="_compute_l10n_ar_payment_foreign_currency",
        string="Default Policy for Payment in Foreign Currency",
    )

    def _compute_l10n_ar_payment_foreign_currency(self):
        for company in self:
            company.l10n_ar_payment_foreign_currency = self.env["ir.config_parameter"].sudo().get_param(
                f"l10n_ar_edi.{company.id}_foreign_currency_payment", "No")

    @api.depends('l10n_ar_afip_ws_key_id')
    def _compute_afip_crt(self):
        key_ids = self.l10n_ar_afip_ws_key_id.ids
        certs = self.env['certificate.certificate'].search([('private_key_id', 'in', key_ids)])
        key_to_cert = {cert.private_key_id: cert for cert in certs}
        key_to_cert[False] = False
        for company in self:
            if company.country_code != 'AR':
                continue
            if not company.l10n_ar_afip_ws_crt_id:
                company.l10n_ar_afip_ws_crt_id = key_to_cert.get(company.l10n_ar_afip_ws_key_id)
            else:
                company.l10n_ar_afip_ws_crt_id.private_key_id = company.l10n_ar_afip_ws_key_id

    @api.depends('l10n_ar_afip_ws_crt')
    def _compute_l10n_ar_afip_ws_crt_fname(self):
        """ Set the certificate name in the company. Needed in unit tests, solved by a similar onchange method in res.config.settings while setting the certificate via web interface """
        with_crt = self.filtered(lambda x: x.l10n_ar_afip_ws_crt)
        remaining = self - with_crt
        for rec in with_crt:
            certificate = self._l10n_ar_get_certificate_object(rec.with_context(bin_size=False).l10n_ar_afip_ws_crt)
            rec.l10n_ar_afip_ws_crt_fname = certificate.get_subject().CN
        remaining.l10n_ar_afip_ws_crt_fname = ''

    @api.depends('l10n_ar_afip_ws_crt_id.private_key_id')
    def _compute_afip_key(self):
        for company in self:
            if company.country_code != 'AR':
                continue
            company.l10n_ar_afip_ws_key_id = company.l10n_ar_afip_ws_crt_id.private_key_id

    def _get_environment_type(self):
        """ This method is used to return the environment type of the company (testing or production) and will raise an
        exception when it has not been defined yet """
        self.ensure_one()
        if not self.l10n_ar_afip_ws_environment:
            raise UserError(_('AFIP environment not configured for company “%s”, please check accounting settings', self.name))
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

    def set_demo_random_cert(self):
        """ Method used to assign a random certificate to the company. This method is called when loading demo data to
        assign a random certificate to the demo companies. It is also available as button in the res.config.settings
        wizard to let the user change the certificate randomly if the one been set is blocked (because someone else
        is using the same certificate in another database) """
        for company in self:
            if company.country_code != 'AR':
                continue
            old_cert_name = company.l10n_ar_afip_ws_crt_id.name
            rid = random.randint(1, 10)
            new_cert_name = 'AR demo certificate %d' % rid
            new_cert = self.env['certificate.certificate'].search([('name', '=', new_cert_name), ('company_id', '=', company.id)], limit=1)
            if not new_cert:
                cert_file = 'l10n_ar_edi/demo/cert%d.crt' % rid
                new_cert = self.env['certificate.certificate'].create({
                    'name': new_cert_name,
                    'content': base64.b64encode(file_open(cert_file, 'rb').read()),
                    'private_key_id': company.l10n_ar_afip_ws_key_id.id,
                    'company_id': company.id,
                })
            company.l10n_ar_afip_ws_crt_id = new_cert
            _logger.log(25, 'Setting demo certificate from %s to %s in %s company', old_cert_name, new_cert_name, company.name)
