# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    procurement_id = fields.Many2one('procurement.order', 'Procurement', ondelete='set null')
    sale_line_id = fields.Many2one('sale.order.line', 'Sales Order Line', related='procurement_id.sale_line_id', store=True)

    @api.multi
    def unlink(self):
        if any(task.sale_line_id for task in self):
            raise ValidationError(_('You cannot delete a task related to a Sale Order. You can only archive this task.'))
        return super(ProjectTask, self).unlink()

    @api.multi
    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_line_id.order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        self.procurement_id = self.parent_id.procurement_id.id
        self.sale_line_id = self.parent_id.sale_line_id.id
