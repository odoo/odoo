# -*- coding: utf-8 -*-
{
    'name': 'Custom Sale Panels Multiplier',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'إضافة حقل عدد الألواح في Sales Orders مع تأثير على الحسابات المالية',
    'description': """
        Custom Sale Panels Multiplier
        =============================
        
        هذا الموديول يضيف حقل "عدد الألواح" في Sales Order Lines.
        
        المميزات:
        ----------
        * إضافة حقل "عدد الألواح" قبل حقل الكمية
        * ضرب عدد الألواح × الكمية في جميع الحسابات المالية
        * تأثير على السعر، الضرائب، والإجمالي
        * تأثير على الفواتير والـ Deliveries
        * آمن 100% - لا يؤثر على البيانات القديمة
        
        الاستخدام:
        ----------
        1. افتح Quotation جديد
        2. أضف منتج
        3. أدخل الكمية (مثلاً: 10)
        4. أدخل عدد الألواح (مثلاً: 2)
        5. الكمية الفعلية = 2 × 10 = 20
        6. السعر الإجمالي = السعر × 20
        
        ملاحظات:
        --------
        * إذا كان عدد الألواح = 0 أو فارغ، لن يؤثر على الحسابات
        * البيانات القديمة لن تتأثر
        * يمكن إلغاء تثبيت الموديول بدون مشاكل
    """,
    'author': 'Odoo Developer',
    'website': 'https://www.odoo.com',
    'depends': [
        'sale',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
