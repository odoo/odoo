# -*- coding: utf-8 -*-
from odoo.addons import resource
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceResource(models.Model, resource.ResourceResource):

    im_status = fields.Char(related='user_id.im_status')
