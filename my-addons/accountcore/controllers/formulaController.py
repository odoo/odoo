# -*- coding: utf-8 -*-
import random
from functools import partial
from ..models.ac_obj import ACTools
from ..models.ac_period import Period, VoucherPeriod
from odoo import http
from odoo.http import request
# from odoo.tools.profiler import profile
class ACMethosContainer():
    _methods = {}
    @classmethod
    def addMethod(cls, method):
        cls._methods.update({method.name: method})
    @classmethod
    def getMethod(cls, methodName):
        method = cls._methods.get(methodName)
        return method
class ACMethodBace():
    ruleBookName_shunyi = "结转损益"
    def __init__(self, amountTypeName):
        self.name = amountTypeName
    def getAmount(self, account, org, item, period):
        pass
# 期初余额
class ACMethod_beginningBalance(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''期初余额'''
        amount = account.getBegingAmountOf(period.startP, org, item)
        return amount
# 期初借方余额
class ACMethod_beginingDamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''期初借方余额'''
        amount = account.getBegingDAmountOf(period.startP, org, item)
        return amount
# 期初贷方余额
class ACMethod_beginingCamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''期初贷方余额'''
        amount = account.getBegingCAmountOf(period.startP, org, item)
        return amount
# 借方发生额
class ACMethod_damount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''借方发生额'''
        start_p = period.startP
        end_p = period.endP
        amount = account.getDamountBetween(start_p, end_p, org, item)
        return amount
# 贷方发生额
class ACMethod_camount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''贷方发生额'''
        start_p = period.startP
        end_p = period.endP
        amount = account.getCamountBetween(start_p, end_p, org, item)
        return amount
# 期末余额
class ACMethod_endAmount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''期末余额'''
        amount = account.getEndAmountOf(period.endP, org, item)
        return amount
# 期末借方余额
class ACMethod_endDamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''期末借方余额'''
        amount = account.getEndDAmount(period.endP, org, item)
        return amount
# 期末贷方余额
class ACMethod_endCamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''期末贷方余额'''
        amount = account.getEndCAmount(period.endP, org, item)
        return amount
# 本年借方累计发生额
class ACMethod_cumulativeDamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''本年借方累计发生额'''
        endP = period.endP
        amount = account.getCumulativeDAmountOf(endP, org, item)
        return amount
# 本年贷方累计发生额
class ACMethod_cumulativeCamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''本年贷方累计发生额'''
        endP = period.endP
        amount = account.getCumulativeCAmountOf(endP, org, item)
        return amount
# 损益表本期实际发生额
class ACMethod_realHappend(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''损益表本期实际发生额'''
        # 科目在结转损益凭证中的发生额合计'''
        amount_j = ACTools.ZeroAmount()
        # 科目在余额相反方向的发生额
        amount = ACTools.ZeroAmount()
        amount_ = ACTools.ZeroAmount()
        #  启用期初的发生额
        amount_begin = ACTools.ZeroAmount()
        ruleBook = account.env['accountcore.rulebook'].sudo().search(
            [('name', '=', self.ruleBookName_shunyi)])
        vouchers = ruleBook.getVouchersOfOrg(org, period)
        if item:
            entrys = [e for e in vouchers.entrys if (e.account.id == account.id
                                                     and e.account_item.id == item.id)]
            balance = account.getBegins(org, item)
        else:
            entrys = [e for e in vouchers.entrys if e.account.id == account.id]
            balance = account.getBegins(org)
        if account.direction == '1':
            amount_j = sum([ACTools.TranslateToDecimal(e.camount)
                            for e in entrys])
            amount = ACTools.TranslateToDecimal(account.getCamountBetween(period.startP,
                                                                          period.endP,
                                                                          org,
                                                                          item))
            amount_ = ACTools.TranslateToDecimal(account.getDamountBetween(period.startP,
                                                                           period.endP,
                                                                           org,
                                                                           item))
            if balance and period.includeDateTime(balance[0].createDate):
                amount_begin = ACTools.TranslateToDecimal(
                    balance[0].beginCumulativeDamount)
        else:
            amount_j = sum([ACTools.TranslateToDecimal(e.damount)
                            for e in entrys])
            amount = ACTools.TranslateToDecimal(account.getDamountBetween(period.startP,
                                                                          period.endP,
                                                                          org,
                                                                          item))
            amount_ = ACTools.TranslateToDecimal(account.getCamountBetween(period.startP,
                                                                           period.endP,
                                                                           org,
                                                                           item))
            if balance and period.includeDateTime(balance[0].createDate):
                amount_begin = ACTools.TranslateToDecimal(
                    balance[0].beginCumulativeDamount)
        return amount_-(amount-amount_j)+amount_begin
# 损益表本年实际发生额
class ACMethod_realHappendYear(ACMethodBace):
    __ruleBookName = "结转损益"
    def getAmount(self, account, org, item, period):
        '''损益表本年实际发生额'''
        newP = period.getBeginYearToThisEnd()
        # 科目在结转损益凭证中的发生额合计'''
        amount_j = ACTools.ZeroAmount()
        # 科目在余额相反方向的发生额'''
        amount = ACTools.ZeroAmount()
        # 查询期间发生额（不包含启用期初）
        amount_ = ACTools.ZeroAmount()
        #  启用期初的发生额
        amount_begin = ACTools.ZeroAmount()
        ruleBook = account.env['accountcore.rulebook'].sudo().search(
            [('name', '=', self.ruleBookName_shunyi)])
        vouchers = ruleBook.getVouchersOfOrg(org, newP)
        if item:
            entrys = [e for e in vouchers.entrys if (e.account.id == account.id
                                                     and e.account_item.id == item.id)]
            balance = account.getBegins(org, item)
        else:
            entrys = [e for e in vouchers.entrys if e.account.id == account.id]
            balance = account.getBegins(org)
        if account.direction == '1':
            amount_j = sum([ACTools.TranslateToDecimal(e.camount)
                            for e in entrys])
            amount = ACTools.TranslateToDecimal(account.getCamountBetween(newP.startP,
                                                                          newP.endP,
                                                                          org,
                                                                          item))
            amount_ = ACTools.TranslateToDecimal(account.getDamountBetween(newP.startP,
                                                                           newP.endP,
                                                                           org,
                                                                           item))
            if balance and period.includeDateTime(balance[0].createDate):
                amount_begin = ACTools.TranslateToDecimal(
                    balance[0].beginCumulativeDamount)
        else:
            amount_j = sum([ACTools.TranslateToDecimal(e.damount)
                            for e in entrys])
            amount = ACTools.TranslateToDecimal(account.getDamountBetween(newP.startP,
                                                                          newP.endP,
                                                                          org,
                                                                          item))
            amount_ = ACTools.TranslateToDecimal(account.getCamountBetween(newP.startP,
                                                                           newP.endP,
                                                                           org,
                                                                           item))
            if balance and newP.includeDateTime(balance[0].createDate):
                amount_begin = ACTools.TranslateToDecimal(
                    balance[0].beginCumulativeDamount)
        return amount_-(amount-amount_j)+amount_begin
# 即时余额
class ACMethod_currentBalance(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''即时余额'''
        return account.getEndAmount(org, item)
# 即时本年借方累计
class ACMethod_currentCumulativeDamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''即时本年借方累计'''
        return account.getCurrentCumulativeDamount(org, item)
# 即时本年贷方方累计
class ACMethod_currentCumulativeCamount(ACMethodBace):
    def getAmount(self, account, org, item, period):
        '''即时本年贷方累计'''
        return account.getCurrentCumulativeCamount(org, item)
ACMethosContainer.addMethod(ACMethod_beginningBalance('期初余额'))
ACMethosContainer.addMethod(ACMethod_beginingDamount('期初借方余额'))
ACMethosContainer.addMethod(ACMethod_beginingCamount('期初贷方余额'))
ACMethosContainer.addMethod(ACMethod_damount('借方发生额'))
ACMethosContainer.addMethod(ACMethod_camount('贷方发生额'))
ACMethosContainer.addMethod(ACMethod_endAmount('期末余额'))
ACMethosContainer.addMethod(ACMethod_endDamount('期末借方余额'))
ACMethosContainer.addMethod(ACMethod_endCamount('期末贷方余额'))
ACMethosContainer.addMethod(ACMethod_cumulativeDamount('本年借方累计发生额'))
ACMethosContainer.addMethod(ACMethod_cumulativeCamount('本年贷方累计发生额'))
ACMethosContainer.addMethod(ACMethod_realHappend('损益表本期实际发生额'))
ACMethosContainer.addMethod(ACMethod_realHappendYear('损益表本年实际发生额'))
ACMethosContainer.addMethod(ACMethod_currentBalance('即时余额'))
ACMethosContainer.addMethod(ACMethod_currentCumulativeDamount('即时本年借方累计'))
ACMethosContainer.addMethod(ACMethod_currentCumulativeCamount('即时本年贷方累计'))
# 报表公式计算
class FormulaController(http.Controller):
    # 获得科目各种金额
    @http.route('/ac/account', type='http', auth='user', csrf=False)
    def account(self, formula, startDate, endDate, orgIds):
        accountAmount = 'self.accountAmount(' + \
            orgIds+","+startDate+","+endDate+","
        tactics = [('account(', accountAmount)]
        newFormula = self.rebuildFormula(formula, tactics)
        self.env = request.env
        # self.env['accountcore.account'].clear_caches()
        result = eval(newFormula)
        return str(result)
    #获得机构
    @http.route('/ac/show_orgs', type='http', auth='user', csrf=False)
    def getOrgs(self, orgIds):
        '''获取机构/主体名称'''
        orgs = (eval(orgIds)).split("/")
        org_ids = list(map(int, orgs))
        orgsName = request.env['accountcore.org'].sudo().browse(
            org_ids).mapped('name')
        return '+'.join(orgsName)
    #科目金额
    def accountAmount(self, org_ids, start_date, end_data, accountName, hasChild, amountType, itemsName):
        amount = ACTools.ZeroAmount()
        orgIds = org_ids.split("/")
        org_ids = list(map(int, orgIds))
        orgs = self.env['accountcore.org'].sudo().browse(org_ids)
        account = request.env['accountcore.account'].sudo().search(
            [('name', '=', accountName)])
        if len(account) != 1:
            # 如果科目名称不存在
            return amount
        accounts = [account]
        if hasChild.lower() == "true":
            accounts = account.getMeAndChilds()
        items = []
        haveItem = False
        itemExist = False
        if len(itemsName) != 0:
            haveItem = True
            itemsName = itemsName.split("/")
            items = self.env['accountcore.item'].sudo().search(
                [('name', 'in', itemsName)])
            if len(items) > 0:
                itemExist=True
        period = Period(start_date, end_data)
        for org in orgs:
            for ac in accounts:
                if not haveItem:
                    amount += self.getAmountOfType(ac,
                                                   org,
                                                   None,
                                                   amountType,
                                                   period)
                elif (haveItem and itemExist):
                    for item in items:
                        amount += self.getAmountOfType(ac,
                                                       org,
                                                       item,
                                                       amountType,
                                                       period)
                elif (haveItem and not itemExist):
                    pass
                    # 设置了核算项目但核算项目不存在
        return amount
    #获得金额类型
    def getAmountOfType(self, account, org, item, amountType, period):
        '''根据不同的金额类型取数'''
        method = ACMethosContainer.getMethod(amountType)
        amount = ACTools.ZeroAmount()
        # 带有核算项目的科目，取对应机构和科目在余额表有记录的核算项目
        if not item and account.accountItemClass:
            domain = [('org', '=', org.id),
                      ('account', '=', account.id)]
            usedItemsIds = (self.env['accountcore.accounts_balance'].sudo().search(
                domain).mapped('items')).mapped('id')
            items = self.env['accountcore.item'].sudo().browse(
                list(set(usedItemsIds)))
            for itm in items:
                amount += ACTools.TranslateToDecimal(method.getAmount(account,
                                                                      org,
                                                                      itm,
                                                                      period))
        else:
            amount = ACTools.TranslateToDecimal(method.getAmount(account,
                                                                 org,
                                                                 item,
                                                                 period))
        return amount
    # 替换公式为内部名称，并插入更多参数
    def rebuildFormula(self, oldFormula, tactics):
        '''重建公式'''
        newFormula = oldFormula
        for item in tactics:
            newFormula = newFormula.replace(item[0], item[1])
        return newFormula
    @http.route('/ac/cashflow', type='http', auth='user', csrf=False)
    def cashflow(self, formula, startDate, endDate, orgIds):
        '''现金流量取数'''
        replaceStr = 'self.cashflowAmount(' + \
            orgIds+","+startDate+","+endDate+","
        newFormula = formula.replace('cashflow(',replaceStr)
        self.env = request.env
        result = eval(newFormula)
        return str(result)
    def cashflowAmount(self, org_ids, start_date, end_date, cashflowName, hasChild):
        _org_ids = (org_ids).split("/")
        cashflowIds=[]
        cashflowId = self.env['accountcore.cashflow'].sudo().search([('name','=',cashflowName)],limit=1).id
        cashflowIds.append(cashflowId)
        if hasChild.lower() == "true":
            childIds= self.env['accountcore.cashflow'].sudo().search([('id','child_of',cashflowId)]).mapped("id")
            cashflowIds.extend(childIds)
        params = (tuple(cashflowIds),
                    tuple(_org_ids),
                    start_date,
                    end_date)
        query = '''SELECT sum(damount+ camount) as amount
                        FROM public.accountcore_entry 
                        WHERE "cashFlow" IN %s
                        AND org IN %s
                        AND v_voucherdate BETWEEN %s AND %s '''
        self.env.cr.execute(query, params)
        amount=self.env.cr.fetchone()
        if amount[0]:
            return str(amount[0])
        return str(0)
