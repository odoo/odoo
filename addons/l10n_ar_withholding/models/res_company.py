from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    from pyafipws.iibb import IIBB
except ImportError:
    IIBB = None
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ar_tax_base_account_id = fields.Many2one(
        comodel_name='account.account',
        domain=[('deprecated', '=', False)],
        string="Tax Base Account",
        help="Account that will be set on lines created to represent the tax base amounts.")
    arba_cit = fields.Char(
        'CIT ARBA',
        help='Clave de Identificación Tributaria de ARBA',)

    @api.model
    def _get_arba_environment_type(self):
        """
        Function to define homologation/production environment
        First it search for a paramter "arba.ws.env.type" if exists and:
        * is production --> production
        * is homologation --> homologation
        Else
        Search for 'server_mode' parameter on conf file. If that parameter is:
        * 'test' or 'develop' -->  homologation
        * other or no parameter -->  production
        """
        # como no se dispone de claves de homologacion usamos produccion
        # siempre
        environment_type = 'production'
        return environment_type

    @api.model
    def get_arba_login_url(self, environment_type):
        if environment_type == 'production':
            arba_login_url = (
                'https://dfe.arba.gov.ar/DomicilioElectronico/'
                'SeguridadCliente/dfeServicioConsulta.do')
        else:
            arba_login_url = (
                'https://dfe.test.arba.gov.ar/DomicilioElectronico'
                '/SeguridadCliente/dfeServicioConsulta.do')
        return arba_login_url

    def arba_connect(self):
        """
        Method to be called
        """
        self.ensure_one()
        cuit = self.partner_id.ensure_vat()

        if not self.arba_cit:
            raise UserError(_(
                'You must configure CIT password on company %s') % (self.name))

        try:
            ws = IIBB()
            environment_type = self._get_arba_environment_type()
            _logger.info(
                'Getting connection to ARBA on %s mode' % environment_type)

            # argumentos de conectar: self, url=None, proxy="",
            # wrapper=None, cacert=None, trace=False, testing=""
            arba_url = self.get_arba_login_url(environment_type)
            ws.Usuario = cuit
            ws.Password = self.arba_cit
            ws.Conectar(url=arba_url)
            _logger.info(
                'Connection getted to ARBA with url "%s" and CUIT %s' % (
                    arba_url, cuit))
        except ConnectionRefusedError:
            raise UserError('No se pudo conectar a ARBA para extraer los datos de percepcion/retención.'
                            ' Por favor espere unos minutos e intente de nuevo. Sino, cargue manualmente'
                            ' los datos en el cliente para poder operar (fecha %s)' % self.env.context.get('invoice_date'))

        return ws

    @api.model
    def _process_message_error(self, ws):
        message = ws.MensajeError
        message = message.replace('<![CDATA[', '').replace(']]/>', '')
        raise UserError(_('Padron ARBA: %s - %s (%s)') % (ws.CodigoError, message, ws.TipoError))
