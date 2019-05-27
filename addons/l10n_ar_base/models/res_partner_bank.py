# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
import stdnum.ar.cbu

def validate_cbu(cbu):
    return stdnum.ar.cbu.validate(cbu)


class ResPartnerBank(models.Model):

    _inherit = 'res.partner.bank'

    @api.model
    def _get_supported_account_types(self):
        """ Add new account type named cbu used in Argentina
        """
        res = super(ResPartnerBank, self)._get_supported_account_types()
        res.append(('cbu', _('CBU')))
        return res

    @api.model
    def retrieve_acc_type(self, acc_number):
        try:
            validate_cbu(acc_number)
        except Exception:
            return super(ResPartnerBank, self).retrieve_acc_type(acc_number)
        return 'cbu'
