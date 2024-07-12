# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from stdnum.ar.cbu import validate

from odoo import models, api, _

_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_supported_account_types(self):
        """ Add new account type named cbu used in Argentina """
        res = super()._get_supported_account_types()
        res.append(('cbu', _('CBU')))
        return res

    @api.model
    def retrieve_acc_type(self, acc_number):
        try:
            validate(acc_number)
        except Exception:
            return super().retrieve_acc_type(acc_number)
        return 'cbu'
