from odoo import models
from odoo.addons import account, base_vat


class ResPartner(account.ResPartner, base_vat.ResPartner):

    def _l10n_es_is_foreign(self):
        self.ensure_one()

        return self.country_id.code not in ('ES', False) or (self.vat or '').startswith("ESN")
