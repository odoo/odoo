# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

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
        selection=[('finkok', 'Quadrum'), ('solfact', 'Solucion Factible'),
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
        comodel_name='certificate.certificate',
        inverse_name='company_id',
        string='Certificates (MX)',
    )

    # == CFDI EDI ==
    l10n_mx_edi_fiscal_regime = fields.Selection(
        selection=FISCAL_REGIMES_SELECTION,
        string="Fiscal Regime",
        help="It is used to fill Mexican XML CFDI required field "
        "Comprobante.Emisor.RegimenFiscal.")
    l10n_mx_edi_global_invoice_sequence_id = fields.Many2one(
        string="Global Invoice Sequence",
        comodel_name='ir.sequence',
        compute='_compute_l10n_mx_edi_global_invoice_sequence_id',
    )
    l10n_mx_edi_global_invoice_sequence_prefix = fields.Char(
        string="Global Invoice Serie",
        compute='_compute_l10n_mx_edi_global_invoice_sequence_prefix',
        inverse='_inverse_l10n_mx_edi_global_invoice_sequence_prefix',
    )

    @api.depends('account_fiscal_country_id')
    def _compute_l10n_mx_edi_global_invoice_sequence_id(self):
        for company in self:
            if company.account_fiscal_country_id.code == 'MX':
                company.l10n_mx_edi_global_invoice_sequence_id = self.env['ir.sequence'].sudo().search(
                    [('code', '=', 'l10n_mx_global_invoice_cfdi'), ('company_id', '=', company.id)],
                    limit=1,
                )
            else:
                company.l10n_mx_edi_global_invoice_sequence_id = None

    def _create_l10n_mx_edi_global_invoice_sequence(self):
        self.ensure_one()
        sequence = self.env['ir.sequence'].sudo().create({
            'name': f"Global Invoice CFDI ({self.name})",
            'code': 'l10n_mx_global_invoice_cfdi',
            'company_id': self.id,
            'prefix': self.l10n_mx_edi_global_invoice_sequence_prefix,
            'implementation': 'standard',
            'use_date_range': True,
            'padding': 5,
        })
        self.invalidate_recordset(['l10n_mx_edi_global_invoice_sequence_id'])
        return sequence

    @api.depends('account_fiscal_country_id')
    def _compute_l10n_mx_edi_global_invoice_sequence_prefix(self):
        for company in self:
            if company.account_fiscal_country_id.code == 'MX':
                if sequence := company.l10n_mx_edi_global_invoice_sequence_id:
                    company.l10n_mx_edi_global_invoice_sequence_prefix = sequence.prefix
                else:
                    company.l10n_mx_edi_global_invoice_sequence_prefix = 'GINV/'
            else:
                company.l10n_mx_edi_global_invoice_sequence_prefix = None

    def _inverse_l10n_mx_edi_global_invoice_sequence_prefix(self):
        for company in self:
            if (
                company.account_fiscal_country_id.code == 'MX'
                and company.l10n_mx_edi_global_invoice_sequence_prefix
            ):
                if sequence := company.l10n_mx_edi_global_invoice_sequence_id:
                    # Update an existing sequence.
                    if sequence.prefix != company.l10n_mx_edi_global_invoice_sequence_prefix:
                        sequence.prefix = company.l10n_mx_edi_global_invoice_sequence_prefix
                else:
                    # Create a specific sequence for the branch only.
                    # By default, only the sequence of the root company is used (GINV/).
                    # The sequence for the root company will be created the first time a global invoice is created.
                    cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(company)
                    if (
                        company != cfdi_values['root_company']
                        and company.l10n_mx_edi_global_invoice_sequence_prefix != cfdi_values['root_company'].l10n_mx_edi_global_invoice_sequence_prefix
                    ):
                        company._create_l10n_mx_edi_global_invoice_sequence()
                        company.invalidate_recordset(fnames=['l10n_mx_edi_global_invoice_sequence_id'])

    def _l10n_mx_edi_get_foreign_customer_fiscal_position(self):
        """Return the fiscal position for foreign customers from the mexican chart template.
           Return an empty fiscal position in case it was not found.
        """
        self.ensure_one()
        fiscal_position = self.env['account.chart.template'].with_company(self).ref('account_fiscal_position_foreign', raise_if_not_found=False)
        return fiscal_position or self.env['account.fiscal.position']
