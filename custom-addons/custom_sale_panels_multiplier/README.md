# Custom Sale Panels Multiplier

## الوصف
موديول Odoo 19.0 Community لإضافة حقل "عدد الألواح" في Sales Order Lines مع تأثير على الحسابات المالية.

## المميزات
- ✅ إضافة حقل "عدد الألواح" قبل حقل الكمية
- ✅ ضرب عدد الألواح × الكمية في جميع الحسابات المالية
- ✅ تأثير على السعر، الضرائب، والإجمالي
- ✅ تأثير على الفواتير والـ Deliveries
- ✅ آمن 100% - لا يؤثر على البيانات القديمة

## التثبيت

### 1. نسخ الموديول
تأكد من أن الموديول موجود في `custom-addons/custom_sale_panels_multiplier`

### 2. تحديث قائمة الموديولات
```
Apps → Update Apps List
```

### 3. تثبيت الموديول
```
Apps → Search: "Custom Sale Panels Multiplier" → Install
```

### 4. Upgrade (إذا كان مثبت مسبقاً)
```bash
python odoo-bin -u custom_sale_panels_multiplier -d your_database
```

## الاستخدام

### خطوات الاستخدام:
1. افتح Quotation جديد
2. أضف منتج
3. أدخل الكمية (مثلاً: 10)
4. أدخل عدد الألواح (مثلاً: 2)
5. **النتيجة**: الكمية الفعلية = 2 × 10 = 20
6. **النتيجة**: السعر الإجمالي = السعر × 20

### مثال:
- **المنتج**: منشار Hasaa
- **الكمية**: 1.0000 m²
- **عدد الألواح**: 1.00
- **السعر الوحدة**: 530.00 LE
- **الكمية الفعلية**: 1.00 × 1.00 = 1.00
- **الإجمالي**: 530.00 LE

إذا غيرت عدد الألواح إلى 2:
- **الكمية الفعلية**: 2.00 × 1.00 = 2.00
- **الإجمالي**: 530.00 × 2 = 1,060.00 LE

## ملاحظات مهمة

### الأمان
- ✅ إذا كان عدد الألواح = 0 أو فارغ، لن يؤثر على الحسابات
- ✅ البيانات القديمة لن تتأثر
- ✅ يمكن إلغاء تثبيت الموديول بدون مشاكل

### التوافق
- ✅ Odoo 19.0 Community Edition
- ✅ متوافق مع sale_stock, sale_accounting
- ✅ لا يحتاج Enterprise Features

## البنية التقنية

### الملفات:
```
custom_sale_panels_multiplier/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── sale_order_line.py
├── views/
│   └── sale_order_views.xml
└── security/
    └── ir.model.access.csv
```

### الحقول المضافة:
- `number_of_panels`: عدد الألواح (Float)
- `effective_quantity`: الكمية الفعلية (Computed Float, store=True)

### Methods المضافة:
- `_compute_effective_quantity`: حساب الكمية الفعلية
- `_prepare_base_line_for_taxes_computation`: Override للحسابات المالية
- `_compute_amount`: Override لحساب المبالغ
- `_prepare_invoice_line`: Override للفواتير

## الدعم
للمشاكل أو الاستفسارات، يرجى التواصل مع فريق التطوير.

## الترخيص
LGPL-3
