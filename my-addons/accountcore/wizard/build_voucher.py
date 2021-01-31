# -*- coding: utf-8 -*-
from odoo import api
from odoo import exceptions
from odoo import fields
from odoo import models
from ..models.ac_obj import ACTools
from ..models.ac_obj import BalanceLines
# 通过账簿数据快建凭证向导


class BuildVoucher(models.TransientModel):
    '''快建凭证向导'''
    _name = 'accountcore.build_voucher'
    _description = "快建凭证向导"
    voucher_date = fields.Date(string='记账日期',
                               required=True,
                               placeholder='记账日期', default=lambda s: s.env.user.current_date)
    explain = fields.Char(string='分录摘要')
    org = fields.Many2one('accountcore.org', string="目标机构/主体",
                          required=True, default=lambda s: s.env.user.currentOrg)
    account = fields.Many2one('accountcore.account',
                              string='对方科目',
                              required=True)
    accountItemClass = fields.Many2one('accountcore.itemclass',
                                       string='项目类别',
                                       related='account.accountItemClass')
    item = fields.Many2one('accountcore.item', string='核算项目')

    amount_type = fields.Selection(
        [('endDamount', '期末借方余额'),
         ('endCamount', '期末贷方余额'),
         ('damount', '本期借方发生额'),
         ('camount', '本期贷方发生额'),
         ('beginingDamount', '期初借方余额'),
         ('beginingCamount', '期初贷方余额')],
        string='金额来源',
        required=True,
        default='endDamount', help="来自账簿的相关金额栏")

    amount_control = fields.Selection(
        [('1', '保持原样'),
         ('2', '金额取反'),
         ('3', '负数取反'),
         ('4', '正数取反')],
        string='金额控制',
        required=True,
        default='1')
    out_direction = fields.Selection(
        [('1', '借'), ('-1', '贷')], string='生成方向', default='-1', required=True)
    in_direction = fields.Selection(
        [('1', '借'), ('-1', '贷')], string='生成方向', default='1', required=True)
    in_account_items = fields.Text(string="对方科目预览")
    account_items = fields.Text(string="取数科目预览")
    temp = fields.Text(string='缓存余额数据')
    @api.onchange('account')
    # 改变科目时删除核算项目关联
    def _deleteItemsOnchange(self):
        self.items = None

    @api.onchange('account', 'item', 'in_direction', 'amount_type', 'out_direction', 'amount_control')
    def _updata_in_account_items(self):
        '''更新对方科目预览'''
        entry_str = ""
        if self.account:
            entry_str = entry_str+self.account.number+"   "+self.account.name
        if self.accountItemClass:
            entry_str = entry_str+"【"+self.accountItemClass.name+"】"
        if self.item:
            entry_str = entry_str+" "+self.item.name
        dc = "借"
        if self.in_direction == '-1':
            dc = "贷"
        balanceLines = BalanceLines(self.temp)
        # 平衡借贷方金额
        if self.in_direction == self.out_direction:
            amount_in = -self._get_in_amount(balanceLines)
        else:
            amount_in = self._get_in_amount(balanceLines)
        self.in_account_items = dc+":   "+entry_str+"   "+str(amount_in)

    @api.onchange('amount_type', 'out_direction', 'amount_control')
    def _updata_account_items(self):
        '''更新取数科目预览'''
        balanceLines = BalanceLines(self.temp)
        self.account_items = balanceLines.strOfConf(
            self.amount_type, self.out_direction, self.amount_control)
    
    @ACTools.refuse_role_search
    def do(self):
        '''快建凭证生成凭证'''
        try:
            voucher = self._buildVoucherInfo()
        except exceptions.ValidationError as e:
            raise exceptions.ValidationError(e.name+"。可能该科目应有核算项目,而选择了非末级科目行")
        return {'name': '快建凭证',
                'view_mode': 'form',
                'res_model': 'accountcore.voucher',
                'view_id': False,
                'target': 'fullscreen',
                'res_id': voucher.id,
                'type': 'ir.actions.act_window',
                }

    def _buildVoucherInfo(self):
        '''购建凭证推送接口接受的凭证数据'''
        balanceLines = BalanceLines(self.temp)
        explain = self.explain
        entrys = []
        # 构建对方科目分录
        _in_entry = {"account": self.account.id,
                     "explain": explain,
                     'damount': 0,
                     'camount': 0}
        if self.item:
            _in_entry.update({'items': [[6, False, [self.item.id]]]})
        in_entry = [0, '', _in_entry]
        entrys.append(in_entry)
        amount_out = ACTools.ZeroAmount()
        # 构建取数科目分录
        for b in balanceLines.balances:
            # 金额控制
            amount = b.amount_type_control(
                self.amount_type, self.amount_control)
            if amount == ACTools.ZeroAmount():
                continue
            _out_entry = {"account": int(b.account['id']),
                          "explain": explain,
                          'damount': 0,
                          'camount': 0}
            if self.out_direction == '1':
                _out_entry.update({'damount': float(amount)})
            else:
                _out_entry.update({'camount': float(amount)})
            # 组装核算项目
            if b.item['id'] != 0:
                _out_entry.update({'items': [[6, False, [int(b.item['id'])]]]})
            entrys.append([0, '', _out_entry])
            amount_out = amount_out+amount
        if amount_out == ACTools.ZeroAmount():
            raise exceptions.ValidationError("取数科目合计金额为0,不能生成凭证")
        else:
            # 根据取数科目平衡对方科目金额
            if self.in_direction == self.out_direction:
                amount_in = -amount_out

            else:
                amount_in = amount_out
        # 创建新凭证
        voucher = {"voucherdate": self.voucher_date,
                   "org": self.org.id,
                   "entrys": entrys}
        # 用取数科目的合计更新对方科目分录的金额
        if self.in_direction == '1':
            voucher["entrys"][0][2].update({'damount': float(amount_in)})
        else:
            voucher["entrys"][0][2].update({'camount': float(amount_in)})
        return self.env['accountcore.voucher'].create(voucher)

    def _get_in_amount(self, balanceLines):
        '''获得对方科目的合计'''
        amount_out = balanceLines.sum(self.amount_type, self.amount_control)
        return amount_out
