from odoo import models, fields, api
import os

class ReportCategory(models.Model):
    _name = 'report.category'

    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'name'
    _order = 'complete_name'

    name=fields.Char('报表类别')
    complete_name = fields.Char(
        '名称', compute='_compute_complete_name',
        store=True)
    parent_id = fields.Many2one('report.category', '父级', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    report_cate_ids = fields.One2many('report.category', 'parent_id', required=True)
    fastre_action_ids=fields.One2many('ir.actions.report','report_cate_id')

    report_cate_id = fields.Many2one("report.category","报表类别目录")

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    def create(self, vals_list):
         c =super(ReportCategory,self).create(vals_list)
         c.report_cate_id = c.id
         return c

    def write(self, values):
        path=os.path.abspath(os.path.dirname(__file__))+'/../reports/'
        child_reports = self.env['ir.actions.report'].search([('report_cate_id', 'child_of', self.id)])
        before_path=path + self.complete_name.replace(' ','')
        now_name=path+self.complete_name.replace(' ','').replace(self.name,'') + values['name']
        if os.path.exists(before_path):
                if not os.path.exists(now_name):
                    os.rename(before_path, now_name)
                    for child_report in child_reports:
                         file = child_report.report_file.replace(before_path, now_name)
                         child_report.write({'report_file': file})
        if not self.report_cate_id:
            values["report_cate_id"] = self.id
        return super(ReportCategory, self).write(values)
