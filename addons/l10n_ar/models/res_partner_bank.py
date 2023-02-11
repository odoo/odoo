# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


try:
    from stdnum.ar.cbu import validate as validate_cbu
except ImportError:
    import stdnum
    _logger.warning("stdnum.ar.cbu is avalaible from stdnum >= 1.6. The one installed is %s" % stdnum.__version__)

    def validate_cbu(number):
        def _check_digit(number):
            """Calculate the check digit."""
            weights = (3, 1, 7, 9)
            check = sum(int(n) * weights[i % 4] for i, n in enumerate(reversed(number)))
            return str((10 - check) % 10)
        number = stdnum.util.clean(number, ' -').strip()
        if len(number) != 22:
            raise ValidationError('Invalid Length')
        if not number.isdigit():
            raise ValidationError('Invalid Format')
        if _check_digit(number[:7]) != number[7]:
            raise ValidationError('Invalid Checksum')
        if _check_digit(number[8:-1]) != number[-1]:
            raise ValidationError('Invalid Checksum')
        return number


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
