# -*- coding: utf-8 -*-

import base64
from odoo import fields, models

class CreateDataTemplate(models.TransientModel):
    _name = 'fastreport.create.data.template'
    _description = 'Create Data Template'

    model_id = fields.Many2one('ir.model', required=True)
    depth = fields.Integer(required=True, default=1)
    filename = fields.Char('File Name', size=32)
    data = fields.Binary('XML')

    def action_create_xml(self):
       report_obj = self.env['ir.actions.report']
       for data_template in self:
           xml = report_obj.create_xml(
                data_template.model_id.model, data_template.depth)
           base64_str = base64.encodestring(
                ('%s' % (xml)).encode()).decode().replace('\n', '')
           data_template.write({
                'data': base64_str,
                'filename': str(data_template.model_id.name) + '_template.xml'})
           [action] = self.env.ref(
                'fastreport_odoo.action_fastreport_create_data_template').read()
           action.update({'res_id': data_template.id})
       return action
