from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        related='company_id.l10n_es_edi_verifactu_required',
    )

    @api.model
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)

        if data and config.l10n_es_edi_verifactu_required:
            verifactu_invoice_type_field = self.env['ir.model.fields']._get('pos.order', 'l10n_es_invoice_type')
            data[0]['_verifactu_invoice_types'] = [
                {'value': invoice_type.value, 'name': invoice_type.name}
                for invoice_type in verifactu_invoice_type_field.selection_ids
            ]

        return data
