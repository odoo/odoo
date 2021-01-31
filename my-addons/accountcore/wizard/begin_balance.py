# -*- coding: utf-8 -*-
import base64
import xlrd
import datetime
import time
from odoo import exceptions
from odoo import fields
from odoo import models
from odoo import tools
from ..models.ac_obj import ACTools
from ..models.main_models import AccountsBalance
# 启用期初试算平衡向导openpgpwd


class BeginBalanceCheck(models.TransientModel):
    '''启用期初试算平衡向导'''
    _name = 'accountcore.begin_balance_check'
    _description = '启用期初试算平衡向导'
    org_ids = fields.Many2many('accountcore.org',
                               string='待检查机构/主体',
                               required=True,
                               default=lambda s: s.env.user.currentOrg)
    result = fields.Html(string='检查结果')
    # @api.multi

    def do_check(self, *args):
        '''对选中机构执行平衡检查'''
        self.ensure_one()
        check_result = {}
        result_htmlStr = ''
        for org in self.org_ids:
            check_result[org.name] = self._check(org)
        for (key, value) in check_result.items():
            result_htmlStr = result_htmlStr+"<h6>" + \
                key+"</h6>"+"".join([v[1] for v in value])
        self.result = result_htmlStr
        return {
            'name': '启用期初平衡检查',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'accountcore.begin_balance_check',
            'res_id': self.id,
        }

    def _check(self, org):
        '''对一个机构执行平衡检查'''
        rl = []
        # 获得机构期初
        balance_records = AccountsBalance.getBeginOfOrg(org)
        # 检查月初本年累计发生额借方合计=贷方合计
        rl.append(self._checkCumulativeAmountBalance(balance_records))
        # 检查月初余额借方合计=贷方合计
        rl.append(self._checkBeginingAmountBalance(balance_records))
        # 检查月已发生额借方合计=贷方合计
        rl.append(self._checkAmountBalance(balance_records))
        # 检查资产=负债+所有者权益+收入-理论
        rl.append(self._checkBalance(balance_records))
        return rl

    def _checkCumulativeAmountBalance(self, balance_records):
        '''检查月初本年累计发生额借方合计'''
        damount = AccountsBalance._sumFieldOf(
            'cumulativeDamount', balance_records)
        camount = AccountsBalance._sumFieldOf(
            'cumulativeCamount', balance_records)
        imbalanceAmount = damount-camount
        if imbalanceAmount == 0:
            rl_html = "<div><span class='text-success fa fa-check'></span>月初本年借方累计发生额=月初本年贷方累计发生额【" + \
                str(damount) + "="+str(camount)+"】</div>"
            return (True, rl_html)
        else:
            rl_html = "<div><span class='text-danger fa fa-close'></span>月初本年借方累计发生额合计=月初本年贷方累计发生额合计【" + \
                str(damount)+"-" + str(camount) + \
                "="+str(imbalanceAmount)+"】</div>"
            return (False, rl_html)

    def _checkBeginingAmountBalance(self, balance_records):
        '''检查月初余额借方合计'''
        damount = AccountsBalance._sumFieldOf('beginingDamount',
                                              balance_records)
        camount = AccountsBalance._sumFieldOf('beginingCamount',
                                              balance_records)
        imbalanceAmount = damount-camount
        if imbalanceAmount == 0:
            rl_html = "<div><span class='text-success fa fa-check'></span>月初借方余额合计=月初贷方贷方余额合计【" + \
                str(damount) + "=" + str(camount) + "】</div>"
            return (True, rl_html)
        else:
            rl_html = "<div><span class='text-danger fa fa-close'></span>月初借方余额合计=月初贷方余额合计【" +  \
                str(damount) + "-" + str(camount) + \
                "="+str(imbalanceAmount)+"】</div>"
            return (False, rl_html)

    def _checkAmountBalance(self, balance_records):
        '''检查月已发生额借方合计'''
        damount = AccountsBalance._sumFieldOf('damount',
                                              balance_records)
        camount = AccountsBalance._sumFieldOf('camount',
                                              balance_records)
        imbalanceAmount = damount-camount
        if imbalanceAmount == 0:
            rl_html = "<div><span class='text-success fa fa-check'></span>月借方已发生额合计=月贷方已发生额合计【" + \
                str(damount) + "=" + str(camount) + "】</div>"
            return (True, rl_html)
        else:
            rl_html = "<div><span class='text-danger fa fa-exclamation'></span>月借方已发生额合计=月贷方已发生额合计【" + \
                str(damount) + "-" + str(camount) + \
                "="+str(imbalanceAmount)+"】</div>"
            return (False, rl_html)

    def _checkBalance(self, balance_records):
        '''检查资产=负债+所有者权益+收入-成本'''
        return (True, ".....")
# 导入启用期向导


class ImportBeginBalance(models.TransientModel):
    '''导入启动期初向导'''
    _name = "accountcore.import_begin"
    _description = "导入启用期初"
    last_only = fields.Boolean(
        string="只能是明细科目", help="非明细科目不允许导入", readonly=True, default=True)
    control_direction = fields.Boolean(
        string="控制期初余额方向", help="只允许科目的默认余额方向有期初余额", default=True)
    result = fields.Html(string='导入结果', default="")
    auto_create = fields.Boolean(
        string="自动创建核算项目", help="不存在核算项目会尝试自动创建", default=False)
    file = fields.Binary(string="excel文件", attachment=False)
    @ACTools.refuse_role_search
    def do(self):
        '''执行导入'''
        action = {
            'name': '导入启动期初结果',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'accountcore.import_begin',
            'res_id': self.id,
        }
        self.result = ""
        if not self.file:
            self.result = "<div><span class='text-danger fa fa-close'></span><kbd>没有选择excel文件</kbd></div>"
            return action
        book = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        sh = book.sheet_by_index(0)
    # 检查表头
        head_row = sh.row(0)
        self.result = self._checkheader(head_row)
        if len(self.result) > 0:
            return action
    # 清除缓存
        self.env['accountcore.import_begin'].clear_caches()
    # 检查数据行
        self.newItems = []
        for rx in range(1, sh.nrows):
            row = sh.row(rx)
            self.result = self._check_row(row, rx)
            if len(self.result) > 0:
                return action
    # 再次清楚缓存,因为新建了项目
        if self.auto_create:
            self.env['accountcore.import_begin'].clear_caches()
    # 插入数据行
        lost_row = 0
        for rx in range(1, sh.nrows):
            row = sh.row(rx)
            try:
                self._update_row(row)
            except exceptions.ValidationError as e:
                self.result = self.result + "<div><span class='text-danger fa fa-close'></span><kbd>第{}行未导入</kbd>,{}</div>".format(
                    rx-1, e.name)
                lost_row += 1
                continue
        if len(self.result) > 0:
            pass
            self.result = "<div><span class='text-danger fa fa-exclamation'></span><kbd>共{}行</kbd>。完成<kbd>导入{}行</kbd>,另有<kbd>{}行未导入</kbd>。请整理excel数据,不能包含重复行和系统中已存在的记录</div>".format(
                sh.nrows-1, sh.nrows-1-lost_row, lost_row)+self.result
        else:
            self.result = "<div><span class='text-success fa fa-thumbs-o-up'></span>导入完成,一共<kbd>{}</kbd>行。请进入科目初始余额列表界面查看复核</div>".format(
                sh.nrows-1)
        return action

    def _check_row(self, row, rx):
        '''检查行有效性'''
        result = ""
        # 检查机构是否存在
        if not (self._getModelId((row[0].value, 'accountcore.org'))):
            result = result + "<div><span class='text-danger fa fa-close'></span>机构/主体所在列<kbd>{}</kbd>不存在</div>".format(
                row[0].value)
        # 判断日期栏
        if row[1].ctype != 3 and row[1].ctype != 1:
            result = result + "<div><span class='text-danger fa fa-close'></span>日期所在列<kbd>{}</kbd>不是有效的日期格式,正确的格如:<kbd>{}</kbd></div>".format(
                row[1].value, "2020-5-12")
        if row[1].ctype == 1:
            try:
                time.strptime(row[1].value, "%Y-%m-%d")
            except Exception:
                result = result + "<div><span class='text-danger fa fa-close'></span>日期所在列<kbd>{}</kbd>不是有效的日期格式,正确的格如:<kbd>{}</kbd></div>".format(
                    row[1].value, "2020-5-12")
        # 检查科目是否存在
        accountId = self._getModelId((row[3].value, 'accountcore.account'))
        if not accountId:
            result = result + "<div><span class='text-danger fa fa-close'></span>科目所在列<kbd>{}</kbd>不存在</div>".format(
                row[3].value)
        else:
            account = self.env['accountcore.account'].sudo().browse(accountId)
            # 判断金额方向
            if self.control_direction:
                if account.direction == "1" and row[7].ctype == 2 and row[7].value > 0:
                    result = result + "<div><span class='text-danger fa fa-close'></span>科目<kbd>{}</kbd>期初贷方有余额<kbd>{}</kbd></div>".format(
                        row[3].value, row[7].value)
                if account.direction == "-1" and row[6].ctype == 2 and row[6].value > 0:
                    result = result + "<div><span class='text-danger fa fa-close'></span>科目<kbd>{}</kbd>期初借方有余额<kbd>{}</kbd></div>".format(
                        row[3].value, row[6].value)
            # 判断是否末级科目
            if self.last_only and not account.is_last:
                result = result + "<div><span class='text-danger fa fa-close'></span>有非末级科目<kbd>{}</kbd></div>".format(
                    row[3].value)
            # 如果科目后设有作为明细科目核算的项目类别
            if account.accountItemClass:
                itemclassId = self._getModelId(
                    (row[4].value, 'accountcore.itemclass'))
                # 判断核算项目类别是否和科目匹配
                if not itemclassId or account.accountItemClass.id != itemclassId:
                    result = result + "<div><span class='text-danger fa fa-close'></span>核算项目类别<kbd>{}</kbd>和科目<kbd>{}</kbd>不匹配</div>".format(
                        row[4].value, row[3].value)
                else:
                    # 检查核算项目
                    itemId = self._getModelId(
                        (row[5].value, 'accountcore.item'))
                    if not itemId:
                        if not self.auto_create:
                            result = result + "<div><span class='text-danger fa fa-close'></span>核算项目列<kbd>{}</kbd>不存在</div> ".format(
                                row[5].value)
                        # 控制是否新增核算项目
                        elif row[5].value not in self.newItems:
                            self.env["accountcore.item"].sudo().create(
                                {"name": row[5].value, "itemClass": itemclassId})
                            self.newItems.append(row[5].value)
                    else:
                        if itemclassId != self.env['accountcore.item'].sudo().browse(itemId).itemClass.id:
                            result = result + "<div><span class='text-danger fa fa-close'></span>核算项目列<kbd>{}</kbd>不属于核算项目类别<kbd>{}</kbd></div> ".format(
                                row[5].value, row[4].value)
            else:
                if any([row[4].value, row[5].value]):
                    result = result + "<div><span class='text-danger fa fa-close'></span>科目所在列<kbd>{}</kbd>和核算项目类别<kbd>{}</kbd>核算项目<kbd>{}</kbd>不匹配</div> ".format(
                        row[3].value, row[4].value, row[5].value)
        # 判断金额栏
        for col in range(6, 12):
            if len(str(row[col].value)) > 0 and row[col].ctype != 2:
                result = result + "<div><span class='text-danger fa fa-close'></span>金额相关列<kbd>{}</kbd>不是数字</div> ".format(
                    row[col].value)
        if len(result) > 0:
            result = "<div><kbd>第{}行</kbd>出现如下错误:</div>".format(rx-1)+result
        return result

    def _update_row(self, row):
        '''导入行'''
        _createdate = row[1].value
        if row[1].ctype == 3:
            _createdate_tuple = self._getTupleDate(_createdate)
        elif row[1].ctype == 1:
            _createdate_tuple = self._get_createdate_tuple(row[1].value)
        _createDate = datetime.datetime(*_createdate_tuple)
        _org = self._getModelId((row[0].value, 'accountcore.org'))
        _account = self._getModelId((row[3].value, 'accountcore.account'))
        _items = self._getModelId((row[5].value, 'accountcore.item'))
        _beginingDamount = self._str2float(row[6].value)
        _beginingCamount = self._str2float(row[7].value)
        _damount = self._str2float(row[8].value)
        _camount = self._str2float(row[9].value)
        _beginCumulativeDamount = self._str2float(
            row[10].value) if _createdate_tuple[1] > 1 else 0
        _beginCumulativeCamount = self._str2float(
            row[11].value) if _createdate_tuple[1] > 1 else 0
        balance = {'createDate': _createDate,
                   'isbegining': True,
                   'beginingDamount': _beginingDamount,
                   'beginingCamount': _beginingCamount,
                   'damount': _damount,
                   'camount': _camount,
                   'endDamount': _beginingDamount+_damount,
                   'endCamount': _beginingCamount+_camount,
                   'cumulativeDamount': _damount+_beginCumulativeDamount,
                   'cumulativeCamount': _camount+_beginCumulativeCamount,
                   'beginCumulativeDamount': _beginCumulativeDamount,
                   'beginCumulativeCamount': _beginCumulativeCamount,
                   'org': _org,
                   'year': _createdate_tuple[0],
                   'month': _createdate_tuple[1],
                   'account': _account,
                   'items': _items}
        self.env['accountcore.accounts_balance'].sudo().create(balance)

    def _checkheader(self, row):
        '''检查导入的excel的表头格式'''
        result = ""
        headers = ["所属机构/主体",
                   "创建日期",
                   "科目类别",
                   "会计科目",
                   "核算项目类别",
                   "核算项目",
                   "期初借方",
                   "期初贷方",
                   "本期借方金额",
                   "本期贷方金额",
                   "月初本年借方累计",
                   "月初本年贷方累计"]
        for i in range(0, len(headers)):
            if headers[i] != row[i].value:
                result = result + "<div><span class='text-danger fa fa-close'></span>表头不正确, <kbd>{}</kbd>单元格的位置应该为<kbd>{}</kbd></div>".format(
                    row[i].value, headers[i])
        return result

    @tools.ormcache('name_model')
    def _getModelId(self, name_model):
        '''更据名称和模型查找ID'''
        if not name_model[0]:
            return False
        record = self.env[name_model[1]].sudo().search(
            [('name', '=', name_model[0])], limit=1)
        if record.exists():
            return record.id
        return False

    @tools.ormcache('date')
    def _getTupleDate(self, date):
        '''日期单元格转换成元组'''
        return xlrd.xldate_as_tuple(date, 0)

    @tools.ormcache('value')
    def _get_createdate_tuple(self, value):
        '''日期单元格字符串转换成日期元组'''
        split_str = "-"
        if value.find("/") >= 0:
            split_str = "/"
        elif value.find("\\") >= 0:
            split_str = '\\'
        year_s, mon_s, day_s = value.split(split_str)
        return (int(year_s), int(mon_s), int(day_s), 0, 0, 0)

    def _str2float(self, str):
        '''金额单元格转换成数字'''
        try:
            return float(str)
        except Exception as e:
            pass
            return 0
