# -*- coding: utf-8 -*-
{
    'name': '企業聯絡人管理擴展',
    'display_name': 'Enterprise Contact Management Extension',
    'version': '18.0.1.0.0',
    'summary': '企業聯絡人管理擴展模組 - 組織架構、部門管理與聯絡人資訊整合',
    'description': '''
企業聯絡人管理擴展模組
========================

本模組提供完整的企業聯絡人管理功能，包含：
- 企業客戶資訊管理（統一編號、付款資訊等專用欄位）
- 公司部門架構管理（支援多層級組織架構）
- 聯絡人資訊管理（彈性關聯設計）
- 預留服務管理整合擴展點

主要特色：
- 獨立運作，無需額外依賴
- 支援彈性資料關聯（公司/部門/聯絡人可選填）
- 完整的資料驗證機制
- 為未來的服務和工單系統預留擴展介面
- 適用於各種行業的企業客戶管理需求

擴展模組：
- 可搭配 fieldservice 模組實現完整的服務管理
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
    'application': True,
    'auto_install': False,
    'sequence': 10,
}