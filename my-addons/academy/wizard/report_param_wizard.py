from odoo import models, fields, api

class ReportParamWizard(models.TransientModel):
    _name = 'academy.report.param.wizard'
    _order = 'id asc'

    name = fields.Char(u'名称')
    
    @api.model
    def default_get(self, default_fields):
        result = super(ReportParamWizard, self).default_get(default_fields)
    
        result.update({
                'name': 123,
            })
        return result

    def action_ok(self):
       #{'type': 'ir.actions.act_window_close'}
       print(super(ReportParamWizard, self).read(['name']))
       return {
           'name':'myname',
           'type': 'ir.actions.act_window',
           'view_mode':'list,form',
           'target':'main',
           'res_model':"academy.teachers",
           'context':{ 'custValue':'myvalue'}
               }


