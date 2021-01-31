# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api, exceptions
from .main_models import Glob_tag_Model
# jexcel表格模型的字段


class Jexcel_fields(models.AbstractModel):
    '''全局标签模型,用于多重继承方式添加到模型'''
    _name = "accountcore.jexcel_fields"
    _description = 'jexcel模型字段'
    data = fields.Text(string='数据内容', default='[[]]')
    onlydata = fields.Text(string="纯数据内容", default='[[]]')
    data_style = fields.Text(string='模板样式')
    width_info = fields.Text(string='列宽的定义')
    height_info = fields.Text(string='行高的定义')
    header_info = fields.Text(string='表头定义')
    comments_info = fields.Text(string='批注定义')
    merge_info = fields.Text(string='合并单元格定义', default='{}')
    meta_info = fields.Text(string='隐藏的信息定义')
# 报表接收者


class Receiver(models.Model, Glob_tag_Model):
    '''报表接收者'''
    _name = "accountcore.receiver"
    _description = '报表的报送对象'
    number = fields.Char(string='接收者编号')
    name = fields.Char(string='接收者', required=True)
    _sql_constraints = [('accountcore_receiver_name_unique', 'unique(name)',
                         '接收者名称重复了!')]
# 报表类型


class ReportType(models.Model, Glob_tag_Model):
    '''报表类型'''
    _name = 'accountcore.report_type'
    _description = '报表类型'
    number = fields.Char(string='报表类型编号')
    name = fields.Char(string='报表类型名称', required=True)
    _sql_constraints = [('accountcore_reportytpe_name_unique', 'unique(name)',
                         '报表类型名称重复了!')]
# 归档报表


class StorageReport(models.Model, Glob_tag_Model, Jexcel_fields):
    '''归档的报表'''
    _name = 'accountcore.storage_report'
    _description = '归档的报表'
    report_type = fields.Many2one('accountcore.report_type', string='报表类型')
    number = fields.Char(string='归档报表编号')
    name = fields.Char(string='归档报表名称', required=True)
    create_user = fields.Many2one('res.users',
                                  string='归档人',
                                  default=lambda s: s.env.uid,
                                  readonly=True,
                                  required=True,
                                  ondelete='restrict',
                                  index=True)
    startDate = fields.Date(string='取数开始月份')
    endDate = fields.Date(string='取数结束月份')
    orgs = fields.Many2many('accountcore.org', string='机构/主体范围', required=True)
    fast_period = fields.Date(string="选取期间", store=False)
    receivers = fields.Many2many('accountcore.receiver', string='接收者')
    summary = fields.Text(string='归档报表说明')
    htmlstr = fields.Html(string='html内容')
# 报表模板


class ReportModel(models.Model, Glob_tag_Model, Jexcel_fields):
    '''报表模板'''
    _name = 'accountcore.report_model'
    _description = '报表模板，用于生成报表'
    report_type = fields.Many2one(
        'accountcore.report_type', string='报表类型', copy=True)
    guid = fields.Char(string='模板唯一码', required=True,
                       default=lambda s: uuid.uuid4(), copy=False)
    name = fields.Char(string='报表模板名称', required=True, copy=False)
    version = fields.Char(string='报表模板版本', required=True)
    summary = fields.Text(string='报表模板简介')
    explain = fields.Html(string='报表模板详细介绍')
    startDate = fields.Date(string='开始月份')
    endDate = fields.Date(string='结束月份')
    fast_period = fields.Date(string="选取期间", store=False)
    orgs = fields.Many2many('accountcore.org',
                            string='机构/主体范围',
                            default=lambda s: s.env.user.currentOrg,
                            required=True, copy=True)
    _sql_constraints = [('accountcore_repormodel_name_unique', 'unique(name)',
                         '报表模版名称重复了!')]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=0):
        args = args or []
        # 源代码默认为160,突破其限制   详细见 /web/static/src/js/views/form_common.js
        if limit == 160:
            limit = 0
        pos = self.search(args, limit=limit, order='name')
        # return pos.name_get()
        return pos._my_name_get()

    @api.model
    # @api.multi
    def _my_name_get(self):
        result = []
        name = self._rec_name
        if name in self._fields:
            convert = self._fields[name].convert_to_display_name
            for record in self:
                result.append((record.id, convert(
                    record[name], record)+"["+record.version+"]"))
        else:
            for record in self:
                result.append((record.id, "%s,%s" % (
                    record._name, record.guid)))
        return result

    def copy(self, default=None):
        '''复制模板'''
        newName = self.name+"副本"
        records = self.search([('name', '=', newName)])
        while records.exists():
            newName = newName+"副本"
            records = records.search([('name', '=', newName)])
        updateFields = {'name': newName}
        rl = super(ReportModel, self).copy(updateFields)
        return rl
# 科目取数金额类型


class AccountAmountType(models.Model, Glob_tag_Model):
    '''报表科目取数的金额类型'''
    _name = 'accountcore.account_amount_type'
    _description = '报表公式向导科目取数的金额类型'
    number = fields.Char(string='金额类型编码')
    name = fields.Char(string='金额类型', required=True)
    _sql_constraints = [('accountcore_accountamounttype_name_unique', 'unique(name)',
                         '科目取数的金额类型重复了!')]
