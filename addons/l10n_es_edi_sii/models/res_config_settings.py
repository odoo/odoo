# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_sii_certificate_ids = fields.One2many(related='company_id.l10n_es_sii_certificate_ids', readonly=False)
    l10n_es_sii_tax_agency = fields.Selection(related='company_id.l10n_es_sii_tax_agency', readonly=False)
    l10n_es_sii_test_env = fields.Boolean(related='company_id.l10n_es_sii_test_env', readonly=False)
