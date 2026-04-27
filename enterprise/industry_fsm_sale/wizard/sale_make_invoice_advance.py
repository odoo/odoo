# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):
        invoices = super()._create_invoices(sale_orders)
        so_task_mapping = self._context.get('industry_fsm_message_post_task_id')
        if so_task_mapping:
            for invoice in invoices:
                for so in invoice.line_ids.sale_line_ids.order_id:
                    for task_id in so_task_mapping[str(so.id)]:
                        message = _("An invoice has been created: %s", invoice._get_html_link())
                        self.env['project.task'].browse(task_id).message_post(body=message)
        return invoices
