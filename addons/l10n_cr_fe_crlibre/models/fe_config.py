from odoo import fields, models, _, api
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

    province = fields.Char(string="Provincia", required=True)
    canton = fields.Char(string="Cantón", required=True)
    district = fields.Char(string="Distrito", required=True)
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

    @api.constrains('company_id')
    def _check_company_id_unique(self):
        for record in self:
            if record.company_id:
                existing = self.search([
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(
                        _("Ya existe una configuración de Factura Electrónica para esta empresa."))

    def _get_for_company(self, company):
        config = self.search([('company_id', '=', company.id)], limit=1)
        if not config:
            raise UserError(
                _("No hay configuración de Factura Electrónica para la empresa %s.") % company.name)
        return config
