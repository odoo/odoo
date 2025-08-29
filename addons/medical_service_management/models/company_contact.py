# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CompanyContact(models.Model):
    """
    聯絡人管理模型
    
    功能說明：
    - 管理客戶公司的聯絡人資訊
    - 支援彈性關聯設計（公司/部門可選填）
    - 提供完整的聯絡資訊和職務資料
    - 與服務工單和設備管理整合
    """
    _name = 'company.contact'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '聯絡人'
    _order = 'company_id, department_id, name'
    _rec_name = 'display_name'

    # === 基本個人資訊 ===
    name = fields.Char(
        string='姓名',
        required=True,
        help='聯絡人的完整姓名'
    )
    
    display_name = fields.Char(
        string='顯示名稱',
        compute='_compute_display_name',
        store=True,
        help='包含公司和部門資訊的完整顯示名稱'
    )
    
    title_id = fields.Many2one(
        'res.partner.title',
        string='稱謂',
        help='先生、女士等稱謂'
    )
    
    function = fields.Char(
        string='職位',
        help='聯絡人在公司的職位'
    )
    
    active = fields.Boolean(
        string='啟用',
        default=True,
        help='取消勾選以停用此聯絡人'
    )

    # === 聯絡資訊 ===
    phone = fields.Char(
        string='電話',
        help='辦公室電話號碼'
    )
    
    mobile = fields.Char(
        string='手機',
        help='行動電話號碼'
    )
    
    email = fields.Char(
        string='Email',
        help='電子郵件地址'
    )
    
    fax = fields.Char(
        string='傳真',
        help='傳真號碼'
    )
    
    extension = fields.Char(
        string='分機',
        help='電話分機號碼'
    )

    # === 彈性關聯欄位（都可為空） ===
    company_id = fields.Many2one(
        'res.partner',
        string='所屬公司',
        domain="[('is_company', '=', True)]",
        help='聯絡人所屬的公司（可選填）'
    )
    
    department_id = fields.Many2one(
        'company.department',
        string='所屬部門',
        help='聯絡人所屬的部門（可選填）'
    )

    # === 偏好設定 ===
    lang = fields.Selection(
        string='語言',
        selection='_get_languages',
        default='zh_TW',
        help='聯絡人偏好使用的語言'
    )
    
    tz = fields.Selection(
        string='時區',
        selection='_tz_get',
        default=lambda self: self.env.context.get('tz') or 'Asia/Taipei',
        help='聯絡人所在的時區'
    )
    
    # === 通訊偏好 ===
    communication_preference = fields.Selection([
        ('phone', '電話'),
        ('mobile', '手機'),
        ('email', 'Email'),
        ('fax', '傳真'),
    ], string='偏好聯絡方式', default='mobile', help='優先使用的聯絡方式')

    # === 其他資訊 ===
    category_ids = fields.Many2many(
        'res.partner.category',
        string='標籤',
        help='聯絡人分類標籤'
    )
    
    note = fields.Text(
        string='備註',
        help='關於此聯絡人的備註資訊'
    )
    
    # === 服務相關統計 ===
    service_order_count = fields.Integer(
        string='服務工單數',
        compute='_compute_service_order_count',
        store=True,
        help='此聯絡人相關的服務工單總數'
    )
    
    last_service_date = fields.Date(
        string='最後服務日期',
        compute='_compute_last_service_date',
        help='最近一次服務的日期'
    )

    # === 計算方法 ===
    @api.depends('name', 'company_id', 'department_id', 'function')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for contact in self:
            parts = [contact.name]
            
            if contact.function:
                parts.append(f"({contact.function})")
            
            if contact.department_id:
                parts.append(f"- {contact.department_id.name}")
            elif contact.company_id:
                parts.append(f"- {contact.company_id.name}")
                
            contact.display_name = ' '.join(parts)

    @api.depends('company_id', 'department_id')
    def _compute_service_order_count(self):
        """
        計算服務工單數量 - 擴展點
        
        基礎版本：返回 0
        擴展模組可透過繼承此方法來實作實際的服務工單統計邏輯
        
        擴展建議：
        - 可搭配 fieldservice 模組查詢 fsm.order 記錄
        - 透過 x_contact_id 欄位建立關聯
        """
        for contact in self:
            # 基礎實作：返回 0，供擴展模組覆寫
            contact.service_order_count = self._get_service_order_count(contact)

    def _compute_last_service_date(self):
        """
        計算最後服務日期 - 擴展點
        
        基礎版本：返回 False
        擴展模組可透過繼承此方法來實作實際的服務日期統計邏輯
        """
        for contact in self:
            # 基礎實作：返回 False，供擴展模組覆寫
            contact.last_service_date = self._get_last_service_date(contact)
    
    def _get_service_order_count(self, contact):
        """
        取得服務工單數量的內部方法 - 擴展點
        
        Args:
            contact: 聯絡人記錄
            
        Returns:
            int: 服務工單數量，基礎版本返回 0
        """
        # 擴展點：子模組可覆寫此方法實現實際統計
        return 0
    
    def _get_last_service_date(self, contact):
        """
        取得最後服務日期的內部方法 - 擴展點
        
        Args:
            contact: 聯絡人記錄
            
        Returns:
            date: 最後服務日期，基礎版本返回 False
        """
        # 擴展點：子模組可覆寫此方法實現實際統計
        return False

    # === 選項方法 ===
    @api.model
    def _get_languages(self):
        """取得可用語言選項"""
        return self.env['res.lang'].get_installed()

    @api.model
    def _tz_get(self):
        """取得時區選項"""
        # 簡化的時區選項
        return [
            ('Asia/Taipei', 'Asia/Taipei'),
            ('UTC', 'UTC'),
            ('Asia/Shanghai', 'Asia/Shanghai'),
            ('Asia/Hong_Kong', 'Asia/Hong_Kong'),
        ]

    # === 約束驗證 ===
    @api.constrains('company_id', 'department_id')
    def _check_department_company_consistency(self):
        """確保部門與公司的一致性"""
        for contact in self:
            if contact.department_id and contact.company_id:
                if contact.department_id.company_id != contact.company_id:
                    raise models.ValidationError(
                        f'聯絡人 "{contact.name}" 的部門必須屬於所選公司 "{contact.company_id.name}"'
                    )

    @api.constrains('email')
    def _check_email_format(self):
        """驗證 Email 格式"""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for contact in self:
            if contact.email and not re.match(email_pattern, contact.email):
                raise models.ValidationError(f'聯絡人 "{contact.name}" 的 Email 格式不正確')

    # === onchange 方法 ===
    @api.onchange('department_id')
    def _onchange_department_id(self):
        """當選擇部門時，自動設定公司"""
        if self.department_id:
            if not self.company_id or self.company_id != self.department_id.company_id:
                self.company_id = self.department_id.company_id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """當變更公司時，清空不匹配的部門"""
        if self.company_id and self.department_id:
            if self.department_id.company_id != self.company_id:
                self.department_id = False

    # === 動作方法 ===
    def action_open_service_orders(self):
        """
        開啟相關服務工單 - 擴展點
        
        基礎版本：顯示提示訊息
        擴展模組可透過繼承此方法來實作實際的服務工單管理功能
        """
        self.ensure_one()
        
        # 檢查是否有擴展模組提供服務工單功能
        if self._has_service_extension():
            return self._open_service_orders_extended()
        
        # 基礎版本：顯示提示訊息
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '功能提示',
                'message': f'聯絡人 "{self.display_name}" 的服務工單功能需要安裝設備服務擴展模組。\n目前可管理聯絡人基本資訊。',
                'type': 'info',
                'sticky': False,
            }
        }
    
    def _has_service_extension(self):
        """
        檢查是否有服務工單擴展功能 - 擴展點
        
        Returns:
            bool: 是否有服務工單功能，基礎版本返回 False
        """
        # 擴展點：子模組可覆寫此方法
        return False
    
    def _open_service_orders_extended(self):
        """
        開啟擴展的服務工單清單 - 擴展點
        
        Returns:
            dict: 動作字典，基礎版本返回空動作
        """
        # 擴展點：子模組實作此方法
        return {'type': 'ir.actions.act_window_close'}

    def action_send_email(self):
        """發送郵件給聯絡人"""
        self.ensure_one()
        if not self.email:
            raise models.UserError('此聯絡人沒有設定 Email 地址')
            
        return {
            'type': 'ir.actions.act_window',
            'name': '發送郵件',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_ids': [(6, 0, [])],  # 如需要可建立對應 partner
                'default_email_to': self.email,
                'default_subject': f'聯絡：{self.name}',
            }
        }

    # === 搜尋方法增強 ===
    def name_get(self):
        """自定義顯示名稱"""
        result = []
        for contact in self:
            name = contact.display_name or contact.name
            result.append((contact.id, name))
        return result

    @api.model 
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """增強搜尋功能，支援多欄位搜尋"""
        args = args or []
        domain = []
        
        if name:
            domain = [
                '|', '|', '|', '|',
                ('name', operator, name),
                ('function', operator, name), 
                ('email', operator, name),
                ('phone', operator, name),
                ('mobile', operator, name)
            ]
            
        contacts = self.search(domain + args, limit=limit)
        return contacts.name_get()

    # === 建立和複製方法 ===
    @api.model_create_multi
    def create(self, vals_list):
        """
        建立聯絡人時的特殊處理
        
        支援 Odoo 18.0 的批量建立 API
        如果只提供部門而沒提供公司，自動設定公司
        """
        for vals in vals_list:
            # 如果只提供部門而沒提供公司，自動設定公司
            if vals.get('department_id') and not vals.get('company_id'):
                department = self.env['company.department'].browse(vals['department_id'])
                if department.exists():
                    vals['company_id'] = department.company_id.id
                    
        return super().create(vals_list)

    def copy(self, default=None):
        """複製聯絡人時調整名稱"""
        default = default or {}
        if 'name' not in default:
            default['name'] = f"{self.name} (複製)"
        return super().copy(default)