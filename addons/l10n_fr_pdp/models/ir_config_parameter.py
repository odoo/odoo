import re

from odoo import api, models

L10N_FR_PDP_KEY = re.compile(r'^(l10n_fr_pdp\.flow10\.start\.date\.)(\d+)$')  # digit(s) = company id


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def write(self, vals):
        params = super().write(vals)
        self._l10n_fr_pdp_trigger_onchange()
        return params

    def create(self, vals_list):
        params = super().create(vals_list)
        params._l10n_fr_pdp_trigger_onchange()
        return params

    @api.ondelete(at_uninstall=False)
    def _l10n_fr_pdp_ondelete(self):
        self._l10n_fr_pdp_trigger_onchange()

    def _l10n_fr_pdp_trigger_onchange(self):
        """ When hardcoding a flow 10 start date, trigger flow 10 fields computaions
        on moves that may not have been in active period yet.
        """
        company_ids = [
            int(match[2])
            for param in self
            if (match := L10N_FR_PDP_KEY.match(param.key))
        ]
        if not company_ids:
            return
        companies = self.env['res.company'].browse(company_ids)
        companies._force_update_l10n_fr_f10_moves()
