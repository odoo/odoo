# -*- coding: utf-8 -*-
from odoo import api
from odoo import fields
from odoo import models
from odoo import exceptions
from ..models.ac_obj import ACTools
# 克隆凭证向导


class CloneVouchers(models.TransientModel):
    '''克隆凭证向导'''
    _name = 'accountcore.clone_vouchers'
    _description = '克隆凭证向导'
    org = fields.Many2one('accountcore.org', required=True)
    voucherdate = fields.Date(string='新记账日期',
                              placeholder='记账日期', default=lambda s: s.env.user.current_date)
    real_date = fields.Date(string='新业务日期', help='新业务实际发生日期')
    copy_appendixCount = fields.Boolean(string="保留附件数", default=True)
    copy_v_number = fields.Boolean(string="保留凭证号", default=False)
    @ACTools.refuse_role_search
    # @api.model
    def do(self):
        my_default = {'org': self.org.id}
        if hasattr(self, "voucherdate") and self.voucherdate != False:
            my_default.update({"voucherdate": self.voucherdate})
            if self.org.lock_date and ACTools.compareDate(self.voucherdate, self.org.lock_date) != 1:
                raise exceptions.ValidationError('机构/主体:'+str(self.org.name)+'的锁定日期为:' + str(self.org.lock_date)+",新记账日期"+str(self.voucherdate)+"应晚于该日期")
        if hasattr(self, "real_date"):
            my_default.update({"real_date": self.real_date})
        if not self.copy_appendixCount:
            my_default.update({"appendixCount": 1})
        if not self.copy_v_number:
            my_default.update({"v_number": 0})
        vouchers = self.env['accountcore.voucher'].sudo().browse(
            self._context.get('active_ids'))
        new_vouchers = []
        # 检查克隆凭证日期是否晚于机构的锁定日期
        if not hasattr(self, "voucherdate") or not self.voucherdate:
            for v in vouchers:
                if self.org.lock_date and ACTools.compareDate(v.voucherdate, self.org.lock_date) != 1:
                    raise exceptions.ValidationError('机构/主体:'+str(self.org.name)+'的锁定日期为:' + str(self.org.lock_date)+",新记账日期"+str(v.voucherdate)+"应晚于该日期")
        for voucher in vouchers:
            v = voucher.copy(my_default=my_default)
            new_vouchers.append(v.id)
        return {'name': '克隆的凭证',
                'view_mode': 'tree,form',
                'res_model': 'accountcore.voucher',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in',  new_vouchers)]
                }
