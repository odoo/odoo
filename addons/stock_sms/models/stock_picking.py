# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

import threading


class Picking(models.Model):
    _inherit = 'stock.picking'

    def _send_confirmation_email(self):
        super(Picking, self)._send_confirmation_email()
        if not self.env.context.get('skip_text') and not getattr(threading.current_thread(), 'testing', False) and not self.env.registry.in_test_mode():
            pickings = self.filtered(lambda p: p.company_id._get_text_validation('sms') and p.picking_type_id.code == 'outgoing' and (p.partner_id.mobile or p.partner_id.phone))
            for picking in pickings:
                # Sudo as the user has not always the right to read this sms template.
                template = picking.company_id.sudo().stock_sms_confirmation_template_id
                picking._message_sms_with_template(
                    template=template,
                    partner_ids=picking.partner_id.ids,
                    put_in_queue=False
                )
