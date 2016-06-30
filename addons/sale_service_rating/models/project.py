# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Task(models.Model):

    _inherit = 'project.task'

    def _get_partner_to_send_rating_mail(self, task):
        return task.partner_id or task.sale_line_id.order_id.partner_id or task.project_id.partner_id or None
