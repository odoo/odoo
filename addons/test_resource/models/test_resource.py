# -*- coding: utf-8 -*-
from odoo.addons import resource
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceTest(models.Model, resource.ResourceMixin):
    _description = 'Test Resource Model'

    name = fields.Char()
