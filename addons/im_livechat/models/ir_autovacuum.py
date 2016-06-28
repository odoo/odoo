# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AutoVacuum(models.AbstractModel):
    _inherit = 'ir.autovacuum'

    @api.model
    def power_on(self, *args, **kwargs):
        self.pool['mail.channel'].remove_empty_livechat_sessions()
        self.pool['mail.channel.partner'].unpin_old_livechat_sessions()
        return super(AutoVacuum, self).power_on(*args, **kwargs)
