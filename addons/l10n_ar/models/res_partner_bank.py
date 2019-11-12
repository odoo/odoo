# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _
from odoo.exceptions import ValidationError
import stdnum.ar
import logging
_logger = logging.getLogger(__name__)


def validate_cbu(cbu):
    try:
        return stdnum.ar.cbu.validate(cbu)
    except Exception as error:
        msg = _("Argentinian CBU was not validated: %s" % repr(error))
        _logger.log(25, msg)
        raise ValidationError(msg)


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
            validate_cbu(acc_number)
        except Exception:
            return super().retrieve_acc_type(acc_number)
        return 'cbu'
