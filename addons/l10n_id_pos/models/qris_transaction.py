from odoo import models
from odoo.addons import l10n_id


class L10n_IdQrisTransaction(l10n_id.L10n_IdQrisTransaction):

    def _get_supported_models(self):
        return super()._get_supported_models() + ['pos.order']

    def _get_record(self):
        # Override
        # add it for pos.order
        if self.model == 'pos.order':
            return self.env[self.model].search([('uuid', '=', self.model_id)])
        return super()._get_record()
