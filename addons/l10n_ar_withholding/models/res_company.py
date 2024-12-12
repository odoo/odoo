# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ar_tax_ids = fields.One2many('account.fiscal.position.l10n_ar_tax', 'company_id')
    l10n_ar_tax_base_account_id = fields.Many2one(
        comodel_name='account.account',
        domain=[('deprecated', '=', False)],
        string="Tax Base Account",
        help="Account that will be set on lines created to represent the tax base amounts.")
    arba_cit = fields.Char(
        'CIT ARBA',
        help='Clave de Identificación Tributaria de ARBA',
    )

    def _l10n_ar_add_taxes(self, partner, company, date):
        # TODO deberiamos unificar mucho de este codigo con _get_tax_domain, _compute_withholdings y _check_tax_group_overlap
        self.ensure_one()
        taxes = self.env['account.tax']
        for fp_tax in self.l10n_ar_tax_ids:
            domain = self.env['l10n_ar.partner.tax']._check_company_domain(company)
            domain += [('tax_id.tax_group_id', '=', fp_tax.default_tax_id.tax_group_id.id)]
            domain += [
                '|', ('from_date', '<=', date), ('from_date', '=', False),
                '|', ('to_date', '>=', date), ('to_date', '=', False),
            ]
            partner_tax = partner.l10n_ar_partner_tax_ids.filtered_domain(domain).mapped('tax_id')
            # agregamos taxes para grupos de impuestos que no estaban seteados en el partner
            if not partner_tax:
                partner_tax = fp_tax._get_missing_taxes(partner, date)
            taxes |= partner_tax
        return taxes

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
