# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_edi_tax_agency = fields.Selection(related='company_id.l10n_es_edi_tax_agency', readonly=False)
