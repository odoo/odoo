from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        if (self.env.ref('l10n_pe_pos.partner_pe_cf').id,) not in partner_ids:
            partner_ids.append((self.env.ref('l10n_pe_pos.partner_pe_cf').id,))
        return partner_ids

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if read_records and self.env.company.country_id.code == "PE":
            read_records[0]['_consumidor_final_anonimo_id'] = self.env.ref('l10n_pe_pos.partner_pe_cf').id
        return read_records
