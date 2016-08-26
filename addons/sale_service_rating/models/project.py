# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Task(models.Model):
    _inherit = 'project.task'

    def rating_get_partner_id(self):
        if self.partner_id or self.sale_line_id.order_id.partner_id:
            return self.partner_id or self.sale_line_id.order_id.partner_id
        return super(Task, self).rating_get_partner_id()
