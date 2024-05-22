# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_certificate_id = fields.Many2one(
        string="Certificate (ES)",
        store=True,
        readonly=False,
        comodel_name='l10n_es_edi.certificate',
        compute="_compute_l10n_es_edi_certificate",
    )
    l10n_es_edi_certificate_ids = fields.One2many(
        comodel_name='l10n_es_edi.certificate',
        inverse_name='company_id',
    )
    l10n_es_edi_tax_agency = fields.Selection(
        string="Tax Agency for SII",
        selection=[
            ('aeat', "Agencia Tributaria española"),
            ('gipuzkoa', "Hacienda Foral de Gipuzkoa"),
            ('bizkaia', "Hacienda Foral de Bizkaia"),
        ],
        default=False,
    )
    l10n_es_edi_test_env = fields.Boolean(
        string="Test Mode",
        help="Use the test environment",
    )

    @api.depends('country_id', 'l10n_es_edi_certificate_ids')
    def _compute_l10n_es_edi_certificate(self):
        for company in self:
            if company.country_code == 'ES':
                company.l10n_es_edi_certificate_id = self.env['l10n_es_edi.certificate'].search(
                    [('company_id', '=', company.id)],
                    order='date_end desc',
                    limit=1,
                )
            else:
                company.l10n_es_edi_certificate_id = False
