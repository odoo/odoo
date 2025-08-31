# 企業聯絡人管理擴展模組

**Enterprise Contact Management Extension**

## 📋 模組概述

本模組為企業通用的聯絡人管理擴展模組，基於 Odoo 18.0 Community Edition 開發。採用獨立運作設計，可單獨使用，也可搭配 Field Service 等擴展模組實現完整的企業服務管理功能。適用於各種需要完整客戶聯絡人管理的行業。

## ✨ 主要功能

### 🏢 企業客戶管理
- **完整財務資訊**：統編、付款方式、收款銀行、交易幣別
- **兼容性欄位**：公司電話、郵箱、網站、地址等
- **統計資訊**：部門數量、聯絡人數量、設備數量統計
- **擴展整合**：預留服務管理系統整合擴展點
- **本地化支援**：支援台灣銀行選項和統編驗證

### 🏛️ 公司部門管理
- **階層架構**：支援多層級部門組織結構
- **完整資訊**：部門代碼、聯絡方式、地址資訊
- **分機管理**：電話分機號碼管理
- **聯絡人統計**：部門聯絡人數量追蹤
- **設備關聯**：預留設備管理擴展點

### 👥 聯絡人管理
- **彈性關聯**：可關聯公司、部門或保持獨立
- **通訊偏好**：支援多種聯絡方式偏好設定
- **分類標籤**：完整的聯絡人分類系統
- **服務記錄**：預留服務歷史追蹤功能

### 📊 統計與報表
- **即時統計**：實時顯示部門、聯絡人、設備數量
- **關聯查詢**：快速查看相關聯的記錄
- **擴展提示**：未安裝擴展模組時的友善提示

## 🔧 技術特色

- **🚀 獨立運作**：最小依賴，無需額外模組即可使用
- **🔗 標準繼承**：使用 Odoo 模型繼承，不修改核心代碼
- **🎯 擴展設計**：完整的擴展點架構，便於功能擴展
- **✅ 資料驗證**：包含完整的資料一致性和格式驗證
- **👤 權限控制**：細緻的用戶權限和存取控制
- **📱 多視圖**：提供列表、表單、看板等多種界面視圖
- **🔐 安全設計**：符合 Odoo 安全最佳實踐

## 📦 系統需求

### 基本需求
- **Odoo**: Community Edition 18.0+
- **Python**: 3.10 - 3.13
- **PostgreSQL**: 12+
- **作業系統**: Linux/Windows/macOS

### 必需依賴
```python
'depends': [
    'base',      # Odoo 核心模組
    'contacts',  # 聯絡人管理
    'mail',      # 郵件整合和活動追蹤
],
```

### 可選依賴
- `fieldservice` - 設備服務管理擴展
- `account` - 會計模組整合

## 🚀 安裝與配置

### 1. 下載與安裝

#### 方法一：Git Clone（推薦）
```bash
# 進入 Odoo 插件目錄
cd /path/to/odoo/addons

# 克隆模組
git clone https://github.com/your-repo/medical_service_management.git
```

#### 方法二：直接下載
```bash
# 確認模組檔案位置
ls D:\odoo_commuity\addons\medical_service_management\
```

### 2. 模組安裝步驟

#### 透過 Odoo 界面安裝
1. **啟動 Odoo 服務器**
   ```bash
   ./start_odoo.sh -d your_database
   ```

2. **更新應用程式列表**
   - 登入 Odoo 後台
   - 啟用開發者模式：設定 → 啟用開發者模式
   - 應用程式 → 更新應用程式列表

3. **安裝模組**
   - 搜尋「企業聯絡人管理擴展」
   - 點選「安裝」按鈕
   - 等待安裝完成

#### 透過命令列安裝
```bash
# 安裝模組
./start_odoo.sh -d your_database -i medical_service_management

# 或包含示範資料
./start_odoo.sh -d your_database -i medical_service_management --without-demo=False
```

### 3. 模組更新

#### 更新單一模組
```bash
# 更新模組
./start_odoo.sh -d your_database -u medical_service_management
```

#### 強制更新（解決快取問題）
```bash
# 停止後更新
./start_odoo.sh -d your_database -u medical_service_management --stop-after-init

# 清除快取後重啟
./start_odoo.sh -d your_database --dev=all
```

#### 更新所有模組
```bash
# 更新所有已安裝的模組
./start_odoo.sh -d your_database --update=all
```

## 📖 使用指南

### 🏢 客戶公司管理

#### 新增客戶公司
1. **基本步驟**
   - 聯絡人 → 建立
   - 勾選「是公司」
   - 填寫公司名稱和基本資訊

2. **財務資訊設定**
   - 使用標準「Tax ID」欄位填寫統編
   - 設定付款方式（電匯/月結/現金/支票）
   - 選擇收款銀行和帳號
   - 設定交易幣別（TWD/USD/EUR）

3. **聯絡資訊設定**
   - 填寫地址資訊
   - 設定公司電話、手機、郵箱
   - 添加公司網站

#### 查看統計資訊
- **部門統計**：點選統計按鈕查看所屬部門
- **聯絡人統計**：檢視所有相關聯絡人
- **設備統計**：預留擴展模組功能

### 🏛️ 部門管理

#### 新增部門
1. **進入部門管理**
   - 企業聯絡人管理 → 聯絡人管理 → 公司部門

2. **建立部門層級**
   - 設定部門名稱和代碼
   - 選擇上級部門（可選）
   - 填寫部門聯絡資訊

3. **聯絡資訊設定**
   - 電話和分機號碼
   - 手機、傳真、郵箱
   - 網站和地址資訊

#### 部門階層管理
- **多層結構**：支援無限層級的部門架構
- **序號排序**：可調整部門顯示順序
- **啟用狀態**：可停用不再使用的部門

### 👥 聯絡人管理

#### 新增聯絡人
1. **基本資訊**
   - 企業聯絡人管理 → 聯絡人管理 → 聯絡人
   - 填寫姓名、職位、稱謂

2. **關聯設定**
   - 選擇所屬公司（可選）
   - 選擇所屬部門（可選）
   - 系統會自動驗證關聯一致性

3. **通訊設定**
   - 設定聯絡方式偏好
   - 添加分類標籤
   - 填寫聯絡資訊

#### 彈性關聯設計
- **獨立聯絡人**：可不歸屬任何公司或部門
- **公司聯絡人**：直接歸屬於公司
- **部門聯絡人**：歸屬於特定部門
- **一致性驗證**：系統自動檢查公司與部門的關聯

### 📊 查詢與報表

#### 搜尋功能
- **多條件搜尋**：姓名、職位、公司、部門等
- **狀態篩選**：啟用/停用狀態過濾
- **關聯篩選**：有公司、有部門、有服務記錄等

#### 群組功能
- **按公司分組**：查看各公司的聯絡人
- **按部門分組**：檢視部門人員結構
- **按職位分組**：了解職位分佈情況

## 🛠️ 界面說明

### 主選單結構
```
企業聯絡人管理
├── 聯絡人管理
│   ├── 客戶公司        # 企業客戶列表
│   ├── 公司部門        # 部門管理界面
│   └── 聯絡人          # 聯絡人管理界面
└── 配置 (預留給擴展模組)
```

### 表單界面功能

#### 客戶公司表單
- **標頭按鈕**：儲存、捨棄變更
- **統計按鈕**：部門數、聯絡人數、設備數
- **頁籤結構**：
  - 基本資訊：名稱、統編、地址
  - 財務資訊：付款方式、銀行資訊
  - 聯絡資訊：電話、郵箱、網站

#### 部門管理表單
- **標頭區域**：儲存、捨棄按鈕
- **狀態標示**：停用部門會顯示紅色標籤
- **資訊分組**：
  - 基本資訊：代碼、上級部門、順序
  - 聯絡資訊：電話、分機、手機、郵箱
  - 地址資訊：完整地址管理
- **下級部門**：顯示子部門列表

#### 聯絡人表單
- **標頭按鈕**：儲存、捨棄變更
- **統計按鈕**：服務工單統計、發送郵件
- **主要資訊**：
  - 基本資料：稱謂、姓名、職位
  - 關聯設定：公司、部門
  - 通訊偏好：偏好聯絡方式

### 列表視圖功能
- **多選編輯**：批次修改記錄
- **可選欄位**：用戶可自訂顯示欄位
- **排序功能**：點選欄位標題排序
- **快速搜尋**：頂部搜尋框

### 看板視圖
- **分組顯示**：按公司或部門分組
- **拖拽操作**：可拖拽移動記錄
- **統計資訊**：顯示相關統計數據

## 📋 資料模型

### res.partner（擴展）
**繼承標準聯絡人模型，新增企業客戶管理功能**

#### 財務欄位
```python
x_payment_bank          # 收款銀行選項
x_payment_account       # 收款帳號
x_payment_method        # 付款方式（電匯/月結/現金/支票）
x_payment_currency      # 交易幣別（TWD/USD/EUR）
```

#### 兼容性欄位
```python
company_country_id      # 公司國家（計算欄位）
company_language        # 公司語言
company_phone           # 公司電話
company_mobile          # 公司手機
company_email           # 公司郵箱
company_website         # 公司網站
company_address         # 公司地址（計算欄位）
```

#### 關聯欄位
```python
x_department_ids        # 關聯的部門列表
x_contact_ids          # 關聯的聯絡人列表
```

#### 統計欄位
```python
x_department_count      # 部門數量（計算欄位）
x_contact_count         # 聯絡人數量（計算欄位）
x_equipment_count       # 設備數量（預留擴展）
```

### company.department
**公司部門管理模型**

#### 基本資訊
```python
name                    # 部門名稱（必填）
display_name            # 完整顯示名稱（計算欄位）
code                    # 部門代碼
sequence               # 顯示順序
active                 # 啟用狀態
```

#### 層級結構
```python
company_id             # 所屬公司
parent_id              # 上級部門
child_ids              # 下級部門列表
```

#### 聯絡資訊
```python
phone                  # 電話
phone_extension        # 分機號碼
mobile                 # 手機
fax                    # 傳真
email                  # 郵箱
website                # 網站
```

#### 地址資訊
```python
street                 # 街道地址
street2                # 地址2
city                   # 城市
state_id               # 省/州
country_id             # 國家
zip                    # 郵遞區號
```

#### 統計欄位
```python
contact_count          # 聯絡人數量（計算欄位）
equipment_count        # 設備數量（預留擴展）
```

### company.contact
**企業聯絡人管理模型**

#### 基本資訊
```python
name                   # 聯絡人姓名（必填）
display_name           # 完整顯示名稱（計算欄位）
title_id               # 稱謂
function               # 職位/職務
active                 # 啟用狀態
```

#### 關聯設定
```python
company_id             # 所屬公司（可選）
department_id          # 所屬部門（可選）
```

#### 通訊資訊
```python
phone                  # 電話
mobile                 # 手機
email                  # 郵箱
website                # 個人網站
communication_preference # 通訊偏好（手機/郵箱）
```

#### 分類與記錄
```python
category_ids           # 分類標籤
last_service_date      # 最近服務日期
service_order_count    # 服務工單數量（預留擴展）
```

## 🔐 權限管理

### 使用者群組
```python
base.group_user           # 一般使用者：讀取、建立、修改（不可刪除）
base.group_system         # 系統管理員：完整 CRUD 權限
base.group_portal         # 入口網站使用者：僅可讀取
```

### 存取權限矩陣
| 模型 | 一般使用者 | 系統管理員 | 入口用戶 |
|------|------------|------------|----------|
| res.partner | ✅讀取 ✅建立 ✅修改 ❌刪除 | ✅✅✅✅ | ✅❌❌❌ |
| company.department | ✅✅✅❌ | ✅✅✅✅ | ✅❌❌❌ |
| company.contact | ✅✅✅❌ | ✅✅✅✅ | ✅❌❌❌ |

### 記錄規則
- **部門存取**：使用者只能存取其有權限的公司部門
- **聯絡人存取**：根據公司歸屬限制存取範圍
- **多公司支援**：預留多公司環境的權限控制

## 🔧 API 說明

### 主要 API 方法

#### res.partner 擴展方法
```python
def _compute_department_count(self):
    """計算部門數量"""
    
def _compute_contact_count(self):
    """計算聯絡人數量"""
    
def _compute_equipment_count(self):
    """計算設備數量（擴展點）"""
    
def _get_equipment_count(self):
    """取得設備數量的內部方法（可被擴展模組覆寫）"""
```

#### company.department 方法
```python
def _compute_display_name(self):
    """計算完整顯示名稱，包含階層結構"""
    
def _compute_contact_count(self):
    """計算聯絡人數量"""
```

#### company.contact 方法
```python
def _compute_display_name(self):
    """計算顯示名稱"""
    
def _check_company_department_consistency(self):
    """驗證公司與部門關聯的一致性"""
```

### 約束和驗證

#### 資料驗證
```python
@api.constrains('x_payment_account')
def _check_payment_account(self):
    """驗證收款帳號與銀行的一致性"""

@api.constrains('company_id', 'department_id')  
def _check_company_department_consistency(self):
    """驗證公司與部門關聯的一致性"""
```

## 🎯 擴展開發

### 擴展點架構

本模組採用完整的擴展點設計，所有需要擴展的功能都預留了標準介面：

#### 主要擴展點
```python
# 設備相關擴展點
def _get_equipment_count(self):
    """設備數量統計擴展點"""
    return 0  # 基礎實作返回 0

# 服務相關擴展點  
def _get_service_order_count(self):
    """服務工單統計擴展點"""
    return 0  # 基礎實作返回 0
```

### 擴展模組開發範例

#### 1. 建立擴展模組
```python
# __manifest__.py
{
    'name': 'Equipment Service Extension',
    'depends': ['medical_service_management', 'fieldservice'],
    # ...
}
```

#### 2. 擴展基礎模型
```python
# models/res_partner.py
from odoo import models, fields, api

class ResPartnerEquipmentExtension(models.Model):
    _inherit = 'res.partner'
    
    def _get_equipment_count(self):
        """覆寫設備數量計算"""
        # 實作實際的設備統計邏輯
        return len(self.equipment_ids)
```

### 建議的擴展模組

#### 🔧 設備管理擴展
- 設備追蹤和歷史記錄
- QR Code 整合
- 保固管理
- 維護排程

#### 📋 服務工單擴展
- 三種工單類型（保養/維修/檢查）
- 技術人員派遣
- 客戶簽名和 PDF 報表
- 工單狀態追蹤

#### 📊 報表分析擴展
- 服務統計報表
- 客戶滿意度追蹤
- 設備效能分析
- 維護成本分析

## 🐛 故障排除

### 常見問題

#### 1. 模組安裝失敗
```bash
# 問題：依賴模組未安裝
# 解決：手動安裝依賴
./start_odoo.sh -d your_database -i base,contacts,mail

# 問題：權限不足
# 解決：檢查檔案權限
chmod -R 755 /path/to/addons/medical_service_management
```

#### 2. 欄位顯示錯誤
```bash
# 問題：Invalid field 'x_tax_id'
# 解決：強制更新模組
./start_odoo.sh -d your_database -u medical_service_management --stop-after-init

# 問題：視圖快取問題
# 解決：清除快取
./start_odoo.sh -d your_database --dev=all
```

#### 3. 權限問題
```python
# 問題：Access Denied
# 解決：檢查使用者群組
# 進入開發者模式 → 使用者與公司 → 使用者 → 檢查群組設定
```

#### 4. 資料一致性錯誤
```python
# 問題：ValidationError
# 解決：檢查關聯資料一致性
# 確保部門的 company_id 與聯絡人的 company_id 一致
```

### 除錯方法

#### 啟用除錯模式
```bash
# 開發模式啟動
./start_odoo.sh -d your_database --dev=all --log-level=debug

# 查看詳細日誌
tail -f /var/log/odoo/odoo.log
```

#### 資料庫檢查
```sql
-- 檢查模組安裝狀態
SELECT name, state FROM ir_module_module 
WHERE name = 'medical_service_management';

-- 檢查視圖定義
SELECT name, model, arch_db FROM ir_ui_view 
WHERE model IN ('res.partner', 'company.department', 'company.contact');
```

### 效能最佳化

#### 資料庫最佳化
```sql
-- 重建索引
REINDEX TABLE res_partner;
REINDEX TABLE company_department;
REINDEX TABLE company_contact;

-- 更新統計資訊
ANALYZE res_partner;
ANALYZE company_department; 
ANALYZE company_contact;
```

#### 快取清理
```python
# Python 控制台執行
env['ir.ui.view'].clear_caches()
env['ir.model.fields'].clear_caches()
env.cr.commit()
```

## 📈 版本歷史

### v18.0.1.0.0（目前版本）
- ✅ 初始版本發布
- ✅ 基礎聯絡人管理功能
- ✅ 部門階層管理
- ✅ 企業客戶擴展欄位
- ✅ 完整的權限控制
- ✅ 示範資料和文檔

### 計劃版本

#### v18.0.1.1.0
- 🔄 多語言支援
- 🔄 進階搜尋和過濾
- 🔄 批次操作功能
- 🔄 匯入匯出工具

#### v18.0.2.0.0
- 🔄 API 介面擴展
- 🔄 Webhook 整合
- 🔄 進階報表功能
- 🔄 行動裝置最佳化

## 🤝 貢獻指南

### 開發環境設置
```bash
# 1. 克隆倉庫
git clone https://github.com/your-repo/medical_service_management.git

# 2. 建立開發分支
git checkout -b feature/your-feature-name

# 3. 安裝開發依賴
pip install -r requirements-dev.txt

# 4. 執行測試
python -m pytest tests/
```

### 程式碼規範
- 遵循 PEP 8 Python 程式碼風格
- 使用 Black 進行程式碼格式化
- 添加適當的文檔字串
- 保持測試覆蓋率 > 80%

### 提交流程
1. Fork 專案
2. 建立功能分支
3. 進行開發和測試
4. 提交 Pull Request
5. 等待程式碼審查

## 📞 技術支援

### 聯絡資訊
- **文檔**: [模組文檔](https://github.com/your-repo/medical_service_management/wiki)
- **問題回報**: [GitHub Issues](https://github.com/your-repo/medical_service_management/issues)
- **功能建議**: [GitHub Discussions](https://github.com/your-repo/medical_service_management/discussions)

### 社群支援
- **Odoo Community**: [OCA 論壇](https://github.com/OCA/field-service)
- **Stack Overflow**: 使用標籤 `odoo` 和 `field-service`

---

## 📄 授權資訊

**版本**: 18.0.1.0.0  
**授權**: LGPL-3  
**作者**: Your Company  
**基於**: Odoo Community Association (OCA) Field Service  
**相容性**: Odoo Community Edition 18.0

---

*最後更新: 2025-08-31*