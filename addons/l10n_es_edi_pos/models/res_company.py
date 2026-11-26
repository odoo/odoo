# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

# Order in which the fiscal systems take over the POS orders when several are active.
# - TicketBAI before SII: in the Basque territories, TicketBAI already reports the
#   issued invoices (e.g. Orden Foral 330/2022 of Gipuzkoa), SII only the other books.
# - Veri*Factu last: companies under SII or TicketBAI are exempt from Veri*Factu, so it
#   should never coexist with them; it is listed only to keep the result deterministic.
POS_FISCAL_MODE_PRIORITY = ('tbai', 'sii', 'verifactu')

# Modes in which every POS order is an individual fiscal document (as opposed to SII,
# where the orders are summarized in the F4 session closing entry).
POS_FISCAL_MODES_INDIVIDUAL_DOCUMENT = ('tbai', 'verifactu')


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config):
        # EXTENDS 'point_of_sale'
        return super()._load_pos_data_fields(config) + ['l10n_es_simplified_invoice_limit']

    def _l10n_es_pos_get_available_fiscal_modes(self):
        """Hook for the EDI POS modules.

        Each module adds its own mode ('tbai', 'sii', 'verifactu') to the returned set
        when its EDI is active for this company. Modules only declare availability:
        the choice between several available modes is made in
        `_l10n_es_pos_get_fiscal_mode`, so the result does not depend on the
        module loading order.

        :return: set of available mode codes
        """
        self.ensure_one()
        return set()

    def _l10n_es_pos_get_fiscal_mode(self):
        """Return the fiscal system handling the POS orders of this company.

        :return: 'tbai', 'sii', 'verifactu', or False when no EDI is active
        """
        self.ensure_one()
        available_modes = self._l10n_es_pos_get_available_fiscal_modes()
        return next((mode for mode in POS_FISCAL_MODE_PRIORITY if mode in available_modes), False)

    def _l10n_es_get_pos_edi_mode(self):
        self.ensure_one()
        fiscal_mode = self._l10n_es_pos_get_fiscal_mode()
        return fiscal_mode if fiscal_mode in POS_FISCAL_MODES_INDIVIDUAL_DOCUMENT else False
