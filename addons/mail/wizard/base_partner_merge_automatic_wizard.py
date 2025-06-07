# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import format_list


class MergePartnerAutomatic(models.TransientModel):

    _inherit = 'base.partner.merge.automatic.wizard'

    def _log_merge_operation(self, src_partners, dst_partner):
        super(MergePartnerAutomatic, self)._log_merge_operation(src_partners, dst_partner)
        dst_partner.message_post(
            body=self.env._(
                "Merged with the following partners: %s",
                format_list(
                    self.env,
                    [
                        self.env._("%(partner)s <%(email)s> (ID %(id)s)", partner=p.name, email=p.email or "n/a", id=p.id)
                        for p in src_partners
                    ]
                ),
            )
        )
