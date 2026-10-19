# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.mail.tools.discuss import Store


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _log_merge_operation(self, src_partners, dst_partner):
        super()._log_merge_operation(src_partners, dst_partner)
        dst_partner.message_post(
            body=self.env._(
                "Merged with the following partners: %s",
                [
                    self.env._("%(partner)s <%(email)s> (ID %(id)s)", partner=p.name, email=p.email or "n/a", id=p.id)
                    for p in src_partners
                ],
            )
        )

    def _action_next_screen(self):
        """Clear all partner threads from the client store then proceed as in super.

        Clearing the destination record ensures the messages are fetched again.
        As the thread may otherwise keep previously cached values.

        Other threads were actually deleted so they should be cleared either way.
        """
        action = super()._action_next_screen()
        return Store().delete(self.partner_ids | self.dst_partner_id, as_thread=True).get_client_action(next_action=action)
