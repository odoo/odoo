from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        if read_records and self.env.company.country_id.code == 'SA':
            read_records[0]['_l10n_sa_is_on_phase_2'] = bool(config.invoice_journal_id._l10n_sa_ready_to_submit_einvoices())
        return read_records
