# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_create_task(self, project):
        """ Set the product's worksheet template on the created task
            when the task is automatically created from a sales order's confirmation
        """
        self.ensure_one()
        template = self.product_id.worksheet_template_id
        if template:
            return super(SaleOrderLine, self.with_context(default_worksheet_template_id=template.id))._timesheet_create_task(project)
        else:
            return super(SaleOrderLine, self)._timesheet_create_task(project)
