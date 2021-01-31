from odoo import models, fields,api


class FieldOption(models.Model):
    _name = 'field.option'
    name=fields.Char('字段名')
    alias=fields.Char('别名',lenght=128)
    name_id=fields.Many2one('ir.model.fields','系统字段',domain="[('model_id','=',parent_model_id)]")
    ttype=fields.Char(string='类型')
    child_count = fields.Integer('关联字段个数',compute='_compute_child_count')
    relevance_model=fields.Many2one('ir.model','模型')
    parent_id=fields.Many2one('field.option')
    children_ids = fields.One2many('field.option','parent_id','模型字段列表',copy=True)
    field_option_id=fields.Many2one(comodel_name='ir.actions.report',string='字段类型')
    parent_model_id = fields.Integer("parent_model_id",related="field_option_id.model_id.id")
    report_id=fields.Integer()

    @api.depends('children_ids')
    def _compute_child_count(self):
        for res in self:
            res.child_count = len(res.children_ids)

    def jump_multiple_tree(self):
        return{
            'type': 'ir.actions.act_window',
            'res_model': 'multiple.field',
            # 'limit':1,
            'name': '报表字段选择',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            'context': {'field_option_id': False,'parent_id':self.id,'default_field_model_id':self.relevance_model.id},
            'view_mode': 'form',
            # 'res_id':'stage_inventory_form1',
            'target': 'new',
            'auto_search': True,
        }


    def form_button(self):
        view_id = self.env.ref('fastreport_odoo.act_report_fastreport_form1').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'field.option',
            # 'limit':1,
            'name': '报表字段',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            'context':{'default_parent_model_id':self.relevance_model.id},
            'view_mode': 'form',
            # 'res_id':'stage_inventory_form1',
            'views': [(view_id, "form")],
            'target': 'new',
            'res_id': self.id,
            'auto_search': True,
        }




    @api.onchange('name_id')
    def _compute_id(self):
        if not self.name_id:
            return
        for res in self:
            data=self.env['ir.model.fields'].search([('id','=',res.name_id.id)])
            res.ttype=data['ttype']
            res.name=data['name']
            if data['ttype'] == 'one2many' or data['ttype'] == 'many2one' or data['ttype'] == 'many2many':
                res.relevance_model = self.env['ir.model'].search([('model', '=', data['relation'])]).id

    def empty_fields(self):
        self.env['field.option'].search([('parent_id','=',self.id)]).unlink()

    def design_fields(self):
        if not self.relevance_model['model']:
            return
        option = []
        self.env.cr.execute("""SELECT   A.id,
                                        A.NAME,
                                        A.model,
                                        A.ttype,
                                        A.relation,
                                        A.relation_field
                                    FROM
                                        ir_model_fields
                                        A LEFT JOIN ir_model b ON A.model_id = b.ID
                                    WHERE
                                        b.ID = """ + str(self.relevance_model.id))
        res = self.env.cr.dictfetchall()
        for re in res:
            fied = {}
            fied['name'] = re['name']
            fied['report_id'] = self.field_option_id.id
            fied['name_id'] = re['id']
            fied['parent_id'] = self.id
            fied['ttype'] = re['ttype']
            if str(re['ttype']) == 'one2many' or str(re['ttype']) == 'many2one' or str(re['ttype']) == 'many2many':
                fied['relevance_model'] = self.env['ir.model'].search([('model', '=', re['relation'])]).id
            self.env['field.option'].search(
                ['&', ('field_option_id', '=', self.field_option_id.id), ('name_id', '=', re['id'])]).unlink()
            option.append(fied)
        self.env['field.option'].create(option)

    def delete(self):
        self.env['field.option'].search(
            ['|',('id', '=', self.id),('parent_id','=',self.id)]).unlink()

class irmodel(models.Model):
    _inherit = 'ir.model.fields'
    _rec_name = 'name'

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "%s" % record.name))
        return result
