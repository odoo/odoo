# -*- coding: utf-8 -*-
from decimal import Decimal
import json
from odoo import api
from odoo import exceptions
from odoo import fields
from odoo import models
from ..models.main_models import AccountsBalance
from ..models.main_models import Voucher
from ..models.ac_period import Period
from ..models.main_models import Glob_tag_Model
from ..models.ac_obj import ACTools, BalanceLine, BalanceLines
# 向导部分-开始
# 新增下级科目的向导


class CreateChildAccountWizard(models.TransientModel, Glob_tag_Model):
    '''新增下级科目的向导'''
    _name = 'accountcore.create_child_account'
    _description = '新增下级科目向导'
    fatherAccountId = fields.Many2one('accountcore.account',
                                      string='上级科目',
                                      help='新增科目的直接上级科目')
    fatherAccountNumber = fields.Char(related='fatherAccountId.number',
                                      string='上级科目编码')
    org = fields.Many2many('accountcore.org',
                           string='所属机构/主体',
                           help="科目所属机构/主体",
                           index=True,
                           ondelete='restrict')
    accountsArch = fields.Many2one('accountcore.accounts_arch',
                                   string='所属科目体系',
                                   help="科目所属体系",
                                   index=True,
                                   ondelete='restrict')
    accountClass = fields.Many2one('accountcore.accountclass',
                                   string='科目类别',
                                   index=True,
                                   ondelete='restrict')
    number = fields.Char(string='科目编码', required=True)
    name = fields.Char(string='科目名称', required=True)
    direction = fields.Selection([('1', '借'),
                                  ('-1', '贷')],
                                 string='余额方向',
                                 required=True)
    is_show = fields.Boolean(string='凭证中显示', default=True)
    cashFlowControl = fields.Boolean(string='分配现金流量')
    itemClasses = fields.Many2many('accountcore.itemclass',
                                   string='包含的核算项目类别',
                                   help="录入凭证时,提示选择该类别下的核算项目",
                                   ondelete='restrict')
    accountItemClass = fields.Many2one('accountcore.itemclass',
                                       string='作为明细科目的类别(凭证中必填项目)',
                                       help="录入凭证分录时必须输入的该类别下的一个核算项目,作用相当于明细科目",
                                       ondelete='restrict')
    explain = fields.Html(string='科目说明')
    @api.model
    def default_get(self, field_names):
        default = super().default_get(field_names)
        fatherAccountId = self.env.context.get('active_id')
        fatherAccount = self.env['accountcore.account'].sudo().search(
            [['id', '=', fatherAccountId]])
        default['accountsArch'] = fatherAccount.accountsArch.id
        default['fatherAccountId'] = fatherAccountId
        default['org'] = fatherAccount.org.ids
        default['accountClass'] = fatherAccount.accountClass.id
        default['direction'] = fatherAccount.direction
        default['cashFlowControl'] = fatherAccount.cashFlowControl
        default['number'] = fatherAccount.number + \
            '.' + str(fatherAccount.currentChildNumber)
        return default

    @ACTools.refuse_role_search
    @api.model
    def create(self, values):
        if 'name' in values:
            if '-' in values['name']:
                raise exceptions.ValidationError("科目名称中不能含有'-'字符")
            if ' ' in values['name']:
                raise exceptions.ValidationError("科目名称中不能含有空格")
        fatherAccountId = self.env.context.get('active_id')
        accountTable = self.env['accountcore.account'].sudo()
        fatherAccount = accountTable.search(
            [['id', '=', fatherAccountId]])
        newAccount = {'fatherAccountId': fatherAccountId,
                      'accountClass': fatherAccount.accountClass.id,
                      'cashFlowControl': values['cashFlowControl'],
                      'name': fatherAccount.name+'---'+values['name'],
                      'direction': fatherAccount.direction,
                      'number': fatherAccount.number + '.'
                      + str(fatherAccount.currentChildNumber)}
        fatherAccount.currentChildNumber = fatherAccount.currentChildNumber+1
        values.update(newAccount)
        rl = super(CreateChildAccountWizard, self).create(values)
        if values["accountItemClass"] and (values["accountItemClass"] not in values["itemClasses"][0][2]):
            (values["itemClasses"][0][2]).insert(0, values["accountItemClass"])
        a = accountTable.create(values)
        # 添加到上级科目的直接下级
        fatherAccount.write({'childs_ids': [(4, a.id)], 'is_show': False})
        return rl
# 用户设置模型字段的默认取值向导(如，设置凭证默认值)


class AccountcoreUserDefaults(models.TransientModel):
    '''用户设置模型字段的默认取值向导'''
    _name = 'accountcoure.userdefaults'
    _description = '用户设置模型字段默认值'
    # default_ruleBook = fields.Many2many('accountcore.rulebook',
    #                                     string='默认凭证标签')
    default_org = fields.Many2one('accountcore.org',
                                  string='默认机构/主体', default=lambda s: s.env.user.currentOrg)
    default_voucherDate = fields.Date(string='记账日期',
                                      default=lambda s: s.env.user.current_date)
    default_real_date = fields.Date(string='业务日期')
    default_glob_tag = fields.Many2many('accountcore.glob_tag',
                                        string='默认全局标签')
    # 设置新增凭证,日期,机构和账套字段的默认值

    def setDefaults(self):
        modelName = 'accountcore.voucher'
        self._setDefault(modelName,
                         'glob_tag',
                         self.default_glob_tag.ids)
        self._setDefault(modelName,
                         'org',
                         self.default_org.id)
        self._setDefault(modelName, 'voucherdate',
                         json.dumps(self.default_voucherDate.strftime('%Y-%m-%d')))
        if self.default_real_date:
            self._setDefault(modelName, 'real_date',
                             json.dumps(self.default_real_date.strftime('%Y-%m-%d')))
        else:
            self._setDefault(modelName, 'real_date', json.dumps(""))
        self.env.user.currentOrg = self.default_org.id
        self.env.user.current_date = self.default_voucherDate
        return True
    # 设置默认值

    def _setDefault(self, modelName, fieldName, defaultValue):
        idOfField = self._getIdOfIdField(fieldName,
                                         modelName,)
        rd = self._getDefaultRecord(idOfField)
        if rd.exists():
            self._modifyDefault(rd, idOfField, defaultValue)
        else:
            self._createDefault(idOfField, defaultValue)
    # 获取要设置默认值的字段在ir.model.fields中的id

    def _getIdOfIdField(self, fieldName, modelname):
        domain = [('model', '=', modelname),
                  ('name', '=', fieldName)]
        rds = self.env['ir.model.fields'].sudo().search(domain, limit=1)
        return rds.id
    # 是否已经设置过该字段的默认值

    def _getDefaultRecord(self, id):
        domain = [('field_id', '=', id),
                  ('user_id', '=', self.env.uid)]
        rds = self.env['ir.default'].sudo().search(domain, limit=1)
        return rds

    def _modifyDefault(self, rd, idOfField, defaultValue):
        rd.write({
            'field_id': idOfField,
            'json_value': defaultValue,
            'user_id': self.env.uid
        })

    def _createDefault(self, idOfField, defaultValue):
        self.env['ir.default'].sudo().create({
            'field_id': idOfField,
            'json_value': defaultValue,
            'user_id': self.env.uid
        })

# 科目余额查询向导


class GetAccountsBalance(models.TransientModel):
    '''科目余额查询向导'''
    _name = 'accountcore.get_account_balance'
    _description = '科目查询向导'
    startDate = fields.Date(string="开始期间")
    endDate = fields.Date(string="结束期间")
    fast_period = fields.Date(string="选取期间", store=False)
    onlyShowOneLevel = fields.Boolean(string="只显示一级科目", default=False)
    summaryLevelByLevel = fields.Boolean(string='逐级汇总科目',
                                         default=True,
                                         readonly=True)
    includeAccountItems = fields.Boolean(string='包含核算项目', default=True)
    no_show_no_hanppend = fields.Boolean(string='隐藏无发生额的科目', default=False)
    order_orgs = fields.Boolean(string='多机构/主体分开显示', default=False)
    noShowZeroBalance = fields.Boolean(string='隐藏余额为零的科目', default=False)
    noShowNoAmount = fields.Boolean(
        string='没有任何金额不显示', default=True)
    sum_orgs = fields.Boolean(
        string='多机构/主体合并显示', default=False)
    orgs = fields.Many2many(
        'accountcore.org',
        string='机构/主体范围',
        default=lambda s: s.env.user.currentOrg,
        required=True
    )
    account = fields.Many2many('accountcore.account',
                               string='科目范围',
                               required=True)
    # @api.multi

    def getReport(self):
        '''查询科目余额'''
        self.ensure_one()
        if len(self.orgs) == 0:
            raise exceptions.ValidationError('你还没选择机构/主体范围！')
        if len(self.account) == 0:
            self.account = self.env['accountcore.account'].search([])
        self._setDefaultDate()
        [data] = self.read()
        startDate = data['startDate']
        start_year = startDate.year
        start_month = startDate.month
        period = self._periodIsBeforBeging(
            start_year, start_month, data['orgs'],  data['account'])
        if period:
            raise exceptions.ValidationError(
                "查询的开始期间 " + str(start_year) + "-"+str(start_month) + " 早于查询范围内科目: "+str(period[1])+" 等的启用期,查询的开始期间不能大于启用期间(因启用期前的期初余额无法明确,会导致逻辑错误,禁止查询),最早可选择 "+period[0]+" 为查询的开始期间")
        datas = {
            'form': data
        }
        return self.env.ref('accountcore.accounctore_accountsbalance_report').report_action([], data=datas)

    def _setDefaultDate(self):
        if not self.startDate:
            self.startDate = '1900-01-01'
        if not self.endDate:
            self.endDate = '2219-12-31'
        if self.startDate > self.endDate:
            raise exceptions.ValidationError('你选择的开始日期不能大于结束日期')

    def _periodIsBeforBeging(self, start_year, start_month, org_ids, account_ids):
        '''检查查询期间是否早于启用期间'''
        accounts = self.env['accountcore.account'].sudo().browse(account_ids)
        all_ids = []
        for ac in accounts:
            all_ids.extend(ac.getMeAndChild_ids())
        domain = [('isbegining', '=', True),
                  ('org', 'in', org_ids),
                  ('account', 'in', list(set(all_ids))), '|', '&',
                  ('year', '=', start_year),
                  ('month', '>', start_month),
                  ('year', '>', start_year)]
        records = self.env['accountcore.accounts_balance'].sudo().search(
            domain)
        if records.exists():
            records_sorted = records.sorted(key=lambda r: r.year+r.month*12)
            period_str = str(records_sorted[-1].year) + \
                "-"+str(records_sorted[-1].month)
            return (period_str, records_sorted[-1].account.name)
        return False
# 科目明细/总账查询向导


class GetSubsidiaryBook(models.TransientModel):
    "科目明细/总账查询向导"
    _name = 'accountcore.get_subsidiary_book'
    _description = '科目明细账查询向导'
    startDate = fields.Date(string='开始月份')
    endDate = fields.Date(string='结束月份')
    fast_period = fields.Date(string="选取期间", store=False)
    orgs = fields.Many2many('accountcore.org',
                            string='机构/主体范围',
                            default=lambda s: s.env.user.currentOrg,
                            required=True)
    account = fields.Many2many(
        'accountcore.account', string='查询的科目', required=True)
    only_this_level = fields.Boolean(string='只包含本级科目', default=False)
    item = fields.Many2one('accountcore.item', string='查询的核算项目')
    show_general = fields.Boolean(string="显示总账")
    show_unique_number = fields.Boolean(string="显示唯一号", default=True)
    show_orgs = fields.Boolean(string="显示机构/主体", default=True)
    # @api.multi

    def getReport(self, *args):
        self.ensure_one()
        if len(self.orgs) == 0:
            raise exceptions.ValidationError('你还没选择机构/主体范围！')
        if not self.account:
            raise exceptions.ValidationError('你需要选择查询的科目！')
        self._setDefaultDate()
        [data] = self.read()
        datas = {
            'form': data
        }
        return self.env.ref('accountcore.subsidiarybook_report').report_action([], data=datas)

    def _setDefaultDate(self):
        if not self.startDate:
            self.startDate = '1900-01-01'
        if not self.endDate:
            self.endDate = '2219-12-31'
        if self.startDate > self.endDate:
            raise exceptions.ValidationError('你选择的开始日期不能大于结束日期')
# 自动结转损益向导


class currencyDown_sunyi(models.TransientModel):
    "自动结转损益向导"
    _name = 'accountcore.currency_down_sunyi'
    _description = '自动结转损益向导'
    startDate = fields.Date(string='开始月份', required=True)
    endDate = fields.Date(string='结束月份', required=True)
    fast_period = fields.Date(string="选取期间", store=False)
    orgs = fields.Many2many(
        'accountcore.org',
        string='机构/主体范围',
        default=lambda s: s.env.user.currentOrg, required=True)
    auto_lock = fields.Boolean(string='自动锁定', default=True, help="锁定到结转损益的日期")
    # def soucre(self):
    #     return self.env.ref('rulebook_1')
    # @api.multi
    @ACTools.refuse_role_search
    def do(self, *args):
        '''执行结转损益'''
        self.ensure_one()
        if len(self.orgs) == 0:
            raise exceptions.ValidationError('你还没选择机构/主体范围！')
        if self.startDate > self.endDate:
            raise exceptions.ValidationError('你选择的开始日期不能大于结束日期')
        # 获得需要结转的会计期间
        periods = Period(self.startDate, self.endDate).getPeriodList()
        # 检查开始日期和锁定日期
        for _org in self.orgs:
            if _org.lock_date and ACTools.compareDate(self.startDate, _org.lock_date) != 1:
                raise exceptions.ValidationError('机构/主体:'+str(_org.name)+'的锁定日期为:' + str(
                    _org.lock_date)+",结转损益的开始日期为"+str(self.startDate)+",结转日期应晚于锁定日期,或请管理员修改锁定日期")
        self.t_entry = self.env['accountcore.entry']
        # 本年利润科目
        self.ben_nian_li_run_account = self.env['accountcore.special_accounts'].sudo().search([
            ('name', '=', '本年利润科目')]).accounts
        if self.ben_nian_li_run_account:
            self.ben_nian_li_run_account_id = self.ben_nian_li_run_account.id
        else:
            self.ben_nian_li_run_account_id = self.env.ref(
                'special_accounts_1')
        # 损益调整科目
        self.sun_yi_tiao_zhen_account = self.env['accountcore.special_accounts'].sudo().search([
            ('name', '=', '以前年度损益调整科目')]).accounts
        if self.sun_yi_tiao_zhen_account:
            self.sun_yi_tiao_zhen_account_id = self.sun_yi_tiao_zhen_account.id
        else:
            self.sun_yi_tiao_zhen_account_id = self.env.ref(
                'special_accounts_3')
        # 依次处理选种机构
        # 生成的凭证列表
        voucher_ids = []
        for org in self.orgs:
            # 依次处理会计期间
            for p in periods:
                voucher = self._do_currencyDown(org, p)
                if voucher:
                    voucher_ids.append(voucher.id)
        # 自动锁定到结转损益日期
        if self.auto_lock:
            self.orgs.sudo().write({"lock_date": periods[-1].endDate})
        return {'name': '自动生成的结转损益凭证',
                'view_mode': 'tree,form',
                'res_model': 'accountcore.voucher',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', voucher_ids)]
                }

    def _do_currencyDown(self, org, voucher_period):
        '''结转指定机构某会计期间的损益'''
        # 找出损益类相关科目
        accounts = self._get_sunyi_accounts(org)
        # 获得损益类相关科目在期间的余额
        accountsBalance = self._get_balances(org, voucher_period, accounts)
        # 根据余额生成结转损益的凭证
        voucher = self._creat_voucher(accountsBalance, org, voucher_period)
        return voucher

    def _get_sunyi_accounts(self, org):
        '''获得该机构的结转损益类科目'''
        # 属于损益类别的科目,但不包括"以前年度损益调整"
        accounts = self.env['accountcore.account'].sudo().search([('accountClass.name', '=', '损益类'),
                                                                  ('id', '!=',
                                                                   #    self.sun_yi_tiao_zhen_account.id),
                                                                   self.sun_yi_tiao_zhen_account_id),
                                                                  '|', ('org',
                                                                        '=', org.id),
                                                                  ('org', '=', False)])
        return accounts

    def _get_balances(self, org, vouhcer_period, accounts):
        '''获得某一机构在一个会计月份的余额记录'''
        accountsBalance = []
        for account in accounts:
            if not account.accountItemClass:
                balance = account.getBalanceOfVoucherPeriod(vouhcer_period,
                                                            org,
                                                            None)
                if balance:
                    accountsBalance.append(balance)
            else:
                items = account.getAllItemsInBalancesOf(org)
                if items:
                    for item in items:
                        balance = account.getBalanceOfVoucherPeriod(vouhcer_period,
                                                                    org,
                                                                    item)
                        if balance:
                            accountsBalance.append(balance)
        return accountsBalance

    def _creat_voucher(self, accountsBalance, org, voucer_period):
        '''新增结转损益凭证'''
        # 结转到本年利润的借方合计
        zero = Decimal.from_float(0).quantize(Decimal('0.00'))
        sum_d = Decimal.from_float(0).quantize(Decimal('0.00'))
        # 结转到本年利润的贷方合计
        sum_c = Decimal.from_float(0).quantize(Decimal('0.00'))
        entrys_value = []
        # 根据科目余额生成分录
        for b in accountsBalance:
            b_items_id = []
            if b.items.id:
                b_items_id = [b.items.id]
            endAmount = Decimal.from_float(b.endDamount).quantize(
                Decimal('0.00'))-Decimal.from_float(b.endCamount).quantize(Decimal('0.00'))
            if b.account.direction == '1':
                if endAmount != zero:
                    entrys_value.append({"explain": '结转损益',
                                         "account": b.account.id,
                                         "items": [(6, 0, b_items_id)],
                                         "camount": endAmount
                                         })
                    sum_d = sum_d + endAmount
            else:
                if endAmount != zero:
                    entrys_value.append({"explain": '结转损益',
                                         "account": b.account.id,
                                         "items": [(6, 0, b_items_id)],
                                         "damount": -endAmount
                                         })
                    sum_c = sum_c - endAmount
        # 本年利润科目分录
        # 结转到贷方
        if sum_d != zero:
            entrys_value.append({"explain": '结转损益',
                                 #  "account": self.ben_nian_li_run_account.id,
                                 "account": self.ben_nian_li_run_account_id,
                                 "damount": sum_d
                                 })
        # 结转到借方
        if sum_c != zero:
            entrys_value.append({"explain": '结转损益',
                                 #  "account": self.ben_nian_li_run_account.id,
                                 "account": self.ben_nian_li_run_account_id,
                                 "camount": sum_c
                                 })
        if len(entrys_value) < 2:
            return None
        # entrys = self.t_entry.sudo().create(entrys_value)
        entrys = []
        for e in entrys_value:
            entrys.append([0, '', e])
        voucher = self.env['accountcore.voucher'].sudo().create({
            'voucherdate': voucer_period.endDate,
            'org': org.id,
            'soucre': self.env.ref('accountcore.source_2').id,
            'ruleBook': [(6, 0, [self.env.ref('accountcore.rulebook_1').id])],
            # 'entrys': [(6, 0, entrys.ids)],
            'entrys': entrys,
            'createUser': self.env.uid,
        })
        return voucher

# 新增下级现金流量向导


class CreateChildCashoFlowWizard(models.TransientModel, Glob_tag_Model):
    '''新增下级现金流量的向导'''
    _name = 'accountcore.create_child_cashflow'
    _description = '新增下级现金流量向导'
    parent_id = fields.Many2one('accountcore.cashflow',
                                string='上级现金流量名称',
                                help='新增现金流量的直接上级科目')
    parent_number = fields.Char(related='parent_id.number',
                                string='上级现金流量编码')
    cashFlowType = fields.Many2one('accountcore.cashflowtype',
                                   string='现金流量类别',
                                   index=True,
                                   ondelete='restrict')
    number = fields.Char(string='现金流量编码', required=True)
    name = fields.Char(string='现金流量名称', required=True)
    direction = fields.Selection(
        [("-1", "流出"), ("1", "流入")], string='流量方向', required=True)
    sequence = fields.Integer(string="显示优先级", help="显示顺序", default=100)
    @api.model
    def default_get(self, field_names):
        default = super().default_get(field_names)
        parent_id = self.env.context.get('active_id')
        parent = self.env['accountcore.cashflow'].sudo().search(
            [['id', '=', parent_id]])
        default['parent_id'] = parent_id
        default['cashFlowType'] = parent.cashFlowType.id
        default['direction'] = parent.direction
        default['number'] = parent.number + \
            '.' + str(parent.currentChildNumber)
        return default

    @ACTools.refuse_role_search
    @api.model
    def create(self, values):
        parent_id = self.env.context.get('active_id')
        Table = self.env['accountcore.cashflow'].sudo()
        parent = Table.search(
            [['id', '=', parent_id]])
        newOne = {'parent_id': parent_id,
                  'cashFlowType': parent.cashFlowType.id,
                  'name':  parent.name+'---'+values['name'],
                  'number': parent.number + '.'
                  + str(parent.currentChildNumber),
                  'direction': parent.direction}
        parent.currentChildNumber = parent.currentChildNumber+1
        values.update(newOne)
        rl = super(CreateChildCashoFlowWizard, self).create(values)
        a = Table.create(values)
        # 添加到上级科目的直接下级
        parent.write({'childs_ids': [(4, a.id)]})
        return rl
        # 向导部分-结束
# 报表生成向导


class GetReport(models.TransientModel):
    "报表生成向导"
    _name = 'accountcore.get_report'
    _description = '报表生成向导'
    report_model = fields.Many2one('accountcore.report_model',
                                   string='报表模板')
    guid = fields.Char(related='report_model.guid')
    summary = fields.Text(related='report_model.summary')
    startDate = fields.Date(string='开始月份',
                            required=True,
                            default=lambda s: s.env.user.current_date)
    endDate = fields.Date(string='结束月份',
                          required=True,
                          default=lambda s: s.env.user.current_date)
    fast_period = fields.Date(string="选取期间", store=False)
    orgs = fields.Many2many('accountcore.org',
                            string='机构/主体范围',
                            default=lambda s: s.env.user.currentOrg,
                            required=True)

    def do(self):
        '''根据模板生成报表'''
        report = self.env['accountcore.report_model'].sudo().browse(
            self.report_model.id)
        report[0].startDate = self.startDate
        report[0].endDate = self.endDate
        report[0].orgs = self.orgs
        return {
            'name': "生成报表",
            'type': 'ir.actions.act_window',
            'res_model': 'accountcore.report_model',
            'view_mode': 'form',
            'views': [[self.env.ref('accountcore.accountcore_report_model_auto_form').id, 'form']],
            'target': 'main',
            'res_id': self.report_model.id,
            'context': {
                'form_view_initial_mode': 'edit',
            }
        }
# 设置报表模板公式向导


class ReportModelFormula(models.TransientModel):
    '''设置报表公式向导'''
    _name = 'accountcore.reportmodel_formula'
    _description = '设置报表公式向导'
    account_id = fields.Many2one('accountcore.account', string='会计科目')
    has_child = fields.Boolean(string='是否包含明细科目', default=True)
    item_ids = fields.Many2many('accountcore.item', string='作为明细科目的核算项目')
    account_amount_type = fields.Many2one('accountcore.account_amount_type',
                                          string='金额类型')
    formula = fields.Text(string='公式内容')
    btn_join_reduce = fields.Char()
    btn_join_add = fields.Char()
    btn_clear = fields.Char()
    btn_show_orgs = fields.Char(store=False)
    btn_start_date = fields.Char(store=False)
    btn_end_date = fields.Char(store=False)
    btn_between_date = fields.Char(store=False)
    @api.model
    def default_get(self, field_names):
        default = super().default_get(field_names)
        if self.env.context.get('ac'):
            default['formula'] = self.env.context.get('ac')
        return default

    @ACTools.refuse_role_search
    def do(self):
        '''公式填入单元格'''
        return {
            'type': 'ir.actions.client',
            'name': '',
            'tag': 'update_formula',
            'target': 'new',
            'context': {'ac_formula': self.formula}
        }

    @api.onchange('btn_join_reduce')
    def join_reduce(self):
        '''减进公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_join_reduce:
            return
        if not self.account_id.name:
            return {
                'warning': {
                    'message': "请选择会计科目",
                },
            }
        if not self.account_amount_type:
            return {
                'warning': {
                    'message': "请选择金额类型",
                },
            }
        items = ''
        for i in self.item_ids:
            items = items+i.name+'/'
        mark = "-"
        if not self.formula:
            self.formula = ""
        self.formula = (self.formula+mark+"account('"
                        + self.account_id.name
                        + "','"+str(self.has_child)
                        + "','"+self.account_amount_type.name
                        + "','"+items
                        + "')")

    @api.onchange('btn_join_add')
    def join_add(self):
        '''加进公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_join_add:
            return
        if not self.account_id.name:
            return {
                'warning': {
                    'message': "请选择会计科目",
                },
            }
        if not self.account_amount_type:
            return {
                'warning': {
                    'message': "请选择金额类型",
                },
            }
        items = ''
        for i in self.item_ids:
            items = items+i.name+'/'
        mark = ""
        if self.formula:
            mark = "+"
        else:
            self.formula = ""
        self.formula = (self.formula+mark+"account('"
                        + self.account_id.name
                        + "','"+str(self.has_child)
                        + "','"+self.account_amount_type.name
                        + "','"+items
                        + "')")

    @api.onchange('btn_clear')
    def join_clear(self):
        '''清除公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_clear:
            return
        self.formula = ""

    @api.onchange('btn_show_orgs')
    def join_show_orgs(self):
        '''填入取机构/主体名称的公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_show_orgs:
            return
        self.formula = "show_orgs()"

    @api.onchange('btn_start_date')
    def join_start_date(self):
        '''填入取数的开始日期'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_start_date:
            return
        self.formula = "startDate()"

    @api.onchange('btn_end_date')
    def join_end_date(self):
        '''填入取数的结束日期'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_end_date:
            return
        self.formula = "endDate()"

    @api.onchange('btn_between_date')
    def join_between_date(self):
        '''填入取数的期间'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_between_date:
            return
        self.formula = "betweenDate()"


class StoreReport(models.TransientModel):
    '''报表归档向导'''
    _name = 'accountcore.store_report'
    _description = '报表归档向导'
    number = fields.Char(string='归档报表编号')
    name = fields.Char(string='归档报表名称', required=True)
    create_user = fields.Many2one('res.users',
                                  string='归档人',
                                  default=lambda s: s.env.uid,
                                  readonly=True,
                                  required=True,
                                  ondelete='restrict',
                                  index=True)
    start_date = fields.Date(string='数据开始月份')
    end_date = fields.Date(string='数据结束月份')
    orgs = fields.Many2many('accountcore.org', string='机构/主体范围', required=True)
    receivers = fields.Many2many('accountcore.receiver', string='接收者(报送对象)')
    summary = fields.Text(string='归档报表说明')
    htmlstr = fields.Html(string='html内容')
    @ACTools.refuse_role_search
    def do(self):
        reportModelId = self._context["model_id"]
        reportModel = self.env['accountcore.report_model'].sudo().browse([
            reportModelId])[0]
        orgIds = [org.id for org in reportModel.orgs]
        receiversIds = [r.id for r in self.receivers]
        onlydata = self._context["onlydata"]
        data_style = self._context["data_style"]
        merge_info = self._context["merge_info"]
        width_info = self._context["width_info"]
        height_info = self._context["height_info"]
        comments_info = self._context["comments_info"]
        meta_info = self._context["meta_info"]
        header_info = self._context["header_info"]
        self.env['accountcore.storage_report'].sudo().create([{
            "report_type": reportModel.report_type.id,
            "receivers":  [(6, 0, receiversIds)],
            "endDate": reportModel.endDate,
            "startDate": reportModel.startDate,
            "summary": self.summary,
            "data": onlydata,
            "onlydata": onlydata,
            "data_style":data_style,
            "width_info":width_info,
            "height_info":height_info,
            "header_info":header_info,
            "comments_info":comments_info,
            "merge_info":merge_info,
            "meta_info":meta_info,
            "number": self.number,
            "name": self.name,
            "create_user": self.env.uid,
            "orgs":  [(6, 0, orgIds)],
        }])


# 设置报表现金流量公式向导


class ReportCashFlowFormula(models.TransientModel):
    '''设置报表现金流量公式向导'''
    _name = 'accountcore.report_cashflow_formula'
    _description = '设置报表现金流量公式向导'
    cashflow_id = fields.Many2one('accountcore.cashflow', string='现金流量项目')
    has_child = fields.Boolean(string='是否包含明细', default=True)
    formula = fields.Text(string='公式内容')
    btn_join_reduce = fields.Char()
    btn_join_add = fields.Char()
    btn_clear = fields.Char()
    btn_show_orgs = fields.Char(store=False)
    btn_start_date = fields.Char(store=False)
    btn_end_date = fields.Char(store=False)
    btn_between_date = fields.Char(store=False)
    @api.model
    def default_get(self, field_names):
        default = super().default_get(field_names)
        if self.env.context.get('ac'):
            default['formula'] = self.env.context.get('ac')
        return default

    @ACTools.refuse_role_search
    def do(self):
        '''公式填入单元格'''
        return {
            'type': 'ir.actions.client',
            'name': '',
            'tag': 'update_formula',
            'target': 'new',
            'context': {'ac_formula': self.formula}
        }

    @api.onchange('btn_join_reduce')
    def join_reduce(self):
        '''减进公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_join_reduce:
            return
        if not self.cashflow_id.name:
            return {
                'warning': {
                    'message': "请选择现金流量项目",
                },
            }
        mark = "-"
        if not self.formula:
            self.formula = ""
        self.formula = (self.formula+mark+"cashflow('"
                        + self.cashflow_id.name
                        + "','"+str(self.has_child)
                        + "')")

    @api.onchange('btn_join_add')
    def join_add(self):
        '''加进公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_join_add:
            return
        if not self.cashflow_id.name:
            return {
                'warning': {
                    'message': "请选择现金流量项目",
                },
            }
        mark = ""
        if self.formula:
            mark = "+"
        else:
            self.formula = ""
        self.formula = (self.formula+mark+"cashflow('"
                        + self.cashflow_id.name
                        + "','"+str(self.has_child)
                        + "')")

    @api.onchange('btn_clear')
    def join_clear(self):
        '''清除公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_clear:
            return
        self.formula = ""

    @api.onchange('btn_show_orgs')
    def join_show_orgs(self):
        '''填入取机构/主体名称的公式'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_show_orgs:
            return
        self.formula = "show_orgs()"

    @api.onchange('btn_start_date')
    def join_start_date(self):
        '''填入取数的开始日期'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_start_date:
            return
        self.formula = "startDate()"

    @api.onchange('btn_end_date')
    def join_end_date(self):
        '''填入取数的结束日期'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_end_date:
            return
        self.formula = "endDate()"

    @api.onchange('btn_between_date')
    def join_between_date(self):
        '''填入取数的期间'''
        # 窗口弹出时不执行，直接返回
        if not self.btn_between_date:
            return
        self.formula = "betweenDate()"
