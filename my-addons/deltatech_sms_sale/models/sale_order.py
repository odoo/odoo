# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


import threading

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _send_order_confirmation_mail(self):
        if not getattr(threading.currentThread(), "testing", False) and not self.env.registry.in_test_mode():
            sales = self.filtered(
                lambda o: o.company_id.sale_order_sms_post and (o.partner_id.mobile or o.partner_id.phone)
            )
            for sale in sales:
                # Sudo as the user has not always the right to read this sms template.
                template = sale.company_id.sudo().sale_order_sms_post_template_id
                sale.with_context(mail_notify_author=True)._message_sms_with_template(
                    template=template, partner_ids=sale.partner_id.ids, put_in_queue=False
                )
        return super(SaleOrder, self)._send_order_confirmation_mail()

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if not getattr(threading.currentThread(), "testing", False) and not self.env.registry.in_test_mode():
            sales = self.filtered(
                lambda p: p.company_id.sale_order_sms_confirm and (p.partner_id.mobile or p.partner_id.phone)
            )
            for sale in sales:
                # Sudo as the user has not always the right to read this sms template.
                template = sale.company_id.sudo().sale_order_sms_confirm_template_id
                sale.with_context(mail_notify_author=True)._message_sms_with_template(
                    template=template, partner_ids=sale.partner_id.ids, put_in_queue=False
                )
        return res
