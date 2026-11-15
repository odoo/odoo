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
            verifactu_invoice_type_field = self.env['pos.order']._fields['l10n_es_invoice_type']
            data[0]['_verifactu_invoice_types'] = [
                {'value': value, 'name': name}
                for value, name in verifactu_invoice_type_field._description_selection(self.env)
            ]

        return data
