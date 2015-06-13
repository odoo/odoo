# -*- coding: utf-8 -*-
from openerp import fields, models

class hr_applicant(models.Model):

    _inherit = 'hr.applicant'

    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=lambda self: [('res_model', '=', self._name)], auto_join=True, string='Attachments')
