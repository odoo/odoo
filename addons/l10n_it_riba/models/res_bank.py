import logging

from odoo import api, models, fields
from odoo.addons.base_iban.models.res_partner_bank import get_bban_from_iban

_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def _l10n_it_get_bban_components(self):
        self.ensure_one()
        if self.acc_type != 'iban':
            return False
        bban = get_bban_from_iban(self.acc_number)
        return (bban[0], bban[1:6], bban[6:11], bban[11:])

    @api.depends()
    def _compute_l10n_it_get_bban_components(self):
        for bank in self:
            bban_components = bank._l10n_it_get_bban_components() or [False ** 4]
            bank.l10n_it_cin, bank.l10n_it_abi, bank.l10n_it_cab, bank.l10n_it_ccn = bban_components

    l10n_it_cin = fields.Char(compute='_compute_l10n_it_get_bban_components')
    l10n_it_abi = fields.Char(compute='_compute_l10n_it_get_bban_components')
    l10n_it_cab = fields.Char(compute='_compute_l10n_it_get_bban_components')
    l10n_it_ccn = fields.Char(compute='_compute_l10n_it_get_bban_components')
