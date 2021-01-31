# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
from functools import partial
import random
import time
from ..models.ac_obj import ACTools
from ..models.ac_period import Period, VoucherPeriod
from odoo import http, exceptions
from odoo.exceptions import AccessDenied
from odoo.http import request
# from odoo.tools.profiler import profile
# 外部系统接口


class WebapiController(http.Controller):
    @http.route('/ac/createvoucher', type='json', auth='public', methods=['POST'], cors='*', csrf=False)
    # 接受外部系统推送过来的凭证信息并新增凭证
    def create_voucher(self, loginUser, pw, autoCreate, data, mark, *args, **kw):
        '''接受推送的凭证'''
        # 检查权限
        self.env = request.env
        user = self._check_access(loginUser, pw, mark)
        # 检查凭证逻辑
        self._check_voucher_logic(data)
        # 构建符合格式的凭证
        voucher = self._build_voucher(autoCreate, data, user)
        v = self.env['accountcore.voucher'].sudo().create(voucher)
        return {"uniqueNumber": v.uniqueNumber}
    # 检查权限

    def _check_access(self, loginUser, pw, mark):
        '''检查权限'''
        user = self.env['res.users'].sudo().search([('login', '=', loginUser)])
        user.ensure_one()
        assert pw
        self.env.cr.execute(
            "SELECT COALESCE(password, '') FROM res_users WHERE id=%s",
            [user.id]
        )
        [hashed] = self.env.cr.fetchone()
        valid, replacement = user._crypt_context()\
            .verify_and_update(pw, hashed)
        if replacement is not None:
            user._set_encrypted_password(user.id, replacement)
        if not valid:
            raise AccessDenied()
        # 检查校验值
        self._check_mark(mark)
        return user
    # 检查数据逻辑

    def _check_voucher_logic(self, data):
        '''检查推送的凭证是否符合逻辑'''
        # 检查机构
        if "org" not in data:
            raise exceptions.UserError('缺少机构/主体参数：org')
        if not data['org']:
            raise exceptions.UserError('机构/主体参数org的值不能为空')
        # 检查日期是否正确
        time.strptime(data['voucherdate'], "%Y-%m-%d")
        if 'real_date' in data and data['real_date']:
            time.strptime(data['real_date'], "%Y-%m-%d")
        # 分录是否>=两条
        if len(data['entrys']) < 2:
            raise exceptions.UserError('一张凭证需要两条以上的分录')
        # 检查分录借方合计=贷方合计等
        sum_d = ACTools.ZeroAmount()
        sum_c = ACTools.ZeroAmount()
        for e in data['entrys']:
            # 检查每条分录是否有金额且不全为零
            if (e['camount'] == 0 and e['damount'] == 0) or (e['camount'] != 0 and e['damount'] != 0):
                raise exceptions.UserError('分录的借贷方金不能全为0或都不为0')
            # 检查后带核算项目类别的分录,必选类别是否<=1
            if 'items' in e:
                require_itemclass = ([require[1]
                                      for require in e['items']]).count(True)
                if require_itemclass > 1:
                    raise exceptions.UserError('科目后的必选核算项目只能有一个')
            sum_d = sum_d+ACTools.TranslateToDecimal(e['damount'])
            sum_c = sum_c+ACTools.TranslateToDecimal(e['camount'])
        if sum_c-sum_d != ACTools.ZeroAmount():
            raise exceptions.UserError('分录的借方合计不等于贷方合计')
    # 检查校验值

    def _check_mark(self, mark):
        '''检查校验值'''
        if mark != "accountcore":
            raise AccessDenied()
    # 购建凭证

    def _build_voucher(self, autoCreate, data, user):
        '''根据获得的凭证信息构建符合规范的凭证'''
        voucher = {}
        voucher.update(data)
        # 购建机构/主体
        voucher['org'] = self._build_org(voucher['org'], autoCreate)
        # 购建全局标签
        if 'glob_tag' in voucher:
            voucher['glob_tag'] = self._build_glob_tag(
                voucher['glob_tag'], autoCreate)
        # 购建每条分录
        for i in range(0, len(voucher['entrys'])):
            entry = voucher['entrys'][i]
            # 购建每条分录的科目
            entry['account'] = self._build_account(
                entry['account'], autoCreate)
            if 'items' in entry:
                items = entry['items']
                # 购建核算项目和类别
                entry['items'] = self._build_item(items, autoCreate)
                account = self.env['accountcore.account'].sudo().browse([
                    entry['account']])
                # 更新科目带的核算项目类别
                self._updataAccountItemClass(account, items)
            # 购建每条分录现金流量
            if 'cashFlow' in entry:
                cashflow = entry['cashFlow']
                entry['cashFlow'] = self._build_cashflow(cashflow, False)
            # 购建每条分录的全局标签
            if 'glob_tag' in entry:
                glob_tags = entry['glob_tag']
                entry['glob_tag'] = self._build_glob_tag(glob_tags, autoCreate)
            voucher['entrys'][i] = [0, '', entry]
        # 设置凭证状态为审核,审核人,制单人,单据来源
        voucher.update({'state': 'reviewed',
                        'reviewer': user.id,
                        'createUser': user.id, })
        # 设置凭证来源
        if 'soucre' not in voucher:
            source = "推送"
        else:
            source = voucher['soucre']
        # 注意这里是soucre而不是source!
        voucher.update({'soucre': self._build_Source(source, autoCreate)})
        return [voucher]
    # 更新科目带的核算项目类别

    def _updataAccountItemClass(self, account, items):
        '''更新科目带的核算项目类别'''
        account.itemClasses
        account.accountItemClass
        items_classNames = [className[0] for className in items]
        itemClasses = self.env['accountcore.itemclass'].sudo().search(
            [('name', 'in', items_classNames)])
        itemClasses_updata = itemClasses-account.itemClasses
        for item in items:
            if item[1]:
                mast_item = itemClasses_updata.filtered(
                    lambda i: i.name == item[0])
                # 如果科目后已有必选项目类别,而且和需要添加的必选项目类别不同
                if account.accountItemClass and mast_item:
                    raise exceptions.UserError(
                        '核算项目【'+item[0]+'】存在,但是不属于指定的类别')
                # 科目被使用过
                elif account.haveBeenUsedInBalance() and mast_item:
                    raise exceptions.UserError(
                        '科目【'+account.name+'】已经被使用过,不能添加必选核算项目')
                elif mast_item:
                    account.write({'accountItemClass': mast_item.id})
                break
        for itemClass in itemClasses_updata:
            account.write({'itemClasses': [(4, itemClass.id)]})
    # 购建会计科目

    def _build_account(self, accountInfo, autoCreate):
        '''购建会计科目'''
        accountNames = ACTools.splitAccountName(accountInfo["name"])
        accountNames.reverse()
        accountNames_stack = []
        exist_parent_id = 0
        for a in accountNames:
            i = AccountInfo(a, self.env)
            if i.id == 0:
                accountNames_stack.append(a)
            else:
                exist_parent_id = i.id
                break
        if exist_parent_id != 0 and len(accountNames_stack) == 0:
            return exist_parent_id
        if exist_parent_id == 0:
            if not autoCreate:
                raise exceptions.UserError('科目【'+accountInfo["name"]+'】不存在')
            # 购建一级科目
            # 判断购建一级科目的必须信息是否有
            self._check_accountInfo(accountInfo)
            number = accountInfo["number"]
            direction = accountInfo['direction']
            first_accountName = accountNames_stack.pop()
            # 购建科目类别
            accountClass = AccountClassInfo(
                accountInfo['accountClass'], self.env)
            if accountClass.id == 0:
                accountClass.create()
            first_account = self._build_first_account(
                first_accountName, number, direction, accountClass.id)
            exist_parent_id = first_account.id
        if autoCreate:
            while len(accountNames_stack) > 0:
                next_accountName = accountNames_stack.pop()
                next_account = AccountInfo(next_accountName, self.env)
                next_account.create(exist_parent_id)
                exist_parent_id = next_account.id
        else:
            raise exceptions.UserError('科目【'+accountInfo["name"]+"】不存在")
        return exist_parent_id

    def _check_accountInfo(self, accountInfo):
        '''检查购建一级科目的信息是否完整正确'''
        if "number" not in accountInfo or not accountInfo['number']:
            raise exceptions.UserError(
                '科目【'+accountInfo["name"]+'】没有提供创建其一级科目的科目编号参数:number')
        if "direction" not in accountInfo:
            raise exceptions.UserError(
                '科目【'+accountInfo["name"]+'】没有提供创建其一级科目的科目余额方向参数:direction')
        if "accountClass" not in accountInfo or not accountInfo['accountClass']:
            raise exceptions.UserError(
                '科目【'+accountInfo["name"]+'】没有提供的一级科目的科目类别参数:accountClass')
        if "." in accountInfo["number"] or "---" in accountInfo["number"]:
            raise exceptions.UserError(
                '科目【'+accountInfo["name"]+'】提供的一级科目编码不能包含.和---特殊字符')
        if accountInfo['direction'] not in ['借', '贷']:
            raise exceptions.UserError(
                '科目【'+accountInfo["name"]+'】提供的一级科目余额方向只能是字符"借"或"贷"')
        return True

    def _build_first_account(self, first_accountName, number, direction, accountClassId):
        '''购建一级科目'''
        if direction == '借':
            direction = "1"
        else:
            direction = "-1"
        account = self.env['accountcore.account'].sudo().create({'name': first_accountName,
                                                                 "number": number,
                                                                 "direction": direction,
                                                                 "accountClass": accountClassId})
        return account
    # 购建机构/主体

    def _build_org(self, items, autoCreate):
        '''购建机构/主体'''
        if not items:
            raise exceptions.UserError("需要为org参数设置正确的值")
        else:
            i = OrgInfo(items, self.env)
            # 如果不存在相同名称的项目
            if i.id == 0:
                # 是否自动新建
                if autoCreate:
                    # 新建项目
                    i.create()
                else:
                    raise exceptions.UserError('机构/主体【'+i.name+"】不存在")
            return i.id
    # 购建核算项目

    def _build_item(self, items, autoCreate):
        '''购建核算项目'''
        if not items:
            return []
        else:
            ids = []
            for item in items:
                item_type, mast, name = item
                i = ItemInfo(name, self.env)
                # 如果不存在相同名称的项目
                if i.id == 0:
                    # 是否自动新建
                    if autoCreate:
                        i_class = ItemclassInfo(item_type, self.env)
                        if i_class.id == 0 and autoCreate:
                            # 新建项目类别
                            i_class.create()
                        # 新建项目
                        i.create(i_class.id)
                    else:
                        raise exceptions.UserError('核算项目【'+name+"】不存在")
                ids.append(i.id)
        return [[6, False, ids]]
    # 购建现金流量

    def _build_cashflow(self, items, autoCreate):
        '''购建现金流量项目'''
        if not items:
            return False
        else:
            i = CashflowInfo(items, self.env)
            # 如果不存在相同名称的项目
            if i.id == 0:
                # 是否自动新建
                if autoCreate:
                    pass
                    # 暂未实现现金流量项目的自动新增
                else:
                    raise exceptions.UserError('现金流量项目【'+i.name+"】不存在")
            return i.id
    # 购建全局标签

    def _build_glob_tag(self, items, autoCreate):
        '''购建全局标签'''
        if not items:
            return []
        else:
            ids = []
            for item in items:
                item_type, name = item
                i = GlobTagInfo(name, self.env)
                # 如果不存在相同名称的标签
                if i.id == 0:
                    # 是否自动新建
                    if autoCreate:
                        i_class = GlobTagClassInfo(item_type, self.env)
                        if i_class.id == 0 and autoCreate:
                            # 新建标签类别
                            i_class.create()
                        # 新建标签
                        i.create(i_class.id)
                    else:
                        raise exceptions.UserError('全局标签【'+name+"】不存在")
                ids.append(i.id)
        return [[6, False, ids]]
    # 购建凭证来源

    def _build_Source(self, items, autoCreate):
        '''购建全局标签'''
        if not items:
            items = "推送"
        # 默认来源为"推送"
        i = SourceInfo(items, self.env)
        # 如果不存在相同名称的项目
        if i.id == 0:
            # 是否自动新建
            if autoCreate:
                i.create(items)
            else:
                raise exceptions.UserError('凭证来源【'+i.name+"】不存在")
        return i.id


class NameId():
    def __init__(self, name, env):
        self.env = env
        self.name = name
        self.id = 0
        self._build()

    def _build(self):
        '''检查名称是否存在'''
        if self.id == 0:
            record = self.env[self.model_name].sudo().search(
                [('name', '=', self.name)], limit=1)
            if record:
                self.id = record.id

    @abstractmethod
    def create(self, *arg, **kw):
        '''没有就创建一个'''
        pass
# 机构/主体对象


class OrgInfo(NameId):
    model_name = "accountcore.org"

    def create(self, *arg, **kw):
        record = self.env[self.model_name].sudo().create([{'name': self.name}])
        self.id = record.id
# 科目类别对象


class AccountClassInfo(NameId):
    model_name = "accountcore.accountclass"

    def create(self, *arg, **kw):
        record = self.env[self.model_name].sudo().create([{'name': self.name}])
        self.id = record.id
# 科目信息对象


class AccountInfo(NameId):
    model_name = "accountcore.account"

    def create(self, *arg, **kw):
        fatherAccountId = arg[0]
        fatherAccount = self.env[self.model_name].sudo().browse([
            fatherAccountId])
        newAccount = {'fatherAccountId': fatherAccountId,
                      'accountClass': fatherAccount.accountClass.id,
                      'cashFlowControl': fatherAccount.cashFlowControl,
                      'name': self.name,
                      'direction': fatherAccount.direction,
                      'number': fatherAccount.number + '.'
                      + str(fatherAccount.currentChildNumber)}
        fatherAccount.currentChildNumber = fatherAccount.currentChildNumber+1
        a = self.env[self.model_name].sudo().create(newAccount)
        # 添加到上级科目的直接下级
        fatherAccount.write({'childs_ids': [(4, a.id)], 'is_show': False})
        self.id = a.id
# 核算项目类别信息


class ItemclassInfo(NameId):
    model_name = "accountcore.itemclass"

    def create(self, *arg, **kw):
        record = self.env[self.model_name].sudo().create([{'name': self.name}])
        self.id = record.id
# 核算项目信息


class ItemInfo(NameId):
    model_name = "accountcore.item"

    def create(self, *arg, **kw):
        class_id = arg[0]
        record = self.env[self.model_name].sudo().create(
            [{'name': self.name, 'itemClass': class_id}])
        self.id = record.id
# 现金流量项目类别信息


class CashflowTypeInfo(NameId):
    model_name = "accountcore.cashflowtype"

    def create(self, *arg, **kw):
        record = self.env[self.model_name].sudo().create([{'name': self.name}])
        self.id = record.id
# 现金流量项目项目信息


class CashflowInfo(NameId):
    model_name = "accountcore.cashflow"

    def create(self, *arg, **kw):
        class_id = arg[0]
        record = self.env[self.model_name].sudo().create(
            [{'name': self.name, 'cashFlowType': class_id}])
        self.id = record.id
# 全局标签类别信息


class GlobTagClassInfo(NameId):
    model_name = "accountcore.glob_tag_class"

    def create(self, *arg, **kw):
        record = self.env[self.model_name].sudo().create([{'name': self.name}])
        self.id = record.id
# 全局标签信息


class GlobTagInfo(NameId):
    model_name = "accountcore.glob_tag"

    def create(self, *arg, **kw):
        class_id = arg[0]
        record = self.env[self.model_name].sudo().create(
            [{'name': self.name, 'glob_tag_class': class_id}])
        self.id = record.id
# 凭证来源信息


class SourceInfo(NameId):
    model_name = "accountcore.source"

    def create(self, *arg, **kw):
        class_id = arg[0]
        record = self.env[self.model_name].sudo().create([{'name': self.name}])
        self.id = record.id
