# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = الصفحة السابقة
pdfjs-previous-button-label = السابقة
pdfjs-next-button =
    .title = الصفحة التالية
pdfjs-next-button-label = التالية
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = صفحة
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = من { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } من { $pagesCount })
pdfjs-zoom-out-button =
    .title = بعّد
pdfjs-zoom-out-button-label = بعّد
pdfjs-zoom-in-button =
    .title = قرّب
pdfjs-zoom-in-button-label = قرّب
pdfjs-zoom-select =
    .title = التقريب
pdfjs-presentation-mode-button =
    .title = انتقل لوضع العرض التقديمي
pdfjs-presentation-mode-button-label = وضع العرض التقديمي
pdfjs-open-file-button =
    .title = افتح ملفًا
pdfjs-open-file-button-label = افتح
pdfjs-print-button =
    .title = اطبع
pdfjs-print-button-label = اطبع
pdfjs-save-button =
    .title = احفظ
pdfjs-save-button-label = احفظ
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = نزّل
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = نزّل
pdfjs-bookmark-button =
    .title = الصفحة الحالية (عرض URL من الصفحة الحالية)
pdfjs-bookmark-button-label = الصفحة الحالية

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = الأدوات
pdfjs-tools-button-label = الأدوات
pdfjs-first-page-button =
    .title = انتقل إلى الصفحة الأولى
pdfjs-first-page-button-label = انتقل إلى الصفحة الأولى
pdfjs-last-page-button =
    .title = انتقل إلى الصفحة الأخيرة
pdfjs-last-page-button-label = انتقل إلى الصفحة الأخيرة
pdfjs-page-rotate-cw-button =
    .title = أدر باتجاه عقارب الساعة
pdfjs-page-rotate-cw-button-label = أدر باتجاه عقارب الساعة
pdfjs-page-rotate-ccw-button =
    .title = أدر بعكس اتجاه عقارب الساعة
pdfjs-page-rotate-ccw-button-label = أدر بعكس اتجاه عقارب الساعة
pdfjs-cursor-text-select-tool-button =
    .title = فعّل أداة اختيار النص
pdfjs-cursor-text-select-tool-button-label = أداة اختيار النص
pdfjs-cursor-hand-tool-button =
    .title = فعّل أداة اليد
pdfjs-cursor-hand-tool-button-label = أداة اليد
pdfjs-scroll-page-button =
    .title = استخدم تمرير الصفحة
pdfjs-scroll-page-button-label = تمرير الصفحة
pdfjs-scroll-vertical-button =
    .title = استخدم التمرير الرأسي
pdfjs-scroll-vertical-button-label = التمرير الرأسي
pdfjs-scroll-horizontal-button =
    .title = استخدم التمرير الأفقي
pdfjs-scroll-horizontal-button-label = التمرير الأفقي
pdfjs-scroll-wrapped-button =
    .title = استخدم التمرير الملتف
pdfjs-scroll-wrapped-button-label = التمرير الملتف
pdfjs-spread-none-button =
    .title = لا تدمج هوامش الصفحات مع بعضها البعض
pdfjs-spread-none-button-label = بلا هوامش
pdfjs-spread-odd-button =
    .title = ادمج هوامش الصفحات الفردية
pdfjs-spread-odd-button-label = هوامش الصفحات الفردية
pdfjs-spread-even-button =
    .title = ادمج هوامش الصفحات الزوجية
pdfjs-spread-even-button-label = هوامش الصفحات الزوجية

## Document properties dialog

pdfjs-document-properties-button =
    .title = خصائص المستند…
pdfjs-document-properties-button-label = خصائص المستند…
pdfjs-document-properties-file-name = اسم الملف:
pdfjs-document-properties-file-size = حجم الملف:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } ك.بايت ({ $b } بايتات)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } م.بايت ({ $b } بايتات)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } ك.بايت ({ $size_b } بايت)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } م.بايت ({ $size_b } بايت)
pdfjs-document-properties-title = العنوان:
pdfjs-document-properties-author = المؤلف:
pdfjs-document-properties-subject = الموضوع:
pdfjs-document-properties-keywords = الكلمات الأساسية:
pdfjs-document-properties-creation-date = تاريخ الإنشاء:
pdfjs-document-properties-modification-date = تاريخ التعديل:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }، { $time }
pdfjs-document-properties-creator = المنشئ:
pdfjs-document-properties-producer = منتج PDF:
pdfjs-document-properties-version = إصدارة PDF:
pdfjs-document-properties-page-count = عدد الصفحات:
pdfjs-document-properties-page-size = مقاس الورقة:
pdfjs-document-properties-page-size-unit-inches = بوصة
pdfjs-document-properties-page-size-unit-millimeters = ملم
pdfjs-document-properties-page-size-orientation-portrait = طوليّ
pdfjs-document-properties-page-size-orientation-landscape = عرضيّ
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = خطاب
pdfjs-document-properties-page-size-name-legal = قانونيّ

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = ‏{ $width } × ‏{ $height } ‏{ $unit } (‏{ $orientation })
pdfjs-document-properties-page-size-dimension-name-string = ‏{ $width } × ‏{ $height } ‏{ $unit } (‏{ $name }، { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = العرض السريع عبر الوِب:
pdfjs-document-properties-linearized-yes = نعم
pdfjs-document-properties-linearized-no = لا
pdfjs-document-properties-close-button = أغلق

## Print

pdfjs-print-progress-message = يُحضّر المستند للطباعة…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }٪
pdfjs-print-progress-close-button = ألغِ
pdfjs-printing-not-supported = تحذير: لا يدعم هذا المتصفح الطباعة بشكل كامل.
pdfjs-printing-not-ready = تحذير: ملف PDF لم يُحمّل كاملًا للطباعة.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = بدّل ظهور الشريط الجانبي
pdfjs-toggle-sidebar-notification-button =
    .title = بدّل ظهور الشريط الجانبي (يحتوي المستند على مخطط أو مرفقات أو طبقات)
pdfjs-toggle-sidebar-button-label = بدّل ظهور الشريط الجانبي
pdfjs-document-outline-button =
    .title = اعرض فهرس المستند (نقر مزدوج لتمديد أو تقليص كل العناصر)
pdfjs-document-outline-button-label = مخطط المستند
pdfjs-attachments-button =
    .title = اعرض المرفقات
pdfjs-attachments-button-label = المُرفقات
pdfjs-layers-button =
    .title = اعرض الطبقات (انقر مرتين لتصفير كل الطبقات إلى الحالة المبدئية)
pdfjs-layers-button-label = ‏‏الطبقات
pdfjs-thumbs-button =
    .title = اعرض مُصغرات
pdfjs-thumbs-button-label = مُصغّرات
pdfjs-current-outline-item-button =
    .title = ابحث عن عنصر المخطّط التفصيلي الحالي
pdfjs-current-outline-item-button-label = عنصر المخطّط التفصيلي الحالي
pdfjs-findbar-button =
    .title = ابحث في المستند
pdfjs-findbar-button-label = ابحث
pdfjs-additional-layers = الطبقات الإضافية

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = صفحة { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = مصغّرة صفحة { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = ابحث
    .placeholder = ابحث في المستند…
pdfjs-find-previous-button =
    .title = ابحث عن التّواجد السّابق للعبارة
pdfjs-find-previous-button-label = السابق
pdfjs-find-next-button =
    .title = ابحث عن التّواجد التّالي للعبارة
pdfjs-find-next-button-label = التالي
pdfjs-find-highlight-checkbox = أبرِز الكل
pdfjs-find-match-case-checkbox-label = طابق حالة الأحرف
pdfjs-find-match-diacritics-checkbox-label = طابِق التشكيل
pdfjs-find-entire-word-checkbox-label = كلمات كاملة
pdfjs-find-reached-top = تابعت من الأسفل بعدما وصلت إلى بداية المستند
pdfjs-find-reached-bottom = تابعت من الأعلى بعدما وصلت إلى نهاية المستند
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [zero] لا  مطابقة
        [one] { $current } من أصل { $total } مطابقة
        [two] { $current } من أصل { $total } مطابقة
        [few] { $current } من أصل { $total } مطابقة
        [many] { $current } من أصل { $total } مطابقة
       *[other] { $current } من أصل { $total } مطابقة
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [zero] { $limit } مطابقة
        [one] أكثر من { $limit } مطابقة
        [two] أكثر من { $limit } مطابقة
        [few] أكثر من { $limit } مطابقة
        [many] أكثر من { $limit } مطابقة
       *[other] أكثر من { $limit } مطابقات
    }
pdfjs-find-not-found = لا وجود للعبارة

## Predefined zoom values

pdfjs-page-scale-width = عرض الصفحة
pdfjs-page-scale-fit = ملائمة الصفحة
pdfjs-page-scale-auto = تقريب تلقائي
pdfjs-page-scale-actual = الحجم الفعلي
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }٪

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = صفحة { $page }

## Loading indicator messages

pdfjs-loading-error = حدث عطل أثناء تحميل ملف PDF.
pdfjs-invalid-file-error = ملف PDF تالف أو غير صحيح.
pdfjs-missing-file-error = ملف PDF غير موجود.
pdfjs-unexpected-response-error = استجابة خادوم غير متوقعة.
pdfjs-rendering-error = حدث خطأ أثناء عرض الصفحة.

## Annotations

# Variables:
#   $date (Date) - the modification date of the annotation
#   $time (Time) - the modification time of the annotation
pdfjs-annotation-date-string = { $date }، { $time }
# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [تعليق { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = أدخل لكلمة السر لفتح هذا الملف.
pdfjs-password-invalid = كلمة سر خطأ. من فضلك أعد المحاولة.
pdfjs-password-ok-button = حسنا
pdfjs-password-cancel-button = ألغِ
pdfjs-web-fonts-disabled = خطوط الوب مُعطّلة: تعذّر استخدام خطوط PDF المُضمّنة.

## Editing

pdfjs-editor-free-text-button =
    .title = نص
pdfjs-editor-free-text-button-label = نص
pdfjs-editor-ink-button =
    .title = ارسم
pdfjs-editor-ink-button-label = ارسم
pdfjs-editor-stamp-button =
    .title = أضِف أو حرّر الصور
pdfjs-editor-stamp-button-label = أضِف أو حرّر الصور
pdfjs-editor-highlight-button =
    .title = أبرِز
pdfjs-editor-highlight-button-label = أبرِز
pdfjs-highlight-floating-button1 =
    .title = أبرِز
    .aria-label = أبرِز
pdfjs-highlight-floating-button-label = أبرِز
pdfjs-editor-signature-button =
    .title = أضِف توقيع
pdfjs-editor-signature-button-label = أضِف توقيع

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = محرِّر الإبراز
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = محرِّر الرسم
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = محرِّر التوقيع: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = محرِّر الصور

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = أزِل الرسم
pdfjs-editor-remove-freetext-button =
    .title = أزِل النص
pdfjs-editor-remove-stamp-button =
    .title = أزِل الصورة
pdfjs-editor-remove-highlight-button =
    .title = أزِل الإبراز
pdfjs-editor-remove-signature-button =
    .title = أزِل التوقيع

##

# Editor Parameters
pdfjs-editor-free-text-color-input = اللون
pdfjs-editor-free-text-size-input = الحجم
pdfjs-editor-ink-color-input = اللون
pdfjs-editor-ink-thickness-input = السماكة
pdfjs-editor-ink-opacity-input = العتامة
pdfjs-editor-stamp-add-image-button =
    .title = أضِف صورة
pdfjs-editor-stamp-add-image-button-label = أضِف صورة
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = السماكة
pdfjs-editor-free-highlight-thickness-title =
    .title = غيّر السُمك عند إبراز عناصر أُخرى غير النص
pdfjs-editor-add-signature-container =
    .aria-label = عناصر التحكم في التوقيع والتوقيعات المحفوظة
pdfjs-editor-signature-add-signature-button =
    .title = أضِف توقيع جديد
pdfjs-editor-signature-add-signature-button-label = أضِف توقيع جديد
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = التوقيع المحفوظ: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = محرِّر النص
    .default-content = ابدأ في كتابة…
pdfjs-free-text =
    .aria-label = محرِّر النص
pdfjs-free-text-default-content = ابدأ الكتابة…
pdfjs-ink =
    .aria-label = محرِّر الرسم
pdfjs-ink-canvas =
    .aria-label = صورة أنشأها المستخدم

## Alt-text dialog

pdfjs-editor-alt-text-button-label = نص بديل
pdfjs-editor-alt-text-edit-button =
    .aria-label = حرّر النص البديل
pdfjs-editor-alt-text-edit-button-label = تحرير النص البديل
pdfjs-editor-alt-text-dialog-label = اختر خيار
pdfjs-editor-alt-text-dialog-description = يساعد النص البديل عندما لا يتمكن الأشخاص من رؤية الصورة أو عندما لا يتم تحميلها.
pdfjs-editor-alt-text-add-description-label = أضِف وصف
pdfjs-editor-alt-text-add-description-description = استهدف جملتين تصفان الموضوع أو الإعداد أو الإجراءات.
pdfjs-editor-alt-text-mark-decorative-label = علّمها على أنها زخرفية
pdfjs-editor-alt-text-mark-decorative-description = يُستخدم هذا في الصور المزخرفة، مثل الحدود أو العلامات المائية.
pdfjs-editor-alt-text-cancel-button = ألغِ
pdfjs-editor-alt-text-save-button = احفظ
pdfjs-editor-alt-text-decorative-tooltip = عُلّمت على أنها زخرفية
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = على سبيل المثال، "يجلس شاب على الطاولة لتناول وجبة"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = نص بديل

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = الزاوية اليُسرى العُليا — غيّر الحجم
pdfjs-editor-resizer-label-top-middle = أعلى الوسط - غيّر الحجم
pdfjs-editor-resizer-label-top-right = الزاوية اليُمنى العُليا - غيّر الحجم
pdfjs-editor-resizer-label-middle-right = اليمين الأوسط - غيّر الحجم
pdfjs-editor-resizer-label-bottom-right = الزاوية اليُمنى السُفلى - غيّر الحجم
pdfjs-editor-resizer-label-bottom-middle = أسفل الوسط - غيّر الحجم
pdfjs-editor-resizer-label-bottom-left = الزاوية اليُسرى السُفلية - غيّر الحجم
pdfjs-editor-resizer-label-middle-left = مُنتصف اليسار - غيّر الحجم
pdfjs-editor-resizer-top-left =
    .aria-label = الزاوية اليُسرى العُليا — غيّر الحجم
pdfjs-editor-resizer-top-middle =
    .aria-label = أعلى الوسط - غيّر الحجم
pdfjs-editor-resizer-top-right =
    .aria-label = الزاوية اليُمنى العُليا - غيّر الحجم
pdfjs-editor-resizer-middle-right =
    .aria-label = اليمين الأوسط - غيّر الحجم
pdfjs-editor-resizer-bottom-right =
    .aria-label = الزاوية اليُمنى السُفلى - غيّر الحجم
pdfjs-editor-resizer-bottom-middle =
    .aria-label = أسفل الوسط - غيّر الحجم
pdfjs-editor-resizer-bottom-left =
    .aria-label = الزاوية اليُسرى السُفلية - غيّر الحجم
pdfjs-editor-resizer-middle-left =
    .aria-label = مُنتصف اليسار - غيّر الحجم

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = أبرِز اللون
pdfjs-editor-colorpicker-button =
    .title = غيّر اللون
pdfjs-editor-colorpicker-dropdown =
    .aria-label = اختيارات الألوان
pdfjs-editor-colorpicker-yellow =
    .title = أصفر
pdfjs-editor-colorpicker-green =
    .title = أخضر
pdfjs-editor-colorpicker-blue =
    .title = أزرق
pdfjs-editor-colorpicker-pink =
    .title = وردي
pdfjs-editor-colorpicker-red =
    .title = أحمر

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = أظهِر الكل
pdfjs-editor-highlight-show-all-button =
    .title = أظهِر الكل

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = حرّر النص البديل (وصف الصورة)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = أضِف النص البديل (وصف الصورة)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = اكتب وصفك هنا…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = وصف مختصر للأشخاص الذين لا يستطيعون رؤية الصورة أو عندما لا يتم تحميل الصورة.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = أُنشئ هذا النص البديل تلقائيًا وقد يكون غير دقيق.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = اطّلع على المزيد
pdfjs-editor-new-alt-text-create-automatically-button-label = أنشئ نص بديل تلقائيًا
pdfjs-editor-new-alt-text-not-now-button = ليس الآن
pdfjs-editor-new-alt-text-error-title = لم يتمكن من إنشاء نص بديل تلقائيًا
pdfjs-editor-new-alt-text-error-description = يُرجى كتابة نص بديلك أو المحاولة مرة أخرى لاحقًا.
pdfjs-editor-new-alt-text-error-close-button = أغلق
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = يُنزّل نموذج الذكاء الاصطناعي للنص البديل ({ $downloadedSize } من { $totalSize } م.بايت)
    .aria-valuetext = يُنزّل نموذج الذكاء الاصطناعي للنص البديل ({ $downloadedSize } من { $totalSize } م.بايت)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = أُضِيف نص بديل
pdfjs-editor-new-alt-text-added-button-label = أُضِيف نص بديل
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = نص بديل مفقود
pdfjs-editor-new-alt-text-missing-button-label = نص بديل مفقود
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = راجع النص البديل
pdfjs-editor-new-alt-text-to-review-button-label = راجع النص البديل
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = أُنشئ تلقائيًا: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = إعدادات النص البديل للصورة
pdfjs-image-alt-text-settings-button-label = إعدادات النص البديل للصورة
pdfjs-editor-alt-text-settings-dialog-label = إعدادات النص البديل للصورة
pdfjs-editor-alt-text-settings-automatic-title = نص بديل تلقائي
pdfjs-editor-alt-text-settings-create-model-button-label = أنشئ نص بديل تلقائيًا
pdfjs-editor-alt-text-settings-create-model-description = يقترح أوصافًا لمساعدة الأشخاص الذين لا يستطيعون رؤية الصورة أو عندما لا يتم تحميل الصورة.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = نموذج الذكاء الاصطناعي للنص البديل ({ $totalSize } م.بايت)
pdfjs-editor-alt-text-settings-ai-model-description = يتم تشغيله محليًا على جهازك حتى تظل بياناتك خاصة. مطلوب للنص البديل التلقائي.
pdfjs-editor-alt-text-settings-delete-model-button = احذف
pdfjs-editor-alt-text-settings-download-model-button = نزّل
pdfjs-editor-alt-text-settings-downloading-model-button = يُنزل…
pdfjs-editor-alt-text-settings-editor-title = مُحرِّر النص البديل
pdfjs-editor-alt-text-settings-show-dialog-button-label = أظهِر مُحرِّر النص البديل على الفور عند إضافة صورة
pdfjs-editor-alt-text-settings-show-dialog-description = يساعدك على التأكد من أن جميع صورك تحتوي على نص بديل.
pdfjs-editor-alt-text-settings-close-button = أغلق

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = أُزِيل البرز
pdfjs-editor-undo-bar-message-freetext = أُزيل النص
pdfjs-editor-undo-bar-message-ink = أُزِيلت الرسمة
pdfjs-editor-undo-bar-message-stamp = أُزيلت الصورة
pdfjs-editor-undo-bar-message-signature = أُزيل التوقيع
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [zero] أُزيل لا تعليق
        [one] أُزيل تعليق
        [two] أُزيل تعليقين
        [few] أُزيلت { $count } تعليقات
        [many] أُزيل { $count } تعليق
       *[other] أُزيل { $count } تعليق
    }
pdfjs-editor-undo-bar-undo-button =
    .title = تراجع
pdfjs-editor-undo-bar-undo-button-label = تراجع
pdfjs-editor-undo-bar-close-button =
    .title = أغلق
pdfjs-editor-undo-bar-close-button-label = أغلق

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = يتيح هذا النموذج للمستخدم إنشاء توقيع لإضافته إلى مستند PDF. ويمكن للمستخدم تحرير الاسم (الذي يعمل أيضًا كنص بديل)، وحفظ التوقيع بشكل اختياري للاستخدام المتكرر.
pdfjs-editor-add-signature-dialog-title = أضِف توقيعا

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = اكتب
    .title = اكتب
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = ارسم
    .title = ارسم
pdfjs-editor-add-signature-image-button = صورة
    .title = صورة

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = اكتب توقيعك
    .placeholder = اكتب توقيعك
pdfjs-editor-add-signature-draw-placeholder = ارسم توقيعك
pdfjs-editor-add-signature-draw-thickness-range-label = السماكة
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = سمك الرسم: { $thickness }
pdfjs-editor-add-signature-image-placeholder = اسحب الملف هنا لرفعه
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] أو اختر ملفات الصور
       *[other] أو تصفح ملفات الصور
    }

## Controls

pdfjs-editor-add-signature-description-label = الوصف (نص بديل)
pdfjs-editor-add-signature-description-input =
    .title = الوصف (نص بديل)
pdfjs-editor-add-signature-description-default-when-drawing = توقيع
pdfjs-editor-add-signature-clear-button-label = امحُ التوقيع
pdfjs-editor-add-signature-clear-button =
    .title = امحُ التوقيع
pdfjs-editor-add-signature-save-checkbox = احفظ التوقيع
pdfjs-editor-add-signature-save-warning-message = لقد وصلت إلى الحد الأقصى وهو 5 توقيعات محفوظة. أزِل توقيع واحد لحفظ المزيد.
pdfjs-editor-add-signature-image-upload-error-title = تعذر رفع الصورة.
pdfjs-editor-add-signature-image-upload-error-description = تحقق من اتصال الشبكة لديك أو جرّب صورة أخرى.
pdfjs-editor-add-signature-error-close-button = أغلق

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = ألغِ
pdfjs-editor-add-signature-add-button = أضِف
pdfjs-editor-edit-signature-update-button = حدّث

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = أزِل التوقيع المحفوظ
pdfjs-editor-delete-signature-button-label1 = أزِل التوقيع المحفوظ

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = عدّل الوصف

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = عدّل الوصف
