# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()
        if self.source in ('mobile', 'kiosk') and self.mobile and self.preset_id.sms_receipt_template_id:
            try:
                self.action_sent_message_on_sms(self.mobile, template=self.preset_id.sms_receipt_template_id)
            except UserError as e:
                _logger.warning("Error while sending sms receipt for self order %s : %s", self.name, e.args[0])
        return res
