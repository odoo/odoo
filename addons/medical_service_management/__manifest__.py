# -*- coding: utf-8 -*-
{
    'name': '醫療聯絡人管理基礎模組',
    'version': '18.0.1.0.0',
    'summary': '醫療行業聯絡人管理基礎模組 - 獨立運作，可擴展',
    'description': '''
醫療聯絡人管理基礎模組
========================

本模組提供完整的聯絡人管理功能，包含：
- 客戶公司資訊管理（企業客戶專用欄位）
- 公司部門架構管理  
- 聯絡人資訊管理（彈性關聯設計）
- 預留設備服務整合擴展點

主要特色：
- 獨立運作，無需額外依賴
- 支援彈性資料關聯（公司/部門/聯絡人可選填）
- 完整的資料驗證機制
- 為未來的設備和工單系統預留擴展介面
- 符合醫療設備行業需求

擴展模組：
- 可搭配 fieldservice 模組實現完整的設備服務管理
- 支援模組化擴展，便於維護和升級
    ''',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Contacts',
    'license': 'LGPL-3',
    
    # 基礎依賴（最小化）
    'depends': [
        'base',
        'contacts',
        'mail',
    ],
    
    # 資料檔案載入順序
    'data': [
        # 安全權限
        'security/ir.model.access.csv',
        
        # 資料檔案
        'data/company_department_data.xml',
        
        # 視圖檔案
        'views/res_partner_views.xml',
        'views/company_department_views.xml',
        'views/company_contact_views.xml',
        'views/menu.xml',
    ],
    
    # 示範資料
    'demo': [
        'demo/medical_service_demo.xml',
    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 10,
}