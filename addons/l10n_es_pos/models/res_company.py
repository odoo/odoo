from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _load_pos_data_fields(self, config):
        # the payload is built for one till, so the country that decides its
        # shape is that till's company -- not whichever company the reader
        # happens to have selected
        params = super()._load_pos_data_fields(config)
        if config.company_id.country_id.code == "ES":
            params += ["street", "city", "zip", "l10n_es_simplified_invoice_limit"]
        return params
