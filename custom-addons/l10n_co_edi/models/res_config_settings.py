# coding: utf-8
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_co_edi_username = fields.Char(related='company_id.l10n_co_edi_username', readonly=False,
                                       string='Username')
    l10n_co_edi_password = fields.Char(related='company_id.l10n_co_edi_password', readonly=False,
                                       string='Password')
    l10n_co_edi_company = fields.Char(related='company_id.l10n_co_edi_company', readonly=False,
                                      string='Company Registry')
    l10n_co_edi_account = fields.Char(related='company_id.l10n_co_edi_account', readonly=False,
                                      string='Account ID')
    l10n_co_edi_test_mode = fields.Boolean(related='company_id.l10n_co_edi_test_mode', readonly=False,
                                           string='Test mode')
    l10n_co_edi_header_gran_contribuyente = fields.Char(related='company_id.l10n_co_edi_header_gran_contribuyente', readonly=False,
                                                        string='Gran Contribuyente')
    l10n_co_edi_header_tipo_de_regimen = fields.Char(related='company_id.l10n_co_edi_header_tipo_de_regimen', readonly=False,
                                                     string='Tipo de Régimen')
    l10n_co_edi_header_retenedores_de_iva = fields.Char(related='company_id.l10n_co_edi_header_retenedores_de_iva', readonly=False,
                                                        string='Retenedores de IVA')
    l10n_co_edi_header_autorretenedores = fields.Char(related='company_id.l10n_co_edi_header_autorretenedores', readonly=False,
                                                      string='Autorretenedores')
    l10n_co_edi_header_resolucion_aplicable = fields.Char(related='company_id.l10n_co_edi_header_resolucion_aplicable', readonly=False,
                                                          string='Resolucion Aplicable')
    l10n_co_edi_header_actividad_economica = fields.Char(related='company_id.l10n_co_edi_header_actividad_economica', readonly=False,
                                                         string='Actividad Económica')
    l10n_co_edi_header_bank_information = fields.Text(related='company_id.l10n_co_edi_header_bank_information', readonly=False,
                                                      string='Bank Information')
    l10n_co_edi_template_code = fields.Selection(string="Colombia Template Code",
                                                 readonly=False, related="company_id.l10n_co_edi_template_code")
