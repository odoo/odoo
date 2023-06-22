from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_company(self):
        res = super()._loader_params_res_company()
        if not self.config_id.is_spanish:
            return res
        res["search_params"]["fields"] += ["street", "city", "zip"]
        return res

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if not self.config_id.is_spanish:
            return
        seq = self.config_id.l10n_es_simplified_invoice_sequence_id
        loaded_data["l10n_es_simplified_invoice"] = {
            "number": seq._get_current_sequence().number_next_actual,
            "prefix": seq._get_prefix_suffix()[0],
            "padding": seq.padding,
        }
