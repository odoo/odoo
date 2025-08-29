# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartnerExtended(models.Model):
    """
    擴展 res.partner 模型，新增醫療設備服務管理所需的企業客戶欄位
    
    主要功能：
    - 新增企業客戶專用財務資訊欄位
    - 建立與部門、設備、合約的關聯
    - 提供統計資訊和快捷操作
    """
    _inherit = 'res.partner'

    # === 企業客戶專用財務欄位 ===
    x_tax_id = fields.Char(
        string='統一編號',
        help='企業統一編號，用於發票和稅務處理'
    )
    
    x_payment_bank = fields.Selection([
        ('ctbc', '中國信託商業銀行'),
        ('bot', '臺灣銀行'),
        ('fubon', '富邦銀行'),
        ('cathay', '國泰世華銀行'),
        ('esun', '玉山銀行'),
        ('mega', '兆豐國際商業銀行'),
        ('first', '第一銀行'),
        ('hua_nan', '華南銀行'),
        ('chang_hwa', '彰化銀行'),
        ('other', '其他銀行'),
    ], string='收款銀行', help='指定收款銀行')
    
    x_payment_account = fields.Char(
        string='收款帳號',
        help='銀行收款帳號'
    )
    
    x_payment_method = fields.Selection([
        ('wire', '電匯'),
        ('monthly', '月結'),
        ('cash', '現金'),
        ('check', '支票'),
    ], string='付款方式', default='wire', help='合約約定的付款方式')
    
    x_payment_currency = fields.Selection([
        ('TWD', '新台幣 (TWD)'),
        ('USD', '美元 (USD)'),
        ('EUR', '歐元 (EUR)'),
    ], string='交易幣別', default='TWD', help='主要交易使用幣別')
    
    # === 關聯欄位 ===
    x_department_ids = fields.One2many(
        'company.department', 
        'company_id', 
        string='部門清單',
        help='該公司下屬的所有部門'
    )
    
    x_contact_ids = fields.One2many(
        'company.contact',
        'company_id',
        string='聯絡人清單', 
        help='該公司的所有聯絡人'
    )
    
    # 從 fieldservice 模組繼承的設備關聯
    # equipment_ids 已由 fieldservice 模組提供
    
    # === 統計欄位 ===
    x_department_count = fields.Integer(
        string='部門數量',
        compute='_compute_department_count',
        store=True,
        help='該公司的部門總數'
    )
    
    x_contact_count = fields.Integer(
        string='聯絡人數量', 
        compute='_compute_contact_count',
        store=True,
        help='該公司的聯絡人總數'
    )
    
    x_equipment_count = fields.Integer(
        string='設備數量',
        compute='_compute_equipment_count',
        store=True,
        help='該公司擁有的設備總數'
    )

    # === 計算方法 ===
    @api.depends('x_department_ids')
    def _compute_department_count(self):
        """計算部門數量"""
        for partner in self:
            partner.x_department_count = len(partner.x_department_ids)

    @api.depends('x_contact_ids')
    def _compute_contact_count(self):
        """計算聯絡人數量"""
        for partner in self:
            partner.x_contact_count = len(partner.x_contact_ids)
    
    @api.depends('is_company')
    def _compute_equipment_count(self):
        """
        計算設備數量 - 擴展點
        
        基礎版本：返回 0
        擴展模組可透過繼承此方法來實作實際的設備統計邏輯
        
        擴展建議：
        - 可搭配 fieldservice 模組實現完整功能
        - 透過 fsm.location 和 fsm.equipment 計算設備數量
        """
        for partner in self:
            # 基礎實作：返回 0，供擴展模組覆寫
            partner.x_equipment_count = self._get_equipment_count()
    
    def _get_equipment_count(self):
        """
        取得設備數量的內部方法 - 擴展點
        
        Returns:
            int: 設備數量，基礎版本返回 0
        """
        # 擴展點：子模組可覆寫此方法實現實際統計
        return 0

    # === 動作方法 ===
    def action_open_departments(self):
        """開啟部門清單視圖"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - 部門清單',
            'res_model': 'company.department',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
            'target': 'current',
        }
    
    def action_open_contacts(self):
        """開啟聯絡人清單視圖"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - 聯絡人清單',
            'res_model': 'company.contact',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
            'target': 'current',
        }
    
    def action_open_equipments(self):
        """
        開啟設備清單視圖 - 擴展點
        
        基礎版本：顯示提示訊息
        擴展模組可透過繼承此方法來實作實際的設備管理功能
        """
        self.ensure_one()
        
        # 檢查是否有擴展模組提供設備功能
        if self._has_equipment_extension():
            return self._open_equipments_extended()
        
        # 基礎版本：顯示提示訊息
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '功能提示',
                'message': f'客戶 "{self.name}" 的設備管理功能需要安裝設備服務擴展模組。\n目前可管理部門和聯絡人資訊。',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def _has_equipment_extension(self):
        """
        檢查是否有設備擴展功能 - 擴展點
        
        Returns:
            bool: 是否有設備功能，基礎版本返回 False
        """
        # 擴展點：子模組可覆寫此方法
        return False
    
    def _open_equipments_extended(self):
        """
        開啟擴展的設備清單 - 擴展點
        
        Returns:
            dict: 動作字典，基礎版本返回空動作
        """
        # 擴展點：子模組實作此方法
        return {'type': 'ir.actions.act_window_close'}

    # === 約束和驗證 ===
    @api.constrains('x_tax_id')
    def _check_tax_id_format(self):
        """驗證統一編號格式（台灣統一編號為8位數字）"""
        for partner in self:
            if partner.x_tax_id and partner.country_id and partner.country_id.code == 'TW':
                if not (partner.x_tax_id.isdigit() and len(partner.x_tax_id) == 8):
                    raise models.ValidationError('台灣統一編號必須為8位數字')

    @api.constrains('x_payment_account')
    def _check_payment_account(self):
        """驗證收款帳號與銀行的一致性"""
        for partner in self:
            if partner.x_payment_account and not partner.x_payment_bank:
                raise models.ValidationError('設定收款帳號時必須同時選擇收款銀行')