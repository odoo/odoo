# -*- coding: utf-8 -*-
import calendar
import datetime
from decimal import Decimal
import json
import logging
import psycopg2
import threading
from .ac_obj import ACTools
from .ac_obj import CURRENCY_ID
from odoo import models, fields, api, SUPERUSER_ID, exceptions
from odoo import tools
from odoo import sql_db
# import sys
# sys.path.append('.\\.\\server\\odoo')
# sys.path.append('.\\.\\')

# 日志
LOGGER = logging.getLogger(__name__)
# 新增,修改,删除凭证时对科目余额的改变加锁
VOCHER_LOCK = threading.RLock()
# 本位币人民币在odoo中的id
CNY = CURRENCY_ID

# 全局标签模型,用于多重继承方式添加到模型


class Glob_tag_Model(models.AbstractModel):
    '''全局标签模型,用于多重继承方式添加到模型'''
    _name = "accountcore.glob_tag_model"
    _description = '全局标签模型'
    glob_tag = fields.Many2many('accountcore.glob_tag',
                                string='全局标签',
                                index=True)


# 全局标签类别
class GlobTagClass(models.Model):
    '''全局标签类别'''
    _name = 'accountcore.glob_tag_class'
    _description = '全局标签类别'
    number = fields.Char(string='全局标签类别编码')
    name = fields.Char(string='全局标签类别名称', required=True)
    summary = fields.Char(string='使用范围和简介')
    _sql_constraints = [('accountcore_itemclass_number_unique', 'unique(number)',
                         '全局标签类别编码重复了!'),
                        ('accountcore_itemclass_name_unique', 'unique(name)',
                         '全局标签类别名称重复了!')]


# 模块全局标签
class GlobTag(models.Model):
    '''模块全局标签'''
    _name = 'accountcore.glob_tag'
    _description = '模块全局标签'
    name = fields.Char(string='全局标签名称', required=True)
    glob_tag_class = fields.Many2one('accountcore.glob_tag_class',
                                     string='全局标签类别',
                                     index=True,
                                     ondelete='restrict')
    summary = fields.Char(string='使用范围和简介')
    js_code = fields.Text(string='js代码')
    python_code = fields.Text(string='python代码')
    sql_code = fields.Text(string='sql代码')
    str_code = fields.Text(string='字符串')
    application = fields.Html(string='详细使用说明')
    _sql_constraints = [('accountcore_glob_tag_name_unique', 'unique(name)',
                         '模块全局标签重复了!')]


# model-开始
# 会计机构/主体
class Org(models.Model, Glob_tag_Model):
    '''会计机构/主体'''
    _name = 'accountcore.org'
    _description = '会计机构/主体'
    number = fields.Char(string='机构/主体编码')
    org_class = fields.Char(string="机构组名")
    name = fields.Char(string='机构/主体名称', required=True)
    is_current = fields.Boolean(string="当前机构/主体", compute="_is_current")
    accounts = fields.One2many('accountcore.account', 'org', string='科目')
    user_ids = fields.Many2many('res.users', string='有权用户')
    start_date = fields.Date(
        string="启用日期", compute="_get_start_date", help="该机构/主体的科目最早启用日期")
    lock_date = fields.Date(string="锁定日期", help="只能修改该日期后的凭证")
    last_voucher_date = fields.Date(
        string="最后凭证日", compute="_get_last_voucher_date")
    _sql_constraints = [('accountcore_org_number_unique', 'unique(number)',
                         '机构/主体编码重复了!'),
                        ('accountcore_org_name_unique', 'unique(name)',
                         '机构/主体名称重复了!')]

    def _is_current(self):
        '''是否当前机构'''
        current_id = self.env.user.currentOrg.id
        for e in self:
            if current_id == e.id:
                e.is_current = True
            else:
                e.is_current = False

    def toggle(self):
        return {
            'name': "设置机构/主体默认值",
            'type': 'ir.actions.act_window',
            'res_model': 'accountcoure.userdefaults',
            'view_mode': 'form',
            'target': 'new',
        }
        
    @api.model
    def create(self, values):
        '''新增'''
        rl = super(Org, self).create(values)
        m_glob_tags = self.env["accountcore.glob_tag"]
        # 添加对应的全局关联方标签(和机构/主体名称同名)
        if "name" in values:
            exist_tag = m_glob_tags.search(
                [("name", "=", values["name"])], limit=1)
            if not exist_tag:
                m_glob_tags.create(
                    [{"glob_tag_class": self.env.ref('accountcore.glob_tag_class_6').id, "name": rl.name}])
        return rl

    def write(self, values):
        ''''''
        # 同时修改对应的全局关联方标签(和机构/主体名称同名)
        m_glob_tags = self.env["accountcore.glob_tag"]
        for mySelf in self:
            old_name = mySelf.name
            if "name" in values:
                exist_tag = m_glob_tags.search(
                    [("name", "=", old_name)], limit=1)
                if not exist_tag:
                    m_glob_tags.create(
                        [{"glob_tag_class": self.env.ref('accountcore.glob_tag_class_6').id, "name": values["name"]}])
                else:
                    exist_tag.write({"name": values["name"]})
        rl = super(Org, self).write(values)
        return rl

    def unlink(self):
        '''删除'''
        for mySelf in self:
            if mySelf.id == 1:
                raise exceptions.ValidationError("不能删除默认机构/主体，可以修改")
        rl_bool = super(Org, self).unlink()
        return rl_bool

    def _get_start_date(self):
        '''获得机构/主体的启用期'''
        for org in self:
            banlances = self.env['accountcore.accounts_balance'].search(
                [('org', '=', org.id)], order='createDate', limit=2)
            if banlances.exists():
                org.start_date = banlances[0].createDate
            else:
                org.start_date = None

    def _get_last_voucher_date(self):
        '''机构/主体最后的凭证日'''
        for org in self:
            last_voucher = self.env['accountcore.voucher'].search(
                [('org', '=', org.id)], order='voucherdate desc', limit=1)
            if last_voucher:
                org.last_voucher_date = last_voucher.voucherdate
            else:
                org.last_voucher_date = None


# 会计科目体系


class AccountsArch(models.Model, Glob_tag_Model):
    '''会计科目体系'''
    _name = 'accountcore.accounts_arch'
    _description = '会计科目体系'
    number = fields.Char(string='科目体系编码', required=True)
    name = fields.Char(string='科目体系名称', required=True,
                       help='对科目的一个分类,例如通用科目,某行业科目等')
    accounts = fields.One2many(
        'accountcore.account', 'accountsArch', string='科目')
    _sql_constraints = [('accountcore_accoutsarch_number_unique', 'unique(number)',
                         '科目体系编码重复了!'),
                        ('accountcore_accountsarch_name_unique', 'unique(name)',
                         '科目体系名称重复了!')]


# 核算项目类别
class ItemClass(models.Model, Glob_tag_Model):
    '''核算项目类别'''
    _name = 'accountcore.itemclass'
    _description = '核算项目类别'
    number = fields.Char(string='核算项目类别编码')
    name = fields.Char(string='核算项目类别名称',
                       help='对核算项目的一个分类,不能重复,例如:员工,部门等')
    _sql_constraints = [('accountcore_itemclass_number_unique', 'unique(number)',
                         '核算项目类别编码重复了!'),
                        ('accountcore_itemclass_name_unique', 'unique(name)',
                         '核算项目类别名称重复了!')]

# 核算项目


class Item(models.Model, Glob_tag_Model):
    '''核算项目'''
    _name = 'accountcore.item'
    _description = '核算项目'
    org = fields.Many2many('accountcore.org',
                           string='所属机构/主体',
                           help="核算项目所属机构/主体,该机构/主体可以使用的核算项目,不选默认全部机构/主体可用",
                           index=True,
                           ondelete='restrict')
    uniqueNumber = fields.Char(string='唯一编号')
    number = fields.Char(string='核算项目编码')
    name = fields.Char(string='核算项目名称',
                       required=True,
                       help="核算项目名称")
    itemClass = fields.Many2one('accountcore.itemclass',
                                string='核算项目类别',
                                index=True,
                                required=True,
                                ondelete='restrict')
    item_class_name = fields.Char(related='itemClass.name',
                                  string='项目类别',
                                  index=True,
                                  store=True,
                                  ondelete='restrict')
    _sql_constraints = [('accountcore_item_number_unique', 'unique(number)',
                         '核算项目编码重复了!'),
                        ('accountcore_item_name_unique', 'unique(name)',
                         '核算项目名称重复了!')]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=20):
        # 更据context中account的值来对item的搜索进行过滤,仅查找account下挂的item类别中的item
        domain = []
        if name:
            domain = ['|', ('number', operator, name),
                      ('name', operator, name)]
        if 'account' in self.env.context:
            accountId = self.env.context['account']
            account = self.env['accountcore.account'].sudo().browse(accountId)
            filter_itemClass = [
                itemclass.id for itemclass in account.itemClasses]
            args.append(('itemClass', 'in', filter_itemClass))
        context = self.env.context
        org_id = context.get('org_id')
        # 上下文取消覆写函数对org范围的控制
        control_org = context.get('control_org')
        control_org = control_org if control_org else True
        if org_id:
            # 修改凭证时从上下文取
            org = org_id
        else:
            # 新增时从用户默认值取，凭证机构的change会触发默认值从新设置
            org = self.env.user.currentOrg.id
        if control_org:
            domain = ['|', ('org', '=', False),
                      ('org', 'in', [org])]+args + domain
        elif args:
            domain = ['|', ('org', '=', False)]+args + domain
        pos = self.search(domain, limit=limit, order='number')
        return pos._my_name_get()

    @api.model
    # @api.multi
    def _my_name_get(self):
        result = []
        name = self._rec_name
        context = self.env.context
        show_balance = context.get('show_balance')
        if show_balance:
            org_id = context.get('org_id')
            accountOfItem_id = context.get("account")
            if org_id:
                # 修改凭证时从上下文取
                org = self.env['accountcore.org'].sudo().browse(org_id)
            else:
                # 新增时从用户默认值取，凭证机构的change会触发默认值从新设置
                org = self.env.user.currentOrg
            account = None
            if accountOfItem_id:
                account = self.env['accountcore.account'].sudo().browse(
                    accountOfItem_id)
        if name in self._fields:
            convert = self._fields[name].convert_to_display_name
            if show_balance and account:
                for record in self:
                    endAmount = account.getEndAmount(org, record)
                    showStr = convert(record[name], record)
                    if endAmount != 0:
                        showStr = showStr+"__"+'{:,.2f}'.format(endAmount)
                    result.append(
                        (record.id, showStr))
            else:
                for record in self:
                    result.append(
                        (record.id, convert(record[name], record)))
        else:
            for record in self:
                result.append((record.id, "%s,%s" % (record._name, record.id)))
        return result

    @api.model
    def getEntryItems(self, ids):
        '''获得核算项目列表(前端凭证分录获得核算项目列表)'''
        items = self.browse(ids)
        itemslist = []
        for i in items:
            itemslist.append({'id': i.id,
                              'name': i.name,
                              'itemClass': i.itemClass.id})
        return itemslist

    @api.model
    def create(self, values):
        '''新增项目'''
        values['uniqueNumber'] = self.env['ir.sequence'].next_by_code(
            'item.uniqueNumber')
        rl = super(Item, self).create(values)
        self.env.user.current_itemclass = rl.itemClass.id
        return rl

    @api.model
    def default_get(self, field_names):
        default = super().default_get(field_names)
        # 如果上下文有此标记为TRUE,就用res.user中设置的项目类别
        if not self.env.context.get('itemclass_no_from_userInfo'):
            default['itemClass'] = self.env.user.current_itemclass.id
        return default


# 凭证标签
class RuleBook(models.Model, Glob_tag_Model):
    '''特殊的会计科目'''
    '''凭证标签'''
    _name = 'accountcore.rulebook'
    _description = '凭证标签'
    number = fields.Char(string='凭证标签编码', required=True)
    name = fields.Char(string='凭证标签名称', required=True, help='用于给凭证做标记')
    _sql_constraints = [('accountcore_rulebook_number_unique', 'unique(number)',
                         '标签编码重复了!'),
                        ('accountcore_rulebook_name_unique', 'unique(name)',
                         '标签名称重复了!')]
    # 获得所有标记的凭证

    def getVouchers(self):
        '''获得所有标记的凭证'''
        vouchers = self.env['accountcore.voucher'].sudo().search(
            [('ruleBook', '=', self.id)])
        return vouchers

    # 获得机构下所有标记的凭证
    def getVouchersOfOrg(self, org, periods=None):
        '''获得机构下所有标记的凭证'''
        vouchers = self.getVouchers().filtered(lambda v: v.org.id == org.id)
        if (periods):
            records = vouchers.filtered(
                lambda v: periods.includeDateTime(v.voucherdate))
            return records
        else:
            return vouchers


# 科目类别
class AccountClass(models.Model, Glob_tag_Model):
    '''会计科目类别'''
    _name = 'accountcore.accountclass'
    _description = '会计科目类别'
    number = fields.Char(string='科目类别编码', required=True)
    name = fields.Char(string='科目类别名称', required=True,
                       help='对科目的一个分类,例如：资产类,负载类')
    _sql_constraints = [('accountcore_accountclass_number_unique', 'unique(number)',
                         '科目类别编码重复了!'),
                        ('accountcore_accountclass_name_unique', 'unique(name)',
                         '科目类别名称重复了!')]


# 会计科目
class Account(models.Model, Glob_tag_Model):
    '''会计科目'''
    _name = 'accountcore.account'
    _description = '会计科目'
    org = fields.Many2many('accountcore.org',
                           string='所属机构/主体',
                           help="该机构/主体可以使用的科目,不选默认全部机构/主体可用",
                           ondelete='restrict',
                           index=True)

    accountsArch = fields.Many2one('accountcore.accounts_arch',
                                   string='所属科目体系',
                                   help="科目所属体系",
                                   index=True,
                                   ondelete='restrict')

    accountClass = fields.Many2one('accountcore.accountclass',
                                   string='科目类别',
                                   index=True,
                                   ondelete='restrict',
                                   required=True)
    number = fields.Char(string='科目编码', required=True)
    name = fields.Char(string='科目名称', required=True)
    direction = fields.Selection([('1', '借'),
                                  ('-1', '贷')],
                                 string='余额方向',
                                 required=True)
    is_show = fields.Boolean(string='凭证中可选', default=True)
    is_last = fields.Boolean(string='末级科目', compute="_is_last", store=True)
    cashFlowControl = fields.Boolean(string='分配现金流量')
    itemClasses = fields.Many2many('accountcore.itemclass',
                                   string='科目要统计的核算项目类别',
                                   help="录入凭证分录时供的核算项目类别",
                                   ondelete='restrict')
    accountItemClass = fields.Many2one('accountcore.itemclass',
                                       string='作为明细科目的类别(凭证中必填项目)',
                                       help="录入凭证分录时必须输输入的核算项目类别,作用相当于明细科目",
                                       ondelete='restrict')
    fatherAccountId = fields.Many2one('accountcore.account',
                                      string='上级科目',
                                      help="科目的上级科目",
                                      index=True,
                                      ondelete='restrict')
    childs_ids = fields.One2many('accountcore.account',
                                 'fatherAccountId',
                                 string='直接下级科目',
                                 ondelete='restrict')
    currentChildNumber = fields.Integer(default=10,
                                        string='新建下级科目待用编号')
    explain = fields.Html(string='科目说明')
    itemClassesHtml = fields.Char(string="核算类别",
                                  help="录入凭证分录时可以选择的核算项目.其中带*的相当于明细科目,为必选.其他不带*的为统计项目,可选",
                                  compute='_itemClassesHtml',
                                  store=True)
    _sql_constraints = [('accountcore_account_number_unique', 'unique(number)',
                         '科目编码重复了!'),
                        ('accountcore_account_name_unique', 'unique(name)',
                         '科目名称重复了!')]

    @ACTools.refuse_role_search
    @api.model
    def create(self, values):
        '''新增科目'''
        self._check_name(values['name'])
        rl = super(Account, self).create(values)
        return rl

    # @api.multi
    def write(self, values):
        '''修改科目'''
        if 'name' in values:
            self._check_name(values['name'])
        rl = super(Account, self).write(values)
        return rl

    def _check_name(self, name):
        '''检查科目名称'''
        if ' ' in name:
            raise exceptions.ValidationError("科目名称中不能含有空格")

    @api.onchange('accountItemClass')
    def _checkAccountItem(self):
        '''改变作为明细科目的核算项目类别'''
        account_id = self.env.context.get('account_id')
        old_accountItemClass = self.env['accountcore.account'].sudo().browse(
            [account_id]).accountItemClass
        old_accountItemClass_id = old_accountItemClass.id
        accountBalances = self.env['accountcore.accounts_balance'].sudo().search(
            [('account', '=', account_id),
             ('items', '=', old_accountItemClass_id)])
        if accountBalances.exists():
            if old_accountItemClass:
                raise exceptions.ValidationError('该科目下的核算项目['+old_accountItemClass.name+'] \
                已经使用,不能改变.你可以添加新的明细科目,在新的明细科目下设置你想要的核算项目类别')
            else:
                raise exceptions.ValidationError(
                    '该科目已经使用,不能改变.你可以添加新的明细科目,在新的明细科目下设置你想要的核算项目类别')

    @api.onchange('itemClasses')
    def _checkItemClasses(self):
        '''改变科目的核算项目类别 '''
        if self.accountItemClass and self.accountItemClass.id not in self.itemClasses.ids:
            raise exceptions.ValidationError(
                '['+self.accountItemClass.name+"]已经作为明细科目的类别,不能删除.如果要删除,请你在'作为明细的类别'中先取消它")

    # @api.multi
    @api.depends('childs_ids')
    def _is_last(self):
        '''是否末级科目'''
        for a in self:
            if a.childs_ids:
                a.is_last = False
            else:
                a.is_last = True

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=0):
        args = args or []
        domain = []
        # 同时根据科目编号和名称进行搜索
        if name:
            domain = ['|', ('number', operator, name),
                      ('name', operator, name), ]
        # 源代码默认为160,突破其限制   详细见 /web/static/src/js/views/form_common.js
        if limit == 160:
            limit = 0
        context = self.env.context
        org_id = context.get('org_id')
        control_org = context.get('control_org')
        control_org = control_org if control_org else True

        if org_id:
            # 修改凭证时从上下文取
            org = org_id
        else:
            # 新增时从用户默认值取，凭证机构的change会触发默认值从新设置
            org = self.env.user.currentOrg.id
        if control_org:
            domain = ['|', ('org', '=', False),
                      ('org', 'in', [org])]+args+domain
        elif args:
            domain = ['|', ('org', '=', False)]+args+domain
        pos = self.search(domain, limit=limit, order='number')
        return pos._my_name_get()

    @api.model
    # @api.multi
    def _my_name_get(self):
        result = []
        name = self._rec_name
        context = self.env.context
        show_balance = context.get('show_balance')
        if show_balance:
            org_id = context.get('org_id')
            if org_id:
                # 修改凭证时从上下文取
                org = self.env['accountcore.org'].sudo().browse(org_id)
            else:
                # 新增时从用户默认值取，凭证机构的change会触发默认值从新设置
                org = self.env.user.currentOrg
        if name in self._fields:
            convert = self._fields[name].convert_to_display_name
            if show_balance:
                for record in self:
                    endAmount = record.getEndAmount(org, None)
                    showStr = (record['number'])+"【" + \
                        convert(record[name], record)+"】"
                    if endAmount != 0:
                        showStr = showStr+'{:,.2f}'.format(endAmount)
                    result.append((record.id, showStr))
            else:
                for record in self:
                    result.append(
                        (record.id,  (record['number'])+"【"+convert(record[name], record)+"】"))
        else:
            for record in self:
                result.append((record.id, "%s,%s" % (record._name, record.id)))
        return result

    @api.model
    def get_itemClasses(self, accountId):
        '''获得科目下的核算项目类别'''
        account = self.browse([accountId])
        itemClasses = account.itemClasses
        accountItemClassId = account.accountItemClass.id
        return [{'id': i.id, 'name':  (("■"+i.name)
                                       if i.id == accountItemClassId else i.name)}
                for i in itemClasses]

    # @api.multi
    @api.depends('itemClasses', 'accountItemClass')
    def _itemClassesHtml(self):
        '''购建科目相关核算项目展示内容'''
        content = None
        itemTypes = None
        for account in self:
            content = []
            if account.itemClasses:
                accountItemClassId = account.accountItemClass.id
                itemTypes = account.itemClasses
                content = [('■'+itemType.name) if(itemType.id == accountItemClassId)
                           else itemType.name for itemType in itemTypes]

            account.itemClassesHtml = '/'.join(content)
        return True
    # 获得科目下的全部明细科目和自生对象的ID
    # @api.multi

    def getMeAndChild_ids(self):
        '''获得科目下的全部明细科目和自生的ID'''
        self.ensure_one()
        # 通过科目编码来判断
        # return self.search([('number', 'like', self.number)]).mapped('id')
        return self.getMeAndChilds().mapped('id')

    # 获得科目下的全部明细科目和自生对象
    # @api.multi
    def getMeAndChilds(self):
        '''获得科目下的全部明细科目和自生'''
        self.ensure_one()
        # 通过科目编码来判断
        # return self.search([('number', 'like', self.number)])
        rl = self
        for c in self.childs_ids:
            rl = rl | c.getMeAndChilds()
        return rl

    # 科目在余额表里是否有记录(只比较科目))

    def isUsedInBalance(self):
        '''科目在余额表里是否有记录(只比较科目))'''
        if len(self.getAllBalances()) > 0:
            return True
        else:
            return False

    # 获得科目的余额记录，未排序，相同科目下的不同机构和核算项目视为同一科目

    def getAllBalances(self):
        '''获得科目的余额记录,相同科目下的不同机构/主体和核算项目视为同一科目'''
        domain = [('account', '=', self.id)]
        account_balances = self.env["accountcore.accounts_balance"].sudo().search(
            domain)
        return account_balances

    # 获得科目的余额记录，未排序

    def getBalances(self, org=None, item=None):
        '''获得科目(考虑机构/主体和核算项目)的余额记录,相同科目下的不同机构/主体和核算项目视为不同科目'''
        domain = [('account', '=', self.id)]
        if item:
            domain.append(('items', '=', item.id))
        else:
            domain.append(('items', '=', False))
        if org:
            domain.append(('org', '=', org.id))
        else:
            domain.append(('org', '=', False))
        account_balances = self.env["accountcore.accounts_balance"].sudo().search(
            domain)
        return account_balances
    # 获得启用期初的记录

    def getBegins(self, org=None, item=None):
        '''获得启用期初的记录'''
        rs = self.getBalances(org, item)
        rl = rs.filtered(lambda r: r.isbegining)
        if len(rl) == 0:
            return None
        return rl
    # 获得指定月份的余额记录

    def getBlanceOf(self, year, month, org=None, item=None):
        '''获得指定月份的余额记录'''
        rs = self.getBalances(org, item)
        rl = rs.filtered(lambda r: r.year == year and r.month == month)
        if len(rl) == 0:
            return None
        return rl
    # 获得科目余额链(按期间排序，包含期初)

    def getChain(self, org, item=None):
        '''获得科目余额链,期间从早到晚'''
        rs = self.getBalances(org, item)
        rs_sorted = rs.sorted(key=lambda r: (
            r.year, r.month, not r.isbegining))
        return rs_sorted

        # 获得当下科目余额记录
    def getBalanceOfVoucherPeriod(self, voucher_period, org, item):
        '''获得指定会计期间的科目余额记录'''
        chain = self.getChain(org, item)
        compareMark = voucher_period.year*12+voucher_period.month
        rs = chain.filtered(lambda r: (r.year*12+r.month) <= compareMark)
        if len(rs) == 0:
            balance = None
        else:
            balance = rs[-1]
        return balance

    def getBalance(self, org, item):
        '''获得当下科目余额记录'''
        chain = self.getChain(org, item)
        if len(chain) == 0:
            return None
        return chain[-1]

    def getBalanceBetween(self, start_p, end_p, org, item):
        '''获得一个期间范围的余额记录'''
        chain = self.getChain(org, item)
        startMark = start_p.year*12+start_p.month
        endMark = end_p.year*12+end_p.month
        rs = chain.filtered(lambda r: startMark <=
                            (r.year*12+r.month) <= endMark)
        if len(rs) == 0:
            balance = None
        else:
            balance = rs
        return balance
    # 获取指定会计期间的期初余额

    def getBegingAmountOf(self, voucher_period, org, item):
        '''获得会计期间的期初余额'''
        amount = 0
        startP = voucher_period
        preP = startP.getPreP()
        # 获取前一个期间的期末余额
        balance = self.getBalanceOfVoucherPeriod(preP, org, item)
        if balance:
            if self.direction == '1':
                amount = balance.endDamount-balance.endCamount
            else:
                amount = balance.endCamount-balance.endDamount
        else:
            # 期初
            balance = self.getBalanceOfVoucherPeriod(startP, org, item)
            if balance:
                if self.direction == '1':
                    amount = balance.beginingDamount-balance.beginingCamount
                else:
                    amount = balance.beginingCamount-balance.beginingDamount
            # 在启用当年的年初1月
            elif startP.month == 1:
                begin = self.getBegins(org, item)
                if begin and begin.year == startP.year:
                    amount = begin.begin_year_amount
        return amount

    # 获得指定会计期间的期初借方余额
    def getBegingDAmountOf(self, voucher_period, org, item):
        '''获得会计期间的期初借方余额'''
        amount = 0
        startP = voucher_period
        preP = startP.getPreP()
        # 获取前一个期间的期末余额
        balance = self.getBalanceOfVoucherPeriod(preP, org, item)
        if balance:
            amount = balance.endDamount-balance.endCamount
            if amount < 0:
                amount = 0
        else:
            # 期初
            balance = self.getBalanceOfVoucherPeriod(startP, org, item)
            if balance:
                amount = balance.beginingDamount-balance.beginingCamount
                if amount < 0:
                    amount = 0
            # 在启用当年的年初1月
            elif startP.month == 1:
                begin = self.getBegins(org, item)
                if begin and begin.year == startP.year:
                    begin_d = begin.beginingDamount-begin.beginCumulativeDamount
                    begin_c = begin.beginingCamount-begin.beginCumulativeCamount
                    if abs(begin_d) > abs(begin_c):
                        amount = begin_d-begin_c

        return amount
    # 获得指定会计期间的期初贷方余额

    def getBegingCAmountOf(self, voucher_period, org, item):
        '''获得会计期间的期初贷方方余额'''
        amount = 0
        startP = voucher_period
        preP = startP.getPreP()
        # 获取前一个期间的期末余额
        balance = self.getBalanceOfVoucherPeriod(preP, org, item)
        if balance:
            amount = balance.endCamount-balance.endDamount
            if amount < 0:
                amount = 0
        else:
            # 期初
            balance = self.getBalanceOfVoucherPeriod(startP, org, item)
            if balance:
                amount = balance.beginingCamount-balance.beginingDamount
                if amount < 0:
                    amount = 0
            # 在启用当年的年初1月
            elif startP.month == 1:
                begin = self.getBegins(org, item)
                if begin and begin.year == startP.year:
                    begin_d = begin.beginingDamount-begin.beginCumulativeDamount
                    begin_c = begin.beginingCamount-begin.beginCumulativeCamount
                    if abs(begin_d) < abs(begin_c):
                        amount = begin_c - begin_d
        return amount
    # 获得一个期间的借方发生额

    def getDamountBetween(self, start_p, end_p, org, item):
        '''获得一个期间的借方发生额'''
        chains = self.getBalanceBetween(start_p, end_p, org, item)
        amount = 0
        if chains:
            for i in range(0, len(chains)):
                amount += chains[i].damount
        return amount

    # 获得一个期间的贷方发生额
    def getCamountBetween(self, start_p, end_p, org, item):
        '''获得一个期间的贷方发生额'''
        chains = self.getBalanceBetween(start_p, end_p, org, item)
        amount = 0
        if chains:
            for i in range(0, len(chains)):
                amount += chains[i].camount
        return amount
    # 获得指定会计期间的期末余额

    def getEndAmountOf(self, end_p, org, item):
        '''获得指定会计期间的期末余额'''

        amount = 0
        endP = end_p
        balance = self.getBalanceOfVoucherPeriod(endP, org, item)
        if balance:
            if self.direction == '1':
                amount = balance.endDamount-balance.endCamount
            else:
                amount = balance.endCamount-balance.endDamount
        return amount
    # 期末借方余额

    def getEndDAmount(self, end_p, org, item):
        '''期末借方余额'''
        amount = 0
        endP = end_p
        balance = self.getBalanceOfVoucherPeriod(endP, org, item)
        if balance:
            amount = balance.endDamount-balance.endCamount
            if amount < 0:
                amount = 0
        return amount

    # 期末贷方余额
    def getEndCAmount(self, end_p, org, item):
        '''期末借方余额'''
        amount = 0
        endP = end_p
        balance = self.getBalanceOfVoucherPeriod(endP, org, item)
        if balance:
            amount = balance.endCamount-balance.endDamount
            if amount < 0:
                amount = 0
        return amount

    # 获得指定会计期间的本年累计金额（借方，贷方）

    def getCumulativeAmountOf(self, voucher_period, org, item):
        '''获得指定期间的本年累计金额'''
        balance = self.getBalanceOfVoucherPeriod(voucher_period, org, item)
        if balance:
            return (balance.cumulativeDamount, balance.cumulativeCamount)
        else:
            return (0, 0)
    # 获得指定会计期间的本年借方累计

    def getCumulativeDAmountOf(self, voucher_period, org, item):
        '''获得指定会计期间的本年借方累计'''
        return self.getCumulativeAmountOf(voucher_period, org, item)[0]
    # 获得指定会计期间的本年贷方累计

    def getCumulativeCAmountOf(self, voucher_period, org, item):
        '''获得指定会计期间的本年贷方累计'''
        return self.getCumulativeAmountOf(voucher_period, org, item)[1]

    # 获得当下科目的余额

    def getEndAmount(self, org, item):
        '''获得当下的科目余额金额'''
        amount = 0
        balance = self.getBalance(org, item)
        if balance:
            if self.direction == '1':
                amount = balance.endDamount-balance.endCamount
            else:
                amount = balance.endCamount-balance.endDamount
        return amount

     # 获得即时本年借方累计

    def getCurrentCumulativeDamount(self, org, item):
        '''获得即时本年借方累计金额'''
        amount = 0
        balance = self.getBalance(org, item)
        if balance:
            amount = balance.cumulativeDamount
        return amount

     # 获得即时本年贷方累计

    def getCurrentCumulativeCamount(self, org, item):
        '''获得即时本年贷方累计金额'''
        amount = 0
        balance = self.getBalance(org, item)
        if balance:
            amount = balance.cumulativeCamount
        return amount

    # 获得科目在余额表中使用过的所有核算项目

    def getAllItemsInBalances(self):
        '''获得科目在余额表中使用过的所有核算项目'''
        if not self.accountItemClass:
            return None
        rs = self.getAllBalances()
        items = rs.mapped('items')
        return items
    #  获得某机构/主体范围内科目在余额表中使用过的所有核算项目

    def getAllItemsInBalancesOf(self, org):
        '''获得某机构/主体范围内科目在余额表中使用过的所有核算项目'''
        if not self.accountItemClass:
            return None
        rs = self.getAllBalances()
        rs_org = rs.filtered(lambda r: r.org.id == org.id)
        items = rs_org.mapped('items')
        return items

    # @api.multi
    def showInVoucher(self):
        '''在凭证中显示'''
        self.write({'is_show': True})

    # @api.multi
    def cancelShowInVoucher(self):
        '''取消凭证中显示'''
        self.write({'is_show': False})

    def getAllItemClassIds(self):
        '''获取科目带的项目类别,如[[id,true],[id,false]]'''
        itemClass_list = []
        for i in self.itemClasses:
            if i.id != self.accountItemClass:
                itemClass_list.append([i.id, False])
            else:
                itemClass_list.append([i.id, True])
        return itemClass_list
    # 判断科目已经在余额表中存在

    def haveBeenUsedInBalance(self):
        '''判断科目在余额表中已被使用过'''
        accountBalances = self.env['accountcore.accounts_balance'].sudo().search(
            [('account', '=', self.id)], limit=1)
        if accountBalances.exists():
            return True
        else:
            return False


# 特殊的会计科目


class SpecialAccounts(models.Model, Glob_tag_Model):
    '''特殊的会计科目'''
    _name = "accountcore.special_accounts"
    _description = '特殊的会计科目'
    name = fields.Char(string='特殊性', required=True)
    purpos = fields.Html(string='用途说明')
    accounts = fields.Many2many('accountcore.account',
                                string='科目',
                                required=True)
    children = fields.Boolean(string='包含明细科目')
    items = fields.Many2many('accountcore.item', string='核算项目')
    _sql_constraints = [('accountcore_special_accounts_name_unique', 'unique(name)',
                         '特殊性描述重复了!')]


# 现金流量类别
class CashFlowType(models.Model, Glob_tag_Model):
    '''现金流量类别'''
    _name = 'accountcore.cashflowtype'
    _description = '现金流量类别'
    number = fields.Char(string='现金流量项目类别编码', required=True)
    name = fields.Char(string='现金流量项目类别', required=True)
    _sql_constraints = [('accountcore_cashflowtype_number_unique', 'unique(number)',
                         '现金流量类别编码重复了!'),
                        ('accountcore_cashflowtype_name_unique', 'unique(name)',
                         '现金流量类别名称重复了!')]


# 现金流量
class CashFlow(models.Model, Glob_tag_Model):
    '''现金流量项目'''
    _name = 'accountcore.cashflow'
    _description = '现金流量项目'
    _parent_store = True
    cashFlowType = fields.Many2one('accountcore.cashflowtype',
                                   string='现金流量类别',
                                   required=True,
                                   index=True)
    number = fields.Char(string="现金流量编码", required=True)
    currentChildNumber = fields.Integer(default=10,
                                        string='新建下级待用编号')
    name = fields.Char(string='现金流量名称', required=True)
    parent_id = fields.Many2one('accountcore.cashflow',
                                string='上级现金流量项目',
                                ondelete='restrict')
    parent_path = fields.Char(index=True)
    childs_ids = fields.One2many('accountcore.cashflow',
                                 'parent_id',
                                 string='直接下级流量',
                                 ondelete='restrict')
    direction = fields.Selection(
        [("-1", "流出"), ("1", "流入")], string='流量方向', required=True)
    _sql_constraints = [('accountcore_cashflow_number_unique', 'unique(number)',
                         '现金流量编码重复了!'),
                        ('accountcore_cashflow_name_unique', 'unique(name)',
                         '现金流量名称重复了!')]
    sequence = fields.Integer(string="显示优先级", help="显示顺序", default=100)
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=20):
        args = args or []
        domain = []
        # 同时根据编号和名称进行搜索
        if name:
            domain = ['|', ('number', operator, name),
                      ('name', operator, name)]
        # 源代码默认为160,突破其限制   详细见 /web/static/src/js/views/form_common.js
        if limit == 160:
            limit = 0
        pos = self.search(domain+args, limit=limit, order='sequence desc')
        return pos._my_name_get()

    @api.model
    # @api.multi
    def _my_name_get(self):
        result = []
        name = self._rec_name
        if name in self._fields:
            convert = self._fields[name].convert_to_display_name
            for record in self:
                showStr = ("【" + record['number'])+"】" + \
                    convert(record[name], record)
                result.append((record.id, showStr))
        else:
            for record in self:
                showStr = ("【" + record['number'])+"】" +\
                    convert(record[name], record)
                result.append((record.id, "%s,%s" % (showStr, record.id)))
        return result


# 凭证文件
class VoucherFile(models.Model):
    _name = 'accountcore.voucherfile'
    _description = "凭证相关文件"
    appedixfileType = fields.Char(string='文件类型', required=True)


# 凭证来源
class Source(models.Model, Glob_tag_Model):
    '''凭证来源'''
    _name = 'accountcore.source'
    _description = '凭证来源'
    number = fields.Char(string='凭证来源编码')
    name = fields.Char(string='凭证来源名称', required=True)
    _sql_constraints = [('accountcore_source_number_unique', 'unique(number)',
                         '凭证来源编码重复了!'),
                        ('accountcore_source_name_unique', 'unique(name)',
                         '凭证来源名称重复了!')]


# 记账凭证
class Voucher(models.Model, Glob_tag_Model):
    '''会计记账凭证'''
    _name = 'accountcore.voucher'
    _description = '会计记账凭证'
    name = fields.Char(related='uniqueNumber', string="唯一号", store=True)
    voucherdate = fields.Date(string='记账日期',
                              required=True,
                              placeholder='记账日期', default=fields.Date.today())
    real_date = fields.Date(string='业务日期', help='业务实际发生日期')
    # 前端通过voucherDate生成,不要直接修改
    year = fields.Integer(string='年份',
                          compute='getYearMonth',
                          store=True,
                          index=True)
    # 前端通过voucherDate生成,不要直接修改
    month = fields.Integer(string='月份',
                           compute='getYearMonth',
                           store=True,
                           index=True)
    soucre = fields.Many2one('accountcore.source',
                             string='凭证来源',
                             default=1,
                             readonly=True,
                             required=True,
                             ondelete='restrict')
    org = fields.Many2one('accountcore.org',
                          string='机构/主体',
                          required=True,
                          index=True,
                          ondelete='restrict')
    ruleBook = fields.Many2many('accountcore.rulebook',
                                string='凭证标签',
                                index=True,
                                help='可用于标记不同的凭证',
                                ondelete='restrict')
    v_number = fields.Integer(string='凭证号', group_operator='count')
    number = fields.Integer(string='策略号',
                            compute='getVoucherNumber',
                            search="searchNumber")
    appendixCount = fields.Integer(string='附件张数',
                                   default=1,
                                   required=True)
    createUser = fields.Many2one('res.users',
                                 string='制单人',
                                 default=lambda s: s.env.uid,
                                 readonly=True,
                                 required=True,
                                 ondelete='restrict',
                                 index=True)
    reviewer = fields.Many2one('res.users',
                               string='审核人',
                               ondelete='restrict',
                               readonly=True,
                               indext=True)
    entrys = fields.One2many('accountcore.entry',
                             'voucher',
                             string='分录', copy=True)
    voucherFile = fields.Many2one('accountcore.voucherfile',
                                  string='附件文件',
                                  ondelete='restrict')
    state = fields.Selection([('creating', '制单'),
                              ('reviewed', '已审核')],
                             default='creating', index=True)
    uniqueNumber = fields.Char(string='唯一编号')
    b_guid = fields.Char(string="业务流水唯一号")
    numberTasticsContainer_str = fields.Char(string='凭证可用编号策略',
                                             default="{}")
    entrysHtml = fields.Html(string="分录内容",
                             compute='createEntrysHtml',
                             store=True)
    roolbook_html = fields.Char(string="凭证的标签",
                                compute='buildRuleBook',
                                store=True)
    sum_amount = fields.Monetary(
        string='借贷方差额', default=0, compute='balance_check')

    # Monetory类型字段必须有
    currency_id = fields.Many2one('res.currency',
                                  compute='get_currency',
                                  readonly=True,
                                  string="本位币",)
    b_source = fields.Char(string="业务标识")

    @api.onchange('org')
    def _set_userdefault_org(self):
        '''改变用户默认机构/主体'''
        currentUserId = self.env.uid
        currentUserTable = self.env['res.users'].sudo().browse(currentUserId)
        currentUserTable.write(
            {'currentOrg': self.org.id})

    # @api.multi
    def get_currency(self):
        # Monetory类型字段必须有 currency_id
        for s in self:
            s.currency_id = CNY 

    @api.onchange('entrys')
    def balance_check(self):
        '''凭证借方-贷方差额显示'''
        d_amount = 0
        c_amount = 0
        for e in self.entrys:
            d_amount = e.damount+d_amount
            c_amount = e.camount+c_amount
        self.sum_amount = d_amount-c_amount

    # @api.multi
    @api.depends('voucherdate')
    def getYearMonth(self):
        for v in self:
            v.year = v.voucherdate.year
            v.month = v.voucherdate.month

    # @api.multi
    @ACTools.refuse_role_search
    def reviewing(self):
        '''审核凭证'''
        vouchers = self.filtered(lambda v: not v.reviewer)
        for v in vouchers:
            v.write({'state': 'reviewed', 'reviewer': self.env.uid})

    # @api.multi
    def cancelReview(self):
        '''取消凭证审核'''
        vouchers = self.filtered(
            lambda v: v.reviewer.id == self.env.uid or v.reviewer.name == "Public user")
        if not vouchers.exists():
            raise exceptions.UserError('没有可供取消审核的凭证,只能取消自己审核的凭证,或所选凭证有未被审核过')
        for v in vouchers:
            v.write({'state': 'creating', 'reviewer': None})

    @api.model
    def create(self, values):
        '''新增凭证'''
        # 只允许一条分录更新余额表,进程锁
        VOCHER_LOCK.acquire()
        # 出错了，必须释放锁，要不就会死锁
        try:
            values['uniqueNumber'] = self.env['ir.sequence'].next_by_code(
                'voucher.uniqueNumber')
            rl = super(Voucher, self).create(values)
            # 如果是复制新增就不执行凭证检查
            isCopye = self.env.context.get('ac_from_copy')
            if isCopye:
                pass
            else:
                try:
                    rl.checkVoucher(values)
                except Exception as ee:
                    self.env.cr.rollback()
                    raise ee
                # 跟新处理并发冲突
            rl.updateBalance()
            try:
                self.env.cr.commit()
            except Exception as e:
                n = self.env.context.get('ac_create_count', 0)
                if int(n) < 3:
                    self.env.cr.rollback()
                    sql_db.flush_env(self.env.cr)
                    n += 1
                    rl = self.with_context(
                        {'ac_create_count': n}) .create(values)
                else:
                    raise e
        finally:
            VOCHER_LOCK.release()
        return rl

    # @api.multi
    def write(self, values):
        '''修改编辑凭证'''
        self.ensure_one
        needUpdateBalance = False
        VOCHER_LOCK.acquire()
        # 出错了，必须释放锁，要不就会死锁
        try:
            if any(['voucherdate' in values,
                    'org' in values]):
                needUpdateBalance = True
            elif 'entrys' in values:
                es = values['entrys']
                # n判断如果只是删除分录,也需要更新科目余额表
                n = 0
                for e in es:
                    fields = e[2]
                    if not fields:
                        n = n+1
                        continue
                    if any(['damount' in fields,
                            'acmount' in fields,
                            'account' in fields,
                            'items' in fields]):
                        needUpdateBalance = True
                        break
                if n == len(es):
                    needUpdateBalance = True
            # 先从余额表减去原来的金额
            if needUpdateBalance:
                self.updateBalance(isAdd=False)
            rl_bool = super(Voucher, self).write(values)
            #  如果下面的检验抛出错误,将导致余额表数据出错!!!!
            self.checkVoucher(values)
            # 再从余额表加上新的金额
            if needUpdateBalance:
                self.updateBalance()
                # 跟新处理并发冲突
                try:
                    self.env.cr.commit()
                except Exception as e:
                    n = self.env.context.get('ac_write_count', 0)
                    if int(n) < 3:
                        self.env.cr.rollback()
                        sql_db.flush_env(self.env.cr)
                        n += 1
                        rl_bool = self.with_context(
                            {'ac_write_count': n}).write(values)
                    else:
                        raise e
        except Exception as e:
            raise e
        finally:
            VOCHER_LOCK.release()
        return rl_bool

    # @api.multi
    def copy(self, default=None, my_default={}):
        '''复制凭证'''
        if "voucherdate" not in my_default:
            self._checkDate()
        updateFields = {'state': 'creating',
                        'reviewer': None,
                        'createUser': self.env.uid,
                        'numberTasticsContainer_str': '{}'}
        updateFields.update(my_default)
        rl = super(Voucher, self.with_context(
            {'ac_from_copy': True})).copy(updateFields)
        return rl

    # @api.multi
    def unlink(self):
        '''删除凭证'''
        for voucher in self:
            if voucher.state == "reviewed":
                raise exceptions.ValidationError('有凭证已审核不能删除，请选择未审核凭证')
            voucher._checkDate()
        VOCHER_LOCK.acquire()
        for voucher in self:
            voucher.updateBalance(isAdd=False)
        rl_bool = super(Voucher, self).unlink()
        # 跟新处理并发冲突
        try:
            self.env.cr.commit()
        finally:
            VOCHER_LOCK.release()
        return rl_bool

    @staticmethod
    def getNumber(container_str, numberTastics_id):
        '''设置获得对应策略下的凭证编号'''
        number = VoucherNumberTastics.get_number(
            container_str, numberTastics_id)
        return number

    @staticmethod
    def getNewNumberDict(container_str, numberTastics_id, number):
        '''获得改变后的voucherNumberTastics字段数字串'''
        container = json.loads(container_str)
        container[str(numberTastics_id)] = number
        newNumberDict = json.dumps(container)
        return newNumberDict

    @api.depends('numberTasticsContainer_str')
    def getVoucherNumber(self):
        '''获得凭证编号,依据用户默认的凭证编号策略'''
        # if 用户设置了默认编号策略

        if(self.env.user.voucherNumberTastics):
            currentUserNumberTastics_id = self.env.user.voucherNumberTastics.id
        else:
            for record in self:
                record.number = 0
            return True
        for record in self:
            record.number = self.getNumber(record.numberTasticsContainer_str,
                                           currentUserNumberTastics_id)
        return True

    @api.model
    def checkVoucher(self, voucherDist):
        '''凭证检查'''
        self._checkDate()
        self._checkEntyCount(voucherDist)
        self._checkCDBalance(voucherDist)
        self._checkChashFlow(voucherDist)
        self._checkCDValue(voucherDist)
        self._checkRequiredItemClass()

    @api.model
    def _checkDate(self):
        '''检查凭证日期是否晚于锁定日期'''
        if self.org.lock_date and self._compareDate(self.voucherdate, self.org.lock_date) != 1:
            raise exceptions.ValidationError(
                '机构/主体:'+str(self.org.name)+'的锁定日期为:' + str(self.org.lock_date)+",操作凭证的记账日期应晚于该日期")

    @tools.ormcache('date1.year', 'date1.month', 'date1.day', 'date2.year', 'date2.month', 'date2.day')
    def _compareDate(self, date1, date2):
        return ACTools.compareDate(date1, date2)

    @api.model
    def _checkEntyCount(self, voucherDist):
        '''检查是否有分录'''
        if len(self.entrys) > 1:
            return True
        else:
            raise exceptions.ValidationError('需要录入两条以上的会计分录')

    @api.model
    def _checkCDBalance(self, voucherDist):
        '''检查借贷平衡'''
        camount = ACTools.ZeroAmount()
        damount = ACTools.ZeroAmount()
        camount = sum(ACTools.TranslateToDecimal(entry.camount)
                      for entry in self.entrys)
        damount = sum(ACTools.TranslateToDecimal(entry.damount)
                      for entry in self.entrys)
        if camount == damount:
            return True
        else:
            raise exceptions.ValidationError('借贷金额不平衡')

    @api.model
    def _checkCDValue(self, voucherDist):
        '''分录借贷方是否全部为零'''
        for entry in self.entrys:
            if entry.camount == 0 and entry.damount == 0:
                raise exceptions.ValidationError('借贷方金额不能全为零')
        return True

    @api.model
    def _checkChashFlow(self, voucherDist):
        # TODO -tiger:''
        return True

    # @api.multi
    @api.depends('entrys', 'entrys.account.name', 'entrys.items.name', 'entrys.sequence')
    def createEntrysHtml(self):
        '''创建凭证分录展示内容'''
        content = None
        entrys = None
        for voucher in self:
            content = "<div class='oe_accountcore_entrys'>"
            if voucher.entrys:
                entrys = voucher.entrys.sorted(lambda x:x.sequence)
                for entry in entrys:
                    content = content+self._buildingEntryHtml(entry)
            content = content+"</div>"
            voucher.entrysHtml = content
        return True

    # @api.multi
    @api.depends('ruleBook', 'ruleBook.name')
    def buildRuleBook(self):
        '''购建凭证标签展示内容'''
        for voucher in self:
            content = [item.name for item in voucher.ruleBook]
            voucher.roolbook_html = '/'.join(content)

    def _buildingEntryHtml(self, entry):
        '''购建一条分录展示内容'''
        content = ""
        items = ""
        for item in entry.items:
            items = items+"【"+item.item_class_name+"】"+item.name
        if entry.explain:
            explain = entry.explain
        else:
            explain = "*"
        damount = format(entry.damount, '0.2f') if entry.damount != 0 else ""
        camount = format(entry.camount, '0.2f') if entry.camount != 0 else ""
        content = content+"<div>"+"<div class='oe_ac_explain'>" + \
            explain+"</div>"+"<div class='oe_ac_account'>" + \
            entry.account.name+items+"</div>" + "<div class='o_list_number'>" + \
            damount+"</div>" + "<div class='o_list_number'>" + \
            camount+"</div>"
        if entry.cashFlow:
            content = content+"<div class='oe_ac_cashflow'>" + \
                entry.cashFlow.name+"</div></div>"
        else:
            content = content+"<div class='oe_ac_cashflow'></div></div>"
        return content

    def searchNumber(self, operater, value):
        '''计算字段凭证编号的查找'''
        comparetag = ('>', '>=', '<', '<=')
        if operater in comparetag:
            raise exceptions.UserError('这里不能使用比较大小查询,请使用=号')
        tasticsValue1 = '%"' + \
            str(self.env.user.voucherNumberTastics.id)+'": ' \
            + str(value)+',%'
        tasticsValue2 = '%"' + \
            str(self.env.user.voucherNumberTastics.id)+'": '  \
            + str(value)+'}%'
        return['|', ('numberTasticsContainer_str', 'like', tasticsValue1),
               ('numberTasticsContainer_str', 'like', tasticsValue2)]

    @api.model
    def _checkRequiredItemClass(self):
        '''检查科目的必录核算项目类别'''
        entrys = self.entrys
        for entry in entrys:
            itemClass_need = entry.account.accountItemClass
            if itemClass_need.id:
                items = entry.items
                itemsClasses_ids = [item.itemClass.id for item in items]
                if itemClass_need.id not in itemsClasses_ids:
                    raise exceptions.ValidationError(
                        entry.account.name+" 科目的 "+itemClass_need.name+' 为必须录入项目')
        return True

    @api.model
    def updateBalance(self, isAdd=True):
        '''更新余额'''
        for entry in self.entrys:
            # isAdd 表示是否依据分录金额减少(false)还是增加余额表金额(TRUE)
            self._updateAccountBalance(entry, isAdd)

    @api.model
    def _updateAccountBalance(self, entry, isAdd=True):
        '''新增和修改凭证，更新科目余额'''
        item = entry.getItemByitemClass(entry.account.accountItemClass)
        if item:
            itemId = item.id
        else:
            itemId = False

        if isAdd:
            computMark = 1  # 增加金额
        else:
            computMark = -1  # 减少金额
        entry_damount = entry.damount*computMark
        entry_camount = entry.camount*computMark
        accountBalanceTable = self.env['accountcore.accounts_balance']
        accountBalanceMark = AccountBalanceMark(orgId=self.org.id,
                                                accountId=entry.account.id,
                                                itemId=itemId,
                                                createDate=self.voucherdate,
                                                accountBalanceTable=accountBalanceTable,
                                                isbegining=False)
        # if 一条会计分录有核算项目
        if entry.items:
            for item_ in entry.items:
                accountBalance = self._getBalanceRecord(entry.account.id,
                                                        item_.id)
                # if 当月已经存在一条该科目的余额记录（不包括启用期初余额那条）
                if accountBalance.exists():
                    self._modifyBalance(entry_damount,
                                        accountBalance,
                                        entry_camount)
                    return True
                # else 不存在就新增一条,但必须是科目的必选核算项目类
                elif item_.id == itemId:
                    self._buildBalance(True,
                                       accountBalanceMark,
                                       entry,
                                       entry_damount,
                                       entry_camount)
                    return True
            # 存在统计项目,不存在核算项的情况,
            accountBalance = self._getBalanceRecord(entry.account.id)
            # if 当月已经存在一条该科目的余额记录（不包括启用期初余额那条）
            if accountBalance.exists():
                self._modifyBalance(entry_damount,
                                    accountBalance,
                                    entry_camount)
            # else 不存在就新增一条
            else:
                # 不排除启用期初那条记录
                self._buildBalance(False,
                                   accountBalanceMark,
                                   entry,
                                   entry_damount,
                                   entry_camount)
            return True

        # else 一条会计分录没有核算项目
        else:
            accountBalance = self._getBalanceRecord(entry.account.id)
            # if 当月已经存在一条该科目的余额记录（不包括启用期初余额那条）
            if accountBalance.exists():
                self._modifyBalance(entry_damount,
                                    accountBalance,
                                    entry_camount)
            # else 不存在就新增一条
            else:
                # 不排除启用期初那条记录
                self._buildBalance(False,
                                   accountBalanceMark,
                                   entry,
                                   entry_damount,
                                   entry_camount)

        return True

    def _modifyBalance(self, entry_damount, accountBalance, entry_camount):
        '''对已存在的科目余额记录进行修改'''
        if entry_damount != 0:
            # 科目借方余额=科目借方余额+凭证分录借方
            accountBalance.addDamount(entry_damount)
        elif entry_camount != 0:
            accountBalance.addCamount(entry_camount)
            # 更新以后各月余额记录的期初
        accountBalance.changeNextBalanceBegining(accountBalance.endDamount,
                                                 accountBalance.endCamount)

    def _buildBalance(self, haveItem, accountBalanceMark, entry, entry_damount, entry_camount):
        '''在余额表创建一条余额记录，该科目包含核算项目'''
        accountBalanceTable = self.env['accountcore.accounts_balance']
        # 不排除启用期初那条记录
        pre_balanceRecords = accountBalanceMark.get_pre_balanceRecords_all()
        # 不排除启用期初那条记录
        next_balanceRecords = accountBalanceMark.get_next_balanceRecords_all()

        if haveItem:
            newBalanceInfo = dict(accountBalanceMark)
        else:
            accountBalanceMark.items = None
            newBalanceInfo = dict(accountBalanceMark)
        # 以前月份存在数据就根据最月份的相关金额来更新期初余额
        if pre_balanceRecords.exists():
            pre_record = pre_balanceRecords[-1]
            newBalanceInfo['preRecord'] = pre_record.id
            newBalanceInfo['beginingDamount'] = \
                pre_record.beginingDamount + pre_record.damount
            newBalanceInfo['beginingCamount'] = \
                pre_record.beginingCamount + pre_record.camount
        # 以后月份存在数据就添加以后最近一月那条记录的关联
        next_record = None
        if next_balanceRecords.exists():
            next_record = next_balanceRecords[0]
            newBalanceInfo['nextRecord'] = next_record.id
        # 分录的借贷方金额作为新增这条余额记录的借贷方的发生额
        if entry.damount != 0:
            newBalanceInfo['damount'] = entry_damount
        elif entry.camount != 0:
            newBalanceInfo['camount'] = entry_camount
        # 创建新的余额记录
        newBalance = accountBalanceTable.sudo().create(newBalanceInfo)
        if next_record:
            next_record.preRecord = newBalance.id
        # 建立和前期余额记录的关联
        if pre_balanceRecords.exists():
            pre_record.nextRecord = newBalance.id
        # 更新以后各月余额记录的期初
        newBalance.changeNextBalanceBegining(
            newBalance.endDamount, newBalance.endCamount)

    @api.model
    def _getBalanceRecord(self, accountId, itemId=False):
        '''获得分录对应期间和会计科目下的核算项目的余额记录，排除启用期初那条记录'''
        balanasTable = self.env['accountcore.accounts_balance']
        org = self.org.id
        year = self.voucherdate.year
        month = self.voucherdate.month
        record = balanasTable.search([['org', '=', org],
                                      ['year', '=', year],
                                      ['month', '=', month],
                                      ['account', '=', accountId],
                                      ['items', '=', itemId],
                                      ['isbegining', '=', False]])
        return record

    @ACTools.refuse_role_search
    def writeoff(self):
        '''冲销'''
        voucher_date = fields.Date.today()
        if self.env.user.current_date:
            voucher_date = self.env.user.current_date
        uniqueNumber = self.uniqueNumber
        entrys = []
        for entry in self.entrys:
            newEntry = {}
            explain = "【冲销"+uniqueNumber+"号凭证】"
            if entry.explain:
                explain = str(entry.explain)+explain
            newEntry = {"explain": explain,
                        "account": entry.account.id,
                        "damount": -entry.damount,
                        "camount": -entry.camount,
                        "items": [(6, 0, entry.items.ids)],
                        "cashFlow": entry.cashFlow.id
                        }
            entrys.append((0, 0, newEntry))
        newVoucher = {'org': self.org.id,
                      'state': 'reviewed',
                      'reviewer': self.env.uid,
                      'createUser': self.env.uid,
                      'numberTasticsContainer_str': '{}',
                      'soucre': self.env.ref('accountcore.source_2').id,
                      'appendixCount': 0,
                      'voucherdate': voucher_date,
                      'ruleBook': [(6, 0, [self.env.ref("accountcore.rulebook_8").id])],
                      'entrys': entrys}
        rl = self.with_context(
            {'ac_from_copy': True}).create(newVoucher)
        return {
            'name': "冲销",
            'type': 'ir.actions.act_window',
            'res_model': 'accountcore.voucher',
            'view_mode': 'form',
            'res_id': rl.id,
        }

    @api.model
    def show_vouchers(self):
        '''打开凭证列表窗体'''
        if self.env.user.currentOrg:
            context = dict(
                self.env.context,
                search_default_this_month=1,
                search_default_pre_month=1,
                search_default_org=self.env.user.currentOrg.id,
            )
        else:
            context = dict(
                self.env.context,
                search_default_this_month=1,
                search_default_pre_month=1,
                search_default_group_by_org=1,
            )
        return {
            'name': '凭证列表',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'accountcore.voucher',
            'context': context,
        }
# 分录


class Enty(models.Model, Glob_tag_Model):
    '''一条分录'''
    _name = 'accountcore.entry'
    _description = "会计分录"
    voucher_id = fields.Integer(related="voucher.id", string='voucher_id')
    v_number = fields.Integer(
        related="voucher.v_number", string='凭证号', store=True)
    voucher = fields.Many2one('accountcore.voucher',
                              string='所属凭证',
                              index=True,
                              ondelete='cascade')
    org = fields.Many2one(related="voucher.org",
                          store=True,
                          string="机构/主体")
    v_voucherdate = fields.Date(related="voucher.voucherdate",
                                store=True,
                                string="记账日期",
                                index=True)
    v_real_date = fields.Date(related="voucher.real_date",
                              store=True,
                              string="业务日期",
                              index=True)
    v_year = fields.Integer(related="voucher.year",
                            store=True,
                            string="年",
                            index=True)
    v_month = fields.Integer(related="voucher.month",
                             store=True,
                             string="月",
                             index=True)
    explain = fields.Char(string='分录摘要')
    account = fields.Many2one('accountcore.account',
                              string='会计科目',
                              required=True,
                              index=True,
                              ondelete='restrict')
    items = fields.Many2many('accountcore.item',
                             string='核算统计项目',
                             index=True,
                             ondelete='restrict')
    # Monetory类型字段必须有
    currency_id = fields.Many2one('res.currency',
                                  compute='get_currency',
                                  readonly=True,
                                  string="本位币",)
    damount = fields.Monetary(string='借方金额', default=0)
    # Monetory类型字段必须有currency_id
    camount = fields.Monetary(string='贷方金额', default=0)
    cashFlow = fields.Many2one('accountcore.cashflow',
                               string='现金流量项目',
                               index=True,
                               ondelete='restrict')
    # 必录的核算项目
    account_item = fields.Many2one('accountcore.item', string='*核算项目',
                                   compute="_getAccountItem",
                                   store=True,
                                   index=True)
    items_html = fields.Html(string="科目和核算统计项目",
                             compute='_createItemsHtml',
                             store=True)
    business = fields.Text(string='业务数据')
    currency_amount = fields.Float(string="他币金额")
    ac_currency = fields.Many2one('accountcore.ac_currency', string="他币")
    sequence = fields.Integer(index=True, default=1)
    # @api.multi
    @api.depends('account.name', 'items.name', 'account_item', 'items.item_class_name')
    def _createItemsHtml(self):
        for entry in self:
            content = ["【"+item.item_class_name+"】" +
                       item.name+"<br/>" for item in entry.items]
            # ?新增分录行时会触发entry.account.name=FALSE
            entry.items_html = str(entry.account.name)+'<br/>'+''.join(content)

    # @api.multi
    @api.depends('items', 'account')
    def _getAccountItem(self):
        '''科目的必录项目类的具体项目'''
        for entry in self:
            if not entry.account.accountItemClass:
                entry.account_item = None
                continue
            id_ = entry.account.accountItemClass.id
            # account_item = entry.account_item
            if entry.items:
                for item in entry.items:
                    if item.itemClass.id == id_:
                        entry.account_item = item.id
                        break
                    entry.account_item = None
                continue

    @api.onchange('damount')
    def _damountChange(self):
        if self.damount != 0:
            self.camount = 0

    @api.onchange('camount')
    def _CamountChange(self):
        if self.camount != 0:
            self.damount = 0

    @api.onchange('account')
    # 改变科目时删除核算项目关联
    def _deleteItemsOnchange(self):
        self.items = None

    # @api.multi
    def get_currency(self):
        # Monetory类型字段必须有 currency_id
        for s in self:
            s.currency_id = CNY

    @api.model
    def getItemByitemClassId(self, itemClassId):
        '''返回分录中指定类别的核算项目'''
        if self.items:
            # items = self.items
            for item in self.items:
                if (item.itemClass.id == itemClassId):
                    return item
        return None

    @api.model
    def getItemByitemClass(self, itemClass):
        '''返回分录中指定类别的核算项目'''
        return self.getItemByitemClassId(itemClass.id)

    def show_voucher(self):
        '''分录列表关联查看凭证'''
        return {
            'name': "",
            'type': 'ir.actions.act_window',
            'res_model': 'accountcore.voucher',
            'view_mode': 'form',
            'res_id': self.voucher_id,
            'target': '',
        }

    @api.model
    def show_vouchers(self):
        '''打开分录列表窗体'''
        if self.env.user.currentOrg:
            context = dict(
                self.env.context,
                search_default_this_month=1,
                search_default_pre_month=1,
                search_default_org=self.env.user.currentOrg.id,
            )
        else:
            context = dict(
                self.env.context,
                search_default_this_month=1,
                search_default_pre_month=1,
                search_default_group_by_org=1,
            )
        return {
            'name': '凭证分录列表',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form,pivot',
            'res_model': 'accountcore.entry',
            'context': context,
        }

    def getStatisticsItems(self):
        '''获得统计项目'''
        if self.items and self.account_item:
            return [item for item in self.items if item.id != self.account_item.id]
        elif self.items:
            return [item for item in self.items]
        else:
            return []

# 凭证编号策略


class VoucherNumberTastics(models.Model, Glob_tag_Model):
    '''凭证策略号的生成策略,一张凭证在不同的策略下有不同的凭证策略号,自动生成凭证策略号需要指定一个策略'''
    _name = 'accountcore.voucher_number_tastics'
    _description = '凭证策略号生成策略'
    number = fields.Char(string='策略编码')
    name = fields.Char(string='策略名称', required=True)
    # is_defualt = fields.Boolean(string='默认使用')
    _sql_constraints = [('accountcore_voucher_number_tastics_unique', 'unique(name)',
                         '凭证编号策略名称重复了!')]

    @staticmethod
    def get_number(tastics_str, tastics_id):
        '''设置获得对应策略下的凭证编号'''
        container = json.loads(tastics_str)
        number = container.get(str(tastics_id), 0)
        return number


# 科目余额
class AccountsBalance(models.Model):
    '''科目余额'''
    _name = 'accountcore.accounts_balance'
    _description = '科目余额'
    name = fields.Integer(related='id', store=True, group_operator='count')
    org = fields.Many2one(
        'accountcore.org',
        string='所属机构/主体',
        required=True,
        index=True,
        ondelete='restrict')
    # default=lambda s: s.env.user.currentOrg)
    createDate = fields.Date(string="创建日期",
                             required=True,
                             default=lambda s: s.env.user.current_date)
    # 通过createDate生成,不要直接修改
    year = fields.Integer(string='年',
                          required=True,
                          index=True, group_operator='count')
    # 通过createDate生成,不要直接修改
    month = fields.Integer(string='月', required=True,
                           index=True, group_operator='count')
    isbegining = fields.Boolean(
        string="是启用期间", default=False, index=True, group_operator='count_distinct')
    account = fields.Many2one('accountcore.account',
                              string='会计科目',
                              required=True,
                              index=True,
                              ondelete='restrict')
    account_number = fields.Char(related='account.number',
                                 string='科目编码',
                                 store=True,
                                 index=True)
    account_class_id = fields.Many2one(related='account.accountClass',
                                       string='科目类别',
                                       store=True,
                                       index=True)
    accountItemClass = fields.Many2one('accountcore.itemclass',
                                       string='核算项目类别',
                                       related='account.accountItemClass',
                                       store=True,
                                       index=True)
    items = fields.Many2one('accountcore.item',
                            string='核算项目',
                            index=True,
                            ondelete='restrict')
    beginingDamount = fields.Monetary(string="期初借方", default=0)  # 当月初
    beginingCamount = fields.Monetary(string='期初贷方', default=0)
    # Monetory类型字段必须有currency_id
    damount = fields.Monetary(string='本期借方金额', default=0)
    camount = fields.Monetary(string='本期贷方金额', default=0)
    endDamount = fields.Monetary(string="期末借方余额",
                                 compute='getEndingBalance_D',
                                 store=True)
    endCamount = fields.Monetary(string="期末贷方余额",
                                 compute='getEndingBalance_C',
                                 store=True)
    cumulativeDamount = fields.Monetary(string='本年借方累计',
                                        compute='getCumulativeDamount',
                                        store=True,
                                        default=0)
    cumulativeCamount = fields.Monetary(string='本年贷方累计',
                                        compute='getCumulativeCamount',
                                        store=True,
                                        default=0)

    beginCumulativeDamount = fields.Monetary(string='月初本年借方累计', default=0)
    beginCumulativeCamount = fields.Monetary(string='月初本年贷方累计', default=0)
    preRecord = fields.Many2one(
        'accountcore.accounts_balance', string='最近上一期记录')
    nextRecord = fields.Many2one(
        'accountcore.accounts_balance', string='最近后一期记录')
    # Monetory类型字段必须有,要不无法正常显示
    currency_id = fields.Many2one('res.currency',
                                  compute='get_currency',
                                  readonly=True,
                                  string="本位币",)
    begin_year_amount = fields.Monetary(
        string="年初余额", compute='_getYearBeginAmount')

    # @api.multi
    @api.onchange('beginingDamount', 'beginingCamount', 'beginCumulativeDamount', 'beginCumulativeCamount')
    def _getYearBeginAmount(self):
        '''计算启用期的年初余额'''
        for b in self:
            begin_d = b.beginingDamount-b.beginCumulativeDamount
            begin_c = b.beginingCamount-b.beginCumulativeCamount
            if b.account.direction == '1':
                b.begin_year_amount = begin_d-begin_c
            else:
                b.begin_year_amount = begin_c-begin_d

    @api.onchange('beginingDamount')
    def _damountChange(self):
        if self.beginingDamount != 0:
            self.beginingCamount = 0

    @api.onchange('beginingCamount')
    def _CamountChange(self):
        if self.beginingCamount != 0:
            self.beginingDamount = 0

    @api.onchange('account')
    # 改变科目时删除核算项目关联
    def _deleteItemsOnchange(self):
        self.items = None

    # @api.multi
    def get_currency(self):
        # Monetory类型字段必须有 currency_id
        for s in self:
            s.currency_id = CNY

    @api.onchange('createDate')
    @api.depends('createDate')
    def change_period(self):
        if self.createDate:
            self.year = self.createDate.year
            self.month = self.createDate.month

    # @api.multi
    @api.depends('beginingDamount', 'damount')
    def getEndingBalance_D(self):
        '''计算期末贷方余额'''
        for record in self:
            record.endDamount = record.beginingDamount+record.damount
        return True

    # @api.multi
    @api.depends('beginingCamount', 'camount')
    def getEndingBalance_C(self):
        '''计算期末借方余额'''
        for record in self:
            record.endCamount = record.beginingCamount+record.camount
        return True

    @api.depends('beginCumulativeDamount', 'damount', 'beginingDamount')
    def getCumulativeDamount(self):
        '''计算本年借方累计发生额'''
        # 机构科目项目在本年内1月到本月的余额记录
        # 如果是改变启用期初,就不处理
        for one in self:
            if one.isbegining:
                one.cumulativeDamount = one.beginCumulativeDamount+one.damount
                return True
            one.cumulativeDamount = one._getCumulativeAmount(is_d=True)
        return True

    @api.depends('beginCumulativeCamount', 'camount', 'beginingCamount')
    def getCumulativeCamount(self):
        '''计算本年借方累计发生额'''
        for one in self:
            # 如果不是改变启用期初,就不处理
            if one.isbegining:
                self.cumulativeCamount = one.beginCumulativeCamount+one.camount
                return True
            one.cumulativeCamount = one._getCumulativeAmount(is_d=False)
        return True

    @api.model
    def create(self, values):
        '''新增一条科目余额记录'''
        if self._check_repeat(values):
            raise exceptions.ValidationError(
                '不能新增,因为已经存在一条相同科目的期初余额记录, 请在该行记录上修改或删除重复!')
        # if 创建的不是启用期初
        if not values['isbegining']:
            rl = super(AccountsBalance, self).create(values)
        elif self._check_preVoucherExist(values):
            raise exceptions.ValidationError(
                '''不能在该月份创建启用期初，因为在该月前包含有该科目的凭证!
                删除该科目以前月份的凭证或分录，就可以在该月创建启用期初''')
        else:
            # 只允许一条分录更新余额表,进程锁
            VOCHER_LOCK.acquire()
            # 出错了，必须释放锁，要不就会死锁
            try:
                rl = super(AccountsBalance, self).create(values)
                # 删除启用期以前的余额记录（不删影响对科目余额表的查询）
                preBalances = rl.get_pre_balanceRecords(
                    includeCrrentMonth=False)
                if len(preBalances) > 0:
                    preBalances.unlink()
                # 更新启用期以后各期的期初余额,
                nextBalances = (rl.get_next_balanceRecords(
                    includeCurrentMonth=True)).filtered(lambda r: not r.isbegining)

                if len(nextBalances) > 0:
                    rl.setNextBalance(nextBalances[0])
                    rl.changeNextBalanceBegining(rl.endDamount,
                                                 rl.endCamount)
            finally:
                VOCHER_LOCK.release()
        return rl

    # @api.multi
    def unlink(self):
        '''删除科目余额记录'''
        locked = False
        for mySelf in self:
            if mySelf.isbegining:
                VOCHER_LOCK.acquire()
                locked = True
                break
            else:
                continue
        try:
            for mySelf in self:
                mySelf.deleteRelatedAndUpdate()
            rl_bool = super(AccountsBalance, self).unlink()
        finally:
            if locked:
                VOCHER_LOCK.release()
        return rl_bool

    # @api.multi
    def write(self, values):
        '''修改编辑科目余额'''
        self.ensure_one()
        if self.isbegining:
            VOCHER_LOCK.acquire()
            try:
                if any(['account' in values,
                        'items' in values,
                        'year' in values,
                        'month' in values,
                        'org' in values]):
                    oldSelf = {}
                    oldSelf['org'] = self.org.id
                    oldSelf['createDate'] = self.createDate
                    oldSelf['year'] = self.year
                    oldSelf['month'] = self.month
                    oldSelf['account'] = self.account.id
                    if (values.setdefault('items', False)):
                        oldSelf['items'] = self.items.id
                    else:
                        oldSelf['items'] = None
                    oldSelf['beginingDamount'] = self.beginingDamount
                    oldSelf['beginingCamount'] = self.beginingCamount
                    oldSelf['damount'] = self.damount
                    oldSelf['camount'] = self.camount
                    oldSelf['endDamount'] = self.endDamount
                    oldSelf['endCamount'] = self.endCamount
                    oldSelf['cumulativeDamount'] = self.beginCumulativeDamount+self.damount
                    oldSelf['cumulativeCamount'] = self.beginCumulativeCamount+self.camount
                    oldSelf['beginCumulativeDamount'] = self.beginCumulativeDamount
                    oldSelf['beginCumulativeCamount'] = self.beginCumulativeCamount
                    oldSelf['preRecord'] = None
                    oldSelf['nextRecord'] = None
                    oldSelf['isbegining'] = self.isbegining
                    oldSelf.update(values)
                    # 改变科目后，如果科目有必选项目类别，判断是否输入
                    if not oldSelf['items']:
                        newAccount = self.env['accountcore.account'].sudo().browse([
                            oldSelf['account']])
                        itemClass_need = newAccount.accountItemClass
                        if itemClass_need.id:
                            raise exceptions.ValidationError(
                                newAccount.name+" 科目的 "+itemClass_need.name+' 为必须录入项目')

                    if self._check_preVoucherExist(oldSelf):
                        raise exceptions.ValidationError('''不能在该月份创建启用期初，因为在该月前包含有该科目的凭证!
                    删除该科目以前月份的凭证或分录，就可以在该月创建启用期初''')
                    if self._check_repeat(oldSelf):
                        raise exceptions.ValidationError(
                            '''已经存在一条相同科目的期初余额记录行,请取消,在另一行已存在的记录上修改!
                            若不想保留本行，请勾选本行，并在动作中选择删除操作''')
                    # 删除旧关系，更新原有余额记录链各种金额，但不删除记录
                    self.deleteRelatedAndUpdate()

                    rl_bool = super(AccountsBalance, self).write(oldSelf)
                    # 删除启用期以前的余额记录（不删影响对科目余额表的查询）
                    preBalances = self.get_pre_balanceRecords(
                        includeCrrentMonth=False)
                    if len(preBalances) > 0:
                        preBalances.unlink()
                    # 添加新的关系，更新新的余额记录链条各种金额
                    self.buildRelatedAndUpdate()
                    return rl_bool
                else:
                    # 更新启用期初的本年累计
                    if 'beginCumulativeDamount' in values:
                        values.update(
                            {'cumulativeDamount': values['beginCumulativeDamount']})
                    if 'beginCumulativeCamount' in values:
                        values.update(
                            {'cumulativeCamount': values['beginCumulativeCamount']})
                    rool_bool = super(AccountsBalance, self).write(values)
                    # 跟新本期及以后期间的科目余额记录的期初余额
                    nextBalances = (self.get_next_balanceRecords(True)).filtered(
                        lambda r: not r.isbegining)
                    if len(nextBalances) > 0:
                        self.changeNextBalanceBegining(
                            self.endDamount, self.endCamount)
                    return rool_bool
            finally:
                VOCHER_LOCK.release()
        else:
            rl_bool = super(AccountsBalance, self).write(values)
            return rl_bool

    @api.model
    def addDamount(self, amount):
        self.damount = self.damount+amount

    @api.model
    def addCamount(self, amount):
        self.camount = self.camount+amount

    @api.model
    def changeNextBalanceBegining(self, end_damount, end_camount):
        '''更新以后各期的期初余额,依据对象的nextRecord属性,damount变动的借方'''
        if self.nextRecord:
            nextRecord = self.nextRecord
            nextRecord.beginingDamount = end_damount
            nextRecord.beginingCamount = end_camount
            nextRecord.changeNextBalanceBegining(
                nextRecord.endDamount, nextRecord.endCamount)
        else:
            return

    @api.model
    def updateCumulative(self, cumulativeDamount, cumulativeCamount):
        '''更新启用期初当年的各余额记录的本年累计'''
        currenYearRecords = self.search(
            [('year', '=', self.year),
             ('org', '=', self.org.id),
             ('account', '=', self.account.id),
             ('items', '=', self.items.id),
             ('isbegining', '=', False)])
        for r in currenYearRecords:
            r.write({'cumulativeDamount': r.cumulativeDamount+cumulativeDamount,
                     'cumulativeCamount': r.cumulativeCamount+cumulativeCamount})

    @api.model
    def changePreBalanceBegining(self, begin_damount, begin_camount):
        '''更新以前各期期的期初余额,依据对象的preRecord属性'''
        if self.preRecord:
            preRecord = self.preRecord
            preRecord.beginingDamount = begin_damount-self.preRecord.damount
            preRecord.beginingCamount = begin_camount-self.preRecord.camount
            preRecord.changePreBalanceBegining(
                preRecord.beginingDamount, preRecord.beginingCamount)
        else:
            return

    def get_pre_balanceRecords(self, includeCrrentMonth=True):
        '''获得记录科目余额的当月以前月份记录集合，默认包含当月'''
        balanceRecords = self.get_my_balanceRecords()
        if not includeCrrentMonth:
            pre_balanceRecords = (balanceRecords.filtered(lambda r: (
                r.year < self.year
                or (r.year == self.year
                    and r.month < self.month)))).sorted(key=lambda a: (a.year, a.month))
        else:
            pre_balanceRecords = (balanceRecords.filtered(lambda r: (
                r.year < self.year
                or (r.year == self.year
                    and r.month <= self.month)))).sorted(key=lambda a: (a.year, a.month))
        return pre_balanceRecords

    def get_next_balanceRecords(self, includeCurrentMonth=False):
        '''获得记录科目余额的以后月份记录集合，默认不包含当月'''
        balanceRecords = self.get_my_balanceRecords()
        if not includeCurrentMonth:
            next_balanceRecords = (balanceRecords.filtered(lambda r: (
                r.year > self.year
                or (r.year == self.year
                    and r.month > self.month)))).sorted(key=lambda a: (a.year, a.month))
        else:
            next_balanceRecords = (balanceRecords.filtered(lambda r: (
                r.year > self.year
                or (r.year == self.year
                    and r.month >= self.month)))).sorted(key=lambda a: (a.year, a.month))
        return next_balanceRecords

    def get_my_balanceRecords(self):
        '''获得记录科目余额的各月份记录集合'''
        accountBalanceTable = self.env['accountcore.accounts_balance']
        domain_org = ('org', '=', self.org.id)
        domain_account = ('account', '=', self.account.id)
        if self.items:
            domain_item = ('items', '=', self.items.id)
            balanceRecords = accountBalanceTable.search(
                [domain_org, domain_account, domain_item])
        else:
            balanceRecords = accountBalanceTable.search(
                [domain_org, domain_account])
        return balanceRecords

    def setNextBalance(self, accountBalance):
        '''设置两期余额对象的关联关系'''
        self.nextRecord = accountBalance
        accountBalance.preRecord = self

    def isSameWith(self, accountBalance):
        '''判断两个余额对象是不是同一机构,科目和核算项目'''
        if (self.org != accountBalance.org) or (self.account != accountBalance.account):
            return False
        elif self.items != AccountsBalance.items:
            return False
        return True

    def deleteRelatedAndUpdate(self):
        '''取消余额记录前后期的关联，同时更新关联余额'''
        # 前期没有余额记录，后期有
        if all([self.nextRecord, (not self.preRecord)]):
            self.changeNextBalanceBegining(0, 0)
            self.nextRecord.preRecord = None
            self.nextRecord = None
            # if删除的是启用期初，以后各期本年累计需要减去用该启用期初时的本年累计
            if self.isbegining:
                self.updateCumulative(-self.cumulativeDamount,
                                      -self.cumulativeCamount)
        # 前后期都有余额记录
        elif all([self.nextRecord, self.preRecord]):
            self.preRecord.setNextBalance(self.nextRecord)
            self.changeNextBalanceBegining(self.preRecord.endDamount,
                                           self.preRecord.endCamount)
        # 前期有，后期都没有余额记录,不用处理
        return self

    def buildRelatedAndUpdate(self):
        '''新建（启用期初）余额记录的前后期关系，同时更新关联记录余额'''
        nextBalances = (self.get_next_balanceRecords(True)).filtered(
            lambda r: not r.isbegining)
        preBalances = self.get_pre_balanceRecords(includeCrrentMonth=False)
        if len(nextBalances) > 0:

            self.setNextBalance(nextBalances[0])
            self.changeNextBalanceBegining(self.endDamount,
                                           self.endCamount)
        if len(preBalances) > 0:
            preBalances[-1].setNextBalance(self)
            self.changePreBalanceBegining(self.beginingDamount,
                                          self.beginingCamount)

    def _getCumulativeAmount(self, is_d):
        '''本年累计金额'''
        records = self.search([('year', '=', self.year),
                               ('org', '=', self.org.id),
                               ('account', '=', self.account.id),
                               ('items', '=', self.items.id)])
        selfMonth = self.month
        beginingRecord = records.filtered(lambda r: r.isbegining)
        fieldName = 'damount' if is_d else 'camount'
        # if 如果启用期初记录在当年
        if beginingRecord.exists():
            beginMonth = beginingRecord.month
            if is_d:
                beginAmount = beginingRecord.beginCumulativeDamount
            else:
                beginAmount = beginingRecord.beginCumulativeCamount
            # 在启用月份以前
            if selfMonth < beginMonth:
                rds_between_begin_self = records.filtered(
                    lambda rd: selfMonth < rd.month < beginMonth)
                yearAmount = beginAmount - \
                    sum(rds_between_begin_self.mapped(fieldName))
            # 在启用月份及以后
            else:
                rds_between_begin_self = records.filtered(
                    lambda rd: beginMonth <= rd.month <= selfMonth)
                yearAmount = beginAmount + \
                    sum(rds_between_begin_self.mapped(fieldName))
        # 启用期初记录不在当年
        else:
            rds_before_and_self = records.filtered(
                lambda rd: rd.month <= selfMonth)
            yearAmount = sum(rds_before_and_self.mapped(fieldName))
        return yearAmount

    @api.model
    def _getBalanceRecord(self, entry, itemId=False):
        '''获得分录对应期间和会计科目下的核算项目的余额记录，排除启用期初那条记录'''
        balanasTable = self.env['accountcore.accounts_balance']
        org = entry.org.id
        year = entry.v_year
        month = entry.v_month
        record = balanasTable.search([['org', '=', org],
                                      ['year', '=', year],
                                      ['month', '=', month],
                                      ['account', '=', entry.account.id],
                                      ['items', '=', itemId],
                                      ['isbegining', '=', False]])
        return record

    @api.model
    def _check_repeat(self, accountBalance):
        '''检查是否已经有一条期初或余额记录'''
        if ('items' in accountBalance):
            if accountBalance['isbegining'] == True:
                records = self.search([('org', '=', accountBalance['org']),
                                       ('account', '=',
                                        accountBalance['account']),
                                       ('items', '=', accountBalance['items']),
                                       ('isbegining', '=', True),
                                       ('year', '=', accountBalance['year']),
                                       ('month', '=', accountBalance['month'])], limit=1)
            else:
                records = self.search([('org', '=', accountBalance['org']),
                                       ('year', '=', accountBalance['year']),
                                       ('month', '=', accountBalance['month']),
                                       ('account', '=',
                                        accountBalance['account']),
                                       ('items', '=', accountBalance['items']),
                                       ('isbegining', '=', False)], limit=1)

        else:
            if accountBalance['isbegining'] == True:
                records = self.search([('org', '=', accountBalance['org']),
                                       ('account', '=',
                                        accountBalance['account']),
                                       ('isbegining', '=', True),
                                       ('year', '=', accountBalance['year']),
                                       ('month', '=', accountBalance['month'])], limit=1)
            else:
                records = self.search([('org', '=', accountBalance['org']),
                                       ('year', '=', accountBalance['year']),
                                       ('month', '=', accountBalance['month']),
                                       ('account', '=',
                                        accountBalance['account']),
                                       ('isbegining', '=', False)], limit=1)
        if records.exists():
            return True
        return False

    def _check_preVoucherExist(self, value):
        '''检查以前期间是否存在凭证'''
        domain = [('org', '=', value['org']),
                  ('account', '=', value['account']),
                  ('items', '=', value.setdefault('items', False)),
                  '|', ('v_year', '<', value['year']),
                  '&', ('v_year', '=', value['year']),
                  ('v_month', '<', value['month'])]
        entrys = self.env['accountcore.entry'].sudo().search(domain, limit=1)
        if len(entrys) > 0:
            return True
        return False

    @classmethod
    def getBeginOfOrg(cls, org):
        '''获得机构的启用期初记录'''
        domain = [('org', '=', org.id), ('isbegining', '=', True)]
        env = org.env['accountcore.accounts_balance']
        return env.sudo().search(domain)

    @classmethod
    def getFielValueOf(cls, field_name, records):
        '''获取记录中某字段值'''
        return records.mapped(field_name)

    @classmethod
    def _sumFieldOf(cls, field_name, records):
        '''对某字段求和'''
        fieldsValue = cls.getFielValueOf(field_name, records)
        fieldsValue_ = [(Decimal.from_float(v)).quantize(
            Decimal('0.00')) for v in fieldsValue]
        return sum(fieldsValue_)


# 科目余额用对象
class AccountBalanceMark(object):
    def __init__(self, orgId, accountId, itemId, createDate, accountBalanceTable, isbegining):
        self.org = orgId
        self.account = accountId
        self.items = itemId
        self.createDate = createDate
        self.year = createDate.year
        self.month = createDate.month
        self.isbegining = isbegining
        self.accountBalanceTable = accountBalanceTable

    def keys(self):
        return ('org',
                'account',
                'items',
                'createDate',
                'year',
                'month',
                'isbegining')

    def __getitem__(self, item):
        return getattr(self, item)

    def get_pre_balanceRecords_all(self):
        '''获得相同科目余额前期记录集合，不排除期初那条'''
        accountBalanceTable = self.accountBalanceTable
        domain_org = ('org', '=', self.org)
        domain_account = ('account', '=', self.account)
        domain_item = ('items', '=', self.items)
        balanceRecords = accountBalanceTable.search(
            [domain_org, domain_account, domain_item])
        # 该科目的前期记录集合
        pre_balanceRecords = (balanceRecords.filtered(lambda r: (
            r.year < self.year
            or (r.year == self.year
                and r.month <= self.month)))).sorted(key=lambda a: (a.year, a.month, not a.isbegining))
        return pre_balanceRecords

    def get_next_balanceRecords_all(self):
        '''获得相同科目余额后期记录集合，不排除期初那条'''
        accountBalanceTable = self.accountBalanceTable
        domain_org = ('org', '=', self.org)
        domain_account = ('account', '=', self.account)
        domain_item = ('items', '=', self.items)
        balanceRecords = accountBalanceTable.search(
            [domain_org, domain_account, domain_item])
        # 该科目的后期记录集合
        next_balanceRecords = (balanceRecords.filtered(lambda r: (
            r.year > self.year
            or (r.year == self.year
                and r.month > self.month)))).sorted(key=lambda a: (a.year, a.month, not a.isbegining))
        return next_balanceRecords
