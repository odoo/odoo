# -*- coding: utf-8 -*-
# editor:huang tiger ###### Sun Jul 14 17:16:10 CST 2019
import copy
import datetime
import decimal
import json
import re
import time
from odoo import exceptions
from odoo import models, fields, api
from odoo import http
from ..models.ac_obj import ACTools
from ..models.ac_period import Period
import sys
sys.path.append('.\\.\\server')


# 查询明细账
class SubsidiaryBook(models.AbstractModel):
    '''查询明细账'''
    _name = 'report.accountcore.subsidiary_book_report'
    _description = '明细账查询报表'
    @api.model
    def _get_report_values(self, docids, data=None):
        form = data['form']
        org_id = form['orgs']
        orgs = self.env['accountcore.org'].sudo().browse(org_id)
        # 多机构/主体合并显示名称
        data['sum_orgs_name'] = "+".join(orgs.mapped('name'))
        data['sum_orgids'] = org_id
        # 获取查询向导的表单输入
        # 查询的会计期间
        period = Period(form['startDate'],
                        form['endDate'])
        org_ids = form['orgs']
        account_ids = form['account']
        # 存放每个科目明细账的容器
        multi_entrys = []
        # 对每一个科目生成明细账
        for account_id in account_ids:
            item = form['item']
            # 向导中选择的科目
            main_account = self.env['accountcore.account'].sudo().search(
                [('id', '=', account_id)])
            # 获得查询科目及其全部明细科目的ID列表,通过科目编号查找
            searchAccount = [account_id]
            if not form['only_this_level']:
                searchAccount = main_account.getMeAndChild_ids()
            # 依据是否在查询向导中选择了核算项目,构建不同的查询参数,从数据库取出明细
            # if选择了核算项目
            if item:
                item_id = form['item'][0]
                # 用于获得分录明细
                params = (period.start_year,
                          1,
                          period.end_year,
                        #   period.end_month,
                          12,
                          tuple(org_ids),
                          tuple(searchAccount),
                          item_id)
                # 从数据库获得需要的分录明细
                # 用于查询期初余额
                params2 = (period.start_year,
                           tuple(org_ids),
                           tuple(searchAccount),
                           item_id)
            # 没有选择核算项目
            else:
                params = (period.start_year,
                          1,
                          period.end_year,
                        #   period.end_month,
                          12,
                          tuple(org_ids),
                          tuple(searchAccount))
                params2 = (period.start_year,
                           tuple(org_ids),
                           tuple(searchAccount))
            # 从获得查询期间的分录明细
            entrys = self._getEntrys(params)
            # 科目在查询期间的全部分录明细,从开始日期的年初开始
            entryArchs = self.build_entryArchs(entrys)
            # 科目在查询期间的余额表记录
            beginingOfYearBalance = self._getBeginingOfYearBalance(params2)
            beginBlances = self._getBeginBalances(params)
            entrys = EntrysAssembler(main_account,
                                     item,
                                     period,
                                     beginingOfYearBalance,
                                     beginBlances,
                                     entryArchs,
                                     )
            multi_entrys.append(entrys)
            data["period"] = period 
        return {'doc_ids': docids,
                'docs': multi_entrys,
                'data': data}

    def _getBeginingOfYearBalance(self, params):
        '''获得查询范围的年初余额'''
        len_parmas = len(params)
        # 在向导中没有选择核算项目
        if len_parmas == 3:
            query = ''' SELECT
                            year,
                            month,
                            org as org_id,
                            account as account_id,
                            items as item_id,
                            "endDamount",
                            "endCamount",
                            isbegining
                        FROM
                            accountcore_accounts_balance
                        WHERE
                            (year <= %s-1)
                            AND org in %s
                            AND account in %s
                        ORDER BY  org_id,
                                  account_id,
                                  item_id,
                                  year desc,
                                  month desc,
                                  isbegining asc'''
        # elif 在向导中选择了核算项目
        elif len_parmas == 4:
            query = ''' SELECT
                            year,
                            month,
                            org as org_id,
                            account as account_id,
                            items as item_id,
                            "endDamount",
                            "endCamount",
                            isbegining
                        FROM
                            accountcore_accounts_balance
                        WHERE
                            (year <= %s-1)
                            AND org in %s
                            AND account in %s
                            AND items = %s
                        ORDER BY  org_id,
                                  account_id,
                                  item_id,
                                  year desc,
                                  month desc,
                                  isbegining asc'''
        else:
            raise exceptions.ValidationError('查询参数数量错误!')

        self.env.cr.execute(query, params)
        records = self.env.cr.dictfetchall()
        temp_accountId = ""
        temp_itemId = ""
        temp_orgId = ""
        # 期初借方余额列表
        d = []
        # 期初贷方余额列表
        c = []
        for record in records:
            # if 已经对开始期间以前的最近一条相同科目和核算项目的记录取了数,就跳到下一个record(
            # 也就是取到了查询期间离期初最近的那一条余额记录,如果存在,这条记录的期初就是该科目在
            # 查询期间的期初)
            if (record['org_id'] == temp_orgId
                and record['account_id'] == temp_accountId
                    and record['item_id'] == temp_itemId):
                continue
            else:
                d.append(record['endDamount'])
                c.append(record['endCamount'])
                temp_orgId = record['org_id']
                temp_accountId = record['account_id']
                temp_itemId = record['item_id']
        # 求和,得出年初余额
        return (sum(d), sum(c))

    def _getBeginBalances(self, params):
        '''获得查询期间的出现的启用期初余额记录'''
        len_parmas = len(params)
        if len_parmas == 6:
            query = ''' SELECT
                            year,
                            month,
                            sum("beginingDamount") as begin_d,
                            sum("beginingCamount") as begin_c,
                            sum(damount) as damount,
                            sum(camount) as camount,
                            sum("cumulativeDamount") as cumulative_d,
                            sum("cumulativeCamount") as cumulative_c
                        FROM
                            accountcore_accounts_balance
                        WHERE
                            year*12+month >= %s*12+%s
                            AND year*12+month<=%s*12+%s
                            AND org in %s
                            AND account in %s
                            AND isbegining = True
                        GROUP BY year, month'''
        elif len_parmas == 7:
            query = ''' SELECT
                            year,
                            month,
                            sum("beginingDamount") as begin_d,
                            sum("beginingCamount") as begin_c,
                            sum(damount) as damount,
                            sum(camount) as camount,
                            sum("cumulativeDamount") as cumulative_d,
                            sum("cumulativeCamount") as cumulative_c
                        FROM
                            accountcore_accounts_balance
                        WHERE
                            year*12+month >= %s*12+%s
                            AND year*12+month<=%s*12+%s
                            AND org in %s
                            AND account in %s
                            AND items = %s
                            AND isbegining =True
                        GROUP BY year, month '''
        else:
            raise exceptions.ValidationError('查询参数数量错误!')

        self.env.cr.execute(query, params)
        beginRecords = self.env.cr.dictfetchall()
        return beginRecords

    def build_entryArchs(self, entrys):
        '''构建明细记录'''
        # 选择的凭证编号策略
        # 对数据库取得的明细数据转化为对象列表
        entryArchs = []
        for entry in entrys:
            entry_arch = EntryArch()
            entry_arch.voucher_id = entry['voucher_id']
            entry_arch.org_id = entry['org_id']
            entry_arch.voucherdate = entry['voucherdate']
            entry_arch.year = entry['year']
            entry_arch.month = entry['month']
            entry_arch.org_name = entry['org_name']
            entry_arch.v_number = entry['v_number']
            entry_arch.uniqueNumber = entry['uniqueNumber']
            entry_arch.roolbook_html = entry['roolbook_html']
            entry_arch.explain = entry['explain']
            entry_arch.account_number = entry['account_number']
            entry_arch.account_name = entry['account_name']
            entry_arch.damount = entry['damount']
            entry_arch.camount = entry['camount']
            entry_arch.items_html = re.sub(
                r'<br>|<p>|</p>', '', entry['items_html'])
            entry_arch.direction = entry['direction']
            entry_arch.cash_flow = entry['cash_flow']
            entry_arch.need_check = False
            entryArchs.append(entry_arch)
        return entryArchs

    def _getEntrys(self, params):
        '''构建没有选择核算项目的查询语句并执行'''
        len_parmas = len(params)
        if len_parmas == 6:
            query = '''SELECT
                    t_voucher.id as voucher_id,
                    voucherdate,
                    t_voucher.year as year,
                    t_voucher.month as month,
                    t_voucher.v_number as v_number,
                    "uniqueNumber",
                    t_voucher.roolbook_html as roolbook_html,
                    t_org.id as org_id,
                    t_org.name as org_name,
                    t_entry.explain as explain,
                    t_account.number as account_number,
                    t_account.name as account_name,
                    t_entry.items_html as items_html,
                    t_entry.damount as damount,
                    t_entry.camount as camount,
                    t_account.direction as direction,
                    t_cashflow.name as cash_flow
                FROM accountcore_voucher as t_voucher
                LEFT OUTER JOIN accountcore_entry as t_entry on t_voucher.id=t_entry.voucher
                LEFT OUTER JOIN accountcore_account as t_account on t_entry.account=t_account.id
                LEFT OUTER JOIN accountcore_org as t_org on t_voucher.org=t_org.id
                LEFT OUTER JOIN accountcore_cashflow as t_cashflow on t_entry."cashFlow"=t_cashflow.id
                WHERE
                     year*12+month >= %s*12+%s
                     AND year*12+month<=%s*12+%s
                     AND t_voucher.org in %s
                     AND t_entry.account in %s
                ORDER BY voucherdate,org_name,account_number,t_voucher.v_number
                '''
        elif len_parmas == 7:
            query = '''SELECT
                    t_voucher.id as voucher_id,
                    voucherdate,
                    t_voucher.year as year,
                    t_voucher.month as month,
                    t_voucher.v_number as v_number,
                    "uniqueNumber",
                    t_voucher.roolbook_html as roolbook_html,
                    t_org.id as org_id,
                    t_org.name as org_name,
                    t_entry.explain as explain,
                    t_account.number as account_number,
                    t_account.name as account_name,
                    t_entry.items_html as items_html,
                    t_entry.damount as damount,
                    t_entry.camount as camount,
                    t_account.direction as direction,
                    t_cashflow.name as cash_flow
                FROM accountcore_voucher as t_voucher
                LEFT OUTER JOIN accountcore_entry as t_entry on t_voucher.id=t_entry.voucher
                LEFT OUTER JOIN accountcore_account as t_account on t_entry.account=t_account.id
                LEFT OUTER JOIN accountcore_org as t_org on t_voucher.org=t_org.id
                LEFT OUTER JOIN accountcore_cashflow as t_cashflow on t_entry."cashFlow"=t_cashflow.id
                WHERE
                    year*12+month >= %s*12+%s
                    AND year*12+month<=%s*12+%s
                    AND t_voucher.org in %s
                    AND t_entry.account in %s
                    AND t_entry.account_item = %s
                ORDER BY voucherdate,org_name,account_number,v_number
                '''
        else:
            raise exceptions.ValidationError('查询参数数量错误!')

        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()


# 明细账明细
class EntryArch(object):
    '''明细账明细'''
    __slots__ = ['voucher_id',
                 'org_id',
                 'voucherdate',
                 'year',
                 'month',
                 'v_number',
                 'number',
                 'uniqueNumber',
                 'roolbook_html',
                 'org_name',
                 'explain',
                 'account_number',
                 'account_name',
                 'items_html',
                 'damount',
                 'camount',
                 'balance_d',
                 'balance_c',
                 'balance',
                 'direction',
                 'cash_flow',
                 'is_not_begining',
                 'is_PrebeginBalance',
                 'need_check']

    def __init__(self):
        self.voucher_id = 0,
        self.org_id = 0,
        self.voucherdate = None
        self.year = 0
        self.month = 0
        self.v_number = ''
        self.number = ''
        self.uniqueNumber = ""
        self.roolbook_html = ""
        self.org_name = ''
        self.explain = ''
        self.account_number = ''
        self.account_name = ''
        self.items_html = ''
        self.damount = 0
        self.camount = 0
        self.balance_d = 0
        self.balance_c = 0
        self.balance = 0
        self.direction = None
        self.cash_flow = ''
        self.is_not_begining = True
        self.is_PrebeginBalance = False
        self.need_check = False


# 年初余额
class BeginYear(EntryArch):
    '''年初余额'''

    def __init__(self, year, direction, damount, camount, need_check=False):
        super(BeginYear, self).__init__()
        self.explain = '年初余额'
        self.year = year
        self.month = 1
        self.voucherdate = year
        self.direction = direction
        self.balance_d = damount
        self.balance_c = camount
        self.balance = (
            damount-camount) if direction == '1' else (camount-damount)
        self.need_check = need_check


# 月初到启用日
class BeginBalance(EntryArch):
    '''月初到启用日'''

    def __init__(self, year, month, direction, damount, camount, need_check=False):
        super(BeginBalance, self).__init__()
        self.explain = '月初到启用日'
        self.year = year
        self.month = month
        self.direction = direction
        self.voucherdate = year
        self.damount = damount
        self.camount = camount
        self.is_not_begining = False
        self.need_check = need_check


# 启用月初以前
class PrebeginBalance(EntryArch):
    '''启用月初以前'''

    def __init__(self, year, month, direction, damount, camount, need_check=False):
        super(PrebeginBalance, self).__init__()
        # 不要改变名称，在
        self.explain = '年初至启用月初'
        self.year = year
        self.month = month
        self.direction = direction
        self.voucherdate = year
        self.damount = damount
        self.camount = camount
        self.is_not_begining = False
        self.is_PrebeginBalance = True
        self.need_check = need_check


# 本月合计
class SumMonth(EntryArch):
    '''本月合计'''

    def __init__(self, year, month, direction, damount, camount, balance=0, need_check=False):
        super(SumMonth, self).__init__()
        self.explain = '本月合计'
        self.voucherdate = year
        self.year = year
        self.month = month
        self.direction = direction
        self.damount = damount
        self.camount = camount
        self.balance = balance
        self.need_check = need_check


# 本年累计
class CumulativeYear(EntryArch):
    '''本年累计'''

    def __init__(self, year, month, direction, damount, camount, balance=0, need_check=False):
        super().__init__()
        self.explain = '本年累计'
        self.year = year
        self.month = month
        self.voucherdate = year
        self.direction = direction
        self.damount = damount
        self.camount = camount
        self.balance = balance
        self.need_check = need_check


# 明细账组装器
class EntrysAssembler():
    '''明细账组装器'''

    def __init__(self,
                 main_account,
                 item,
                 period=None,
                 beginingOfYearBalance=None,
                 beginBalances=None,
                 entryArchs=None
                 ):
        self.main_account = main_account
        self.item = item
        self.period = period
        self.beginingOfYearBalance = beginingOfYearBalance
        self.beginBalances = beginBalances
        self.entryArchs = entryArchs
        self.entrys = []

        self._generating(period)

    def _generating(self, period):
        '''生成明细账'''
        self._addBegingBalance()
        if len(self.entryArchs) == 0:
            # 添加年初余额
            self.entrys.append(BeginYear(period.start_year,
                                         self.main_account.direction,
                                         self.beginingOfYearBalance[0],
                                         self.beginingOfYearBalance[1]))
            return
        # 查询范围内有启用期初,就添加启用期初,因为如果启用期初有当月已发生额,需要计入当月发生额
        tmp_year = self.entryArchs[0].year
        tmp_month = self.entryArchs[0].month
        main_direction = self.main_account.direction
        # 本月合计
        sum_month_d = 0
        sum_month_c = 0
        # 本年累计
        sum_year_d = 0
        sum_year_c = 0
        # 每年年初,没考虑查询期间有启用期初的
        tmp_begin_year_d = self.beginingOfYearBalance[0]
        tmp_begin_year_c = self.beginingOfYearBalance[1]

        # 查询期间启用期初记录的本年累计和期初余额对年初借贷方的影响
        thisYearbegins = list(
            filter(lambda b: b['year'] == tmp_year, self.beginBalances))
        # 启用期初对年初借方影响
        # d = sum([b['begin_d']-b['cumulative_d']+b['damount']
        #          for b in thisYearbegins])
        d = sum([b['begin_d']-b['cumulative_d']+b['damount']
                 for b in thisYearbegins])
        tmp_begin_year_d = tmp_begin_year_d+d
        # 启用期初对年初贷方影响
        c = sum([b['begin_c']-b['cumulative_c']+b['camount']
                 for b in thisYearbegins])
        tmp_begin_year_c = tmp_begin_year_c+c

        # 调整后的年初余额
        tmp_pre_blanace = tmp_begin_year_d-tmp_begin_year_c
        # 添加年初余额
        self.entrys.append(BeginYear(tmp_year,
                                     self.main_account.direction,
                                     tmp_begin_year_d,
                                     tmp_begin_year_c))

        # entryArchs必须已经按年月进行了升序排列,查询期间的各月启用期初记录被看做一条分录
        # 启用期初的"当月已反生额的借贷方"被看做一条分录的借贷方
        for e in self.entryArchs:
            if main_direction != e.direction:
                raise exceptions.ValidationError(
                    e.account_name+"科目默认余额方向和"+self.main_account.name+"的方向不一致")

            # 新的一年开始
            if e.year != tmp_year:
                # if tmp_month == 12:
                # if True:
                # 添加查询期间最后的本月合计
                self.entrys.append(SumMonth(tmp_year,
                                            tmp_month,
                                            main_direction,
                                            sum_month_d,
                                            sum_month_c, self.entrys[-1].balance, self.entrys[-1].need_check))
                # 添加本年累计
                self.entrys.append(CumulativeYear(tmp_year,
                                                  tmp_month,
                                                  main_direction,
                                                  sum_year_d,
                                                  sum_year_c, self.entrys[-1].balance, self.entrys[-1].need_check))
                # 添加年初余额
                tmp_begin_year_d = tmp_begin_year_d+sum_year_d
                tmp_begin_year_c = tmp_begin_year_c+sum_year_c

                thisYearbegins = list(
                    filter(lambda b: b['year'] == e.year, self.beginBalances))
                # 启用期初对年初借方影响
                d = sum([b['begin_d']-b['cumulative_d']+b['damount']
                         for b in thisYearbegins])
                tmp_begin_year_d = tmp_begin_year_d+d
                # 启用期初对年初贷方影响
                c = sum([b['begin_c']-b['cumulative_c']+b['camount']
                         for b in thisYearbegins])
                tmp_begin_year_c = tmp_begin_year_c+c

                self.entrys.append(BeginYear(e.year,
                                             main_direction,
                                             tmp_begin_year_d,
                                             tmp_begin_year_c))
                 # 不同启用期混合查询,需要修正为年初余额
                if main_direction == '1':
                    tmp_pre_blanace = tmp_begin_year_d-tmp_begin_year_c
                elif main_direction == '-1':
                    tmp_pre_blanace = -tmp_begin_year_d+tmp_begin_year_c

                sum_year_d = 0
                sum_year_c = 0
                sum_month_d = 0
                sum_month_c = 0

                tmp_year = e.year
                tmp_month = e.month
            if e.year == tmp_year and e.month == tmp_month:
                # 依据余额方向更新余额记
                if main_direction == '1':
                    e.balance = tmp_pre_blanace+e.damount-e.camount
                    if ACTools.TranslateToDecimal(e.balance) == ACTools.ZeroAmount():
                        e.balance = 0.00
                elif main_direction == '-1':
                    e.balance = -tmp_pre_blanace-e.damount+e.camount
                    if ACTools.TranslateToDecimal(e.balance) == ACTools.ZeroAmount():
                        e.balance = 0.00
                tmp_pre_blanace = tmp_pre_blanace+e.damount-e.camount
                self.entrys.append(e)
                if not e.is_PrebeginBalance:
                    sum_month_d = sum_month_d+e.damount
                    sum_month_c = sum_month_c+e.camount
                sum_year_d = sum_year_d+e.damount
                sum_year_c = sum_year_c+e.camount

            if (e.year == tmp_year and e.month != tmp_month):
                # 添加本月合计
                self.entrys.append(SumMonth(tmp_year,
                                            tmp_month,
                                            main_direction,
                                            sum_month_d,
                                            sum_month_c, self.entrys[-1].balance, self.entrys[-1].need_check))
                # 添加本年累计
                self.entrys.append(CumulativeYear(tmp_year,
                                                  tmp_month,
                                                  main_direction,
                                                  sum_year_d,
                                                  sum_year_c, self.entrys[-1].balance, self.entrys[-1].need_check))
                # 一个月结束,本月合计清零
                sum_month_d = 0
                sum_month_c = 0

                # 依据余额方向更新余额记
                if main_direction == '1':
                    e.balance = tmp_pre_blanace+e.damount-e.camount
                    if ACTools.TranslateToDecimal(e.balance) == ACTools.ZeroAmount():
                        e.balance = 0.00
                elif main_direction == '-1':
                    e.balance = -tmp_pre_blanace-e.damount+e.camount
                    if ACTools.TranslateToDecimal(e.balance) == ACTools.ZeroAmount():
                        e.balance = 0.00
                tmp_pre_blanace = tmp_pre_blanace+e.damount-e.camount
                self.entrys.append(e)

                if not e.is_PrebeginBalance:
                    sum_month_d = sum_month_d+e.damount
                    sum_month_c = sum_month_c+e.camount
                sum_year_d = sum_year_d+e.damount
                sum_year_c = sum_year_c+e.camount

            tmp_year = e.year
            tmp_month = e.month

        # 添加查询期间最后的本月合计
        self.entrys.append(SumMonth(tmp_year,
                                    tmp_month,
                                    main_direction,
                                    sum_month_d,
                                    sum_month_c, self.entrys[-1].balance, self.entrys[-1].need_check))
        # 添加本年累计
        self.entrys.append(CumulativeYear(tmp_year,
                                          tmp_month,
                                          main_direction,
                                          sum_year_d,
                                          sum_year_c, self.entrys[-1].balance, self.entrys[-1].need_check))
        # 过滤出选择期间的数据
        _end_year = self.period.end_year
        _end_month = self.period.end_month
        self.entrys = [e for e in self.entrys if e.year <
                       _end_year or e.year == _end_year and e.month <= _end_month]

    def _addBegingBalance(self):
        '''把查询期间的启用期初加入分录列表'''
        for b in self.beginBalances:
            pre_begin = PrebeginBalance(b['year'],
                                        b['month'],
                                        self.main_account.direction,
                                        b['cumulative_d']-b['damount'],
                                        b['cumulative_c']-b['camount'])
            begin = BeginBalance(b['year'],
                                 b['month'],
                                 self.main_account.direction,
                                 b['damount'],
                                 b['camount'])
            self.entryArchs.append(pre_begin)
            self.entryArchs.append(begin)
        self.entryArchs.sort(key=lambda e: (e.year,
                                            e.month,
                                            str(e.voucherdate),
                                            e.is_not_begining))
        # 判断启用期间是否一致，以提示不同启用期混合查询可能存在的查询逻辑错误
        beginBlances = self.beginBalances
        _lenth = len(beginBlances)
        # 存在不同启用期标志
        # 最晚启用期
        correct_year = 0
        correct_month = 0
        if _lenth > 1:
            if (beginBlances[_lenth-1]['year'] > beginBlances[0]['year'] or
                beginBlances[_lenth-1]['year'] == beginBlances[0]['year'] and
                    beginBlances[_lenth-1]['month'] > beginBlances[0]['month']):
                correct_year = beginBlances[_lenth-1]['year']
                correct_month = beginBlances[_lenth-1]['month']
            for b in self.entryArchs:
                if b.year < correct_year or b.year == correct_year and b.month < correct_month:
                    b.need_check = True
