from odoo import models, fields,api

class ReportParameter(models.Model):
    _name = 'report.parameter'

    name=fields.Char('参数名称')
    code=fields.Text('代码')
    report_id =fields.Many2one('ir.actions.report','父级关联')

