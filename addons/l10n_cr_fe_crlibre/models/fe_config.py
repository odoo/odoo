import base64
import re
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nCrFeConfig(models.Model):
    _name = 'l10n_cr.fe.config'
    _description = 'Configuración de Factura Electrónica CR por empresa'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    environment = fields.Selection(
        selection=[('stag', 'Sandbox (stag)'), ('prod', 'Producción')],
        string="Ambiente", required=True, default='stag')

    identification_type = fields.Selection(
        selection=[('01', 'Física'), ('02', 'Jurídica'), ('03', 'DIMEX'), ('04', 'NITE')],
        string="Tipo de identificación", required=True)
    identification_number = fields.Char(string="Cédula", required=True)
    legal_name = fields.Char(string="Razón social", required=True)
    trade_name = fields.Char(string="Nombre comercial")
    economic_activity_code = fields.Char(string="Código de actividad económica", required=True)

    province = fields.Selection(
        selection=[
            ('1', "San José"), ('2', "Alajuela"), ('3', "Cartago"),
            ('4', "Heredia"), ('5', "Guanacaste"), ('6', "Puntarenas"), ('7', "Limón"),
        ],
        string="Provincia", required=True)
    canton = fields.Char(
        string="Cantón", required=True,
        help="Código numérico de 2 dígitos del cantón según el catálogo de Hacienda "
             "(no el nombre). Ej.: San Carlos en Alajuela es '10'.")
    district = fields.Char(
        string="Distrito", required=True,
        help="Código numérico de 2 dígitos del distrito según el catálogo de Hacienda "
             "(no el nombre). Ej.: Florencia en San Carlos es '02'.")
    neighborhood = fields.Char(string="Barrio", required=True)
    address_detail = fields.Char(string="Otras señas", required=True)
    phone = fields.Char(string="Teléfono")
    email = fields.Char(string="Correo electrónico", required=True)

    branch_number = fields.Char(string="Sucursal", default='001', required=True)
    terminal_number = fields.Char(string="Terminal", default='00001', required=True)

    hacienda_username = fields.Char(
        string="Usuario Hacienda", groups='l10n_cr_fe_crlibre.group_fe_admin')
    hacienda_password = fields.Char(
        string="Contraseña Hacienda", groups='l10n_cr_fe_crlibre.group_fe_admin')
    certificate_file = fields.Binary(
        string="Certificado .p12", groups='l10n_cr_fe_crlibre.group_fe_admin')
    certificate_filename = fields.Char(string="Nombre del archivo")
    certificate_pin = fields.Char(
        string="PIN del certificado", groups='l10n_cr_fe_crlibre.group_fe_admin')

    crlibre_api_username = fields.Char(groups='l10n_cr_fe_crlibre.group_fe_admin')
    crlibre_api_password = fields.Char(groups='l10n_cr_fe_crlibre.group_fe_admin')
    certificate_download_code = fields.Char(readonly=True)

    _company_id_uniq = models.Constraint(
        'UNIQUE (company_id)',
        "Ya existe una configuración de Factura Electrónica para esta empresa.",
    )

    _CANTON_DISTRICT_RE = re.compile(r'^\d{2}$')

    @api.constrains('canton', 'district')
    def _check_l10n_cr_fe_canton_district(self):
        for config in self:
            if config.canton and not self._CANTON_DISTRICT_RE.match(config.canton):
                raise ValidationError(
                    _("El cantón debe ser el código numérico de 2 dígitos del catálogo "
                      "de Hacienda (no el nombre)."))
            if config.district and not self._CANTON_DISTRICT_RE.match(config.district):
                raise ValidationError(
                    _("El distrito debe ser el código numérico de 2 dígitos del catálogo "
                      "de Hacienda (no el nombre)."))

    def _get_for_company(self, company):
        config = self.search([('company_id', '=', company.id)], limit=1)
        if not config:
            raise UserError(
                _("No hay configuración de Factura Electrónica para la empresa %s.") % company.name)
        return config

    def _l10n_cr_fe_next_consecutivo(self, tipo_documento_codigo):
        self.ensure_one()
        # Hacienda exige un correlativo independiente por tipo de documento (01=FE,
        # 03=NC, etc.), cada uno empezando en 1 - por eso el codigo de secuencia
        # incluye el tipo de documento, no solo la empresa.
        code = 'l10n_cr_fe.consecutivo.%s.%s' % (tipo_documento_codigo, self.company_id.id)
        # Advisory lock keyed by company id: prevents two concurrent transactions
        # from both missing the search and creating duplicate ir.sequence rows
        # for this company's first-ever consecutivo.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s)', (self.company_id.id,))
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', code)], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'Consecutivo FE %s - %s' % (tipo_documento_codigo, self.company_id.name),
                'code': code,
                'company_id': self.company_id.id,
                'padding': 10,
                'number_increment': 1,
                'implementation': 'no_gap',
            })
        return sequence.next_by_id()

    def _l10n_cr_fe_ensure_certificate_uploaded(self):
        self.ensure_one()
        if self.certificate_download_code:
            return self.certificate_download_code
        if not self.certificate_file:
            raise UserError(_("Debe cargar el certificado .p12 antes de generar comprobantes."))

        client = self.env['l10n_cr.fe.client']
        if not self.crlibre_api_username:
            username = 'odoo-%s-%s' % (self.company_id.id, uuid.uuid4().hex[:8])
            password = uuid.uuid4().hex
            client.register_api_user(self.company_id.name or username, username, password)
            self.crlibre_api_username = username
            self.crlibre_api_password = password

        login = client.login_api_user(self.crlibre_api_username, self.crlibre_api_password)
        upload = client.upload_certificate(
            login['session_key'], self.crlibre_api_username,
            base64.b64decode(self.certificate_file))
        self.certificate_download_code = upload['download_code']
        return self.certificate_download_code
