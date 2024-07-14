# -*- coding: utf-8 -*-
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

FISCAL_REGIMES_SELECTION = [
    ('601', 'General de Ley Personas Morales'),
    ('603', 'Personas Morales con Fines no Lucrativos'),
    ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
    ('606', 'Arrendamiento'),
    ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
    ('608', 'Demás ingresos'),
    ('609', 'Consolidación'),
    ('610', 'Residentes en el Extranjero sin Establecimiento Permanente en México'),
    ('611', 'Ingresos por Dividendos (socios y accionistas)'),
    ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
    ('614', 'Ingresos por intereses'),
    ('615', 'Régimen de los ingresos por obtención de premios'),
    ('616', 'Sin obligaciones fiscales'),
    ('620', 'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
    ('621', 'Incorporación Fiscal'),
    ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
    ('623', 'Opcional para Grupos de Sociedades'),
    ('624', 'Coordinados'),
    ('625', 'Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas'),
    ('626', 'Régimen Simplificado de Confianza - RESICO'),
    ('628', 'Hidrocarburos'),
    ('629', 'De los Regímenes Fiscales Preferentes y de las Empresas Multinacionales'),
    ('630', 'Enajenación de acciones en bolsa de valores')]


class ResCompany(models.Model):
    _inherit = 'res.company'

    # == PAC web-services ==
    l10n_mx_edi_pac = fields.Selection(
        selection=[('finkok', 'Quadrum (formerly finkok)'), ('solfact', 'Solucion Factible'),
                   ('sw', 'SW sapien-SmarterWEB')],
        string='PAC',
        help='The PAC that will sign/cancel the invoices',
        default='finkok')
    l10n_mx_edi_pac_test_env = fields.Boolean(
        string='PAC test environment',
        help='Enable the usage of test credentials',
        default=False)
    l10n_mx_edi_pac_username = fields.Char(
        string='PAC username',
        help='The username used to request the seal from the PAC',
        groups='base.group_system')
    l10n_mx_edi_pac_password = fields.Char(
        string='PAC password',
        help='The password used to request the seal from the PAC',
        groups='base.group_system')
    l10n_mx_edi_certificate_ids = fields.One2many(
        comodel_name='l10n_mx_edi.certificate',
        inverse_name='company_id',
        string='Certificates (MX)',
    )

    # == CFDI EDI ==
    l10n_mx_edi_fiscal_regime = fields.Selection(
        selection=FISCAL_REGIMES_SELECTION,
        string="Fiscal Regime",
        help="It is used to fill Mexican XML CFDI required field "
        "Comprobante.Emisor.RegimenFiscal.")

    def _l10n_mx_edi_get_foreign_customer_fiscal_position(self):
        """Return the fiscal position for foreign customers from the mexican chart template.
           Return an empty fiscal position in case it was not found.
        """
        self.ensure_one()
        fiscal_position = self.env['account.chart.template'].with_company(self).ref('account_fiscal_position_foreign', raise_if_not_found=False)
        return fiscal_position or self.env['account.fiscal.position']
