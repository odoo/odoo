# -*- coding: utf-8 -*-
import base64
import xlrd
import copy
import datetime
import time
import re
import requests
from odoo import exceptions
from odoo import fields
from odoo import models
from odoo import tools
from ..models.ac_obj import ACTools
from ..models.ac_obj import AutoCreate
from ..models.main_models import AccountsBalance

# 导入凭证向导


class ImportVouchers(models.TransientModel):
    '''导入凭证向导'''
    _name = "accountcore.import_vouchers"
    _description = "导入凭证期初"
    last_only = fields.Boolean(
        string="只能是明细科目", help="非明细科目不允许导入", readonly=True, default=True)
    result = fields.Html(string='导入结果', default="")
    auto_create = fields.Boolean(
        string="自动创建明细科目项目", help="不存在机构,科目,核算项目类别,核算项目等会尝试自动创建", default=False)
    file = fields.Binary(string="excel文件", attachment=False)

    @ACTools.refuse_role_search
    def do(self):
        '''执行导入'''
        action = {
            'name': '导入凭证结果',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'accountcore.import_vouchers',
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
        self.env['accountcore.import_vouchers'].clear_caches()
    # 检查数据行
        self.newItems = []
        start = 1
        end = 1
        vouchers = []
        self.result = self._check_row(sh.row(1), 1)
        if len(self.result) > 0:
            return action
        for rx in range(2, sh.nrows):
            row = sh.row(rx)
            self.result = self._check_row(row, rx)
            if len(self.result) > 0:
                return action
            try:
                next_v_number = int(sh.row(rx)[13].value)
            except Exception:
                self.result = "<div><span class='text-danger fa fa-close'></span><kbd>第{}行</kbd>的<kbd>凭证号{}</kbd>不是整数</div>".format(
                    rx+1, sh.row(rx)[13].value)
                return action
            try:
                pre_v_number = int(sh.row(rx-1)[13].value)
            except Exception:
                self.result = "<div><span class='text-danger fa fa-close'></span><kbd>第{}行</kbd>的<kbd>凭证号{}</kbd>不是整数</div>".format(
                    rx, sh.row(rx+1)[13].value)
                return action
            if pre_v_number != next_v_number or sh.row(rx)[1].value != sh.row(rx-1)[1].value:
                end = rx-1
                result = self._check_voucher(sh.row, start, end)
                if len(result) > 0:
                    voucher_date_cell = sh.row(start)[0]
                    voucher_date = (datetime.datetime(*xlrd.xldate_as_tuple(voucher_date_cell.value, 0))).strftime(
                        "%Y-%m-%d") if voucher_date_cell.ctype == 3 else voucher_date_cell.value
                    self.result = "<div>机构/主体<kbd>{}</kbd>记账日期为<kbd>{}</kbd>的<kbd>{}号凭证</kbd>出现如下错误:</div>".format(
                        sh.row(start)[1].value, voucher_date, pre_v_number)+result
                    return action
                vouchers.append(copy.copy((start, end)))
                start = rx
        result = self._check_voucher(sh.row, start, sh.nrows-1)
        if len(result) > 0:
            v_date_cell = sh.row(start)[0]
            v_date = (datetime.datetime(*xlrd.xldate_as_tuple(v_date_cell.value, 0))
                      ).strftime("%Y-%m-%d") if v_date_cell.ctype == 3 else v_date_cell.value
            self.result = "<div><span class='text-danger fa fa-close'></span>机构/主体<kbd>{}</kbd>记账日期为<kbd>{}</kbd>的<kbd>{:.0f}号凭证</kbd>出现如下错误:</div>".format(
                sh.row(start)[1].value, v_date, float(sh.row(start)[13].value))+result
            return action
        vouchers.append(copy.copy((start, sh.nrows-1)))
    # 再次清除缓存,因为新建了项目
        if self.auto_create:
            self.env['accountcore.import_vouchers'].clear_caches()
    # 导入凭证
        lost_count = 0
        voucher_count = len(vouchers)
        for v in vouchers:
            voucher_info = [sh.row(rx_) for rx_ in range(v[0], v[1]+1)]
            try:
                self._create_voucher(voucher_info)
            except Exception as e:
                lost_count += 1
                reason = e.name if hasattr(e, "name") else str(e)
                self.result = self.result + \
                    "<div><span class='text-danger fa fa-close'></span><kbd>第{}到{}行未导入</kbd>,{}</div>".format(
                        v[0]+1, v[1]+1, reason)
                continue
        if len(self.result) > 0:
            self.result = "<div><span class='text-danger fa fa-exclamation'></span><kbd>共{}张凭证</kbd>。完成<kbd>导入{}张凭证</kbd>,另有<kbd>{}张未导入</kbd>。请整理excel数据,修改未导入凭证并删除已导入凭证,避免重复导入。</div>".format(
                voucher_count, voucher_count-lost_count, lost_count)+self.result
        else:
            self.result = "<div><span class='text-success fa fa-thumbs-o-up'></span>导入完成,一共<kbd>{}张凭证</kbd>。请进入管理凭证菜单,在凭证列表界面查看复核</div>".format(
                voucher_count)
        return action

    def _check_row(self, row, rx):
        '''检查行有效性'''
        result = ""
        # 检查必有项目为空值
        result += self._check_is_empty(row)
        # 检查记账日期业务日期格式
        result += self._check_vouhcer_date(row)
        # 检查记账日期业务日期格式
        result += self._check_real_date(row)
        # 检查金额逻辑
        result += self._check_amount(row)
        # 如果没有勾选自动创建执行的检查
        # 检查机构/主体是否存在
        orgId = self._getIdOf(row[1].value, "accountcore.org")
        if not orgId:
            if not self.auto_create:
                result += "<div><span class='text-danger fa fa-close'></span>机构/主体<kbd>{}</kbd>在系统中不存在</div> ".format(
                    row[1].value)
        # 检查科目是否存在
        accountId = self._getIdOf(row[4].value, "accountcore.account")
        if not accountId:
            if not self.auto_create:
                result += "<div><span class='text-danger fa fa-close'></span>会计科目<kbd>{}</kbd>在系统中不存在</div> ".format(
                    row[4].value)
            else:
                # 自动新增科目,判断科目的一级科目是否存,一级科目不能通过导入自动新增
                first_accountName = ACTools.splitAccountName(row[4].value)[0]
                if self._getIdOf(first_accountName, 'accountcore.account') == 0:
                    result += "<div><span class='text-danger fa fa-close'></span>会计科目<kbd>{}</kbd>的一级科目{}在系统中不存在,可能是拼写错误。一级科目是不能自动新增的</div> ".format(
                        row[4].value, first_accountName)
            # 检查核算项目是否和类型比匹配
            auto_itemId = self._getIdOf(row[6].value, "accountcore.item")
            if auto_itemId:
                auto_item = self.env['accountcore.item'].sudo().browse(
                    auto_itemId)
                if auto_item.item_class_name != row[5].value:
                    result += "<div><span class='text-danger fa fa-close'></span>核算项目名称<kbd>{}</kbd>不属于核算项目类别<kbd>{}</kbd></div> ".format(
                        row[6].value, row[5].value)
            # 检查统计项目是否和类别匹配
            auto_class_items = self._get_statticticsItems(row[7].value)
            for i in auto_class_items:
                if i[0] == str(row[5].value) and row[5].ctype != 0:
                    result += "<div><span class='text-danger fa fa-close'></span>统计项目类别<kbd>{}</kbd>和核算项目类别<kbd>{}</kbd>重复,一个类别不能同时是核算项目又是统计项目</div> ".format(
                        i[0], str(row[5].value))
                auto_statticticsId = self._getIdOf(i[1], "accountcore.item")
                if not auto_statticticsId:
                    if not self.auto_create:
                        result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>在系统中不存在</div> ".format(
                            i[1])
                else:
                    auto_stattictics = self.env['accountcore.item'].sudo().browse(
                        auto_statticticsId)
                    if auto_stattictics.item_class_name != i[0]:
                        result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>不属于类别<kbd>{}</kbd></div> ".format(
                            auto_stattictics.name, i[0])
        else:
            account = self.env['accountcore.account'].sudo().browse(accountId)
            # 判断是否末级科目
            if self.last_only and not account.is_last:
                result = self.result + "<div><span class='text-danger fa fa-close'></span>有非末级科目<kbd>{}</kbd></div>".format(
                    row[4].value)
            # 如果科目后有必选核算项目,检查项目类别,项目是否和科目匹配
            if account.accountItemClass:
                if account.accountItemClass.name != str(row[5].value):
                    result += "<div><span class='text-danger fa fa-close'></span>核算项目类别<kbd>{}</kbd>和科目<kbd>{}</kbd>不匹配</div>".format(
                        row[5].value, row[4].value)
                else:
                    itemId = self._getIdOf(row[6].value, "accountcore.item")
                    if itemId:
                        item = self.env['accountcore.item'].sudo().browse(
                            itemId)
                        if item.item_class_name != row[5].value:
                            result += "<div><span class='text-danger fa fa-close'></span>核算项目名称<kbd>{}</kbd>不属于核算项目类别<kbd>{}</kbd></div> ".format(
                                row[6].value, row[5].value)
                    else:
                        if not self.auto_create:
                            result += "<div><span class='text-danger fa fa-close'></span>核算项目名称<kbd>{}</kbd>在系统中不存在</div> ".format(
                                row[6].value)
            # 检查统计项目是否和科目匹配
            if account.itemClasses:
                if account.accountItemClass:
                    itemClassNames = [
                        itemClass.name for itemClass in account.itemClasses if itemClass.id != account.accountItemClass.id]
                else:
                    itemClassNames = [
                        itemClass.name for itemClass in account.itemClasses]
                _class_items = self._get_statticticsItems(row[7].value)
                for ii in _class_items:
                    if ii[0] == str(row[5].value) and row[5].ctype != 0:
                        result += "<div><span class='text-danger fa fa-close'></span>统计项目类别<kbd>{}</kbd>和核算项目类别<kbd>{}</kbd>重复,一个类别不能同时是核算项目又是统计项目</div> ".format(
                            ii[0], str(row[5].value))
                    if (ii[0] not in itemClassNames):
                        if not self.auto_create:
                            result += "<div><span class='text-danger fa fa-close'></span>统计项目类别<kbd>{}</kbd>和科目<kbd>{}</kbd>不匹配</div> ".format(
                                ii[0], row[4].value)
                        else:
                            statticticsId = self._getIdOf(
                                ii[1], "accountcore.item")
                            if not statticticsId:
                                if not self.auto_create:
                                    result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>在系统中不存在</div> ".format(
                                        ii[1])
                            else:
                                stattictics = self.env['accountcore.item'].sudo().browse(
                                    statticticsId)
                                if stattictics.item_class_name != ii[0]:
                                    result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>不属于类别<kbd>{}</kbd></div> ".format(
                                        stattictics.name, ii[0])
                    else:
                        statticticsId = self._getIdOf(
                            ii[1], "accountcore.item")
                        if not statticticsId:
                            if not self.auto_create:
                                result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>在系统中不存在</div> ".format(
                                    ii[1])
                        else:
                            stattictics = self.env['accountcore.item'].sudo().browse(
                                statticticsId)
                            if stattictics.item_class_name != ii[0]:
                                result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>不属于类别<kbd>{}</kbd></div> ".format(
                                    stattictics.name, ii[0])
            else:
                # 检查统计项目是否和类别匹配
                auto_class_items = self._get_statticticsItems(row[7].value)
                for iii in auto_class_items:
                    if iii[0] == str(row[5].value) and row[5].ctype != 0:
                        result += "<div><span class='text-danger fa fa-close'></span>统计项目类别<kbd>{}</kbd>和核算项目类别<kbd>{}</kbd>重复,一个类别不能同时是核算项目又是统计项目</div> ".format(
                            iii[0], str(row[5].value))
                    auto_statticticsId = self._getIdOf(
                        iii[1], "accountcore.item")
                    if not auto_statticticsId:
                        if not self.auto_create:
                            result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>在系统中不存在</div> ".format(
                                iii[1])
                    else:
                        auto_stattictics = self.env['accountcore.item'].sudo().browse(
                            auto_statticticsId)
                        if auto_stattictics.item_class_name != iii[0]:
                            result += "<div><span class='text-danger fa fa-close'></span>统计项目<kbd>{}</kbd>不属于类别<kbd>{}</kbd></div> ".format(
                                auto_stattictics.name, iii[0])
        # 检查现金流量项目是否存在
        if row[10].ctype != 0 and not self._getIdOf(row[10].value, "accountcore.cashflow"):
            result += "<div><span class='text-danger fa fa-close'></span>现金流量<kbd>{}</kbd>在系统中不存在</div> ".format(
                row[10].value)
        if len(result) > 0:
            result = "<div><kbd>第{}行</kbd>出现如下错误:</div>".format(rx+1)+result
        return result

    def _create_voucher(self, voucher_info):
        '''创建凭证'''
        data = self._build_voucher_data(voucher_info)
        AutoCreate._check_voucher_logic(self, data)
        v = AutoCreate._build_voucher(
            self, self.auto_create, data, self.env.user)
        voucher = self.env['accountcore.voucher'].sudo().create(v)
        return voucher

    def _build_voucher_data(self, voucher_info):
        '''购建推送的json数据'''
        entrys = []
        for row in voucher_info:
            items = []
            if row[5].ctype != 0 and row[6].ctype != 0:
                items.append([row[5].value, True, row[6].value])
            if row[7].ctype != 0:
                statticticsItems = self._get_statticticsItems(row[7].value)
                for item in statticticsItems:
                    items.append([item[0], False, item[1]])
            entry = {
                "account": {
                    "name": str(row[4].value),
                },
                "damount": row[8].value,
                "camount": row[9].value,
                "explain": str(row[2].value),
                "items": items,
            }
            if row[10].ctype != 0:
                entry.update({"cashFlow": str(row[10].value)})
            entrys.append(entry)
        voucher_date_cell = voucher_info[0][0]
        voucherdate_str = (datetime.datetime(*xlrd.xldate_as_tuple(voucher_date_cell.value, 0))).strftime(
            "%Y-%m-%d") if voucher_date_cell.ctype == 3 else voucher_date_cell.value
        data = {
            "voucherdate": voucherdate_str,
            "org": voucher_info[0][1].value,
            "v_number": voucher_info[0][13].value,
            "appendixCount": voucher_info[0][11].value,
            "soucre": "导入",
            "state": "creating",
            "entrys": entrys
        }
        if voucher_info[0][12].ctype != 0:
            real_date_cell = voucher_info[0][12]
            real_date_str = (datetime.datetime(*xlrd.xldate_as_tuple(real_date_cell.value, 0))).strftime(
                "%Y-%m-%d") if real_date_cell.ctype == 3 else real_date_cell.value
            data.update({"real_date": real_date_str})
        return data

    def _checkheader(self, row):
        '''检查导入的excel的表头格式'''
        result = ""
        headers = ["记账日期",
                   "机构/主体",
                   "分录摘要",
                   "科目编码",
                   "会计科目",
                   "核算项目类别",
                   "核算项目名称",
                   "统计项目",
                   "借方金额",
                   "贷方金额",
                   "现金流量项目",
                   "附件张数",
                   "业务日期",
                   "凭证号"]
        for i in range(0, len(headers)):
            if headers[i] != row[i].value:
                result = result + "<div><span class='text-danger fa fa-close'></span>表头不正确, <kbd>{}</kbd>表头单元格的位置应该为<kbd>{}</kbd>,正确的表头应为:{}</div>".format(
                    row[i].value, headers[i], ','.join(headers))
        return result

    def _check_is_empty(self, row):
        '''检查必有项是否为空'''
        result = ""
        if row[0].ctype == 0:
            result += "<div><span class='text-danger fa fa-close'></span>记账日期<kbd>{}</kbd>为空值</div> ".format(
                row[0].value)
        if row[1].ctype == 0:
            result += "<div><span class='text-danger fa fa-close'></span>机构/主体<kbd>{}</kbd>为空值</div> ".format(
                row[1].value)
        if row[4].ctype == 0:
            result += "<div><span class='text-danger fa fa-close'></span>会计科目<kbd>{}</kbd>为空值</div> ".format(
                row[4].value)
        if row[13].ctype == 0:
            result += "<div><span class='text-danger fa fa-close'></span>凭证号<kbd>{}</kbd>为空值</div> ".format(
                row[13].value)
        return result
        # 检查记账日期栏

    def _check_vouhcer_date(self, row):
        '''检查记账日期格式'''
        result = ""
        if row[0].ctype != 3 and row[0].ctype != 1:
            result += "<div><span class='text-danger fa fa-close'></span>记账日期<kbd>{}</kbd>不是有效的日期格式,正确的格如:<kbd>{}</kbd></div>".format(
                row[0].value, "2020-5-12")
        if row[0].ctype == 1:
            try:
                time.strptime(row[0].value, "%Y-%m-%d")
            except Exception:
                result += "<div><span记账日期 class='text-danger fa fa-close'></span记账日期<kbd>{}</kbd>不是有效的日期格式,正确的格如:<kbd>{}</kbd></div>".format(
                    row[0].value, "2020-5-12")
        return result
        # 检查业务日期栏

    def _check_real_date(self, row):
        '''检查业务日期'''
        result = ""
        if row[12].ctype != 3 and row[12].ctype != 1 and row[12].ctype != 0:
            result += "<div><span class='text-danger fa fa-close'></span>业务日期<kbd>{}</kbd>不是有效的日期格式,正确的格如:<kbd>{}</kbd></div>".format(
                row[12].value, "2020-5-12")
        if row[12].ctype == 1:
            try:
                time.strptime(row[12].value, "%Y-%m-%d")
            except Exception:
                result += "<div><span class='text-danger fa fa-close'></span>业务日期<kbd>{}</kbd>不是有效的日期格式,正确的格如:<kbd>{}</kbd></div>".format(
                    row[12].value, "2020-5-12")
        return result

    def _getIdOf(self, name, model_name):
        '''通过模型名称获取ID'''
        return self._getModelId((name, model_name))

    def _check_amount(self, row):
        '''检查金额'''
        result = ""
        if row[8].ctype != 0 and row[8].ctype != 2:
            result += "<div><span class='text-danger fa fa-close'></span>借方金额<kbd>{}</kbd>不是数字</div> ".format(
                row[8].value)
        if row[9].ctype != 0 and row[9].ctype != 2:
            result += "<div><span class='text-danger fa fa-close'></span>贷方金额<kbd>{}</kbd>不是数字</div> ".format(
                row[9].value)
        d_amount = ACTools.str2float(row[8].value)
        c_amount = ACTools.str2float(row[9].value)
        if d_amount != 0 and c_amount != 0:
            result += "<div><span class='text-danger fa fa-close'></span><kbd>分录借贷方不能同时有金额</kbd></div>"
        if d_amount == 0 and c_amount == 0:
            result += "<div><span class='text-danger fa fa-close'></span><kbd>分录借贷方不能同时为零</kbd></div>"
        return result

    def _check_voucher(self, sheet_rows, start, end):
        '''检查凭证整体'''
        result = ""
        if start == end:
            return "<div><span class='text-danger fa fa-close'></span><kbd>第{}行</kbd>只有一条分录</div>".format(start+1)
        # 借贷方金额合计
        d_amount = 0
        c_amount = 0
        org_name = (sheet_rows(start)[1]).value
        voucher_date = self._cell2tuple(sheet_rows(start)[0])
        for i in range(start, end+1):
            d_amount = d_amount+ACTools.str2float(sheet_rows(i)[8].value)
            c_amount = c_amount+ACTools.str2float(sheet_rows(i)[9].value)
            _voucher_date = self._cell2tuple(sheet_rows(i)[0])
            for n in range(0, 3):
                if voucher_date[n] != _voucher_date[n]:
                    result += "<div><span class='text-danger fa fa-close'></span><kbd>第{}行</kbd>所在凭证,各分录行的<kbd>凭证的记账日期不一致</kbd></div>".format(
                        i+1)
            if sheet_rows(i)[1].value != org_name:
                result += "<div><span class='text-danger fa fa-close'></span><kbd>第{}行</kbd>,<kbd>凭证分录的机构/主体不一致</kbd></div>".format(
                    i+1)
        if ACTools.TranslateToDecimal(d_amount) != ACTools.TranslateToDecimal(c_amount):
            result += "<div><span class='text-danger fa fa-close'></span><kbd>第{}行</kbd>所在凭证,<kbd>凭证分录的借方合计不等于贷方合计</kbd></div>".format(
                start+1)
        return result

    def _get_statticticsItems(self, str_):
        '''转换统计项目字符串'''
        if len(str_) == 0:
            return []
        rl = []
        class_item = re.split('/|／', str(str_))
        for i in class_item:
            _class_item = re.split(':|：', i)
            if len(_class_item[0]) == 0 or len(_class_item[1]) == 0:
                raise exceptions.ValidationError(
                    '统计项目列格式不正确,分割符号缺少需要统计项目类别和统计项目')
            rl.append(_class_item)
        return rl

    @tools.ormcache('name_model')
    def _getModelId(self, name_model):
        '''更据名称和模型查找ID'''
        if not name_model[0]:
            return 0
        record = self.env[name_model[1]].sudo().search(
            [('name', '=', name_model[0])], limit=1)
        if record.exists():
            return record.id
        return 0

    @tools.ormcache('date')
    def _date2tuple(self, date):
        '''日期单元格转换成元组'''
        return xlrd.xldate_as_tuple(date, 0)

    @tools.ormcache('value')
    def _dateStr2tuple(self, value):
        '''日期单元格字符串转换成日期元组'''
        split_str = "-"
        if value.find("/") >= 0:
            split_str = "/"
        elif value.find("\\") >= 0:
            split_str = '\\'
        year_s, mon_s, day_s = value.split(split_str)
        return (int(year_s), int(mon_s), int(day_s), 0, 0, 0)

    def _cell2tuple(self, cell):
        '''类日期单元格数据转换成日期tuple形式'''
        if cell.ctype == 3:
            voucher_date = self._date2tuple(cell.value)
        elif cell.ctype == 1:
            voucher_date = self._dateStr2tuple(cell.value)
        return voucher_date
