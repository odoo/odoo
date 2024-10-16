# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import hr


class ResourceResource(hr.ResourceResource):

    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
