from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    l10n_sg_unique_entity_number = fields.Char(related='company_id.l10n_sg_unique_entity_number')
