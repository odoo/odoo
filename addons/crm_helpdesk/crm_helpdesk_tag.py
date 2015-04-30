# -*- coding: utf-8 -*-

from openerp import fields, models

class CrmHelpdeskTag(models.Model):
    _name = "crm.helpdesk.tag"
    _description = "Category of Helpdesk"
    
    name = fields.Char('Name', required=True, translate=True)
