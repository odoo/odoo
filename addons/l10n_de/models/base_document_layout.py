from odoo import models, fields


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    l10n_de_ceo_id = fields.Many2one(related='company_id.l10n_de_ceo_id', readonly=True)
