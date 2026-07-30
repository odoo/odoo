#!/usr/bin/env python3
"""Translate the KSW_commissions and KSW_deduction .pot files to Arabic.

Builds an Arabic ar_001.po next to each .pot using a hand-curated
glossary of HR / payroll / loan terminology aligned with Saudi labor
practice. Strings not found in the dictionary are left as empty
``msgstr`` so the Odoo client falls back to English (preferable to a
machine-mistranslated label).

Run from anywhere:

    python3 /home/odoo/odoo_learning_proj/odoo/custom_addons/KSW/_translate_ksw_to_ar.py
"""
import os
import re
import polib

# ---------------------------------------------------------------------------
# Glossary: english source string → Arabic (Modern Standard / KSA business).
# Keep keys EXACT — including punctuation, ampersand entities, HTML tags.
# ---------------------------------------------------------------------------
TR = {
    # ------------- Core nouns / domain ----------------------------------
    'Employee': 'الموظف',
    'Employees': 'الموظفون',
    '# Employees': 'عدد الموظفين',
    'Department': 'القسم',
    'Job Position': 'المسمى الوظيفي',
    'Manager': 'المدير',
    'Site': 'الموقع',
    'Sites': 'المواقع',
    'Site Manager': 'مدير الموقع',
    'Supervisor': 'المشرف',
    'Accountant': 'المحاسب',
    'Admin': 'مسؤول النظام',
    'Period': 'الفترة',
    'Date': 'التاريخ',
    'Year': 'السنة',
    'Month': 'الشهر',
    'Status': 'الحالة',
    'Code': 'الرمز',
    'Name': 'الاسم',
    'Description': 'الوصف',
    'Sequence': 'الترتيب',
    'Reference': 'المرجع',
    'Sheet Ref.': 'رقم الكشف',
    'Notes': 'ملاحظات',
    'Note': 'ملاحظة',
    'Active': 'مُفعَّل',
    'Archived': 'مؤرشف',
    'Currency': 'العملة',
    'Company': 'الشركة',
    'Bank Account': 'الحساب البنكي',
    'Bank Transfer': 'التحويل البنكي',
    'Bank Transfer Amount': 'مبلغ التحويل البنكي',
    'Amount': 'المبلغ',
    'Total': 'الإجمالي',
    'Subtotal': 'المجموع الفرعي',
    'Lines Subtotal': 'مجموع البنود',
    'Gross Total': 'الإجمالي قبل الخصم',
    'Basic Wage': 'الراتب الأساسي',
    'National ID': 'الهوية الوطنية',
    'Category': 'الفئة',
    'Categories': 'الفئات',
    'Type': 'النوع',
    'Vehicle': 'المركبة',
    'Required': 'المطلوب',
    'Required Trips': 'الرحلات المطلوبة',
    'Actual': 'الفعلي',
    'Actual Trips': 'الرحلات الفعلية',
    'Multiplied Trips': 'الرحلات المضاعفة',
    'Worked Days': 'أيام العمل',
    'Days': 'الأيام',
    'Band': 'الشريحة',
    'Rate': 'النسبة',
    'Tier': 'المستوى',
    'Tier 1': 'المستوى الأول',
    'Tier 2': 'المستوى الثاني',
    'Tier 3': 'المستوى الثالث',
    'Tier 4': 'المستوى الرابع',
    'Tier 5': 'المستوى الخامس',

    # ------------- Commissions / allowances -----------------------------
    'Commission': 'العمولة',
    'Commissions': 'العمولات',
    'Commissions and Other Allowances': 'العمولات والبدلات الأخرى',
    'KSW Commissions': 'عمولات KSW',
    'KSW Commissions & Other Allowances': 'عمولات KSW والبدلات الأخرى',
    'Allowance': 'البدل',
    'Allowances': 'البدلات',
    'Bonus': 'مكافأة',
    'Commission & Allowance Sheet': 'كشف العمولات والبدلات',
    'Commission &amp; Allowance Sheet': 'كشف العمولات والبدلات',
    'Allowance & Commission Lines': 'بنود البدلات والعمولات',
    'Allowance &amp; Commission Lines': 'بنود البدلات والعمولات',
    'Commission Sheet': 'كشف العمولة',
    'Commission Sheets': 'كشوف العمولات',
    'Commission Categories': 'فئات العمولات',
    'Commission Configuration': 'إعدادات العمولات',
    'Commission Templates': 'قوالب العمولات',
    'Commission Template': 'قالب العمولة',
    'Commission Batch': 'دفعة العمولة',
    'Commission Batches': 'دفعات العمولات',
    'Commission Approval': 'اعتماد العمولة',
    'Driver Commission': 'عمولة السائق',
    'Driver Commissions': 'عمولات السائقين',
    'Driver Commission Sheet': 'كشف عمولة السائق',
    'Driver Commission Sheets': 'كشوف عمولات السائقين',
    'Driver Trip Tally': 'إجمالي رحلات السائق',
    'Driver\'s Commission': 'عمولة السائق',
    "Driver's Commission": 'عمولة السائق',
    'Total Commission': 'إجمالي العمولة',
    'Collection Commission': 'عمولة التحصيل',
    'My Sheet': 'كشفي',
    "My Subordinates' Sheets": 'كشوف مرؤوسي',
    'All Sheets': 'كل الكشوف',
    'Awaiting Accountant': 'بانتظار المحاسب',
    'Apply Template': 'تطبيق القالب',
    'Tier Rate Configuration': 'إعدادات نسب المستويات',
    'Tier Rate Reference': 'مرجع نسب المستويات',

    # ------------- Loans / deductions -----------------------------------
    'Loan': 'القرض',
    'Loans': 'القروض',
    'Loan Request': 'طلب قرض',
    'Loan Requests': 'طلبات القروض',
    'Loan Approval': 'اعتماد القرض',
    'Loan Approval History': 'سجل اعتمادات القرض',
    'Loan Details': 'تفاصيل القرض',
    'Loans Deduction': 'خصم القروض',
    'Loans (auto)': 'القروض (تلقائي)',
    'Deduction': 'الخصم',
    'Deductions': 'الخصومات',
    'KSW Deduction': 'خصومات KSW',
    'Deduction Type': 'نوع الخصم',
    'Deduction Types': 'أنواع الخصومات',
    'Installment': 'القسط',
    'Installments': 'الأقساط',
    'Installment Amount': 'قيمة القسط',
    'Installment Modification': 'تعديل القسط',
    'Loan Installment Modification': 'تعديل قسط القرض',
    'Number of Installments': 'عدد الأقساط',
    'Pending': 'معلّق',
    'Paid': 'مدفوع',
    'Skipped': 'متخطى',
    'Paid (Manual)': 'مدفوع (يدوي)',
    'Manual': 'يدوي',
    'Manual entries': 'الإدخالات اليدوية',
    'Settlement': 'التسوية',
    'Awaiting Commission': 'بانتظار العمولة',
    'Awaiting Sheet': 'كشف بانتظار التسوية',
    'Awaiting Commission Sheet': 'بانتظار كشف العمولة',
    'Awaiting Commission Sheet (not yet created)': 'بانتظار كشف العمولة (لم يُنشأ بعد)',
    'Pending Commission Sheet': 'كشف عمولة معلّق',
    'Paid via Commission Sheet': 'مدفوع عبر كشف العمولة',
    'Paid via Sheet': 'مدفوع عبر الكشف',
    'Originally Scheduled Amount': 'المبلغ المجدول أصلاً',
    'Total Loan Amount': 'إجمالي مبلغ القرض',

    # ------------- Approvals / state machine ----------------------------
    'Draft': 'مسودة',
    'Confirmed': 'مؤكَّد',
    'Done': 'منجز',
    'Cancelled': 'مُلغى',
    'Closed': 'مُقفل',
    'Refused': 'مرفوض',
    'Approved': 'معتمد',
    'New': 'جديد',
    'Renewal': 'تجديد',
    'Delete': 'حذف',
    'Submit': 'إرسال',
    'Submitted': 'مُرسَل',
    'Confirm': 'تأكيد',
    'Cancel': 'إلغاء',
    'Save': 'حفظ',
    'Reset': 'إعادة',
    'Reset to Draft': 'إعادة إلى المسودة',
    'Refuse': 'رفض',
    'Approve': 'اعتماد',
    'Send for Approval': 'إرسال للاعتماد',
    'Validate': 'تصديق',
    'Print': 'طباعة',
    'Finalise': 'إنهاء',
    'Finalised': 'مُنهَى',
    'Close Batch': 'إقفال الدفعة',
    'DM Approval': 'اعتماد المدير المباشر',
    'HR Approval': 'اعتماد الموارد البشرية',
    'Accounting Approval': 'اعتماد المحاسبة',
    'DM Approver': 'مُعتمِد المدير المباشر',
    'HR Approver': 'مُعتمِد الموارد البشرية',
    'Accounting Approver': 'مُعتمِد المحاسبة',
    'Approved by': 'اعتُمد بواسطة',
    'Approved by Manager': 'اعتمد من قِبَل المدير',
    'Confirmed by': 'أُكِّد بواسطة',
    'Finalised by': 'أُنهي بواسطة',
    'Reviewed by Accountant': 'روجِع من قِبَل المحاسب',
    'Prepared by Supervisor': 'أُعدَّ من قِبَل المشرف',
    'Printed on': 'طُبع في',

    # ------------- Reports / actions ------------------------------------
    'Report': 'التقرير',
    'Reports': 'التقارير',
    'Bank Files': 'الملفات البنكية',
    'Configuration': 'الإعدادات',
    'Apply': 'تطبيق',
    'All banks – Excel files': 'جميع البنوك – ملفات إكسل',
    'All banks – Text files (Kawthar)': 'جميع البنوك – ملفات نصية (الكوثر)',

    # ------------- Common short labels ----------------------------------
    'Active': 'مُفعَّل',
    'Activities': 'الأنشطة',
    'Activity State': 'حالة النشاط',
    'Activity Type Icon': 'أيقونة نوع النشاط',
    'Activity Exception Decoration': 'تنبيه استثناء النشاط',
    'Action Needed': 'إجراء مطلوب',
    'Attachment Count': 'عدد المرفقات',
    'Attachments': 'المرفقات',
    'Followers': 'المتابعون',
    'Messages': 'الرسائل',
    'Message Delivery Error': 'خطأ في تسليم الرسالة',
    'Number of Messages': 'عدد الرسائل',
    'Number of Actions': 'عدد الإجراءات',
    'Number of Errors': 'عدد الأخطاء',
    'Tags': 'الوسوم',
    'Color': 'اللون',
    'Color Index': 'فهرس اللون',
    'Display Name': 'الاسم الظاهر',
    'Created on': 'تاريخ الإنشاء',
    'Created by': 'أنشأه',
    'Last Updated on': 'آخر تحديث',
    'Last Updated by': 'حدّثه آخراً',
    'ID': 'المعرّف',

    # ------------- HTML / decorative tags (commonly seen) ---------------
    '<strong>Approved by</strong>': '<strong>اعتُمد بواسطة</strong>',
    '<strong>Approved by Manager</strong>': '<strong>اعتمد من قِبَل المدير</strong>',
    '<strong>Bank Transfer Amount</strong>': '<strong>مبلغ التحويل البنكي</strong>',
    '<strong>Basic Wage</strong>': '<strong>الراتب الأساسي</strong>',
    '<strong>Confirmed by</strong>': '<strong>أُكِّد بواسطة</strong>',
    '<strong>Department</strong>': '<strong>القسم</strong>',
    "<strong>Driver's Commission</strong>": '<strong>عمولة السائق</strong>',
    '<strong>Employee</strong>': '<strong>الموظف</strong>',
    '<strong>Finalised by</strong>': '<strong>أُنهي بواسطة</strong>',
    '<strong>Gross Total</strong>': '<strong>الإجمالي قبل الخصم</strong>',
    '<strong>Job Position</strong>': '<strong>المسمى الوظيفي</strong>',
    '<strong>Lines Subtotal</strong>': '<strong>مجموع البنود</strong>',
    '<strong>Loans Deduction</strong>': '<strong>خصم القروض</strong>',
    '<strong>National ID</strong>': '<strong>الهوية الوطنية</strong>',
    '<strong>Period</strong>': '<strong>الفترة</strong>',
    '<strong>Prepared by Supervisor</strong>': '<strong>أُعدَّ من قِبَل المشرف</strong>',
    '<strong>Printed on</strong>': '<strong>طُبع في</strong>',
    '<strong>Reviewed by Accountant</strong>': '<strong>روجِع من قِبَل المحاسب</strong>',
    '<strong>Sheet Ref.</strong>': '<strong>رقم الكشف</strong>',
    '<strong>Site</strong>': '<strong>الموقع</strong>',
    '<strong>Site Manager</strong>': '<strong>مدير الموقع</strong>',
    '<strong>Status</strong>': '<strong>الحالة</strong>',
    '<strong>Supervisor</strong>': '<strong>المشرف</strong>',
    '<strong>Loan Approval:</strong>': '<strong>اعتماد القرض:</strong>',
    '<strong>Step 1 — Loan Details</strong>': '<strong>الخطوة 1 — تفاصيل القرض</strong>',
    '<strong>Step 2 — Justification &amp; Documents</strong>': '<strong>الخطوة 2 — المبرر والمستندات</strong>',
    '<strong>Submit a new loan request</strong>': '<strong>تقديم طلب قرض جديد</strong>',
    '<strong>Summary</strong>': '<strong>الملخص</strong>',
    '<strong>Request under review</strong>': '<strong>الطلب قيد المراجعة</strong>',
    '<strong>You are about to refuse this loan request.</strong>': '<strong>أنت على وشك رفض طلب القرض هذا.</strong>',
    '<strong>⛔ Loan Request Refused</strong>': '<strong>⛔ تم رفض طلب القرض</strong>',
    '<b>At step:</b>': '<b>عند المرحلة:</b>',
    '<b>Reason:</b>': '<b>السبب:</b>',

    # ------------- Step labels / wizards --------------------------------
    '1 – New': '1 – جديد',
    '2 – Renewal': '2 – تجديد',
    '3 – Delete': '3 – حذف',

    # ------------- Settlement label phrases -----------------------------
    'Awaiting Commission Sheet %s': 'بانتظار كشف العمولة %s',
    'Paid via Commission Sheet %s': 'مدفوع عبر كشف العمولة %s',

    # ------------- Validation / error messages --------------------------
    'Category code must be unique.': 'يجب أن يكون رمز الفئة فريداً.',
    'A given holiday can only be entered once per sheet under the same category.':
        'لا يمكن إدخال نفس العطلة أكثر من مرة في الكشف الواحد تحت نفس الفئة.',

    # ------------- Misc ------------------------------------------------
    'Accounting': 'المحاسبة',
    'Accounting: Budget confirmed': 'المحاسبة: الموازنة مؤكَّدة',
    'Awaiting Sheet': 'كشف بانتظار التسوية',
    'Acc Approved By': 'اعتمد من قِبَل المحاسبة',
    'Acc Approved Date': 'تاريخ اعتماد المحاسبة',
    'Acc Original Amount': 'المبلغ الأصلي (محاسبة)',
    'Acc Original Installments': 'الأقساط الأصلية (محاسبة)',
    'Assigned Employees': 'الموظفون المعنيّون',
    'Batch': 'الدفعة',
    'All Sheets': 'كل الكشوف',
    'Apply Template': 'تطبيق القالب',
}

# ---------------------------------------------------------------------------
# Bulk extension — short labels, view text, statuses, holidays, model names
# ---------------------------------------------------------------------------
TR.update({
    # ------------- Selection values / states ----------------------------
    'Done (Finalised)': 'منجز (مُنهَى)',
    'Pending DM': 'بانتظار المدير المباشر',
    'Pending HR': 'بانتظار الموارد البشرية',
    'Pending Accounting': 'بانتظار المحاسبة',
    'Pending GM': 'بانتظار المدير العام',
    'Pending GM Final': 'بانتظار اعتماد المدير العام النهائي',
    'Pending DM Approval': 'بانتظار اعتماد المدير المباشر',
    'Pending HR Approval': 'بانتظار اعتماد الموارد البشرية',
    'Approval State': 'حالة الاعتماد',
    'Approval Confirmations': 'تأكيدات الاعتماد',
    'Confirm Refusal': 'تأكيد الرفض',
    'Refusal Reason': 'سبب الرفض',
    'Refused At': 'رُفض في',
    'Refused By': 'رفضه',
    'Refusing At': 'حالة الرفض عند',
    'Reason for refusal': 'سبب الرفض',
    'Reason': 'السبب',
    'Reopen': 'إعادة فتح',

    # Roles / approver labels
    'DM': 'المدير المباشر',
    'HR': 'الموارد البشرية',
    'GM': 'المدير العام',
    'Officer': 'مسؤول',
    'Self': 'الذاتية',
    'Self-Service': 'الخدمة الذاتية',
    'Dm Approved By': 'اعتمده المدير المباشر',
    'Dm Approved Date': 'تاريخ اعتماد المدير المباشر',
    'Hr Approved By': 'اعتمدته الموارد البشرية',
    'Hr Approved Date': 'تاريخ اعتماد الموارد البشرية',
    'Gm Approved By': 'اعتمده المدير العام',
    'Gm Approved Date': 'تاريخ اعتماد المدير العام',
    'Gm Original Amount': 'المبلغ الأصلي (المدير العام)',
    'Gm Original Installments': 'الأقساط الأصلية (المدير العام)',
    'GM Final Approval': 'الاعتماد النهائي من المدير العام',
    'GM Final Approver': 'مُعتمِد المدير العام النهائي',
    'Confirmed By': 'أُكِّد من قِبَل',
    'Confirmed Date': 'تاريخ التأكيد',
    'Done By': 'أُنجز بواسطة',
    'Done Date': 'تاريخ الإنجاز',
    'Collected By': 'حُصِّل بواسطة',
    'Collected On': 'تاريخ التحصيل',
    'Responsible User': 'المستخدم المسؤول',
    'Company Partner': 'شريك الشركة',
    'User': 'المستخدم',

    # ------------- Buttons / approval actions ---------------------------
    '⛔ Refuse': '⛔ رفض',
    '✅ Approve (DM)': '✅ اعتماد (المدير المباشر)',
    '✅ Approve (HR)': '✅ اعتماد (الموارد البشرية)',
    '✅ Approve (Accounting)': '✅ اعتماد (المحاسبة)',
    '✅ Final Approve (GM)': '✅ الاعتماد النهائي (المدير العام)',
    '✓ Confirmed': '✓ مؤكَّد',
    '➕ Record New Penalty': '➕ تسجيل غرامة جديدة',
    'Submit Request': 'تقديم الطلب',
    'Refuse Loan Request': 'رفض طلب القرض',
    'Request a Loan': 'طلب قرض',
    'Edit': 'تعديل',
    'Edit only': 'تعديل فقط',
    'Edit and Delete': 'تعديل وحذف',
    'Delete only': 'حذف فقط',
    'Export': 'تصدير',
    'Export Bank File': 'تصدير ملف بنكي',
    'Export Mode': 'نمط التصدير',
    'Specific bank – Excel': 'بنك محدد – إكسل',
    'Specific bank – Text file': 'بنك محدد – ملف نصي',

    # ------------- Sheets / driver commission ---------------------------
    'Sheet': 'الكشف',
    'Sheets': 'الكشوف',
    'Sheet Count': 'عدد الكشوف',
    'Sheet Total': 'إجمالي الكشف',
    'Driver': 'السائق',
    'Drivers': 'السائقون',
    'Driver Total': 'إجمالي السائق',
    'Driver Commission Amount': 'مبلغ عمولة السائق',
    'Driver Commission — Monthly Summary': 'عمولة السائق — الملخص الشهري',
    'Per-Driver Roll-up': 'إجمالي لكل سائق',
    'Total Trips (Mult.)': 'إجمالي الرحلات (مضاعفة)',
    'Trip Base': 'أساس الرحلة',
    'Trips': 'الرحلات',
    'Trips in band': 'الرحلات في الشريحة',
    'Mult.': 'مضاعف',
    'Multiplied': 'مضاعف',
    'Req.': 'المطلوب',
    'Vehicle Number': 'رقم المركبة',
    'Vehicle Commission': 'عمولة المركبة',
    'Rate (SAR / trip)': 'النسبة (ريال / رحلة)',
    'Required Trips (full month)': 'الرحلات المطلوبة (شهر كامل)',
    'Required/30d': 'المطلوب / 30 يوم',
    'No driver lines entered.': 'لم تُدخل بيانات سائقين.',
    'No lines entered.': 'لا توجد بنود.',
    'Tier 1 (No Commission)': 'المستوى الأول (بلا عمولة)',
    'Tier 5 (Open)': 'المستوى الخامس (مفتوح)',
    'Tier 5 (remaining)': 'المستوى الخامس (المتبقي)',
    'Tier Breakdown': 'توزيع المستويات',
    'Tier1 Trips': 'رحلات المستوى الأول',
    'Tier2 Trips': 'رحلات المستوى الثاني',
    'Tier3 Trips': 'رحلات المستوى الثالث',
    'Tier4 Trips': 'رحلات المستوى الرابع',
    'Tier5 Trips': 'رحلات المستوى الخامس',
    'Tier2 Rate': 'نسبة المستوى الثاني',
    'Tier3 Rate': 'نسبة المستوى الثالث',
    'Tier4 Rate': 'نسبة المستوى الرابع',
    'Tier5 Rate': 'نسبة المستوى الخامس',
    'Tiered Commission Rules': 'قواعد العمولات المتدرجة',
    'T1': 'م1',
    'T2': 'م2',
    'T3': 'م3',
    'T4': 'م4',
    'T5': 'م5',
    'TOTALS': 'الإجمالي',

    # ------------- Holidays / categories --------------------------------
    'Eid Al-Adha': 'عيد الأضحى',
    'Eid Al-Fitr': 'عيد الفطر',
    'National Day': 'اليوم الوطني',
    'Foundation Day': 'يوم التأسيس',
    'Holiday': 'العطلة',
    'Holiday Bonus': 'بدل العطلة',
    'Required when the category is "Holiday Bonus".':
        'مطلوب عندما تكون الفئة "بدل العطلة".',

    # ------------- Allowance / commission category names ----------------
    'Data Entry Allowance': 'بدل إدخال البيانات',
    'Friday Work Allowance': 'بدل العمل يوم الجمعة',
    'Mobile Phone Allowance': 'بدل الجوال',
    'Project Management Allowance': 'بدل إدارة المشاريع',
    'Location Allowance': 'بدل الموقع',
    'Sales Commission and Other': 'عمولات المبيعات وأخرى',
    'Employee Bonus': 'مكافأة موظف',

    # ------------- Deduction types --------------------------------------
    'Personal Loan': 'قرض شخصي',
    'Salary Advance': 'سُلفة راتب',
    'Government Penalty': 'غرامة حكومية',
    'Internal Penalty': 'غرامة داخلية',
    'EOS — Resignation (Art. 85)': 'نهاية الخدمة — استقالة (المادة 85)',
    'EOS — Termination (Art. 84)': 'نهاية الخدمة — إنهاء عقد (المادة 84)',
    'Force Majeure (Art. 87)': 'القوة القاهرة (المادة 87)',
    'End-of-Service (Saudi Art. 84–88)': 'نهاية الخدمة (المواد السعودية 84–88)',
    'Loan (5-step Approval)': 'قرض (اعتماد بخمس خطوات)',
    'Loan Type': 'نوع القرض',
    'Borrowed': 'مُقترَض',
    'Borrowed (with employee consent)': 'مُقترَض (بموافقة الموظف)',
    'Company Paid (on behalf of employee)': 'دفعته الشركة (نيابة عن الموظف)',
    'Company-Paid': 'مدفوع من الشركة',
    'Penalties': 'الغرامات',
    'Advances & Other': 'السلف وأخرى',
    'Non-loans': 'غير القروض',

    # ------------- Dashboards / lists -----------------------------------
    'Dashboard': 'لوحة المعلومات',
    'My Loans': 'قروضي',
    'My Pending Approvals': 'اعتماداتي المعلّقة',
    "My Employee's Sheets": 'كشوف موظفي',
    'Active Deductions': 'الخصومات الفعّالة',
    'Active Deductions Breakdown': 'تفاصيل الخصومات الفعّالة',
    'All Deductions': 'جميع الخصومات',
    'Other Active Deductions': 'خصومات فعّالة أخرى',
    'Other Active Deductions (same employee)': 'خصومات فعّالة أخرى (لنفس الموظف)',
    'Total Outstanding (other)': 'الإجمالي المتبقي (أخرى)',
    'Monthly Impact (other)': 'الأثر الشهري (أخرى)',
    'Monthly Deduction Total': 'إجمالي الخصم الشهري',
    'Monthly Cumulative Summary': 'الملخص التراكمي الشهري',
    'Total Paid': 'الإجمالي المدفوع',
    'Total Pending': 'الإجمالي المعلّق',
    'Total Payable': 'الإجمالي المستحق',
    'Paid / Total': 'المدفوع / الإجمالي',
    'Progress %': 'نسبة الإنجاز ٪',
    'Progress Percent': 'نسبة الإنجاز',
    'Repayment progress': 'تقدّم السداد',
    'Percentage of the total amount already paid.': 'النسبة المئوية من إجمالي المبلغ المسدّد.',
    'Lines Total': 'إجمالي البنود',
    'Lines': 'البنود',
    'Line': 'البند',
    'By Department': 'حسب القسم',
    'By Employee': 'حسب الموظف',
    'By Type': 'حسب النوع',
    'Summary': 'الملخص',
    'Summary by Department': 'الملخص حسب القسم',
    '— No Department —': '— بلا قسم —',

    # ------------- Field labels / amounts -------------------------------
    'Loans Amount': 'مبلغ القروض',
    'Loans (locked)': 'القروض (مُجمَّدة)',
    'Live Shortfall (auto)': 'العجز الحالي (تلقائي)',
    'Total amount of the deduction.': 'إجمالي مبلغ الخصم.',
    'Total Loan Amount': 'إجمالي مبلغ القرض',
    'Default Installments': 'الأقساط الافتراضية',
    'Default installments must be at least 1.': 'يجب ألا تقل الأقساط الافتراضية عن 1.',
    'Number of monthly installments.': 'عدد الأقساط الشهرية.',
    'Number of monthly installments. Defaults to the type suggestion.':
        'عدد الأقساط الشهرية. يتم استخدام افتراضي النوع.',
    'Estimated amount deducted each month (loan amount / number of installments).':
        'المبلغ التقديري المخصوم كل شهر (إجمالي القرض ÷ عدد الأقساط).',
    'Start Month': 'شهر البداية',
    'Month from which installments start (first day of month).':
        'الشهر الذي تبدأ منه الأقساط (اليوم الأول من الشهر).',
    'Month from which the first installment is deducted.':
        'الشهر الذي يبدأ منه خصم القسط الأول.',
    'Month must be between 1 and 12.': 'يجب أن يكون الشهر بين 1 و 12.',
    'Month number (1-12)': 'رقم الشهر (1-12)',
    'Period Date': 'تاريخ الفترة',
    'First day of (year, month) — used for payslip period matching.':
        'اليوم الأول من (السنة، الشهر) — يُستخدم لمطابقة فترة قسيمة الراتب.',
    'First day of the month covered by this sheet.':
        'اليوم الأول من الشهر الذي يغطيه هذا الكشف.',
    'Wage': 'الراتب',
    'Last Wage': 'آخر راتب',
    'Wage of the current active version.': 'راتب الإصدار الفعّال الحالي.',
    'Service Years': 'سنوات الخدمة',
    'Annual Vacation Balance': 'رصيد الإجازة السنوية',
    'Vacation Balance (days)': 'رصيد الإجازة (أيام)',
    'Vacation Balance Breakdown': 'تفاصيل رصيد الإجازة',
    'Vacation Balance Value': 'قيمة رصيد الإجازة',
    'Human-readable per-version daily-rate breakdown.':
        'تفصيل النسب اليومية لكل إصدار بصيغة قابلة للقراءة.',
    'Acc Original Amount': 'المبلغ الأصلي (المحاسبة)',
    'Acc Original Installments': 'الأقساط الأصلية (المحاسبة)',
    'Acc Approved By': 'اعتمدته المحاسبة',
    'Acc Approved Date': 'تاريخ اعتماد المحاسبة',

    # ------------- Misc field labels ------------------------------------
    'Identification': 'الهوية',
    'Identification No': 'رقم الهوية',
    'X Deduction Currency': 'عملة الخصم',
    'X Refused Date': 'تاريخ الرفض',
    'X Unwind Data': 'بيانات الاسترجاع',
    'X Can Cancel': 'يمكن الإلغاء',
    'X Can Submit': 'يمكن الإرسال',
    'X Can Dm Approve': 'يمكن للمدير المباشر الاعتماد',
    'Current user may delete': 'يحق للمستخدم الحالي الحذف',
    'Current user may edit amount': 'يحق للمستخدم الحالي تعديل المبلغ',
    'Current user may edit installments': 'يحق للمستخدم الحالي تعديل الأقساط',
    'Loan Installment Modification (post-confirmation)':
        'تعديل قسط القرض (بعد التأكيد)',
    'Loan Request Modification (pre-confirmation)':
        'تعديل طلب القرض (قبل التأكيد)',
    'Is Locked': 'مُجمَّد',
    'Is System': 'نظامي',
    'Set on seeded categories. Blocks unlink.':
        'يُحدَّد للفئات المُنشأة افتراضياً. يمنع الحذف.',
    'Stable identifier used in reports / exports. Must be unique.':
        'معرّف ثابت يُستخدم في التقارير والتصدير. يجب أن يكون فريداً.',
    'Short unique code used on payslip input lines (e.g. LOAN, GOVPEN).':
        'رمز قصير فريد يُستخدم على بنود قسيمة الراتب (مثل LOAN, GOVPEN).',
    'Loan-category deduction type. Non-loan types are hidden.':
        'نوع خصم من فئة القروض. الأنواع غير القرضية مخفية.',
    'Only relevant for loan types. Drives the 5-step approval chain.':
        'يُستخدم فقط لأنواع القروض. يُحرّك سلسلة الاعتماد بخمس خطوات.',
    'Only one commission sheet per employee per month.':
        'كشف عمولة واحد فقط لكل موظف في الشهر.',
    'Only one driver commission sheet per site per month.':
        'كشف عمولة سائقين واحد فقط لكل موقع في الشهر.',
    'The deduction type code must be unique.': 'يجب أن يكون رمز نوع الخصم فريداً.',

    # ------------- Hr.payslip / payslip ---------------------------------
    'Pay Slip': 'قسيمة الراتب',
    'Payslip': 'قسيمة الراتب',
    'Payslip that consumed this installment.': 'قسيمة الراتب التي خصمت هذا القسط.',

    # ------------- Manual entry / details -------------------------------
    'Manual Entry': 'إدخال يدوي',
    'Date the manual payment was recorded.': 'تاريخ تسجيل الدفع اليدوي.',
    'Accountant who recorded this manual payment.': 'المحاسب الذي سجّل هذا الدفع اليدوي.',
    'Accountant who finalised the sheet (state confirmed → done).':
        'المحاسب الذي أنهى الكشف (الحالة من مؤكَّد إلى منجز).',
    'Supervisor who confirmed the sheet (state draft → confirmed).':
        'المشرف الذي أكّد الكشف (الحالة من مسودة إلى مؤكَّد).',
    'Are you sure you want to cancel this deduction?':
        'هل أنت متأكد من إلغاء هذا الخصم؟',
    'Actual days worked this month (entered by supervisor).':
        'عدد أيام العمل الفعلي هذا الشهر (يُدخلها المشرف).',
    "Pre-fill lines from the employee's assigned commission template":
        'تعبئة البنود من قالب العمولة المسنَد للموظف',
    "Read own deductions and any subordinate's (employees who report directly to me).":
        'الاطلاع على خصوماته وعلى خصومات مرؤوسيه المباشرين.',
    'See own commission sheet only.': 'الاطلاع على كشف عمولته فقط.',
    'Edit any commission sheet company-wide and reset confirmed sheets back to draft.':
        'تعديل أي كشف عمولة على مستوى الشركة وإعادة الكشوف المؤكَّدة إلى المسودة.',
    'Edit commission sheets for direct subordinates with x_is_attendance_sheet=True.':
        'تعديل كشوف العمولة للمرؤوسين المباشرين الذين تكون لهم بطاقة حضور يدوية.',
    'Create and edit non-loan deductions for all employees.':
        'إنشاء وتعديل الخصومات غير القرضية لجميع الموظفين.',
    'Create your first commission template!': 'أنشئ أول قالب عمولة!',
    'You have no loan requests yet': 'لا توجد لديك طلبات قروض بعد',
    'Decision Support': 'دعم القرار',
    'Details': 'التفاصيل',
    'Schedule': 'الجدول',
    'Sheets': 'الكشوف',
    'Operations': 'العمليات',
    'Commission Management': 'إدارة العمولات',
    'Deduction Management': 'إدارة الخصومات',
    'Financials': 'المالية',
    'Default Lines': 'البنود الافتراضية',
    'Template Lines': 'بنود القالب',
    'Template': 'القالب',

    # ------------- Misc UI words ----------------------------------------
    'Other': 'أخرى',
    'Followers (Partners)': 'المتابعون (الشركاء)',
    'Has Message': 'يحتوي رسالة',
    'Is Follower': 'متابع',
    'Number of errors': 'عدد الأخطاء',
    'Number of messages requiring action': 'عدد الرسائل التي تتطلب إجراءً',
    'Number of messages with delivery error': 'عدد الرسائل ذات خطأ التسليم',
    'If checked, new messages require your attention.':
        'إذا تم تفعيله، فإن الرسائل الجديدة تحتاج اهتمامك.',
    'If checked, some messages have a delivery error.':
        'إذا تم تفعيله، فإن بعض الرسائل بها خطأ في التسليم.',
    'Message Delivery error': 'خطأ تسليم الرسالة',
    'SMS Delivery error': 'خطأ تسليم الرسالة النصية',
    'Website Messages': 'رسائل الموقع',
    'Website communication history': 'سجل تواصل الموقع',
    'My Activity Deadline': 'موعد نهائي لنشاطي',
    'Next Activity Calendar Event': 'حدث التقويم للنشاط التالي',
    'Next Activity Deadline': 'الموعد النهائي للنشاط التالي',
    'Next Activity Summary': 'ملخص النشاط التالي',
    'Next Activity Type': 'نوع النشاط التالي',
    'Type of the exception activity on record.': 'نوع نشاط الاستثناء المسجَّل.',
    'Icon': 'الأيقونة',
    'Icon to indicate an exception activity.': 'أيقونة للدلالة على نشاط استثنائي.',
    'Font awesome icon e.g. fa-tasks': 'أيقونة Font Awesome مثل fa-tasks',
    'Kind': 'النوع',
    'Job': 'الوظيفة',
    'Gross': 'الإجمالي',
    'Completed': 'مكتمل',
    'SAR': 'ريال',
    'Value Date': 'تاريخ القيمة',
    'Payment value date used in TXT files.': 'تاريخ قيمة الدفع المستخدم في ملفات TXT.',
    'Kawthar Operation': 'عملية الكوثر',
    'Default Paying Bank Account': 'حساب البنك الافتراضي للدفع',
    'Fallback for employees who have no personal Salary Paying Bank Account set.':
        'بديل للموظفين الذين ليس لديهم حساب بنكي شخصي محدد للراتب.',
    "Employee's Total This Month": 'إجمالي الموظف هذا الشهر',
    'HR: No pending penalties on this employee':
        'الموارد البشرية: لا توجد غرامات معلّقة على هذا الموظف',

    # ------------- Models (display names) -------------------------------
    'KSW Commission & Allowance Sheet': 'كشف عمولات وبدلات KSW',
    'KSW Commission / Allowance Category': 'فئة عمولات / بدلات KSW',
    'KSW Commission Bank File Export Wizard': 'معالج تصدير ملف بنكي لعمولات KSW',
    'KSW Commission Batch': 'دفعة عمولات KSW',
    'KSW Commission Sheet Line': 'بند كشف عمولة KSW',
    'KSW Commission Sheet Template': 'قالب كشف عمولة KSW',
    'KSW Commission Template Line': 'بند قالب عمولة KSW',
    'KSW Commissions: monthly sheet creation': 'عمولات KSW: الإنشاء الشهري للكشوف',
    'KSW Deduction Installment Line': 'بند قسط خصم KSW',
    'KSW Deduction Type': 'نوع خصم KSW',
    'KSW Deductions': 'خصومات KSW',
    'KSW Driver Commission Line': 'بند عمولة سائق KSW',
    'KSW Driver Commission Sheet': 'كشف عمولة سائق KSW',
    'KSW Loan Refusal Wizard': 'معالج رفض قرض KSW',
    'KSW Loan Request (Self-Service)': 'طلب قرض KSW (خدمة ذاتية)',
    'KSW Work Site': 'موقع عمل KSW',
    'Work Site': 'موقع العمل',
    'Work Sites': 'مواقع العمل',
    'Optional short code used in driver-commission filenames.':
        'رمز قصير اختياري يُستخدم في أسماء ملفات عمولات السائقين.',

    # ------------- Wizard fields / inputs -------------------------------
    'Notes…': 'ملاحظات…',
    'Internal notes…': 'ملاحظات داخلية…',
    'Reason for this deduction...': 'سبب هذا الخصم...',
    'Description / usage notes…': 'وصف / ملاحظات الاستخدام…',
    'Optional notes about this template…': 'ملاحظات اختيارية عن هذا القالب…',
    'Optional notes about when/how to use this template.':
        'ملاحظات اختيارية عن وقت/كيفية استخدام هذا القالب.',
    'Optional extra notes — repayment preferences, urgency, etc.':
        'ملاحظات إضافية اختيارية — تفضيلات السداد، الاستعجال، إلخ.',
    'Optional supporting documents (ID, proof of expense, etc.).':
        'مستندات داعمة اختيارية (هوية، إثبات صرف، إلخ).',
    'Supporting Documents': 'المستندات الداعمة',
    'Additional notes, repayment preferences...': 'ملاحظات إضافية، تفضيلات السداد...',
    'Additional notes...': 'ملاحظات إضافية...',
    'Why do you need this loan? (required)': 'لماذا تحتاج هذا القرض؟ (مطلوب)',
    'Which approval step the loan was at when it was refused.':
        'مرحلة الاعتماد التي كان عندها القرض عند رفضه.',
    'Template name…': 'اسم القالب…',
    'Usage notes, policy...': 'ملاحظات الاستخدام، السياسة...',
    'Accounting must tick this before approving — confirms monthly budget impact and total outstanding are within the approved envelope.':
        'يجب على المحاسبة تأكيد هذا قبل الاعتماد — للتأكد من أن الأثر الشهري وإجمالي المتبقي ضمن الموازنة المعتمدة.',

    # ------------- Inline tiny snippets ---------------------------------
    'You are requesting': 'أنت تطلب',
    'on': 'في',
    'over': 'على مدى',
    'per month starting': 'شهرياً ابتداءً من',
    'sheet(s)': 'كشف/كشوف',
    'month(s) —\n                            approximately': 'شهر/شهور —\n                            تقريباً',
    '<span class="mx-1">/</span>': '<span class="mx-1">/</span>',
    '<span class="mx-2">on</span>': '<span class="mx-2">في</span>',
    '<span class="mx-2">—</span>\n                            <b>By:</b>':
        '<span class="mx-2">—</span>\n                            <b>بواسطة:</b>',
})

# ---------------------------------------------------------------------------
# Final batch — long help-strings, multi-line tooltips, FA-icon snippets
# ---------------------------------------------------------------------------
TR.update({
    # ------- Generic / shared -----------------------------------------
    'State': 'الحالة',
    'Status based on activities\nOverdue: Due date is already passed\nToday: Activity date is today\nPlanned: Future activities.':
        'الحالة بناءً على الأنشطة\nمتأخر: تاريخ الاستحقاق قد فات\nاليوم: تاريخ النشاط هو اليوم\nمخطط: أنشطة مستقبلية.',

    # ------- KSW_commissions help / tooltips --------------------------
    'Adjust the locked loans amount on confirmed sheets and finalise (state done). Implicitly grants Officer scope so the accountant can see every confirmed sheet.':
        'تعديل مبلغ القروض المُجمَّد على الكشوف المؤكَّدة وإنهاؤها (الحالة منجز). يمنح ضمناً صلاحية المسؤول حتى يتمكن المحاسب من رؤية كل الكشوف المؤكَّدة.',
    'Audit-only: amount this installment was created with (auto-generated or manually entered). The "Awaiting Commission" flag is now the authoritative signal that a slice of this month is being routed to the commission sheet — this field is kept purely for traceability.':
        'للتدقيق فقط: المبلغ الذي أُنشئ به هذا القسط (مولَّد تلقائياً أو مُدخل يدوياً). أصبحت إشارة "بانتظار العمولة" هي المرجع لتحويل جزء من هذا الشهر إلى كشف العمولة — يُحتفظ بهذا الحقل لأغراض التتبع فقط.',
    'Auto-resolved from the matching driver-commission line (per site, per period). Phase A: always 0.':
        'يُحدَّد تلقائياً من بند عمولة السائق المطابق (لكل موقع، لكل فترة). المرحلة A: دائماً 0.',
    "Current sum of KSW_deduction pending shortfalls for this employee/period. Frozen into 'Loans Deduction' when you confirm.":
        'إجمالي العجز المعلَّق لخصومات KSW لهذا الموظف/الفترة. يُجمَّد في حقل "خصم القروض" عند التأكيد.',
    'Default amount pre-filled on new sheets. The supervisor can change it on each sheet.':
        'المبلغ الافتراضي المُعبَّأ مسبقاً على الكشوف الجديدة. يمكن للمشرف تغييره على كل كشف.',
    "Drives UI hints. 'holiday_bonus' enables the holiday selector on the line and a unique-per-holiday constraint.":
        'يتحكم بإرشادات الواجهة. تفعيل "holiday_bonus" يُظهر منتقي العطلة على البند ويفرض قيد فريد لكل عطلة.',
    'Editable only by the Commission Accountant while the sheet is in state "confirmed". Frozen from ``loans_amount`` on supervisor-confirm.':
        'قابل للتعديل فقط من قِبَل محاسب العمولات أثناء حالة الكشف "مؤكَّد". يُجمَّد من ``loans_amount`` عند تأكيد المشرف.',
    'Effective trip count after any manual adjustment by the supervisor. Entered directly — not computed.':
        'عدد الرحلات الفعلي بعد أي تعديل يدوي من المشرف. يُدخل مباشرة — لا يُحسب تلقائياً.',
    "Enter the employee's National Identification Number issued by the government (e.g., Aadhaar, SIN, NIN). This is used for official records and statutory compliance.":
        'أدخل رقم الهوية الوطنية للموظف الصادر من الجهة الحكومية. يُستخدم في السجلات الرسمية والامتثال النظامي.',
    'Internal JSON used to unwind the KSW_deduction mutations applied at done time. Touched only by the model.':
        'JSON داخلي يُستخدم لاسترجاع تغييرات خصومات KSW المطبَّقة عند الإنجاز. يُعدَّل فقط من خلال النموذج.',
    'Lines + driver commission. Bank-transfer total uses ``total_payable`` instead (which subtracts loans).':
        'البنود + عمولة السائق. يستخدم إجمالي التحويل البنكي ``total_payable`` بدلاً من ذلك (الذي يخصم القروض).',
    'Manage the commission/allowance category catalog and the site/trip-tier configuration. Independent of the Management/Approval scopes.':
        'إدارة فئات العمولات/البدلات وإعداد المواقع وشرائح الرحلات. مستقل عن صلاحيات الإدارة/الاعتماد.',
    'Required multiplied-trips for an employee who worked the full 30 days. Pro-rated for partial-month attendance: required_trips = round(required_trips_full_month * worked_days / 30).':
        'الرحلات المضاعفة المطلوبة لموظف عمل 30 يوماً كاملة. تُحتسب نسبياً للحضور الجزئي: required_trips = round(required_trips_full_month * worked_days / 30).',
    'Required when the category is "Holiday Bonus". Also enforces unique (sheet, category, holiday) so the same holiday cannot be entered twice on one sheet.':
        'مطلوب عندما تكون الفئة "بدل العطلة". كما يفرض تفرّد (الكشف، الفئة، العطلة) بحيث لا يمكن إدخال نفس العطلة مرتين على الكشف نفسه.',
    'Set when a KSW Commissions sheet finalised this installment as paid. Lets the sheet reset path unwind the offset.':
        'يُحدَّد عندما يُنهي كشف عمولات KSW هذا القسط كمدفوع. يسمح لمسار إعادة الكشف باسترجاع الخصم.',
    'Site assignment used by the KSW driver-commission sub-form. Site change mid-month: the driver line is recorded on the month-end site only.':
        'إسناد الموقع المستخدم في نموذج عمولة السائق الفرعي. عند تغيير الموقع خلال الشهر: يُسجَّل بند السائق على موقع نهاية الشهر فقط.',
    'Sum of all entered line amounts (allowances, commissions, holiday bonuses, etc.).':
        'مجموع جميع مبالغ البنود المُدخلة (البدلات، العمولات، بدلات العطلات، إلخ).',
    'Sum of pending KSW deduction installments for this employee/period that the deduction accountant has flagged "Awaiting Commission" — i.e. slices of monthly installments routed away from payroll so the commission sheet can settle them. The supervisor sees this as read-only; the commission accountant can adjust it after the supervisor confirms.':
        'مجموع أقساط خصومات KSW المعلَّقة لهذا الموظف/الفترة والتي وضع عليها محاسب الخصومات إشارة "بانتظار العمولة" — أي أجزاء من الأقساط الشهرية مُحوَّلة بعيداً عن الراتب لتُسوَّى عبر كشف العمولة. يراها المشرف للقراءة فقط؛ يمكن لمحاسب العمولات تعديلها بعد تأكيد المشرف.',
    'The (existing) commission sheet that will settle this parked installment when finalised. Empty if no sheet exists yet for that employee/month.':
        'كشف العمولة (الموجود) الذي سيُسوّي هذا القسط المُؤجل عند إنهائه. يكون فارغاً إذا لم يُنشأ كشف بعد لذلك الموظف/الشهر.',
    'Tick on a PENDING installment line to mean: do not deduct this slice from payroll — recoup it from the employee\'s monthly commission sheet instead. The matching commission sheet automatically picks it up in its "Loans (auto)" total. Cleared automatically when the line is paid via a commission sheet.':
        'فعّل هذا الخيار على بند قسط معلَّق ليعني: لا تخصم هذا الجزء من الراتب — استرجعه عبر كشف العمولة الشهري للموظف. يلتقطه كشف العمولة المطابق تلقائياً ضمن إجمالي "القروض (تلقائي)". يُلغى تلقائياً عند دفع البند عبر كشف عمولة.',
    'Tier-1 threshold: round(site.required_trips_full_month × worked_days / 30). No commission earned until this is exceeded.':
        'حد المستوى الأول: round(site.required_trips_full_month × worked_days / 30). لا تُكتسب عمولة حتى يتم تجاوزه.',
    'True when state is "done". Drives readonly in the form view via a stored Boolean (Odoo 19 does not reliably evaluate non-stored computes in readonly expressions).':
        'صحيح عندما تكون الحالة "منجز". يُحرّك خاصية القراءة فقط في النموذج عبر بوليان مخزَّن (لا يُقيِّم Odoo 19 بشكل موثوق الحقول المحسوبة غير المخزَّنة في تعابير readonly).',
    'What the bank should actually transfer = total minus the loan deductible (locked amount when state is confirmed/done, otherwise the auto-pulled shortfall).':
        'ما يجب أن يحوّله البنك فعلياً = الإجمالي ناقص خصم القرض (المبلغ المُجمَّد عندما تكون الحالة مؤكَّد/منجز، وإلا فالعجز المسحوب تلقائياً).',
    '<i class="fa fa-info-circle" title="Info" role="img" aria-label="Info"/>\n                    <b class="ms-1">Recouping a slice via the Commission Sheet</b> —\n                    when an employee can\'t afford a full installment from\n                    salary alone, you can route part (or all) of it to\n                    their monthly commission sheet:':
        '<i class="fa fa-info-circle" title="معلومة" role="img" aria-label="معلومة"/>\n                    <b class="ms-1">استرجاع جزء عبر كشف العمولة</b> —\n                    عندما لا يستطيع الموظف تحمّل قسط كامل من الراتب\n                    وحده، يمكنك تحويل جزء (أو كله) إلى كشف عمولته\n                    الشهري:',
    'Add a new row for the <em>same</em> year/month with\n                            the remainder (e.g. 150) and tick\n                            <b>Awaiting Commission</b>. Leave it as\n                            <i>Pending</i>.':
        'أضف بنداً جديداً <em>لنفس</em> السنة/الشهر بالمبلغ\n                            المتبقي (مثلاً 150) وفعّل\n                            <b>بانتظار العمولة</b>. اتركه في حالة\n                            <i>معلَّق</i>.',
    "Reduce the original month's row to the amount\n                            payroll <em>can</em> afford (e.g. 200 → 50).":
        'قلِّل بند الشهر الأصلي إلى المبلغ الذي\n                            <em>يستطيع</em> الراتب تحمّله (مثلاً 200 → 50).',
    'Employees listed here will have these\n                                lines pre-filled when their monthly\n                                commission sheet is created.\n                                An employee can only be assigned to one\n                                template at a time.':
        'سيتم تعبئة هذه البنود مسبقاً للموظفين\n                                المدرجين هنا عند إنشاء كشف عمولتهم\n                                الشهري. يمكن إسناد الموظف إلى قالب واحد\n                                فقط في الوقت ذاته.',
    'The loan total stays balanced (50 + 150 = 200) so\n                    the schedule is unaffected; payroll skips the\n                    parked row, and the commission sheet flips it to\n                    <i>Paid</i> when finalised.':
        'يبقى إجمالي القرض متوازناً (50 + 150 = 200) فلا يتأثر\n                    الجدول؛ يتخطى الراتب البند المُؤجل، ويحوّله كشف\n                    العمولة إلى <i>مدفوع</i> عند الإنهاء.',
    'The matching commission sheet automatically\n                            picks the 150 up in its <i>Loans (auto)</i>\n                            field and settles it on Finalise.':
        'يلتقط كشف العمولة المطابق المبلغ 150 تلقائياً\n                            في حقل <i>القروض (تلقائي)</i> ويُسوّيه عند\n                            الإنهاء.',
    'Templates let you define the standard allowance /\n                commission lines once and assign employees to them.\n                Every new monthly sheet for an assigned employee will\n                be pre-filled with these lines — you only need to\n                adjust the amounts.':
        'تتيح لك القوالب تعريف بنود البدلات / العمولات\n                المعتادة مرة واحدة وإسناد الموظفين إليها. سيتم تعبئة\n                كل كشف شهري جديد لموظف مُسنَد بهذه البنود تلقائياً —\n                ما عليك سوى تعديل المبالغ.',

    # ------- KSW_deduction help / tooltips ----------------------------
    '"Payslip <ref>" for auto-paid lines, "Manual by <user> on <date>" for manual lines.':
        '"قسيمة الراتب <ref>" للبنود المدفوعة تلقائياً، و"يدوي بواسطة <user> في <date>" للبنود اليدوية.',
    '<i class="fa fa-ban fa-lg me-2 mt-1" title="Refuse" role="img" aria-label="Refuse"/>':
        '<i class="fa fa-ban fa-lg me-2 mt-1" title="رفض" role="img" aria-label="رفض"/>',
    '<i class="fa fa-info-circle fa-lg me-2 mt-1" title="Info" role="img" aria-label="Info"/>':
        '<i class="fa fa-info-circle fa-lg me-2 mt-1" title="معلومة" role="img" aria-label="معلومة"/>',
    'A clear, factual explanation of why this loan request is being refused. This will be visible to the employee on the loan form and recorded in the chatter history.':
        'شرح واضح وموضوعي لسبب رفض طلب القرض هذا. سيكون مرئياً للموظف على نموذج القرض ومسجَّلاً في سجل المحادثات.',
    'Accrued untaken annual leave balance for the employee, taken from ksw.annual.leave.remaining_balance.':
        'رصيد الإجازة السنوية المستحق وغير المُستهلك للموظف، مأخوذ من ksw.annual.leave.remaining_balance.',
    'Article 84: ½ month wage × first 5 years + 1 month wage × years above 5 (pro-rated for fractional years).':
        'المادة 84: نصف راتب شهر × السنوات الخمس الأولى + راتب شهر كامل × السنوات بعد الخامسة (مع تقسيم نسبي للسنوات الكسرية).',
    'Article 85: tiered fraction of the termination amount — <2 yrs: nothing, 2–5: 1/3, 5–10: 2/3, ≥10: full. Force majeure → full termination amount.':
        'المادة 85: نسبة متدرجة من مبلغ إنهاء الخدمة — أقل من سنتين: لا شيء، 2–5: الثلث، 5–10: الثلثان، ≥10: كامل. القوة القاهرة → كامل مبلغ إنهاء الخدمة.',
    "Automatically set to the current user's employee. A user can only request a loan for themselves.":
        'يُحدَّد تلقائياً إلى موظف المستخدم الحالي. لا يمكن للمستخدم طلب قرض إلا لنفسه.',
    'Base amount per installment (amount / installments). The last line absorbs the rounding residue.':
        'المبلغ الأساسي للقسط الواحد (المبلغ ÷ عدد الأقساط). يستوعب البند الأخير فروقات التقريب.',
    'Borrowed: employee receives money (loan, advance). Company-paid: company settles a cost on behalf of the employee (gov/internal penalty).':
        'مُقترَض: يستلم الموظف المال (قرض، سُلفة). مدفوع من الشركة: تسدد الشركة تكلفة نيابة عن الموظف (غرامة حكومية/داخلية).',
    'Brief justification for the loan. Helps the DM / HR / Accounting / GM approvers make an informed decision.':
        'مبرر مختصر للقرض. يساعد مُعتمدي المدير المباشر / الموارد البشرية / المحاسبة / المدير العام على اتخاذ قرار مستنير.',
    'Explain clearly why this loan request is being refused. The employee will see this reason.':
        'وضّح بشكل واضح سبب رفض طلب القرض. سيرى الموظف هذا السبب.',
    'Free-text note for the manual payment (reference number, collection channel, etc.).':
        'ملاحظة حرة للدفعة اليدوية (رقم المرجع، قناة التحصيل، إلخ).',
    'Full access to non-loan deductions including delete. Loan-specific edit/delete still requires the dedicated "Loan Modification" privilege — Manager does NOT auto-grant it, so an HR/Admin can be Deduction Manager without being able to touch loan amount/installments or delete loans.':
        'صلاحية كاملة على الخصومات غير القرضية بما في ذلك الحذف. يبقى تعديل/حذف القروض يتطلب صلاحية "تعديل القرض" المخصصة — لا يمنحها دور المدير تلقائياً، فيمكن أن يكون موظف الموارد البشرية / المسؤول مديرَ خصومات دون القدرة على تعديل مبلغ/أقساط القرض أو حذف القروض.',
    'Full modification rights — edit and delete loan records. NOT auto-granted to Deduction Managers; must be set explicitly so an HR/Admin can be a Deduction Manager without inheriting loan modification rights.':
        'صلاحيات تعديل كاملة — تعديل وحذف سجلات القروض. لا تُمنح تلقائياً لمديري الخصومات؛ يجب تفعيلها صراحةً، حتى يمكن أن يكون موظف الموارد البشرية / المسؤول مديرَ خصومات دون أن يرث صلاحيات تعديل القروض.',
    'HR must tick this before approving. If a penalty is pending, create it first via "New Penalty" button so the decision-support values reflect it.':
        'يجب على الموارد البشرية تأكيد هذا قبل الاعتماد. إذا كانت هناك غرامة معلَّقة، أنشئها أولاً عبر زر "غرامة جديدة" لتنعكس على بيانات دعم القرار.',
    'If checked, resignation entitlement equals the full termination amount (Art. 87 — force majeure waives the 2-year minimum and tier reductions).':
        'عند التفعيل، يساوي استحقاق الاستقالة كامل مبلغ إنهاء الخدمة (المادة 87 — القوة القاهرة تُلغي حد السنتين والتدرّج).',
    "May change the date (year/month) and amount of pending installments on a confirmed/active loan. Changing an installment's date to a later month automatically pushes all subsequent pending installments forward by the same month-delta.":
        'يجوز له تغيير التاريخ (السنة/الشهر) والمبلغ للأقساط المعلَّقة على قرض مؤكَّد/فعّال. تغيير تاريخ قسط إلى شهر لاحق يُقدِّم جميع الأقساط اللاحقة المعلَّقة بنفس الفارق الشهري.',
    'May delete deductions (subject to the "no paid installments" guard). Cannot edit amount or installments.':
        'يجوز له حذف الخصومات (مع شرط "عدم وجود أقساط مدفوعة"). لا يمكنه تعديل المبلغ أو الأقساط.',
    'May edit amount and installments on loan deductions (where the state/approval step otherwise permits it).':
        'يجوز له تعديل المبلغ والأقساط على خصومات القروض (حين تسمح بذلك الحالة / مرحلة الاعتماد).',
    'Monetary value of the vacation balance using FIFO historical wage slicing per hr.version.':
        'القيمة المالية لرصيد الإجازة باستخدام تقطيع الرواتب التاريخية بنظام الوارد أولاً يخرج أولاً (FIFO) لكل إصدار من hr.version.',
    'Reason provided by the approver when refusing the loan request. Visible to the employee so they know why it was rejected and can decide whether to modify and resubmit.':
        'السبب الذي يقدمه المُعتمِد عند رفض طلب القرض. مرئي للموظف ليعلم سبب الرفض ويقرر ما إذا كان سيعدله ويعيد إرساله.',
    'Suggested number of installments when creating a new deduction of this type. Can be overridden per record.':
        'عدد الأقساط المقترح عند إنشاء خصم جديد من هذا النوع. يمكن تجاوزه لكل سجل.',
    'Ticked for installment lines added by hand by the accountant (payment collected outside payroll). Auto-generated schedule lines stay False.':
        'يُفعَّل لبنود الأقساط التي يضيفها المحاسب يدوياً (دفعة محصَّلة خارج الراتب). تبقى البنود المولَّدة تلقائياً غير مفعَّلة.',
    "True if the current user can perform the DM approval step on this deduction — either they are the employee's direct manager, or they hold the Deduction Officer/Manager role.":
        'صحيح إذا كان بإمكان المستخدم الحالي تنفيذ خطوة اعتماد المدير المباشر على هذا الخصم — إما لأنه المدير المباشر للموظف، أو لأنه يحمل دور مسؤول/مدير الخصومات.',
    'True if the current user holds the "Delete only" or "Edit and Delete" level of the Loan Modification privilege.':
        'صحيح إذا كان المستخدم الحالي يحمل مستوى "حذف فقط" أو "تعديل وحذف" من صلاحية تعديل القرض.',
    'True if the current user holds the "Edit only" or "Edit and Delete" level of the Loan Modification privilege.':
        'صحيح إذا كان المستخدم الحالي يحمل مستوى "تعديل فقط" أو "تعديل وحذف" من صلاحية تعديل القرض.',
    'When enabled, this type triggers the full DM -> HR -> Accounting -> GM approval workflow. Otherwise the deduction is activated instantly on creation.':
        'عند التفعيل، يُشغّل هذا النوع سلسلة الاعتماد الكاملة: المدير المباشر ← الموارد البشرية ← المحاسبة ← المدير العام. وإلا، يُفعَّل الخصم فوراً عند الإنشاء.',
    'Years of service from earliest contract_date_start of any version to today (calendar days / 365.25).':
        'سنوات الخدمة من أقدم contract_date_start بين الإصدارات حتى اليوم (الأيام التقويمية / 365.25).',
    '<i class="fa fa-info-circle" title="Info" role="img" aria-label="Info"/>\n                                <b class="ms-1">Manual entries</b> —\n                                use the\n                                <i>Add a line</i>\n                                button to record a payment collected\n                                <b>outside payroll</b> (cash, direct\n                                bank transfer, etc.). The row is\n                                saved as <b>Paid (Manual)</b> and\n                                stamped with your name and today\'s\n                                date. Remember to balance the total:\n                                if the employee has already paid a\n                                scheduled month outside payroll,\n                                mark the corresponding pending row\n                                as <b>Skipped</b> (via state) or\n                                reduce its amount, so the sum still\n                                equals the total loan amount.':
        '<i class="fa fa-info-circle" title="معلومة" role="img" aria-label="معلومة"/>\n                                <b class="ms-1">الإدخالات اليدوية</b> —\n                                استخدم زر\n                                <i>إضافة بند</i>\n                                لتسجيل دفعة محصَّلة\n                                <b>خارج الراتب</b> (نقداً، تحويل\n                                بنكي مباشر، إلخ). يُحفظ البند\n                                كـ <b>مدفوع (يدوي)</b> ويُختم\n                                باسمك وتاريخ اليوم. تذكَّر\n                                موازنة الإجمالي: إذا كان الموظف\n                                قد سدَّد شهراً مجدولاً خارج الراتب،\n                                فعيِّن البند المعلَّق المقابل\n                                كـ <b>متخطى</b> (عبر الحالة) أو\n                                خفِّض مبلغه، لكي يبقى المجموع\n                                مساوياً لإجمالي مبلغ القرض.',
    'The reason you provide below\n                                <b>will be shown to the employee</b>\n                                and recorded permanently in the approval\n                                history. Please be clear and respectful.':
        'السبب الذي تكتبه أدناه\n                                <b>سيُعرض على الموظف</b>\n                                ويُسجَّل بشكل دائم في سجل الاعتمادات.\n                                يُرجى أن يكون واضحاً ومهذباً.',
    'Use <b>Request a Loan</b> in the sidebar to submit a new\n                loan. Once submitted, your request goes through the\n                approval chain (DM → HR → Accounting → GM) and you can\n                track its status here.':
        'استخدم <b>طلب قرض</b> في الشريط الجانبي لتقديم قرض\n                جديد. بعد الإرسال، يمر طلبك عبر سلسلة الاعتماد\n                (المدير المباشر ← الموارد البشرية ← المحاسبة ← المدير\n                العام) ويمكنك متابعة حالته هنا.',
    'Your request will be reviewed in four steps:\n                                <span class="badge text-bg-secondary mx-1">1. DM</span>\n                                <i class="fa fa-angle-right mx-1" title="then" role="img" aria-hidden="true"/>\n                                <span class="badge text-bg-secondary mx-1">2. HR</span>\n                                <i class="fa fa-angle-right mx-1" title="then" role="img" aria-hidden="true"/>\n                                <span class="badge text-bg-secondary mx-1">3. Accounting</span>\n                                <i class="fa fa-angle-right mx-1" title="then" role="img" aria-hidden="true"/>\n                                <span class="badge text-bg-secondary mx-1">4. GM</span>.\n                                Track progress under <b>My Loans</b>.':
        'ستُراجَع طلبك في أربع خطوات:\n                                <span class="badge text-bg-secondary mx-1">1. المدير المباشر</span>\n                                <i class="fa fa-angle-right mx-1" title="ثم" role="img" aria-hidden="true"/>\n                                <span class="badge text-bg-secondary mx-1">2. الموارد البشرية</span>\n                                <i class="fa fa-angle-right mx-1" title="ثم" role="img" aria-hidden="true"/>\n                                <span class="badge text-bg-secondary mx-1">3. المحاسبة</span>\n                                <i class="fa fa-angle-right mx-1" title="ثم" role="img" aria-hidden="true"/>\n                                <span class="badge text-bg-secondary mx-1">4. المدير العام</span>.\n                                تابع التقدم من <b>قروضي</b>.',
})


def translate(text):
    """Return the Arabic translation if present, else empty string."""
    if not text:
        return ''
    return TR.get(text, '')


def translate_pot(pot_path, ar_path):
    pot = polib.pofile(pot_path)
    pot.metadata.update({
        'Language': 'ar_001',
        'Plural-Forms': 'nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : '
                        'n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);',
        'X-Generator': 'KSW translator',
    })
    translated = 0
    for entry in pot:
        if entry.msgid_plural:
            # Plural: translate singular and plural separately if both known.
            singular = TR.get(entry.msgid, '')
            plural = TR.get(entry.msgid_plural, '')
            if singular or plural:
                entry.msgstr_plural = {
                    0: singular or plural or '',
                    1: plural or singular or '',
                }
                translated += 1
        else:
            ar = translate(entry.msgid)
            if ar:
                entry.msgstr = ar
                translated += 1
    pot.save(ar_path)
    return translated, len(pot)


def main():
    targets = [
        ('/home/odoo/odoo_learning_proj/odoo/custom_addons/KSW/KSW_commissions/i18n/KSW_commissions.pot',
         '/home/odoo/odoo_learning_proj/odoo/custom_addons/KSW/KSW_commissions/i18n/ar_001.po'),
        ('/home/odoo/odoo_learning_proj/odoo/custom_addons/KSW/KSW_deduction/i18n/KSW_deduction.pot',
         '/home/odoo/odoo_learning_proj/odoo/custom_addons/KSW/KSW_deduction/i18n/ar_001.po'),
    ]
    for pot, ar in targets:
        if not os.path.exists(pot):
            print('skip (missing): %s' % pot)
            continue
        done, total = translate_pot(pot, ar)
        print('%s -> %s : %d / %d translated' % (
            os.path.basename(pot), os.path.basename(ar), done, total))


if __name__ == '__main__':
    main()






