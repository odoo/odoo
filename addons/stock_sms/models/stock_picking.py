# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, modules, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _pre_action_done_hook(self):
        res = super()._pre_action_done_hook()
        if res is True and not self.env.context.get('skip_sms'):
            pickings_to_warn_sms = self._check_warn_sms()
            if pickings_to_warn_sms:
                return pickings_to_warn_sms._action_generate_warn_sms_wizard()
        return res

    def _check_warn_sms(self):
        warn_sms_pickings = self.browse()
        for picking in self:
            is_delivery = picking.company_id._get_text_validation('sms') \
                    and picking.picking_type_id.code == 'outgoing' \
                    and picking.partner_id.phone
            if is_delivery \
                    and not modules.module.current_test \
                    and not picking.company_id.has_received_warning_stock_sms \
                    and picking.company_id._get_text_validation('sms'):
                warn_sms_pickings |= picking
        return warn_sms_pickings

    def _action_generate_warn_sms_wizard(self):
        view = self.env.ref('stock_sms.view_confirm_stock_sms')
        wiz = self.env['confirm.stock.sms'].create({'pick_ids': [(4, p.id) for p in self]})
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

    def _send_confirmation_email(self):
        super()._send_confirmation_email()
        if not self.env.context.get('skip_sms') and not modules.module.current_test:
            pickings = self.filtered(lambda p: p.company_id._get_text_validation('sms') and p.picking_type_id.code == 'outgoing' and p.partner_id.phone)
            for picking in pickings:
                # Sudo as the user has not always the right to read this sms template.
                template = picking.company_id.sudo().stock_sms_confirmation_template_id
                picking._message_sms_with_template(
                    template=template,
                    partner_ids=picking.partner_id.ids,
                    put_in_queue=False
                )
