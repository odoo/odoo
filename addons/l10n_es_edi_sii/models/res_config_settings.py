# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons import l10n_es


class ResConfigSettings(l10n_es.ResConfigSettings):

    l10n_es_sii_certificate_ids = fields.One2many(related='company_id.l10n_es_sii_certificate_ids', readonly=False)
    l10n_es_sii_tax_agency = fields.Selection(related='company_id.l10n_es_sii_tax_agency', readonly=False)
    l10n_es_sii_test_env = fields.Boolean(related='company_id.l10n_es_sii_test_env', readonly=False)
