# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from stdnum.ar.cbu import validate

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    account_type = fields.Selection(selection_add=[('cbu', 'CBU')])

    @api.model
    def retrieve_account_type(self, account_number):
        try:
            validate(account_number)
        except Exception:
            return super().retrieve_account_type(account_number)
        return 'cbu'
