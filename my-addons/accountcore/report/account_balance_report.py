# -*- coding: utf-8 -*-
import copy
import datetime
import decimal
from decimal import Decimal
import json
import time
from odoo import http
from odoo import exceptions
from odoo import models, fields, api
import sys
sys.path.append('.\\.\\server')
# 查询科目余额表


class AccountBalanceReport(models.AbstractModel):
    '''科目余额表'''
    _name = 'report.accountcore.account_balance_report'
    _description = '科目余额表查询报表'
    @api.model
    def _get_report_values(self, docids, data=None):
        # if 是在月列表选择（例如启用期初）
        lines = docids
        if lines:
            lines = self.env['accountcore.accounts_balance'].sudo().browse(
                docids)
            return {'lines': lines}
        form = data['form']
        # 获取查询向导的表单数据
        noShowNoAmount = form['noShowNoAmount']
        noShowZeroBalance = form['noShowZeroBalance']
        no_show_no_hanppend = form['no_show_no_hanppend']
        onlyShowOneLevel = form['onlyShowOneLevel']
        includeAccountItems = form['includeAccountItems']
        order_orgs = form['order_orgs']
        sum_orgs = form['sum_orgs']
        account_ids = form['account']
        org_id = form['orgs']
        data['orgs_count'] = len(org_id)
        orgs = self.env['accountcore.org'].sudo().browse(org_id)
        # 多机构/主体合并显示名称
        data['sum_orgs_name'] = "+".join(orgs.mapped('name'))
        data['sum_orgids'] = org_id
        startDate = datetime.datetime.strptime(form['startDate'],
                                               '%Y-%m-%d')
        start_year = startDate.year
        start_month = startDate.month
        endDate = datetime.datetime.strptime(form['endDate'],
                                             '%Y-%m-%d')
        end_year = endDate.year
        end_month = endDate.month
        # 构建查询数据库的参数
        params = (start_year,
                  start_month,
                  end_year,
                  end_month,
                  tuple(org_id))
        # 科目在查询期间的余额记录(accouncore_accounts_balance表)
        # 例如:现金科目在2019年7月份使用过,就会在accountcore_accounts_balance表中
        # 生成且仅生成一条记录.该记录记录了现金科目在当月的期初余额,借贷方发生额等信息
        # 详细请看数据库的表结构
        DandCAmounts = self._getDAndCAmount(params)
        params_befor_start = (start_year,
                              start_year,
                              start_month,
                              tuple(org_id))
        # 用来存储余额记录的容器对象
        balances = Balances()
        temp_accountId = ""
        temp_itemId = ""
        temp_orgId = ""
        # 科目在查询期间以前的余额记录,按机构,科目,项目和年月进行了排序
        recordsBeforSart = self._getRecordsBeforStart(params_befor_start)
        is_begining = False
        for record in recordsBeforSart:
            # if 已经对开始期间以前的最近一条相同科目和核算项目的记录取了数,就跳到下一个record(
            # 也就是取到了查询期间离期初最近的那一条余额记录,如果存在,这条记录的期初就是该科目在
            # 查询期间的期初)
            if (record['org_id'] == temp_orgId
                and record['account_id'] == temp_accountId
                    and record['item_id'] == temp_itemId):
                # 判断是否在查询开始期间之前,是之前不能取启用期初那条
                if is_begining:
                    if record['year'] < start_year or record['year'] == start_year and record['month'] < start_month:
                        balances.del_(record)
                else:
                    continue
            temp_orgId = record['org_id']
            temp_accountId = record['account_id']
            temp_itemId = record['item_id']
            is_begining = record['isbegining']
            # if 余额明细容器中已经存在，就跳到下一个record
            if balances.exit(temp_orgId,
                             temp_accountId,
                             temp_itemId):
                continue
            # 构建添加到余额容器balances的一条余额对象
            balance = Balance(temp_orgId,
                              temp_accountId,
                              temp_itemId)
            # 添加期初借贷方余额等
            if record['year'] == start_year and record['month'] == start_month:
                balance.beginingDamount = Decimal.from_float(
                    record['beginingDamount']).quantize(Decimal('0.00'))
                balance.beginingCamount = Decimal.from_float(
                    record['beginingCamount']).quantize(Decimal('0.00'))
            elif record['year'] < start_year or record['year'] == start_year and record['month'] < start_month:
                balance.beginingDamount = Decimal.from_float(
                    record['endDamount']).quantize(Decimal('0.00'))
                balance.beginingCamount = Decimal.from_float(
                    record['endCamount']).quantize(Decimal('0.00'))
            else:
                balance.beginingDamount = Decimal.from_float(
                    record['endDamount']).quantize(Decimal('0.00'))
                balance.beginingCamount = Decimal.from_float(
                    record['endCamount']).quantize(Decimal('0.00'))
            balance.item_class_name = record['item_class_name']
            balance.item_id = record['item_id']
            balance.item_name = record['item_name']
            balance.org_name = record['org_name']
            # if 在查询期间范围内有该科目和核算项目的借贷方发生额记录（若范围内没有发生额，则不会生成记录）
            balance_DAndCAmount = None
            for one in DandCAmounts:
                if (one['org_id'] == balance.org_id
                    and one['account_id'] == balance.account_id
                        and one['item_id'] == balance.item_id):
                    balance_DAndCAmount = one
                    break
            if balance_DAndCAmount:
                # 添加查询期间的借贷方发生额
                balance.damount = Decimal.from_float(
                    balance_DAndCAmount['damount']).quantize(Decimal('0.00'))
                balance.camount = Decimal.from_float(
                    balance_DAndCAmount['camount']).quantize(Decimal('0.00'))
                balance.item_class_name = balance_DAndCAmount['item_class_name']
                balance.item_id = balance_DAndCAmount['item_id']
                balance.item_name = balance_DAndCAmount['item_name']
                balance.org_name = balance_DAndCAmount['org_name']
                balance_DAndCAmount['havepre'] = True
            balances.add(balance)
            continue
        # 添加查询期间有发生额，但查询期间之前没有余额记录的相关科目记录,这时期初为0?
        for one in DandCAmounts:
            if one['havepre'] == False:
                balance_current = Balance(one['org_id'],
                                          one['account_id'],
                                          one['item_id'])
                balance_current.beginingDamount = 0
                balance_current.beginingCamount = 0
                balance_current.damount = Decimal.from_float(
                    one['damount']).quantize(Decimal('0.00'))
                balance_current.camount = Decimal.from_float(
                    one['camount']).quantize(Decimal('0.00'))
                balance_current.item_class_name = one['item_class_name']
                balance_current.item_id = one['item_id']
                balance_current.item_name = one['item_name']
                balance_current.org_name = one['org_name']
                balances.add(balance_current)
        balancesList = balances.getBalancesList()
        # 从数据库获得科目表的各科目列表
        accountsArch = self._getAccountAcrch()
        # 科目余额管理器（构建科目余额表）
        # 一个机构一个科目列表结构，后面用余额记录来更新这个列表结构
        accountsArchManager = AccountsArchManager(accountsArch, orgs)
        # 用每一条余额记录来更新科目列表结构
        for balance in balancesList:
            accountArch = accountsArchManager.updateBy(balance)
            # 处理带有核算项目的余额记录
            if balance.item_id:
                accountsArchManager.appendItem(accountArch, balance)
        # 余额记录管理器根据向导选择的各种过滤条件进行筛选
        accountsArchWithItems = accountsArchManager.getAccountArchWihtItems(
            AccountsArch_filter_org(org_id),
            AccountsArch_filter_accounts(account_ids),
            AccountsArch_filter_noShowNoAmount(noShowNoAmount),
            AccountsArch_filter_noShowZeroBalance(noShowZeroBalance),
            AccountsArch_filter_no_show_no_hanppend(no_show_no_hanppend),
            AccountsArch_filter_onlyShowOneLevel(onlyShowOneLevel),
            AccountsArch_filter_includeAccountItems(includeAccountItems),
            AccountsArch_filter_order_orgs(order_orgs),
            AccountsArch_filter_sum_orgs(sum_orgs))
        return {'lines': lines,
                'docs': accountsArchWithItems,
                'data': data}

    def _getRecordsBeforStart(self, params):
        '''获得查询日期前的余额记录,已经按科目项目年份月份进行排序，方便取查询期间范围前的最近一期的余额记录'''
        query = ''' SELECT
                        year,
                        month,
                        org_id,
                        t_org.name as org_name,
                        account_id,
                        t_item.item_class_name,
                        item_id,
                        t_item.name as item_name,
                        "beginingDamount",
                        "beginingCamount",
                        "endDamount",
                        "endCamount",
                        isbegining
                    FROM
                        (SELECT
                            year,
                            month,
                            org as org_id,
                            account as account_id,
                            items as item_id,
                            "beginingDamount",
                            "beginingCamount",
                            "endDamount",
                            "endCamount",
                            isbegining
                        FROM
                            accountcore_accounts_balance
                        WHERE
                            (year < %s
                            OR
                            year =%s AND month <= %s)
                            AND
                            org in %s) as t_accounts_balance
                    LEFT OUTER JOIN accountcore_item as t_item
                    ON t_accounts_balance.item_id=t_item.id
                    LEFT OUTER JOIN accountcore_org as t_org
                    ON t_accounts_balance.org_id=t_org.id
                    ORDER BY  org_id,
                              account_id,
                              item_id,
                              year desc ,
                              month desc,
                              isbegining desc'''
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _getDAndCAmount(self, params):
        '''在查找期间的发生额'''
        # 当期借贷方发生额合计
        query = '''SELECT
                        org_id,
                        t_org.name as org_name,
                        account_id,
                        t_item.item_class_name,
                        item_id,
                        t_item.name as item_name,
                        damount,
                        camount,
                        havepre
                    FROM
                        (SELECT
                            org as org_id,
                            account as account_id,
                            items as item_id ,
                            sum(damount) as damount,
                            sum(camount)as camount,
                            False as havepre
                        FROM
                            accountcore_accounts_balance
                        WHERE
                            year*12+month >= %s*12+%s AND year*12+month<=%s*12+%s
                            AND
                            org in %s
                         GROUP BY org_id,account_id,item_id) AS t_accounts_balance
                    LEFT OUTER JOIN accountcore_item as t_item
                    ON t_accounts_balance.item_id=t_item.id
                    LEFT OUTER JOIN accountcore_org as t_org
                    ON t_accounts_balance.org_id=t_org.id
                    ORDER BY org_id,account_id,item_id'''
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _getAccountAcrch(self):
        '''获得科目表结构对象'''
        query = '''SELECT 
                    null as org_id,
                    '' as org_name,
                    t_account."fatherAccountId" as account_father_id,
                    t_account_class.name as account_class_name,
                    t_account.id as account_id,
                    t_account.number as account_number,
                    t_account.name as account_name,
                    t_account.direction as direction,
                    t_account.is_last as is_last,
                    null as is_virtual,
                    CAST(0 as numeric) as "beginingDamount",
                    CAST(0 as numeric)  as "beginingCamount",
                    CAST(0 as numeric)  as damount,
                    CAST(0 as numeric)  as camount
                FROM accountcore_account AS t_account
                LEFT OUTER JOIN accountcore_accountClass as t_account_class
                ON t_account."accountClass"=t_account_class.id
                ORDER BY account_number'''
        self.env.cr.execute(query)
        rl = self.env.cr.dictfetchall()
        virtual_accounts = []
        for x in rl:
            x['beginingDamount'] = Decimal(0)
            x['beginingCamount'] = Decimal(0)
            x['damount'] = Decimal(0)
            x['camount'] = Decimal(0)
            if not x['is_last']:
                virtualAccount = x.copy()
                virtualAccount['account_father_id'] = x['account_id']
                virtualAccount['is_virtual'] = True
                virtualAccount['is_last'] = True
                virtualAccount['account_name'] = x['account_name']+"▲"
                virtual_accounts.append(virtualAccount)
        return rl+virtual_accounts
# 一条余额记录


class Balance(object):
    '''一条余额记录'''
    __slots__ = ['org_id',
                 'org_name',
                 'account_father_id',
                 'account_id',
                 'account_number',
                 'account_name',
                 'item_class_name',
                 'item_id',
                 'item_number',
                 'item_name',
                 'beginingDamount',
                 'beginingCamount',
                 'damount',
                 'camount',
                 'org_account_item'
                 ]

    def __init__(self, org_id, account_id, item_id):
        self.org_id = org_id
        self.org_name = ""
        self.account_father_id = ""
        self.account_id = account_id
        self.account_number = ""
        self.account_name = ""
        self.item_class_name = ""
        self.item_id = item_id
        self.item_number = ""
        self.item_name = ""
        self.beginingDamount = 0
        self.beginingCamount = 0
        self.damount = 0
        self.camount = 0
        self.org_account_item = str(org_id)+"." \
            + str(account_id)+"-" \
            + str(item_id)

    def keys(self):
        return ('org_id',
                'org_name',
                'item_class_name',
                'item_id',
                'item_number',
                'item_name',
                'beginingDamount',
                'beginingCamount',
                'damount',
                'camount',
                )

    def __getitem__(self, item):
        return getattr(self, item)
# 余额记录的明细容器


class Balances(object):
    '''余额记录的明细容器'''

    def __init__(self):
        self.org_account_items = {}

    def add(self, balance):
        '''添加一行余额记录'''
        mark = str(balance.org_id)+'.' \
            + str(balance.account_id) + "-" \
            + str(balance.item_id)
        self.org_account_items.update({mark: balance})

    def exit(self, org_id, account_id, item_id):
        '''存在相同科目和和核算项目的余额'''
        org_account_item = str(org_id)+"." \
            + str(account_id)+"-" \
            + str(item_id)
        if org_account_item in self.org_account_items:
            return True
        return False

    def getBalancesList(self):
        '''获得balance的列表形式'''
        return self.org_account_items.values()

    def del_(self, balance):
        '''删除'''
        mark = str(balance['org_id'])+'.' \
            + str(balance['account_id']) + "-" \
            + str(balance['item_id'])
        del self.org_account_items[mark]

# 科目余额管理器


class AccountsArchManager(object):
    '''科目余额管理器'''

    def __init__(self, accountsArch, orgs):
        self.accountsArch = []
        self.accountsArch_items = []
        # 一个机构/主体一个科目列表
        for org in orgs:
            newAccountsArch = []
            for account in accountsArch:
                newAccount = account.copy()
                newAccount.update(
                    {'org_id': org.id,
                     'org_name': org.name})
                newAccountsArch.append(newAccount)
            self.accountsArch.extend(newAccountsArch)

    def updateBy(self, balance):
        # 在科目列表中找出该科目
        accountArch = self._getAccountArchById(balance.account_id,
                                               balance.org_id)
        # 更新各种金额
        accountArch.addAmount(balance.beginingDamount,
                              balance.beginingCamount,
                              balance.damount,
                              balance.camount)
        # if有上级科目，下级科目金额合并到上级科目,好像可以删除
        # if accountArch.father_id:
        #     fatherAccount = self._getFatherAccountById(accountArch.father_id,
        #                                                balance.org_id)
        fathId = accountArch.father_id
        while fathId:
            fatherAccount = self._getFatherAccountById(fathId,
                                                       balance.org_id)
            fatherAccount.addAmount(balance.beginingDamount,
                                    balance.beginingCamount,
                                    balance.damount,
                                    balance.camount)
            fathId = fatherAccount.father_id
        return accountArch

    def _getAccountArchById(self, account_id, org_id):
        for line in self.accountsArch:
            if (line['account_id'] == account_id
                    and line['org_id'] == org_id and line['is_last'] == True):
                return AccountArch(line)

    def _getFatherAccountById(self, account_id, org_id):
        for line in self.accountsArch:
            if (line['account_id'] == account_id
                    and line['org_id'] == org_id and line['is_last'] == False):
                return AccountArch(line)

    def appendItem(self, accountArch, balance):
        '''添加带有核算项目的余额记录'''
        accountArch_ = accountArch.do_copy()
        accountArch_.update(balance)
        self.accountsArch_items.append(accountArch_.account)

    def getAccountArchWihtItems(self, *filters):
        '''返回经过过滤排序后的科目余额记录'''
        # 追加带有核算项目的余额记录
        self.accountsArch.extend(self.accountsArch_items)
        self.sortBy('account_number')
        for filter in filters:
            self.accountsArch = filter(self.accountsArch)
        return self.accountsArch

    def sortBy(self, field_str, reverse_it=False):
        '''根据某字段排序'''
        return self.accountsArch.sort(key=lambda t: t['account_number'],
                                      reverse=reverse_it)
# 科目余额管理器管理对象


class AccountArch(object):
    '''科目余额管理器管理对象'''

    def __init__(self, account):
        self.account = account
        self.account_id = account['account_id']
        self.father_id = account['account_father_id']

    def addAmount(self,
                  beginingDamount,
                  beginingCamount,
                  damount,
                  camount):
        self.account['beginingDamount'] = (self.account['beginingDamount']
                                           + beginingDamount)
        self.account['beginingCamount'] = (self.account['beginingCamount']
                                           + beginingCamount)
        self.account['damount'] = self.account['damount']+damount
        self.account['camount'] = self.account['camount']+camount
        return self

    def do_copy(self):
        newAccount = self.account.copy()
        newAccountArch = AccountArch(newAccount)
        return newAccountArch

    def update(self, balance):
        self.account.update(dict(balance))
# 筛选定义-开始
# 筛选机构


class AccountsArch_filter_org(object):
    '''筛选机构'''

    def __init__(self, org_ids):
        self.__org_ids = org_ids

    def __call__(self, accountsArch):
        newAccountsArch = [a for a in accountsArch
                           if a['org_id'] in self.__org_ids]
        return newAccountsArch
# 筛选科目


class AccountsArch_filter_accounts(object):
    '''筛选科目'''

    def __init__(self, account_ids):
        self.__account_ids = account_ids

    def __call__(self, accountsArch):
        newAccountsArch = [a for a in accountsArch
                           if a['account_id'] in self.__account_ids]
        return newAccountsArch
# 无金额不显示


class AccountsArch_filter_noShowNoAmount(object):
    '''无金额不显示'''

    def __init__(self, noShowNoAmount=True):
        self.__noShowNoAmount = noShowNoAmount

    def __call__(self, accountsArch):
        if self.__noShowNoAmount:
            newAccountsArch = [a for a in accountsArch
                               if any([(a['beginingDamount']-a['beginingCamount']) != 0,
                                       a['damount'] != 0,
                                       a['camount'] != 0])]
            return newAccountsArch
        else:
            return accountsArch
# 余额为零不显示


class AccountsArch_filter_noShowZeroBalance(object):
    '''余额为零不显示'''

    def __init__(self, noShowZeroBalance=True):
        self.__noShowZeroBalance = noShowZeroBalance

    def __call__(self, accountsArch):
        if self.__noShowZeroBalance:
            newAccountsArch = [a for a in accountsArch
                               if (a['beginingDamount']
                                   + a['damount']
                                   - a['beginingCamount']
                                   - a['camount'] != 0)]
            return newAccountsArch
        else:
            return accountsArch
# 不显示无发生额的科目


class AccountsArch_filter_no_show_no_hanppend(object):
    '''不显示无发生额的科目'''

    def __init__(self, no_show_no_hanppend=False):
        self.__no_show_no_hanppend = no_show_no_hanppend

    def __call__(self, accountsArch):
        if self.__no_show_no_hanppend:
            newAccountsArch = [a for a in accountsArch
                               if a['damount'] != 0
                               or a['camount'] != 0]
            return newAccountsArch
        else:
            return accountsArch
# 只显示一级科目


class AccountsArch_filter_onlyShowOneLevel(object):
    '''只显示一级科目'''

    def __init__(self, onlyShowOneLevel=False):
        self.__onlyShowOneLevel = onlyShowOneLevel

    def __call__(self, accountsArch):
        if self.__onlyShowOneLevel:
            newAccountsArch = [a for a in accountsArch
                               if not a['account_father_id']
                               and('item_id' not in a
                                   or not a['item_id'])]
            return newAccountsArch
        else:
            return accountsArch
# 不显示核算项目


class AccountsArch_filter_includeAccountItems(object):
    '''不显示核算项目'''

    def __init__(self, includeAccountItems=True):
        self.__includeAccountItems = includeAccountItems

    def __call__(self, accountsArch):
        if self.__includeAccountItems:
            return accountsArch
        else:
            newAccountsArch = [a for a in accountsArch
                               if ('item_id' not in a
                                   or not a['item_id'])]
            return newAccountsArch
# 多机构/主体分开显示


class AccountsArch_filter_order_orgs(object):
    '''多机构/主体分开显示'''

    def __init__(self, order_orgs=True):
        self.__order_orgs = order_orgs

    def __call__(self, accountsArch):
        if self.__order_orgs:
            accountsArch.sort(key=lambda t: (t['org_id'],
                                             t['account_number']))
            return accountsArch
        else:
            return accountsArch
# 多机构/主体合并显示


class AccountsArch_filter_sum_orgs(object):
    '''多机构/主体合并显示'''

    def __init__(self, sum_orgs=False):
        self.__sum_orgs = sum_orgs

    def __call__(self, accountsArch):
        if not self.__sum_orgs:
            return accountsArch
        else:
            accountsArch.sort(key=lambda t: (
                t['account_number'], t['account_name'], t.setdefault('item_id', 0)))
            newAccountsArch = []
            a_temp = ""
            for a in accountsArch:
                add = False
                if a_temp == "":
                    add = True
                elif a_temp['account_name'] != a['account_name']:
                    add = True
                elif a_temp['account_name'] == a['account_name']:
                    # 存在核算项目
                    if a_temp['item_id'] != 0:
                        if a['item_id'] != a_temp['item_id']:
                            add = True
                    # 不存在核算项目
                    else:
                        if a['item_id'] != 0:
                            add = True
                if add:
                    a_temp = a.copy()
                    a_temp['org_id'] = 0
                    a_temp['org_name'] = ''
                    newAccountsArch.append(a_temp)
                else:
                    a_temp['beginingDamount'] += a['beginingDamount']
                    a_temp['beginingCamount'] += a['beginingCamount']
                    a_temp['damount'] += a['damount']
                    a_temp['camount'] += a['camount']
            return newAccountsArch
# 筛选定义-结束
