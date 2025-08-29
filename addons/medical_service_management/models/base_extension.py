# -*- coding: utf-8 -*-

from odoo import models, api


class BaseExtensionMixin(models.AbstractModel):
    """
    基礎擴展 Mixin 類別
    
    為醫療聯絡人管理模組提供統一的擴展介面，便於未來模組擴展和整合。
    
    主要用途：
    - 定義擴展點的標準介面
    - 提供擴展功能的檢測機制
    - 統一管理擴展模組的整合邏輯
    
    擴展建議：
    - 子模組可繼承此 Mixin 並覆寫相關方法
    - 透過 _register_hook() 註冊擴展功能
    - 使用 _has_extension() 檢測可用功能
    """
    _name = 'medical.base.extension'
    _description = '醫療聯絡人管理基礎擴展介面'

    @api.model
    def _register_hook(self):
        """
        註冊擴展鉤子 - 擴展點
        
        此方法在模組載入時被呼叫，用於：
        - 註冊擴展功能
        - 檢查依賴模組
        - 設定整合參數
        
        擴展模組應覆寫此方法來註冊自己的功能。
        """
        super()._register_hook()
        # 基礎實作：無特殊動作，由子模組實作

    def _has_extension(self, extension_type):
        """
        檢查是否有特定類型的擴展功能
        
        Args:
            extension_type (str): 擴展類型
                - 'equipment': 設備管理擴展
                - 'service': 服務工單擴展
                - 'maintenance': 保養管理擴展
                - 'repair': 維修管理擴展
                
        Returns:
            bool: 是否有對應的擴展功能
        """
        # 檢查是否有對應的擴展模組
        extension_mapping = {
            'equipment': self._has_equipment_extension,
            'service': self._has_service_extension,
            'maintenance': self._has_maintenance_extension,
            'repair': self._has_repair_extension,
        }
        
        check_method = extension_mapping.get(extension_type)
        if check_method:
            return check_method()
        
        return False

    def _has_equipment_extension(self):
        """
        檢查是否有設備管理擴展 - 擴展點
        
        Returns:
            bool: 是否有設備管理功能，基礎版本返回 False
        """
        # 可檢查是否安裝了相關模組
        return self._check_module_installed(['fieldservice', 'medical_equipment_service'])

    def _has_service_extension(self):
        """
        檢查是否有服務工單擴展 - 擴展點
        
        Returns:
            bool: 是否有服務工單功能，基礎版本返回 False
        """
        return self._check_module_installed(['fieldservice', 'medical_service_order'])

    def _has_maintenance_extension(self):
        """
        檢查是否有保養管理擴展 - 擴展點
        
        Returns:
            bool: 是否有保養管理功能，基礎版本返回 False
        """
        return self._check_module_installed(['medical_maintenance_management'])

    def _has_repair_extension(self):
        """
        檢查是否有維修管理擴展 - 擴展點
        
        Returns:
            bool: 是否有維修管理功能，基礎版本返回 False
        """
        return self._check_module_installed(['medical_repair_management'])

    def _check_module_installed(self, module_names):
        """
        檢查指定的模組是否已安裝
        
        Args:
            module_names (list): 要檢查的模組名稱列表
            
        Returns:
            bool: 是否至少有一個模組已安裝
        """
        if not isinstance(module_names, list):
            module_names = [module_names]
            
        installed_modules = self.env['ir.module.module'].search([
            ('name', 'in', module_names),
            ('state', '=', 'installed')
        ])
        
        return bool(installed_modules)

    def _get_extension_info(self, extension_type):
        """
        取得擴展功能的詳細資訊
        
        Args:
            extension_type (str): 擴展類型
            
        Returns:
            dict: 擴展資訊，包含名稱、描述、狀態等
        """
        extension_info = {
            'equipment': {
                'name': '設備管理',
                'description': '提供完整的醫療設備管理功能',
                'required_modules': ['fieldservice', 'medical_equipment_service'],
                'features': ['設備追蹤', 'QR Code 整合', '保固管理']
            },
            'service': {
                'name': '服務工單',
                'description': '提供服務工單管理和追蹤功能',
                'required_modules': ['fieldservice', 'medical_service_order'],
                'features': ['工單管理', '技術人員派遣', '客戶簽名']
            },
            'maintenance': {
                'name': '保養管理',
                'description': '提供設備保養計劃和執行管理',
                'required_modules': ['medical_maintenance_management'],
                'features': ['保養計劃', '檢查清單', '保養歷史']
            },
            'repair': {
                'name': '維修管理',
                'description': '提供設備維修記錄和問題追蹤',
                'required_modules': ['medical_repair_management'],
                'features': ['維修記錄', '問題分類', '零件管理']
            }
        }
        
        info = extension_info.get(extension_type, {})
        info['available'] = self._has_extension(extension_type)
        
        return info

    def _show_extension_notification(self, extension_type, context_name="功能"):
        """
        顯示擴展功能的提示通知
        
        Args:
            extension_type (str): 擴展類型
            context_name (str): 上下文名稱（如："客戶 XXX"）
            
        Returns:
            dict: 通知動作字典
        """
        extension_info = self._get_extension_info(extension_type)
        
        if not extension_info:
            message = f'{context_name} 的相關功能需要安裝額外的擴展模組。'
        else:
            required_modules = ', '.join(extension_info.get('required_modules', []))
            message = f'{context_name} 的 {extension_info.get("name")} 功能需要安裝以下模組：\n{required_modules}\n\n{extension_info.get("description")}'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '功能提示',
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }


class ExtensionRegistry(models.AbstractModel):
    """
    擴展註冊表 - 管理所有已註冊的擴展功能
    
    用於：
    - 追蹤已安裝的擴展模組
    - 提供擴展功能的查詢介面
    - 管理擴展之間的相依關係
    """
    _name = 'medical.extension.registry'
    _description = '醫療聯絡人管理擴展功能註冊表'

    @api.model
    def get_available_extensions(self):
        """
        取得所有可用的擴展功能清單
        
        Returns:
            dict: 擴展功能清單，包含詳細資訊
        """
        extension_mixin = self.env['medical.base.extension']
        extension_types = ['equipment', 'service', 'maintenance', 'repair']
        
        extensions = {}
        for ext_type in extension_types:
            extensions[ext_type] = extension_mixin._get_extension_info(ext_type)
        
        return extensions

    @api.model
    def check_dependencies(self, extension_type):
        """
        檢查擴展功能的依賴關係
        
        Args:
            extension_type (str): 擴展類型
            
        Returns:
            dict: 依賴檢查結果
        """
        extension_info = self.env['medical.base.extension']._get_extension_info(extension_type)
        required_modules = extension_info.get('required_modules', [])
        
        dependency_status = {}
        for module_name in required_modules:
            module = self.env['ir.module.module'].search([
                ('name', '=', module_name)
            ], limit=1)
            
            if module:
                dependency_status[module_name] = {
                    'installed': module.state == 'installed',
                    'available': True,
                    'state': module.state
                }
            else:
                dependency_status[module_name] = {
                    'installed': False,
                    'available': False,
                    'state': 'not_found'
                }
        
        return {
            'extension_type': extension_type,
            'dependencies': dependency_status,
            'all_satisfied': all(dep['installed'] for dep in dependency_status.values())
        }