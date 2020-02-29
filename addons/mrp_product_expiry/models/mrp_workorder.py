# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def record_production(self):
        confirm_expired_lots = self._check_expired_lots()
        if confirm_expired_lots:
            return confirm_expired_lots
        return super(MrpWorkorder, self).record_production()

    def _get_expired_context(self, expired_lot_ids):
        context = super(MrpWorkorder, self)._get_expired_context(expired_lot_ids)
        context['default_workorder_id'] = self.id
        return context
