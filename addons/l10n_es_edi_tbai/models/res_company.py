# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

L10N_ES_EDI_TBAI_VERSION = 1.2
L10N_ES_EDI_TBAI_URLS = {
    'signing_policy': {
        'araba': ('https://ticketbai.araba.eus/tbai/sinadura/', ''),
        'bizkaia': ('', ''),
        'gipuzkoa': ('https://www.gipuzkoa.eus/documents/2456431/12093238/TicketBAI_Pol%C3%ADtica_firma_v_1_0.pdf/3c6e5431-bb1d-34ed-5b26-206aaf085452', ''),
    },
    'invoice_test': {
        'araba': 'https://pruebas-ticketbai.araba.eus/TicketBAI/v1/facturas/',
        'bizkaia': 'https://pruesarrerak.bizkaia.eus/N3B4000M/aurkezpena',
        'gipuzkoa': 'https://tbai-prep.egoitza.gipuzkoa.eus/WAS/HACI/HTBRecepcionFacturasWEB/rest/recepcionFacturas/alta'
    },
    'invoice_prod': {
        'araba': 'https://ticketbai.araba.eus/TicketBAI/v1/facturas/',
        'bizkaia': '',
        'gipuzkoa': 'https://tbai-z.egoitza.gipuzkoa.eus/sarrerak/alta'
    },
    'qr_test': {
        'araba': 'https://pruebas-ticketbai.araba.eus/tbai/qrtbai/',
        'bizkaia': 'https://batuz.eus/QRTBAI/',
        'gipuzkoa': 'https://tbai.prep.gipuzkoa.eus/qr/'
    },
    'qr_prod': {
        'araba': 'https://ticketbai.araba.eus/tbai/qrtbai/',
        'bizkaia': 'https://batuz.eus/QRTBAI/',
        'gipuzkoa': 'https://tbai.egoitza.gipuzkoa.eus/qr/'
    },
    'cancel_test': {
        'araba': 'https://pruebas-ticketbai.araba.eus/TicketBAI/v1/anulaciones/',
        'bizkaia': 'https://pruesarrerak.bizkaia.eus/N3B4000M/aurkezpena',
        'gipuzkoa': 'https://tbai-prep.egoitza.gipuzkoa.eus/WAS/HACI/HTBRecepcionFacturasWEB/rest/recepcionFacturas/anulacion'
    },
    'cancel_prod': {
        'araba': 'https://ticketbai.araba.eus/TicketBAI/v1/anulaciones/',
        'bizkaia': '',
        'gipuzkoa': 'https://tbai-z.egoitza.gipuzkoa.eus/sarrerak/baja'
    },
    'xsd': {
        'araba': '',
        'bizkaia': '',
        'gipuzkoa': 'https://www.gipuzkoa.eus/documents/2456431/13761107/Esquemas+de+archivos+XSD+de+env%C3%ADo+y+anulaci%C3%B3n+de+factura_1_2.zip/2d116f8e-4d3a-bff0-7b03-df1cbb07ec52',
    }
}

class ResCompany(models.Model):
    _inherit = 'res.company'

    # === TBAI config ===
    l10n_es_tbai_tax_agency = fields.Selection(
        string="Tax Agency for TBAI",
        selection=[
            ('araba', "Hacienda Foral de Araba"),  # es-vi
            ('bizkaia', "Hacienda Foral de Bizkaia"),  # es-bi
            ('gipuzkoa', "Hacienda Foral de Gipuzkoa"),  # es-ss
        ],
        default=False,  # TODO set default based on region ?
    )

    l10n_es_tbai_test_env = fields.Boolean(
        string="Test Mode",
        help="Use the test environment",
        copy=False
    )

    l10n_es_tbai_url_invoice = fields.Char(
        string="URL for submitting invoices",
        readonly=True,
        compute="_compute_l10n_es_tbai_url_invoice"
    )

    l10n_es_tbai_url_cancel = fields.Char(
        string="URL for canceling invoices",
        readonly=True,
        compute="_compute_l10n_es_tbai_url_cancel"
    )

    l10n_es_tbai_url_qr = fields.Char(
        string="URL for generating QR code",
        readonly=True,
        compute="_compute_l10n_es_tbai_url_qr"
    )

    l10n_es_tbai_url_xsd = fields.Char(
        string="URL to retrieve XSD validation schemas",
        readonly=True,
        compute="_compute_l10n_es_tbai_url_xsd"
    )

    # === TBAI CHAIN HEAD ===
    # TODO should we maintain multiple heads, one for each server (tax administration) ?
    # otherwise (or perhaps either way), user should be prevented from changing administration once chain exists
    l10n_es_tbai_last_posted_id = fields.Many2one(
        string="Last posted invoice",
        store=True,
        comodel_name='account.move')

    # === CERTIFICATES ===
    l10n_es_tbai_certificate_id = fields.Many2one(
        string="Certificate (ES-TicketBAI)",
        store=True,
        readonly=False,
        comodel_name='l10n_es_edi_tbai.certificate',
        compute="_compute_l10n_es_tbai_certificate",
    )
    l10n_es_tbai_certificate_ids = fields.One2many(
        comodel_name='l10n_es_edi_tbai.certificate',
        inverse_name='company_id',
    )

    def _compute_l10n_es_tbai_url(self, prefix):
        if self.country_code == 'ES':
            suffix = 'test' if self.l10n_es_tbai_test_env else 'prod'
            if prefix == 'xsd':
                suffix = ''
            return L10N_ES_EDI_TBAI_URLS[prefix + suffix][self.l10n_es_tbai_tax_agency]
        else:
            return False

    @api.depends('country_id', 'l10n_es_tbai_tax_agency', 'l10n_es_tbai_test_env')
    def _compute_l10n_es_tbai_url_invoice(self):
        for company in self:
            company.l10n_es_tbai_url_invoice = self._compute_l10n_es_tbai_url('invoice_')

    @api.depends('country_id', 'l10n_es_tbai_tax_agency', 'l10n_es_tbai_test_env')
    def _compute_l10n_es_tbai_url_cancel(self):
        for company in self:
            company.l10n_es_tbai_url_cancel = self._compute_l10n_es_tbai_url('cancel_')

    @api.depends('country_id', 'l10n_es_tbai_tax_agency', 'l10n_es_tbai_test_env')
    def _compute_l10n_es_tbai_url_qr(self):
        for company in self:
            company.l10n_es_tbai_url_qr = self._compute_l10n_es_tbai_url('qr_')

    @api.depends('country_id', 'l10n_es_tbai_tax_agency')
    def _compute_l10n_es_tbai_url_xsd(self):
        for company in self:
            company.l10n_es_tbai_url_xsd = self._compute_l10n_es_tbai_url('xsd')

    @api.depends('country_id', 'l10n_es_tbai_certificate_ids')
    def _compute_l10n_es_tbai_certificate(self):
        for company in self:
            if company.country_code == 'ES':
                company.l10n_es_tbai_certificate_id = self.env['l10n_es_edi_tbai.certificate'].search(
                    [('company_id', '=', company.id)],
                    order='date_end desc',
                    limit=1,
                )
            else:
                company.l10n_es_tbai_certificate_id = False
