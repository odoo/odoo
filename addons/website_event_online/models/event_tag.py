# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class EventTagPartner(models.Model):
    _inherit = ['event.tag']

    color = fields.Integer(string='Color Index')
