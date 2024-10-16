# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import resource


class ResourceResource(resource.ResourceResource):

    im_status = fields.Char(related='user_id.im_status')
