# -*- coding: utf-8 -*-
from odoo.addons import resource
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResourceResource(models.Model, resource.ResourceResource):

    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
