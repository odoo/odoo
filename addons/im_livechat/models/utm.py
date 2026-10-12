# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class UtmMixin(models.AbstractModel):
    _inherit = 'utm.mixin'

    @property
    def SELF_REQUIRED_UTM_REF(self):
        return super().SELF_REQUIRED_UTM_REF | {
            'im_livechat.utm_source_chatbot': ('Chatbot', 'utm.source'),
        }
