# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_PROGRESS_STATE


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _can_generate_service(self):
        self.ensure_one()
        # Only normal SO, new subscription or renewal can generate services
        return not self.subscription_state or self.subscription_state in SUBSCRIPTION_PROGRESS_STATE

    def _set_deferred_end_date_from_template(self):
        self.ensure_one()
        super()._set_deferred_end_date_from_template()
        if self.end_date:
            self.order_line.task_id.recurrence_id.write({
                'repeat_type': 'until',
                'repeat_until': self.end_date,
            })
        else:
            self.order_line.task_id.recurrence_id.write({
                'repeat_type': 'forever',
            })

    def _set_closed_state(self, renew=False):
        super()._set_closed_state(renew)
        self.filtered('is_subscription').order_line.task_id.action_unlink_recurrence()
