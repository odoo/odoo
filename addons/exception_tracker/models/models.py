# -*- coding: utf-8 -*-

from odoo import models, fields, api
class Exception(models.Model):
    _name = 'exception_tracker.exception'
    _description = 'exception_tracker.exception'
    
    name = fields.Char(readonly=True)
    message = fields.Text(readonly=True)
    traceback = fields.Text(readonly=True)
    user_context = fields.Text(readonly=True)
    action_context = fields.Text(readonly=True)

    # @api.model_create_multi
    # def create(self, vals_list):       
    #     return super(Exception, self).create(vals_list)

