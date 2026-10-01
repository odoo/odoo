from odoo import api, models


class L10n_Es_Edi_TbaiDocument(models.Model):
    _inherit = 'l10n_es_edi_tbai.document'

    @api.model
    def _is_document_line_refund(self, vals):
        rec = vals.get('record')
        if rec and vals['record']._name == 'pos.order.line':
            return vals['sign'] == 1
        return super()._is_document_line_refund(vals)
