# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):

    _inherit = 'account.move'

    def button_draft(self)
        super().button_draft()
        self.filtered(lamba x: x.payment_id and
                      x.payment_id.payment_method_code == 'own_checks').payment_id._l10n_latam_check_unlink_split_move()

    def button_cancel(self)
        super().button_draft()
        self.filtered(lamba x: x.payment_id and
                      x.payment_id.payment_method_code == 'own_checks').payment_id._l10n_latam_check_unlink_split_move()
