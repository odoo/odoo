# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.fields import Domain


class PosPreset(models.Model):
    _inherit = 'pos.preset'

    def _get_slots_usage_domain(self):
        # A self order waiting for its online payment only holds its slot while its
        # payment is in progress, so an abandoned payment frees the slot
        return Domain.AND([super()._get_slots_usage_domain(), ~self.env['pos.order']._get_online_payment_not_holding_slot_domain()])
