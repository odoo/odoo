# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

import threading


class Picking(models.Model):
    _inherit = 'stock.picking'

    def _sms_get_number_fields(self):
        """ This method returns the fields to use to find the number to use to
        send an SMS on a record. """
        return ['mobile', 'phone']

    def _check_sms_confirmation_popup(self):
        is_delivery = self.company_id.stock_move_sms_validation \
                and self.picking_type_id.code == 'outgoing' \
                and (self.partner_id.mobile or self.partner_id.phone)
        if is_delivery and not getattr(threading.currentThread(), 'testing', False) \
                and not self.env.registry.in_test_mode() \
                and not self.company_id.has_received_warning_stock_sms \
                and self.company_id.stock_move_sms_validation:
            view = self.env.ref('stock_sms.view_confirm_stock_sms')
            wiz = self.env['confirm.stock.sms'].create({'picking_id': self.id})
            return {
                'name': _('SMS'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'confirm.stock.sms',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        return False

    def _send_confirmation_email(self):
        super(Picking, self)._send_confirmation_email()
        if not getattr(threading.currentThread(), 'testing', False) and not self.env.registry.in_test_mode():
            pickings = self.filtered(lambda p: p.company_id.stock_move_sms_validation and p.picking_type_id.code == 'outgoing' and (p.partner_id.mobile or p.partner_id.phone))

            for picking in pickings:
                picking._message_sms_with_template(
                    template=picking.company_id.stock_sms_confirmation_template_id,
                    partner_ids=picking.partner_id.ids,
                    put_in_queue=False
                )
