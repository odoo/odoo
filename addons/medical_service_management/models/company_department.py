# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CompanyDepartment(models.Model):
    """
    公司部門管理模型
    
    功能說明：
    - 管理客戶公司的組織架構
    - 提供部門層級的聯絡資訊
    - 支援階層式部門結構
    - 與聯絡人和設備建立關聯
    """
    _name = 'company.department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '公司部門'
    _order = 'company_id, parent_id, sequence, name'
    _rec_name = 'display_name'

    # === 基本資訊欄位 ===
    name = fields.Char(
        string='部門名稱',
        required=True,
        help='部門的正式名稱'
    )
    
    display_name = fields.Char(
        string='完整名稱',
        compute='_compute_display_name',
        store=True,
        help='顯示完整的部門階層名稱'
    )
    
    code = fields.Char(
        string='部門代碼',
        help='部門的唯一識別代碼'
    )
    
    sequence = fields.Integer(
        string='順序',
        default=10,
        help='部門顯示順序'
    )
    
    active = fields.Boolean(
        string='啟用',
        default=True,
        help='取消勾選以停用此部門'
    )

    # === 關聯欄位 ===
    company_id = fields.Many2one(
        'res.partner',
        string='所屬公司',
        required=True,
        domain="[('is_company', '=', True)]",
        help='此部門所屬的公司'
    )
    
    parent_id = fields.Many2one(
        'company.department',
        string='上級部門',
        domain="[('company_id', '=', company_id)]",
        help='上級部門，支援階層架構'
    )
    
    child_ids = fields.One2many(
        'company.department',
        'parent_id',
        string='下級部門',
        help='此部門的下級部門'
    )

    # === 聯絡資訊欄位 ===
    street = fields.Char(string='地址')
    street2 = fields.Char(string='地址2')
    city = fields.Char(string='城市')
    state_id = fields.Many2one(
        'res.country.state',
        string='省/州',
        domain="[('country_id', '=', country_id)]"
    )
    country_id = fields.Many2one(
        'res.country',
        string='國家',
        default=lambda self: self.env.ref('base.tw')
    )
    zip = fields.Char(string='郵遞區號')
    
    phone = fields.Char(string='電話')
    mobile = fields.Char(string='手機') 
    fax = fields.Char(string='傳真')
    email = fields.Char(string='Email')
    website = fields.Char(string='網站')

    # === 統計和關聯欄位 ===
    contact_ids = fields.One2many(
        'company.contact',
        'department_id',
        string='部門聯絡人',
        help='此部門的聯絡人清單'
    )
    
    contact_count = fields.Integer(
        string='聯絡人數量',
        compute='_compute_contact_count',
        store=True,
        help='此部門的聯絡人總數'
    )
    
    equipment_count = fields.Integer(
        string='設備數量', 
        compute='_compute_equipment_count',
        store=True,
        help='此部門擁有的設備總數'
    )

    # === 描述欄位 ===
    description = fields.Text(string='備註')

    # === 計算方法 ===
    @api.depends('name', 'parent_id', 'company_id')
    def _compute_display_name(self):
        """計算完整顯示名稱，包含階層結構"""
        for department in self:
            names = []
            current = department
            while current:
                names.append(current.name)
                current = current.parent_id
            names.reverse()
            department.display_name = ' / '.join(names)

    @api.depends('contact_ids')
    def _compute_contact_count(self):
        """計算聯絡人數量"""
        for department in self:
            department.contact_count = len(department.contact_ids)

    @api.depends('company_id')
    def _compute_equipment_count(self):
        """
        計算部門設備數量 - 擴展點
        
        基礎版本：返回 0
        擴展模組可透過繼承此方法來實作實際的設備統計邏輯
        
        擴展建議：
        - 可搭配 fieldservice 模組透過 fsm.location 查找設備
        - 實作 x_department_id 欄位到 fsm.location 的關聯
        """
        for department in self:
            # 基礎實作：返回 0，供擴展模組覆寫
            department.equipment_count = self._get_department_equipment_count(department)
    
    def _get_department_equipment_count(self, department):
        """
        取得部門設備數量的內部方法 - 擴展點
        
        Args:
            department: 部門記錄
            
        Returns:
            int: 設備數量，基礎版本返回 0
        """
        # 擴展點：子模組可覆寫此方法實現實際統計
        return 0

    # === 約束方法 ===
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """防止循環引用"""
        if self._has_cycle():
            raise models.ValidationError('錯誤! 不能建立循環的部門階層結構。')

    @api.constrains('company_id', 'parent_id')
    def _check_parent_company(self):
        """確保上級部門屬於同一公司"""
        for department in self:
            if department.parent_id:
                if department.parent_id.company_id != department.company_id:
                    raise models.ValidationError('上級部門必須屬於同一公司')

    @api.constrains('code', 'company_id')
    def _check_code_uniqueness(self):
        """確保部門代碼在同一公司內唯一"""
        for department in self:
            if department.code:
                duplicate = self.search([
                    ('code', '=', department.code),
                    ('company_id', '=', department.company_id.id),
                    ('id', '!=', department.id)
                ])
                if duplicate:
                    raise models.ValidationError(f'部門代碼 "{department.code}" 在同一公司內必須唯一')

    # === 動作方法 ===
    def action_open_contacts(self):
        """開啟此部門的聯絡人清單"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.display_name} - 聯絡人',
            'res_model': 'company.contact',
            'view_mode': 'list,form',
            'domain': [('department_id', '=', self.id)],
            'context': {
                'default_department_id': self.id,
                'default_company_id': self.company_id.id,
            },
            'target': 'current',
        }

    def action_open_equipments(self):
        """
        開啟此部門的設備清單 - 擴展點
        
        基礎版本：顯示提示訊息
        擴展模組可透過繼承此方法來實作實際的設備管理功能
        """
        self.ensure_one()
        
        # 檢查是否有擴展模組提供設備功能
        if self._has_equipment_extension():
            return self._open_department_equipments_extended()
        
        # 基礎版本：顯示提示訊息
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '功能提示',
                'message': f'部門 "{self.display_name}" 的設備管理功能需要安裝設備服務擴展模組。\n目前可管理部門聯絡人資訊。',
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
    
    def _open_department_equipments_extended(self):
        """
        開啟部門擴展的設備清單 - 擴展點
        
        Returns:
            dict: 動作字典，基礎版本返回空動作
        """
        # 擴展點：子模組實作此方法
        return {'type': 'ir.actions.act_window_close'}

    # === 名稱搜尋方法 ===
    def name_get(self):
        """自定義顯示名稱"""
        result = []
        for department in self:
            name = department.display_name or department.name
            result.append((department.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """增強名稱搜尋功能"""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        departments = self.search(domain + args, limit=limit)
        return departments.name_get()

    # === 複製方法覆寫 ===
    def copy(self, default=None):
        """複製部門時自動調整名稱和代碼"""
        default = default or {}
        if 'name' not in default:
            default['name'] = f"{self.name} (複製)"
        if 'code' not in default and self.code:
            default['code'] = f"{self.code}_copy"
        return super().copy(default)