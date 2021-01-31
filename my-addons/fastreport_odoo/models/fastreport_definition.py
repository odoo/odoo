 #-*- coding: utf-8 -*-

import base64
import io
import json
import logging
import os
import shutil
import re
import time
from xml.dom.minidom import getDOMImplementation
from . import hprose_client
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools.safe_eval import safe_eval
import  hprose
from lxml import etree

_logger = logging.getLogger(__name__)

src_chars = """ '"()/*-+?¿!&$[]{}@#`'^:;<>=~%,\\"""
src_chars = str.encode(src_chars, 'iso-8859-1')
dst_chars = """________________________________"""
dst_chars = str.encode(dst_chars, 'iso-8859-1')
empty_report_content = """PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPFJlcG9
ydCBTY3JpcHRMYW5ndWFnZT0iQ1NoYXJwIiBSZXBvcnRJbmZvLkNyZWF0ZWQ9IjAxLzEzLzIwMjEgMTg6MDg6
NTciIFJlcG9ydEluZm8uTW9kaWZpZWQ9IjAxLzEzLzIwMjEgMTg6MDk6NDEiIFJlcG9ydEluZm8uQ3JlYXRvc
lZlcnNpb249IjIwMTkuMy41LjAiPgogIDxEaWN0aW9uYXJ5Lz4KICA8UmVwb3J0UGFnZSBOYW1lPSJQYWdlMS
IgV2F0ZXJtYXJrLkZvbnQ9IuWui+S9kywgNjBwdCI+CiAgICA8UGFnZUhlYWRlckJhbmQgTmFtZT0iUGFnZUh
lYWRlcjEiIFdpZHRoPSI3MTguMiIgSGVpZ2h0PSIyOC4zNSIvPgogICAgPERhdGFCYW5kIE5hbWU9IkRhdGEx
IiBUb3A9IjMxLjY4IiBXaWR0aD0iNzE4LjIiIEhlaWdodD0iMzcuOCIvPgogICAgPFBhZ2VGb290ZXJCYW5kI
E5hbWU9IlBhZ2VGb290ZXIxIiBUb3A9IjcyLjgyIiBXaWR0aD0iNzE4LjIiIEhlaWdodD0iMTguOSIvPgogI
DwvUmVwb3J0UGFnZT4KPC9SZXBvcnQ+"""


class FastReportTemplateContent(models.Model):
    _name = 'fastreport.template.content'
    _description = 'FastReport Report Template Content'

    file = fields.Binary(required=True)
    filename = fields.Char('File Name')
    report_id = fields.Many2one(
        'ir.actions.report', 'Report', ondelete='cascade')
    default = fields.Boolean(default=True)

    report_content=fields.Binary(requiered=True,compute="_compute_report_content",store= True,attachment=False)

    @api.depends("file")
    def _compute_report_content(self):
        for rec in self:
            rec.report_content = rec.file

    @api.model
    def create(self, values):
        result = super(FastReportTemplateContent, self).create(values)

        result.report_id.update()
        return result

    def write(self, values):
        result = super(FastReportTemplateContent, self).write(values)
        for attachment in self:
            attachment.report_id.update()
        return result

class ReportAttachment(models.Model):
    _inherit = 'ir.attachment'

    def getvalue(self):
        return base64.decodestring(self.datas)


# Inherit ir.actions.report.xml and add an action to be able to store
# .jrxml and .properties files attached to the report so they can be
# used as reports in the application.

class FastReportDefinition(models.Model):
    _inherit = 'ir.actions.report'

    def _get_default_report_categ_id(self):
        conext = self.env.context
        if "report_categ_id" in conext:
            return 1
        return 1


    fastreport_output = fields.Selection(
        [('html', 'HTML'), ('csv', 'CSV'),
         ('xls', 'XLS'), ('rtf', 'RTF'),
         ('odt', 'ODT'), ('ods', 'ODS'),
         ('txt', 'Text'), ('pdf', 'PDF')],
        default='pdf')
    rule=fields.Text('报表数据域')
    is_enable=fields.Boolean('是否启用')
    is_download = fields.Boolean('是否下载')
    is_client_open = fields.Boolean("客户端打开")
    field_option_ids=fields.One2many(comodel_name='field.option',inverse_name='field_option_id',string='字段类型',copy=True)
    fastreport_file_ids = fields.One2many(
        'fastreport.template.content', 'report_id', 'Template Content',copy=True)
    # To get the model name from current models in database,we add a new field
    # and it will give us model name at create and update time.
    children_information_ids=fields.One2many('report.parameter','report_id',string='参数',copy=True)
    fastreport_report = fields.Boolean('Is FastReport Report?')
    report_cate_id=fields.Many2one('report.category',string='报表类别',required=True,default=_get_default_report_categ_id)
    report_type = fields.Selection(selection_add=[("fastreport", "FastReport")],ondelete={'fastreport':"cascade"})

    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        d = domain
        e = self._context
        f = self.env.context
        return super()._read_group_raw(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)



    @api.constrains('report_name')
    def _check_something(self):
        for record in self:
            if self.env['ir.actions.report'].search(['&',('report_name','=',record.report_name),('id','!=',record.id)]).id:
                raise ValidationError(u'存在重复的报表名称report_name！')

    # @api.onchange('model_id')
    def empty_field(self):
        res=self.env['field.option'].search([('field_option_id', '=', self.id)])
        self.data_delete(res)
        res = self.env['field.option'].search([('field_option_id', '=', self.id)]).unlink()
        pass
    def data_delete(self,data):
        for data_res in data:
            if data_res['relevance_model']:
                self.data_delete(self.env['field.option'].search([('parent_id', '=',data_res['id'])]))
            self.env['field.option'].search([('parent_id', '=', data_res['id'])]).unlink()
        pass
    def design_field(self):
        if not self.model_id['model']:
            return
        field=[]
        option=[]
      
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
                                        b.ID = """+str(self.model_id.id))
        res = self.env.cr.dictfetchall();
        for re in res:
            fied={}
            fied['field_option_id']=self.id
            fied['name']=re['name']
            fied['report_id'] = self.id
            fied['name_id'] = re['id']
            fied['ttype']=re['ttype']
            if str(re['ttype']) == 'one2many' or str(re['ttype']) == 'many2one' or str(re['ttype']) == 'many2many':
                fied['relevance_model']=self.env['ir.model'].search([('model','=',re['relation'])]).id
            option.append(fied)
        self.env['field.option'].search([('field_option_id','=',self.id)]).unlink()
        self.env['field.option'].create(option)
        pass

    def retrieve_fastreport_attachment(self, record):
        '''Retrieve an attachment for a specific record.

        :param record: The record owning of the attachment.
        :param attachment_name: The optional name of the attachment.
        :return: A recordset of length <=1 or None
        '''
        attachment_obj = self.env['ir.attachment']
        for report in self:
            attachment_name = str(report.name) + '.' + report.fastreport_output
            if report.attachment:
                attachment_name = safe_eval(
                    report.attachment, {'object': record, 'time': time})
            return attachment_obj.search([
                ('store_fname', '=', attachment_name),
                ('res_model', '=', report.model),
                ('res_id', 'in', record.ids)
            ], limit=1)

    def postprocess_fastreport_report(self, record, buffer):
        '''Hook to handle post processing during the jasper report generation.
        The basic behavior consists to create a new attachment containing the
        jasper base64 encoded.

        :param record_id: The record that will own the attachment.
        :param pdf_content: The optional name content of the file to avoid
                            reading both times.
        :return: The newly generated attachment if no AccessError, else None.
        '''
        attachment_obj = self.env['ir.attachment']
        for report in self:
            attachment_name = str(report.name) + '.' + report.fastreport_output
            if report.attachment:
                attachment_name = safe_eval(
                    report.attachment, {'object': record, 'time': time})
            attachment_vals = {
                'name': attachment_name,
                'datas': base64.encodestring(buffer.getvalue()),
                'store_fname': attachment_name,
                'res_model': report.model,
                'res_id': record.id,
            }
            try:
                return attachment_obj.create(attachment_vals)
            except AccessError:
                _logger.warn(
                    "Cannot save %s report %r as attachment",
                    report.fastreport_output, attachment_vals['name'])
            else:
                _logger.info('The %s document %s is now saved in the database',
                             report.fastreport_output, attachment_vals['name'])
            return None

    def get_report_model_field(self,field):
        field_suns = []
        field_sun = self.env['field.option'].search(
            [('parent_id', '=', field)])
        for field_sun_s in field_sun:
            field_suns.append(field_sun_s.name)
        return  field_suns,field_sun

    @api.model
    def generate_report_data(self, pool, datas, model_name, fields, data_dict, prefix):
        # datas = self.env[model_name].search_read(domain,fields)
        if len(datas) > 0:

            language = self._context.get('lang')
            if language == 'en_US':
                language = False
            model_fields = pool[model_name]._fields

            keys_list = model_fields.keys()
            keys_list = sorted(keys_list)#获取所有字段

            for data in datas:
                new_data_dict = {}
                for field in fields:
                    if field.name not in keys_list:
                        continue
                    name = field.name
                    dest_col_name = "-".join([i for i in (prefix, name) if i])#字段名
                    field_type = model_fields[field.name].type#类型

                    if field_type not in ('many2one', 'one2many', 'many2many'):#不属于关联关系
                        if isinstance(data_dict, dict):
                            data_dict[dest_col_name] = data[field.name]
                        if isinstance(data_dict, list):
                            new_data_dict[name] = data[name]

                    if field_type in ('many2one'):
                        comodel_name = model_fields[field.name].comodel_name#获取模型名

                        if isinstance(data_dict, dict):
                            if name not in data_dict.keys():
                                data_dict[name] ={}
                            data_dict[dest_col_name] = data[field.name][0]
                            field_suns ,field_sun =self.get_report_model_field(field.id)
                            d = self.env[comodel_name].search_read([('id', 'in', [data[field.name][0]])],
                                                                   field_suns)
                            self.generate_report_data(pool, d, comodel_name, field_sun, data_dict, field.name)

                        if isinstance(data_dict, list):
                            field_suns ,field_sun =self.get_report_model_field(field.id)
                            if data[field.name]:
                                new_data_dict[dest_col_name] = data[field.name][0]
                                d = self.env[comodel_name].search_read([('id', 'in', [data[field.name][0]])], field_suns)
                                self.generate_report_data(pool, d, comodel_name, field_sun, new_data_dict, field.name)
                            else:
                                new_data_dict[dest_col_name]=[]

                    if field_type in ('one2many', 'many2many'):
                        comodel_name = model_fields[field.name].comodel_name#获取模型名
                        if isinstance(data_dict, dict):
                            if name not in data_dict.keys():
                                data_dict[name] = []
                            field_suns ,field_sun =self.get_report_model_field(field.id)
                            d = self.env[comodel_name].search_read([('id', 'in', data[field.name])],
                                                                   field_suns)
                            self.generate_report_data(pool, d, comodel_name,
                                                      field_sun,
                                                      data_dict[name], "")
                        if isinstance(data_dict, list):
                            field_suns ,field_sun =self.get_report_model_field(field.id)
                            if name not in new_data_dict.keys():
                                new_data_dict[name] = []
                            if data[field.name]:
                                d = self.env[comodel_name].search_read([('id', 'in', data[field.name])], field_suns)
                                self.generate_report_data(pool, d, comodel_name, field_sun, new_data_dict[name], "")
                            else:
                                new_data_dict[name] = []
                if isinstance(data_dict, list):
                    data_dict.append(new_data_dict)

    def get_sys_report_data(self,reportname,docids,report_model):
        self.env.cr.execute('SELECT id, binding_model_id FROM '
                            'ir_act_report_xml WHERE '
                            'report_name = %s LIMIT 1',
                            (reportname,))
        record = self.env.cr.dictfetchone()
        report_data_fields = self.env['field.option'].search([('field_option_id', '=', record['id'])])
        gather = []
        for data_field in report_data_fields:
            gather.append(data_field['name'])

        model_name = report_model
        fields = gather
        data_list = []
        domain = [('id', 'in', docids)]
        model_datas = self.env[model_name].search_read(domain, fields)
        self.generate_report_data(self.pool, model_datas, model_name, report_data_fields, data_list, "")
        return data_list

    def get_report_proxy(self):
        hpclient = hprose.HproseHttpClient(None)
        company = self.env.company
        rpt_srv_url = company.fastreport_server_url or "http://localhost:9005"
        res = hpclient.useService(rpt_srv_url)
        return res

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
            'context': {'field_option_id': self.id,'parent_id':False,'default_field_model_id':self.model_id.id},
            'view_mode': 'form',
            # 'res_id':'stage_inventory_form1',
            'target': 'new',
            'auto_search': True,
        }

    @api.model
    def render_fastreport(self, docids, data):
        cr, uid, context,b = self.env.args
        if not data:
            data = {}
        doc_records = self.model_id.browse(docids)
        report_model_name = 'report.%s' % self.report_name
        self.env.cr.execute('SELECT id, model FROM '
                            'ir_act_report_xml WHERE '
                            'report_name = %s LIMIT 1',
                            (self.report_name,))
        record = self.env.cr.dictfetchone()
        rpt_proxy = self.get_report_proxy()
        report_file = None
        if self.fastreport_file_ids:
           rpts = self.fastreport_file_ids.filtered(lambda f: f.default == True)
           if len(rpts) > 0 :
               report_file = rpts[0].file

        else:
            raise UserError("无效报表文件，请联系系统管理员！")
        report_info = {
            "report_id":self.id,
            "report_name":self.report_name,
            "report_content":str(report_file, encoding="utf-8").replace("77u/","")
        }

        rpt_datasource={
            'report_data':{},
            'report_param':{},
            "report_info":report_info
                  }
        rpt_data = rpt_datasource['report_data']
        rpt_data[self.model.replace(".","") +  "DSet"] = self.get_sys_report_data(self.report_name, docids, self.model)

        report_model2 = self.env[self.model]
        if hasattr(report_model2,"get_report_data"):
            rpt_data.update(report_model2.get_report_data(self.report_name, docids, self.model))

        rpt_param = rpt_datasource['report_param']
        parameters = self.env['report.parameter'].search([('report_id', '=', record['id'])])
        parameter = {}
        for param in parameters:
            locals = {'name': 'SOOO2'}
            c = compile(param.code, 'report_params', 'eval')
            d = eval(c, globals(), locals)
            parameter[param.name] = d
        rpt_param.update(parameter)
        if hasattr(report_model2, "get_report_param"):
            rpt_param.update(report_model2.get_report_param(self.report_name, docids, self.model))

        report_model = self.search([('report_name', '=', report_model_name)])
        if report_model is None:
            raise UserError(_('%s model not found.') % report_model_name)
        data.update({'env': self.env, 'model': record.get('model')})
        if self.attachment_use:
            save_in_attachment = {}
            for doc_record in doc_records:
                attachment_id = self.retrieve_fastreport_attachment(doc_record)
                if attachment_id:
                    save_in_attachment[doc_record.id] = attachment_id
                else:
                   fr_report_path = "C:\\Users\\Randy\\Desktop\\purchse_order.pdf"
                   fr_content=None
                   with open(fr_report_path,'rb') as rpt_doc: 
                        fr_content = rpt_doc.read()
                   jasper_content_stream = io.BytesIO(fr_content)
                   attachment_id = self.postprocess_fastreport_report(
                        doc_record, jasper_content_stream)
                   save_in_attachment[doc_record.id] = attachment_id

                   hpclient = hprose.HproseHttpClient(None)
                   res = hpclient.useService("http://192.168.88.174:9005")
                   val = res.TestService_Hello("myname")
            return self._post_pdf(save_in_attachment), self.fastreport_output

        empty_report2 = rpt_proxy.FastReportService_GetEmptyReportStructure()
        print(empty_report_content.replace("\n","").replace("\r",""))
        l = list()
        l.append({
            "ProductName":"ProductName",
            "ProductDes":"productDescription"})

        rep_data = {
            "Report_Info":{"id":10,"report_content":str(base64.encodebytes("fr content".encode("utf-8")), encoding="utf-8").replace("77u/",""),"format_type":self.fastreport_output},
            "Report_Data":{
                "Products":[
                    {"ProductName":"ProductName","ProductDes":"productDescription"},
                    {"ProductName":"ProductName2","ProductDes":"productDescription2"}
                    ],
                "PrductsTest":[
                    {"ProductName2":"ProductName","ProductDes2":"productDescription"}
                    ]
                },
            "Report_Param":{
                "czy":"Admin"
                }
            }
        rpt_proxy.FastReportService_NewReportFile(json.dumps(l),"C:\\Users\\purchse_order1.pdf")

        pdf_stream = rpt_proxy.FastReportService_ToPdfStream("test",json.dumps(rep_data))
        
        fr_report_path = "C:\\Users\\Randy\\Desktop\\purchse_order.pdf"
        fr_content=None
        with open(fr_report_path,'rb') as rpt_doc: 
            fr_content = rpt_doc.read()
        #jasper = io.BytesIO(pdf_stream)
        return fr_content, self.fastreport_output


    @api.model
    def _get_report_from_name(self, report_name):
        res = super(FastReportDefinition, self)._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env['ir.actions.report']
        domain = [('report_type', '=', 'fastreport'),
                  ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        return report_obj.with_context(context).search(domain, limit=1)

    @api.model
    def get_report_from_name(self,report_name):
        rpt_obj = self._get_report_from_name(report_name)
        rpt_data = dict()
        if rpt_obj:
            rpt_data = dict([
                ("id",rpt_obj.id),
                ("is_download",rpt_obj.is_download),
                ("is_client_open",rpt_obj.is_client_open)
                ])
        return rpt_data

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(FastReportDefinition,self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        context = self.env.context
        if res['type']=="form":
            id = None
            if id:
                doc = etree.XML(res["arch"])
                res["arch"] = etree.tostring(doc)
               # if (your_condition):
        #doc = etree.XML(res['arch'])
        #for field in res['fields']:
           # for node in doc.xpath("//field[@name='%s']" % field):
               # node.set("readonly", "1")
              # modifiers = json.loads(node.get("modifiers"))
               # modifiers['readonly'] = True
               # node.set("modifiers", json.dumps(modifiers))
        #res['arch'] = etree.tostring(doc)
        return res

    @api.model
    def create(self, values):
        if self._context and self._context.get('fastreport_report'):
            if 'model_id' in values:
                values['model'] = self.env['ir.model'].browse(values['model_id']).model
            values['type'] = 'ir.actions.report'
            values['report_type'] = 'fastreport'
            values['fastreport_report'] = True
            if values["is_enable"]:
                values['binding_model_id']= self.env['ir.model'].browse(values['model_id']).id

            if  "fastreport_file_ids" not in values:
                path = os.path.abspath(os.path.dirname(__file__))
                paths = path + '/../reports/' + self.env['report.category'].browse(values['report_cate_id']).complete_name.replace(' ','') + "/" + values['report_name']
                if not os.path.exists(paths):
                    os.makedirs(paths)
                file_content_bytes = base64.b64decode(empty_report_content)
                rpt_file_name = values['report_name'] + '.frx'
                with open(paths + '/' + rpt_file_name, 'wb+') as f:
                    f.write(file_content_bytes)
                values["fastreport_file_ids"] = [(0,0,{
                    "filename":rpt_file_name,
                    "default":True,
                    "file":file_content_bytes
                    })]
            return super(FastReportDefinition, self).create(values)

    def copy(self, default=None):
        new_name = self.report_name + "副本"
        default = dict(default or {})
        new_name_cnt =self.search_count([('report_name','like',new_name)])
        if new_name_cnt==0:
            default['report_name'] = new_name
        else:
            default['report_name'] = new_name + str(new_name_cnt)
        return super(FastReportAction, self).copy(default)

    def write(self, values):
        if self._context and self._context.get('fastreport_report'):
            for report in self:
                for attachment in report.fastreport_file_ids:
                    content = attachment.file
                    file_name = attachment.filename
                    report_categ_id = self.report_cate_id.id
                    if 'report_cate_id' in values:
                        report_categ_id = values['report_cate_id']
                    if not self.is_exist_path(file_name,report_categ_id):
                        path=self.save_file(file_name, content,report_categ_id)

            if 'report_cate_id' in values and 'report_name' in values:
                for report in self:
                    for attachment in report.fastreport_file_ids:
                        content = attachment.file
                        file_name = attachment.filename
                        path=self.save_file(file_name, content,values['report_cate_id'])
                report_path=os.path.abspath(os.path.dirname(__file__)) + '/../reports/'+self.report_cate_id.complete_name.replace(' ', '')
                if os.path.exists(report_path+'/'+self.report_name):
                    shutil.rmtree(report_path+'/'+self.report_name)
                    if not os.listdir(report_path):
                        shutil.rmtree(report_path)

                before_path = path + self.report_name
                now_name = path + values['report_name']
                if os.path.exists(before_path):
                    if not os.path.exists(now_name):
                        os.rename(before_path, now_name)
                        file = self.report_file.replace(before_path, now_name)
                        values["report_file"] = file
            else:
                if 'report_name' in values:
                    path = os.path.abspath(os.path.dirname(__file__)) + '/../reports/'
                    before_path = path + self.report_cate_id.complete_name.replace(' ', '')+'/'+self.report_name
                    now_name = path + self.report_cate_id.complete_name.replace(' ', '')+'/'+values['report_name']

                    if os.path.exists(before_path):
                        if not os.path.exists(now_name):
                            os.rename(before_path, now_name)
                            file = self.report_file.replace(before_path, now_name)
                            values["report_file"] = file

                if 'report_cate_id' in values :
                    for report in self:
                        for attachment in report.fastreport_file_ids:
                            content = attachment.file
                            file_name = attachment.filename
                            self.save_file(file_name, content,values['report_cate_id'])
                            path=os.path.abspath(os.path.dirname(__file__)) + '/../reports/'+self.report_cate_id.complete_name.replace(' ', '')
                        if os.path.exists(path+'/'+self.report_name):
                            shutil.rmtree(path+'/'+self.report_name)
                            if not os.listdir(path):
                                shutil.rmtree(path)
            
            if 'model_id' in values:
                values['binding_model_id']= self.env['ir.model'].browse(values['model_id']).id
            if 'is_enable' in values:
                if values['is_enable']:
                    if 'model_id' in values:
                        values['binding_model_id'] = self.env['ir.model'].browse(values['model_id']).id
                    else:
                        values['binding_model_id']=self.model_id.id
                else:
                    values['binding_model_id'] = None
            else:
                if self.is_enable:
                    pass
                else:
                    values['binding_model_id'] =None

            if 'model_id' in values:
                values['model'] = self.env['ir.model'].browse(values['model_id']).model

            values['type'] = 'ir.actions.report'
            values['report_type'] = 'fastreport'
            values['fastreport_report'] = True
        res = super(FastReportDefinition, self).write(values)
        return res

    def is_exist_path(self,filename,report_cate_id):
        root_path = os.path.abspath(os.path.dirname(__file__))
        route_name=''
        if report_cate_id:
            report=self.env['report.category'].search([('id','=',report_cate_id)])
            route_name=report.complete_name.replace(' ','')
        else:
            route_name=self.report_cate_id.complete_name.replace(' ','')

        dir_path = root_path + '/../reports/'+ route_name +'/' + self.report_name
        file_path = dir_path + '/%s' % filename
        if os.path.exists(file_path):
            return True
        else:
            return False

    def update(self):
        if self._context is None:
            self._context = {}
        for report in self:
            has_default = False

            # Browse attachments and store .jrxml and .properties
            # into jasper_reports/custom_reportsdirectory. Also add
            # or update ir.values data so they're shown on model views.for
            # attachment in self.env['ir.attachment'].browse(attachmentIds)
            for attachment in report.fastreport_file_ids:

                content = attachment.file
                file_name = attachment.filename
                if not file_name or not content:
                    continue
                if not file_name.endswith('.frx') and \
                        not file_name.endswith('.frx'):
                    raise UserError(_('%s is not supported file. Please\
                     Upload .frx files only.') % (file_name))
                path = self.save_file(file_name, content,None)

                if '.frx' in file_name and attachment.default:
                    if has_default:
                        raise UserError(_('There is more than one \
                                         report marked as default'))
                    has_default = True
                    report.write({'report_file': path})
                    report.create_action()
            if not has_default:
                raise UserError(_('No report has been marked as default! \
                                 You need atleast one frx report!'))
            # Ensure the report is registered so it can be used immediately
            # register_jasper_report(report.report_name, report.model)
        return True

    def save_file(self, name, value,report_id):
        path = os.path.abspath(os.path.dirname(__file__))
        route_name=''
        if report_id:
            report=self.env['report.category'].search([('id','=',report_id)])
            route_name=report.complete_name.replace(' ','')
        else:
            route_name=self.report_cate_id.complete_name.replace(' ','')
        paths = path + '/../reports/'+ route_name+'/' + self.report_name
        path += '/../reports/' + route_name + '/' + self.report_name + '/%s' % name

        if not os.path.exists(paths):
            os.makedirs(paths)

        with open(path, 'wb+') as f:
            f.write(base64.decodebytes(value))
        return path

    def normalize(self, text):
        if isinstance(text, str):
            text = text.encode('utf-8')
        return text

    def unaccent(self, text):
        src_chars_list = [
            "'", "(", ")", ",", "/", "*", "-", "+", "?", "¿", "!",
            "&", "$", "[", "]", "{", "}", "@", "#", "`", "^", ":",
            ";", "<", ">", "=", "~", "%", "\\"]
        num_char_dict = {
            '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five',
            '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine', '0': 'Zero'}
        if isinstance(text, str):
            if text[0] in num_char_dict:
                text = text.replace(text[0], num_char_dict.get(text[0]))
            for src in src_chars_list:
                text = text.replace(src, "_")
        return text

    @api.model
    def generate_xml(self, pool, model_name, parent_node, document, depth,
                     first_call):
        if self._context is None:
            self._context = {}

        # First of all add "id" field
        field_node = document.createElement('id')
        parent_node.appendChild(field_node)
        value_node = document.createTextNode('1')
        field_node.appendChild(value_node)
        language = self._context.get('lang')
        if language == 'en_US':
            language = False

        # Then add all fields in alphabetical order
        model_fields = pool[model_name]._fields
        keys_list = model_fields.keys()

        # Remove duplicates because model may have fields with the
        # same name as it's parent
        keys_list = sorted(keys_list)

        for field in keys_list:
            name = False
            if language:
                # Obtain field string for user's language.
                name = self.env['ir.translation']._get_source(
                    '{model},{field}'.format(model=model_name, field=field),
                    'field', language)
            if not name:
                # If there's not description in user's language,
                # use default (english) one.
                name = model_fields[field].string
            if name:
                self.unaccent(name)
            # After unaccent the name might result in an empty string
            if name:
                name = '%s-%s' % (self.unaccent(name), field)
            else:
                name = field
            field_node = document.createElement(name.replace(' ', '_'))

            parent_node.appendChild(field_node)
            field_type = model_fields[field].type

            if field_type in ('many2one', 'one2many', 'many2many'):
                if depth <= 1:
                    continue
                comodel_name = model_fields[field].comodel_name
                self.generate_xml(
                    pool, comodel_name, field_node, document, depth - 1, False)
                continue

            value = field
            if field_type == 'float':
                value = '12345.67'
            elif field_type == 'integer':
                value = '12345'
            elif field_type == 'date':
                value = '2009-12-31 00:00:00'
            elif field_type == 'time':
                value = '12:34:56'
            elif field_type == 'datetime':
                value = '2009-12-31 12:34:56'
            value_node = document.createTextNode(value)
            field_node.appendChild(value_node)

        if depth > 1 and model_name != 'Attachments':
            # Create relation with attachments
            field_node = document.createElement('Attachments-Attachments')
            parent_node.appendChild(field_node)
            self.generate_xml(
                pool, 'ir.attachment', field_node, document, depth - 1, False)

        if first_call:
            # Create relation with user
            field_node = document.createElement('User-User')
            parent_node.appendChild(field_node)
            self.generate_xml(
                pool, 'res.users', field_node, document, depth - 1, False)

            # Create special entries
            field_node = document.createElement('Special-Special')
            parent_node.appendChild(field_node)

            new_node = document.createElement('copy')
            field_node.appendChild(new_node)
            value_node = document.createTextNode('1')
            new_node.appendChild(value_node)

            new_node = document.createElement('sequence')
            field_node.appendChild(new_node)
            value_node = document.createTextNode('1')
            new_node.appendChild(value_node)

            new_node = document.createElement('subsequence')
            field_node.appendChild(new_node)
            value_node = document.createTextNode('1')
            new_node.appendChild(value_node)

    @api.model
    def create_xml(self, model, depth):
        if self._context is None:
            self._context = {}
        document = getDOMImplementation().createDocument(None, 'data', None)
        top_node = document.documentElement
        record_node = document.createElement('record')
        top_node.appendChild(record_node)
        self.generate_xml(self.env, model, record_node, document, depth, True)
        return top_node.toxml()


    @api.model
    def read_report_structure(self):
        report_defs = self.env['ir.actions.report'].search([('report_type','=','fastreport')])
        report_structure = []
        for report_def in report_defs:
            report_temps = self.env['fastreport.template.content'].search([('report_id', '=', report_def.id)])
            struct_obj = {}
            report_temp_list = []
            for report_temp in report_temps:
                temp_data={}
                temp_data['report_temp_id'] = report_temp.id
                temp_data['report_temp_name'] = report_temp.filename
                temp_data['is_default'] = report_temp.default
                report_temp_list.append(temp_data)

            struct_obj['report_id']=report_def.id
            struct_obj['report_path']=report_def.report_cate_id.complete_name.replace(' ', '') + '/' + report_def.report_name
            struct_obj['report_templates']=report_temp_list
            report_structure.append(struct_obj)

        return report_structure

    @api.model
    def transfer_report_data(self,report_id=0,file_id=None,limit=10):
        cr, uid, context, b = self.env.args
        report_model = self.env['ir.actions.report'].search([('id', '=', report_id)])
        doc_records ={}
        search_domain = None
        if report_model.rule:
            search_domain = eval(report_model.rule)

        if search_domain:
            doc_records = self.env[report_model.model].search_read(search_domain,['id'])
        else:
            doc_records = self.env[report_model.model].search_read([],['id'],limit=limit)

        docids = [doc['id'] for doc in doc_records]

        self.env.cr.execute('SELECT id, model FROM '
                            'ir_act_report_xml WHERE '
                            'report_name = %s LIMIT 1',
                            (report_model.report_name,))
        record = self.env.cr.dictfetchone()

        report_file = None
        if report_model.fastreport_file_ids:
            rpts = report_model.fastreport_file_ids.filtered(lambda f: f.id == int(file_id))
            if len(rpts) > 0:
                report_file = rpts[0].file
            else:
                if file_id:
                    report_file = self.env['fastreport.template.content'].search([('id', '=', file_id)])[0].file
        else:
            raise UserError("无效报表文件，请联系系统管理员！")

        file_content=None
        if report_file:
               file_content = str(report_file, encoding="utf-8").replace("77u/", "")

        report_info = {
            "report_id": report_model.id,
            "report_name": report_model.report_name
        }
        rpt_datasource = {
            'report_data': {},
            'report_param': {},
            "report_info": report_info
        }
        rpt_data = rpt_datasource['report_data']
        rpt_data[report_model.model.replace(".", "") + "DSet"] = report_model.get_sys_report_data(report_model.report_name, docids, report_model.model)

        report_model2 = self.env[report_model.model]
        if hasattr(report_model2, "get_report_data"):
            rpt_data.update(report_model2.get_report_data(report_model.report_name, docids, report_model.model))

        rpt_param = rpt_datasource['report_param']
        parameters = self.env['report.parameter'].search([('report_id', '=', record['id'])])
        parameter = {}
        for param in parameters:
            locals = {'name': 'SOOO2'}
            c = compile(param.code, 'report_params', 'eval')
            d = eval(c, globals(), locals)
            parameter[param.name] = d
        rpt_param.update(parameter)
        if hasattr(report_model2, "get_report_param"):
            rpt_param.update(report_model2.get_report_param(report_model.report_name, docids, report_model.model))
        return {
            'datasouce':rpt_datasource, 
            'report_content':file_content,
            'file_id':file_id,
            'report_id':report_id
        }

    @api.model
    def process_report_file(self,report_id,file_id,file_data):
        if file_id:
          
          file=self.env['fastreport.template.content'].search([('id', '=', file_id)])
          file.write({'file':file_data})
          return {
               "report_id":report_id,
               "file_id":file_id
                   }
        else:
           report = request.env["ir.actions.report"].browse([report_id])
           
           if report:
                new_name = report.report_name + ".frx"
                new_name_cnt =self.env['fastreport.template.content'].search_count(["&",("report_id","=",report_id),('filename','like',new_name)])
                if new_name_cnt > 0:
                   new_name = report.report_name + str(new_name_cnt) + ".frx"

                rpt_temp = self.env['fastreport.template.content'].create({
                "report_id":report_id,
                "file":file_data,
                "default":False,
                "filename":new_name})
           return {
               "report_id":report_id,
               "file_id": rpt_temp.mapped("id")
                   }
