
# -*- coding: utf-8 -*-
import datetime
import io
import json
import operator
import re

from odoo import http, exceptions
from odoo.tools import pycompat
from odoo.tools.misc import xlsxwriter
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.http import serialize_exception, request
from odoo.addons.web.controllers.main import ExportFormat, ExportXlsxWriter, GroupExportXlsxWriter, content_disposition

# 导出EXCLE的基类


class AC_ExportXlsxWriter(ExportXlsxWriter):
    def __init__(self, field_names, row_count=0, listType=None):
        self.listType = listType
        self.field_names = field_names
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.base_style = self.workbook.add_format({'text_wrap': True})
        self.base_style.set_font_size(10)
        self.header_style = self.workbook.add_format({'bold': True})
        self.header_style.set_align('center')
        self.header_style.set_font_size(10)
        self.header_bold_style = self.workbook.add_format(
            {'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'})
        self.header_bold_style.set_font_size(10)
        self.date_style = self.workbook.add_format(
            {'text_wrap': True, 'num_format': 'yyyy-mm-dd'})
        self.date_style.set_font_size(10)
        self.datetime_style = self.workbook.add_format(
            {'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.datetime_style.set_font_size(10)
        self.worksheet = self.workbook.add_worksheet()
        self.value = False

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(_('导出的行数过多 (%s 行, 上限为: %s 行) , 请分多次导出') %
                            (row_count, self.worksheet.xls_rowmax))

    def write_header(self):
        for i, fieldname in enumerate(self.field_names):
            self.write(0, i, fieldname, self.header_style)
            self.worksheet.set_column(i, i, self.setColumnWidth(fieldname))

    def setColumnWidth(self, fieldname):
        return AC_ExcelExport.widths.get(fieldname, AC_ExcelExport.default_widths)


class AC_ExcelExport(ExportFormat, http.Controller):
    raw_data = True
    default_widths = 30
    widths = {"策略号": 6,
              "贷方金额": 10,
              "分录摘要": 30,
              "附件张数": 7,
              "机构/主体": 28,
              "机构/主体编码": 10,
              "机构/主体名称": 25,
              "核算类别": 20,
              "核算统计项目": 30,
              "核算项目编码": 12,
              "核算项目类别": 11,
              "核算项目名称": 30,
              "会计科目": 30,
              "记账日期": 10,
              "借方金额": 10,
              "科目编码": 8,
              "科目类别": 12,
              "科目名称": 30,
              "末级科目": 7,
              "凭证的标签": 8,
              "凭证号": 6,
              "凭证来源": 7,
              "凭证中可选": 8,
              "全局标签": 30,
              "审核人": 12,
              "所属机构/主体": 30,
              "所属科目体系": 15,
              "所属凭证": 9,
              "唯一编号": 9,
              "现金流量": 37,
              "业务日期": 10,
              "余额方向": 7,
              "制单人": 12,
              "创建日期": 10,
              "期初借方": 10,
              "期初贷方": 10,
              "本期借方金额": 10,
              "本期贷方金额": 10,
              "月初本年借方累计": 10,
              "月初本年贷方累计": 10,
              "作为明细科目的类别": 10,
              "统计项目": 30,
              "会计科目和核算统计项目": 40,
              "业务标识": 12,
              }

    def index_base(self, data, token, listType):
        params = json.loads(data)
        model, fields, ids, domain = \
            operator.itemgetter('model', 'fields', 'ids',
                                'domain')(params)
        # 表头
        columns_headers = listType.get_colums_headers(fields)
        self.column_count = len(columns_headers)
        Model = request.env[model].sudo().with_context(
            **params.get('context', {}))
        Model = request.env[model].with_context(**params.get('context', {}))
        records = Model.browse(ids) or Model.search(
            domain, offset=0, limit=False, order=False)
        self.row_count = len(records)
        # 表体
        export_data = listType.get_export_data(records)
        response_data = self.from_data(columns_headers, export_data, listType)
        return request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(self.filename(Model._description))),
                                              ('Content-Type', self.content_type)],
                                     cookies={'fileToken': token})

    def ac_index_base(self, listType, file_name):
        ''''自定义直接下载'''
        # 表头
        columns_headers = listType.get_colums_headers(fields=[])
        self.column_count = len(columns_headers)
        # 表体
        export_data = listType.get_export_data([])
        self.row_count = len(export_data)
        response_data = self.from_data(columns_headers, export_data, listType)
        return request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(self.filename(file_name))),
                                              ('Content-Type', self.content_type)],
                                     cookies={'fileToken': ""})

    @property
    def content_type(self):
        return 'application/vnd.ms-excel'

    def filename(self, base):
        return base + '.xlsx'

    def from_data(self, fields, rows, listType):
        with AC_ExportXlsxWriter(fields, len(rows), listType) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(
                        row_index + 1, cell_index, cell_value)
        return xlsx_writer.value

    @http.route('/web/export/accountcore.voucher', type='http', auth="user")
    # @serialize_exception
    def accountcore_voucher(self, data, token):
        listType = ExcelExportVouchers()
        return self.index_base(data, token, listType)

    @http.route('/web/export/accountcore.entry', type='http', auth="user")
    # @serialize_exception
    def accountcore_entry(self, data, token):
        listType = ExcelExportEntrys()
        return self.index_base(data, token, listType)

    @http.route('/web/export/accountcore.account', type='http', auth="user")
    # @serialize_exception
    def accountcore_account(self, data, token):
        listType = ExcelExportAccounts()
        return self.index_base(data, token, listType)

    @http.route('/web/export/accountcore.item', type='http', auth="user")
    # @serialize_exception
    def accountcore_item(self, data, token):
        listType = ExcelExportItems()
        return self.index_base(data, token, listType)

    @http.route('/web/export/accountcore.org', type='http', auth="user")
    # @serialize_exception
    def accountcore_org(self, data, token):
        listType = ExcelExportOrgs()
        return self.index_base(data, token, listType)

    # 导出启用期初余额模板
    @http.route('/web/export/accountcore.begin_model', type='http', auth="user")
    def accountcore_begin_model(self, data='{}', token=""):
        self.env = request.env
        accounts = self.env["accountcore.account"].search(
            ["|", ("org.user_ids", 'in', self.env.user.id), ("org", '=?', False), ('is_last', '=', True)])
        listType = ExcelExportBeginModel(accounts, "某公司", "2020-01-01")
        return self.ac_index_base(listType, '初始余额导入模板')

    # 导出凭证模板
    @http.route('/web/export/accountcore.import_vouchers_model', type='http', auth="user")
    def accountcore_import_vouchers_model(self, data='{}', token=""):
        listType = ExcelExportVoucherModel()
        return self.ac_index_base(listType, '凭证导入模板')

# 凭证列表导出EXCEL


class ExcelExportVouchers():
    def get_colums_headers(self, fields):
        columns_headers = ['记账日期',
                           '机构/主体',
                           '分录摘要',
                           '科目编码',
                           '会计科目和核算统计项目',
                           '借方金额',
                           '贷方金额',
                           '现金流量',
                           '凭证号',
                           '唯一编号',
                           '制单人',
                           '审核人',
                           '业务标识',
                           '全局标签',
                           '凭证来源',
                           '凭证的标签',
                           '策略号',
                           '附件张数']
        return columns_headers

    def get_export_data(self, records):
        export_data = []
        vouchers = records
        for v in vouchers:
            glob_tags = [g.name for g in v.glob_tag]
            glot_tags_str = '/'.join(glob_tags)
            voucher_before_entry = [v.voucherdate, v.org.name]
            _reviewer = v.reviewer.name if v.reviewer else ""
            _b_source = v.b_source if v.b_source else ""
            v_after_entry = [v.v_number,
                             v.uniqueNumber,
                             v.createUser.name,
                             _reviewer,
                             _b_source,
                             glot_tags_str,
                             v.soucre.name,
                             re.sub(r'<br>|<p>|</p>', '', v.roolbook_html),
                             v.number,
                             v.appendixCount]
            entrys = v.entrys
            for e in entrys:
                items_html = re.sub(r'<br>|<p>|</p>', '', e.items_html)
                _explain = e.explain if e.explain else ""
                _cashFlow = e.cashFlow.name if e.cashFlow else ""
                entry = [_explain, e.account.number, items_html,
                         e.damount, e.camount, _cashFlow]
                entry_line = []
                entry_line.extend(voucher_before_entry)
                entry_line.extend(entry)
                entry_line.extend(v_after_entry)
                export_data.append(entry_line)
        return export_data


# 分录列表导出EXCEL


class ExcelExportEntrys():
    def get_colums_headers(self, fields):
        columns_headers = ['记账日期',
                           '机构/主体',
                           '分录摘要',
                           '科目编码',
                           '会计科目',
                           '核算项目类别',
                           '核算项目名称',
                           '统计项目',
                           '借方金额',
                           '贷方金额',
                           '现金流量项目',
                           '附件张数',
                           '业务日期',
                           '凭证号',
                           '所属凭证',
                           '全局标签',
                           '会计科目和核算统计项目']
        return columns_headers

    def get_export_data(self, records):
        export_data = []
        entry = records.sorted(key=lambda r: (
            r.org, r.v_voucherdate, r.v_voucherdate, r.v_number, r.voucher.name))
        for e in entry:
            glob_tags = [g.name for g in e.glob_tag]
            glot_tags_str = '/'.join(glob_tags)
            statisticsItems = e.getStatisticsItems()
            statticticsItems_str = "/".join(
                [item.item_class_name+":"+item.name for item in statisticsItems])
            _explain = e.explain if e.explain else ""
            _accountItemCalss = e.account.accountItemClass.name if e.account.accountItemClass else ""
            _itemName = e.account_item.name if e.account_item else ""
            _cashFlow = e.cashFlow.name if e.cashFlow else ""
            _realdate = e.v_real_date if e.v_real_date else ""
            items_html = re.sub(r'<br>|<p>|</p>', '', e.items_html)
            entry_line = [e.v_voucherdate,
                          e.org.name,
                          _explain,
                          e.account.number,
                          e.account.name,
                          _accountItemCalss,
                          _itemName,
                          statticticsItems_str,
                          e.damount,
                          e.camount,
                          _cashFlow,
                          e.voucher.appendixCount,
                          _realdate,
                          e.v_number,
                          e.voucher.name,
                          glot_tags_str,
                          items_html]
            export_data.append(entry_line)
        return export_data

# 会计科目列表导出EXCEL


class ExcelExportAccounts():
    def get_colums_headers(self, fields):
        columns_headers = ["所属机构/主体",
                           "所属科目体系",
                           "科目类别",
                           "科目编码",
                           "科目名称",
                           "核算类别",
                           "余额方向",
                           "凭证中可选",
                           "末级科目",
                           "全局标签"]
        return columns_headers

    def get_export_data(self, records):
        export_data = []
        lines = records
        for line in lines:
            glob_tags = [g.name for g in line.glob_tag]
            glob_tags_str = '/'.join(glob_tags)
            orgs = [o.name for o in line.org]
            orgs_str = '/'.join(orgs)
            direction = "借"
            if line.direction == "-1":
                direction = "贷"
            excel_line = [orgs_str,
                          line.accountsArch.name,
                          line.accountClass.name,
                          line.number,
                          line.name,
                          line.itemClassesHtml,
                          direction,
                          line.is_show,
                          line.is_last,
                          glob_tags_str]
            export_data.append(excel_line)
            export_data.sort(key=lambda e: e[3])
        return export_data

# 核算项目列表导出EXCEL


class ExcelExportItems():
    def get_colums_headers(self, fields):
        columns_headers = ["所属机构/主体",
                           "核算项目类别",
                           "核算项目编码",
                           "核算项目名称",
                           "唯一编号",
                           "全局标签"]

        return columns_headers

    def get_export_data(self, records):
        export_data = []
        lines = records
        for line in lines:
            glob_tags = [g.name for g in line.glob_tag]
            glob_tags_str = '/'.join(glob_tags)
            orgs = [o.name for o in line.org]
            orgs_str = '/'.join(orgs)
            excel_line = [orgs_str,
                          line.item_class_name,
                          line.number,
                          line.name,
                          line.uniqueNumber,
                          glob_tags_str]
            export_data.append(excel_line)
            export_data.sort(key=lambda e: e[1])
        return export_data

# 核算项目列表导出EXCEL


class ExcelExportOrgs():
    def get_colums_headers(self, fields):
        columns_headers = ["机构/主体编码",
                           "机构/主体名称",
                           "全局标签"]
        return columns_headers

    def get_export_data(self, records):
        export_data = []
        lines = records
        for line in lines:
            glob_tags = [g.name for g in line.glob_tag]
            glob_tags_str = '/'.join(glob_tags)
            excel_line = [line.number,
                          line.name,
                          glob_tags_str]
            export_data.append(excel_line)
        return export_data

# 导出启用初始余额模板


class ExcelExportBeginModel():
    def __init__(self, accounts, org_name, date):
        self.accounts = accounts
        self.org_name = org_name
        self.date = date
        super().__init__()

    def get_colums_headers(self, fields):
        columns_headers = ["所属机构/主体",
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
        return columns_headers

    def get_export_data(self, records):
        export_data = []
        for account in self.accounts:
            itemClassName = ""
            if account.accountItemClass:
                itemClassName = account.accountItemClass.name
            beginingDamount = ""
            beginingCamount = ""
            if account.direction == "1":
                beginingDamount = 0
            else:
                beginingCamount = 0
            excel_line = [self.org_name,
                          self.date,
                          account.accountClass.name,
                          account.name,
                          itemClassName,
                          "",
                          beginingDamount, beginingCamount, 0, 0, 0, 0]
            export_data.append(excel_line)
        return export_data


# 导出凭证模板


class ExcelExportVoucherModel():

    def get_colums_headers(self, fields):
        columns_headers = ["记账日期",
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
        return columns_headers

    def get_export_data(self, records):
        export_data = [['2020-05-16', '某公司', '销售回款(导入凭证模板样例)', '1001', '库存现金', '', '', '', 200000.99, 0, '', '1', '2020-05-06', '1'],
                       ['2020-05-16', '某公司', '销售回款(导入凭证模板样例)', '1122', '应收账款', '往来', '北京美味食品有限公司',
                        '员工:黄虎/部门:销售1部', 0, 200000.99, '+收到其他与经营活动有关的现金', '1', '2020-05-06', '1'],
                       ['2020-05-16', '某公司', '取现(导入凭证模板样例)', '1001', '库存现金',
                        '', '', '', 100000, 0, '', '1', '2020-05-10', '2'],
                       ['2020-05-16', '某公司', '取现(导入凭证模板样例)', '1002.10', '银行存款---渣打银行9898', '', '', '', 0, 100000, '', '1', '2020-05-10', '2']]
        return export_data
