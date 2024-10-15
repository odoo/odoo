# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import mail


class MailTestProperties(models.Model, mail.MailThread):
    _description = 'Mail Test Properties'

    name = fields.Char('Name')
    parent_id = fields.Many2one('mail.test.properties', string='Parent')
    properties = fields.Properties('Properties', definition='parent_id.definition_properties')
    definition_properties = fields.PropertiesDefinition('Definitions')
