# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = صفحهٔ قبلی
pdfjs-previous-button-label = قبلی
pdfjs-next-button =
    .title = صفحهٔ بعدی
pdfjs-next-button-label = بعدی
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = صفحه
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = از { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } از { $pagesCount })
pdfjs-zoom-out-button =
    .title = کوچک‌نمایی
pdfjs-zoom-out-button-label = کوچک‌نمایی
pdfjs-zoom-in-button =
    .title = بزرگ‌نمایی
pdfjs-zoom-in-button-label = بزرگ‌نمایی
pdfjs-zoom-select =
    .title = بزرگ‌نمایی
pdfjs-presentation-mode-button =
    .title = تغییر به حالت ارائه
pdfjs-presentation-mode-button-label = حالت ارائه
pdfjs-open-file-button =
    .title = باز کردن فایل
pdfjs-open-file-button-label = باز کردن
pdfjs-print-button =
    .title = چاپ
pdfjs-print-button-label = چاپ
pdfjs-save-button =
    .title = ذخیره
pdfjs-save-button-label = ذخیره
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = دانلود
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = دانلود
pdfjs-bookmark-button =
    .title = صفحهٔ فعلی (مشاهدهٔ نشانی وب صفحهٔ فعلی)
pdfjs-bookmark-button-label = صفحهٔ فعلی

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = ابزارها
pdfjs-tools-button-label = ابزارها
pdfjs-first-page-button =
    .title = رفتن به صفحهٔ اول
pdfjs-first-page-button-label = رفتن به صفحهٔ اول
pdfjs-last-page-button =
    .title = رفتن به صفحهٔ آخر
pdfjs-last-page-button-label = رفتن به صفحهٔ آخر
pdfjs-page-rotate-cw-button =
    .title = چرخش ساعت‌گرد
pdfjs-page-rotate-cw-button-label = چرخش ساعت‌گرد
pdfjs-page-rotate-ccw-button =
    .title = چرخش پادساعت‌گرد
pdfjs-page-rotate-ccw-button-label = چرخش پادساعت‌گرد
pdfjs-cursor-text-select-tool-button =
    .title = فعال‌سازی ابزار انتخاب متن
pdfjs-cursor-text-select-tool-button-label = ابزار انتخاب متن
pdfjs-cursor-hand-tool-button =
    .title = فعال‌سازی ابزار دست
pdfjs-cursor-hand-tool-button-label = ابزار دست
pdfjs-scroll-page-button =
    .title = استفاده از پیمایش صفحه‌ای
pdfjs-scroll-page-button-label = پیمایش صفحه‌ای
pdfjs-scroll-vertical-button =
    .title = استفاده از پیمایش عمودی
pdfjs-scroll-vertical-button-label = پیمایش عمودی
pdfjs-scroll-horizontal-button =
    .title = استفاده از پیمایش افقی
pdfjs-scroll-horizontal-button-label = پیمایش افقی
pdfjs-scroll-wrapped-button =
    .title = استفاده از پیمایش پیوسته (Wrapped)
pdfjs-scroll-wrapped-button-label = پیمایش پیوسته
pdfjs-spread-none-button =
    .title = بدون صفحات روبه‌رو
pdfjs-spread-none-button-label = تک‌صفحه‌ای
pdfjs-spread-odd-button =
    .title = نمایش دوصفحه‌ای با شروع از صفحات فرد
pdfjs-spread-odd-button-label = صفحات فرد روبه‌رو
pdfjs-spread-even-button =
    .title = نمایش دوصفحه‌ای با شروع از صفحات زوج
pdfjs-spread-even-button-label = صفحات زوج روبه‌رو

## Document properties dialog

pdfjs-document-properties-button =
    .title = ویژگی‌های سند…
pdfjs-document-properties-button-label = ویژگی‌های سند…
pdfjs-document-properties-file-name = نام فایل:
pdfjs-document-properties-file-size = حجم فایل:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } کیلوبایت ({ $b } بایت)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } مگابایت ({ $b } بایت)
pdfjs-document-properties-title = عنوان:
pdfjs-document-properties-author = نویسنده:
pdfjs-document-properties-subject = موضوع:
pdfjs-document-properties-keywords = کلیدواژه‌ها:
pdfjs-document-properties-creation-date = تاریخ ایجاد:
pdfjs-document-properties-modification-date = تاریخ ویرایش:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = سازنده:
pdfjs-document-properties-producer = تولیدکنندهٔ PDF:
pdfjs-document-properties-version = نسخهٔ PDF:
pdfjs-document-properties-page-count = تعداد صفحه‌ها:
pdfjs-document-properties-page-size = اندازهٔ صفحه:
pdfjs-document-properties-page-size-unit-inches = اینچ
pdfjs-document-properties-page-size-unit-millimeters = میلی‌متر
pdfjs-document-properties-page-size-orientation-portrait = عمودی
pdfjs-document-properties-page-size-orientation-landscape = افقی
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Letter
pdfjs-document-properties-page-size-name-legal = Legal

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit } ({ $orientation })
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name }، { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = نمای وب سریع (Fast Web View):
pdfjs-document-properties-linearized-yes = بله
pdfjs-document-properties-linearized-no = خیر
pdfjs-document-properties-close-button = بستن
pdfjs-digital-signature-properties-view-certificate = مشاهدهٔ گواهی
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = دلیل: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = برچسب زمانی: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] زیرامضا ({ $count })
       *[other] زیرامضاها ({ $count })
    }

## Print

pdfjs-print-progress-message = در حال آماده‌سازی سند برای چاپ…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }٪
pdfjs-print-progress-close-button = انصراف
pdfjs-printing-not-supported = هشدار: قابلیت چاپ به‌طور کامل در این مرورگر پشتیبانی نمی‌شود.
pdfjs-printing-not-ready = هشدار: فایل PDF برای چاپ به‌طور کامل بارگیری نشده است.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = پیدا کردن مورد فعلی در طرح کلی
pdfjs-current-outline-item-button-label = مورد فعلی در طرح کلی
pdfjs-findbar-button =
    .title = پیدا کردن در سند
pdfjs-findbar-button-label = پیدا کردن
pdfjs-additional-layers = لایه‌های اضافی

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = تصویر بندانگشتی صفحهٔ { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = انتخاب صفحهٔ { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = صفحهٔ { $page } از { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = پیدا کردن در سند…
    .title = پیدا کردن
pdfjs-find-previous-button =
    .title = پیدا کردن مورد قبلی عبارت
pdfjs-find-previous-button-label = قبلی
pdfjs-find-next-button =
    .title = پیدا کردن مورد بعدی عبارت
pdfjs-find-next-button-label = بعدی
pdfjs-find-highlight-checkbox = برجسته‌سازی همه
pdfjs-find-match-case-checkbox-label = مطابقت بزرگی و کوچکی حروف
pdfjs-find-match-diacritics-checkbox-label = مطابقت اعراب و نشانه‌ها
pdfjs-find-entire-word-checkbox-label = کل کلمات
pdfjs-find-reached-top = به بالای سند رسیدیم، ادامه از پایین
pdfjs-find-reached-bottom = به پایان سند رسیدیم، ادامه از بالا
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } از { $total } مورد منطبق
       *[other] { $current } از { $total } مورد منطبق
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] بیش از { $limit } مورد منطبق
       *[other] بیش از { $limit } مورد منطبق
    }
pdfjs-find-not-found = عبارت پیدا نشد

## Predefined zoom values

pdfjs-page-scale-width = عرض صفحه
pdfjs-page-scale-fit = متناسب با صفحه
pdfjs-page-scale-auto = بزرگ‌نمایی خودکار
pdfjs-page-scale-actual = اندازهٔ واقعی
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }٪

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = صفحهٔ { $page }

## Loading indicator messages

pdfjs-loading-error = هنگام بارگیری فایل PDF خطایی رخ داد.
pdfjs-invalid-file-error = فایل PDF نامعتبر یا خراب است.
pdfjs-missing-file-error = فایل PDF پیدا نشد.
pdfjs-unexpected-response-error = پاسخ غیرمنتظره از سرور.
pdfjs-rendering-error = هنگام رندر کردن صفحه خطایی رخ داد.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [حاشیه‌نویسی { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = برای باز کردن این فایل PDF گذرواژه را وارد کنید.
pdfjs-password-invalid = گذرواژه نامعتبر است. لطفاً دوباره تلاش کنید.
pdfjs-password-ok-button = تأیید
pdfjs-password-cancel-button = انصراف
pdfjs-web-fonts-disabled = فونت‌های وب غیرفعال هستند: امکان استفاده از فونت‌های تعبیه‌شدهٔ PDF وجود ندارد.

## Editing

pdfjs-editor-free-text-button =
    .title = متن
pdfjs-editor-color-picker-free-text-input =
    .title = تغییر رنگ متن
pdfjs-editor-free-text-button-label = متن
pdfjs-editor-ink-button =
    .title = رسم
pdfjs-editor-color-picker-ink-input =
    .title = تغییر رنگ رسم
pdfjs-editor-ink-button-label = رسم
pdfjs-editor-stamp-button =
    .title = افزودن یا ویرایش تصاویر
pdfjs-editor-stamp-button-label = افزودن یا ویرایش تصاویر
pdfjs-editor-highlight-button =
    .title = برجسته‌سازی
pdfjs-editor-highlight-button-label = برجسته‌سازی
pdfjs-highlight-floating-button1 =
    .aria-label = برجسته‌سازی
    .title = برجسته‌سازی
pdfjs-highlight-floating-button-label = برجسته‌سازی
pdfjs-comment-floating-button =
    .aria-label = نظر
    .title = نظر
pdfjs-comment-floating-button-label = نظر
pdfjs-editor-comment-button =
    .aria-label = نظر
    .title = نظر
pdfjs-editor-comment-button-label = نظر
pdfjs-editor-signature-button =
    .title = افزودن امضا
pdfjs-editor-signature-button-label = افزودن امضا

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = ویرایشگر برجسته‌سازی
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = ویرایشگر رسم
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = ویرایشگر امضا: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = ویرایشگر تصویر

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = حذف رسم
pdfjs-editor-remove-freetext-button =
    .title = حذف متن
pdfjs-editor-remove-stamp-button =
    .title = حذف تصویر
pdfjs-editor-remove-highlight-button =
    .title = حذف برجسته‌سازی
pdfjs-editor-remove-signature-button =
    .title = حذف امضا

##

# Editor Parameters
pdfjs-editor-free-text-color-input = رنگ
pdfjs-editor-free-text-size-input = اندازه
pdfjs-editor-ink-color-input = رنگ
pdfjs-editor-ink-thickness-input = ضخامت
pdfjs-editor-ink-opacity-input = شفافیت
pdfjs-editor-stamp-add-image-button =
    .title = افزودن تصویر
pdfjs-editor-stamp-add-image-button-label = افزودن تصویر
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = ضخامت
pdfjs-editor-free-highlight-thickness-title =
    .title = تغییر ضخامت هنگام برجسته‌سازی مواردی غیر از متن
pdfjs-editor-add-signature-container =
    .aria-label = کنترل‌های امضا و امضاهای ذخیره‌شده
pdfjs-editor-signature-add-signature-button =
    .title = افزودن امضای جدید
pdfjs-editor-signature-add-signature-button-label = افزودن امضای جدید
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = امضای ذخیره‌شده: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = ویرایشگر متن
    .default-content = شروع به تایپ کنید…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] نظر
       *[other] نظر
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = بستن نوار کناری
    .title = بستن نوار کناری
pdfjs-editor-comments-sidebar-close-button-label = بستن نوار کناری
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = نکتهٔ مهمی دیدید؟ آن را برجسته کرده و یک نظر ثبت کنید.
pdfjs-editor-comments-sidebar-no-comments-link = بیشتر بدانید

## Alt-text dialog

pdfjs-editor-alt-text-button-label = متن جایگزین
pdfjs-editor-alt-text-edit-button =
    .aria-label = ویرایش متن جایگزین
pdfjs-editor-alt-text-dialog-label = یک گزینه را انتخاب کنید
pdfjs-editor-alt-text-dialog-description = متن جایگزین (Alt text) زمانی که افراد قادر به دیدن تصویر نیستند یا تصویر بارگیری نمی‌شود، کمک‌کننده است.
pdfjs-editor-alt-text-add-description-label = افزودن توضیحات
pdfjs-editor-alt-text-add-description-description = نوشتن ۱ تا ۲ جمله که موضوع، پس‌زمینه یا کارها را شرح دهد پیشنهاد می‌شود.
pdfjs-editor-alt-text-mark-decorative-label = علامت‌گذاری به عنوان تزئینی
pdfjs-editor-alt-text-mark-decorative-description = برای تصاویر تزئینی مانند کادرها یا واترمارک‌ها استفاده می‌شود.
pdfjs-editor-alt-text-cancel-button = انصراف
pdfjs-editor-alt-text-save-button = ذخیره
pdfjs-editor-alt-text-decorative-tooltip = به عنوان تزئینی علامت‌گذاری شد
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = برای مثال: «مرد جوانی پشت میز نشسته و در حال غذا خوردن است»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = متن جایگزین

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = گوشهٔ بالا سمت چپ — تغییر اندازه
pdfjs-editor-resizer-top-middle =
    .aria-label = بالا وسط — تغییر اندازه
pdfjs-editor-resizer-top-right =
    .aria-label = گوشهٔ بالا سمت راست — تغییر اندازه
pdfjs-editor-resizer-middle-right =
    .aria-label = راست وسط — تغییر اندازه
pdfjs-editor-resizer-bottom-right =
    .aria-label = گوشهٔ پایین سمت راست — تغییر اندازه
pdfjs-editor-resizer-bottom-middle =
    .aria-label = پایین وسط — تغییر اندازه
pdfjs-editor-resizer-bottom-left =
    .aria-label = گوشهٔ پایین سمت چپ — تغییر اندازه
pdfjs-editor-resizer-middle-left =
    .aria-label = چپ وسط — تغییر اندازه

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = رنگ برجسته‌سازی
pdfjs-editor-colorpicker-button =
    .title = تغییر رنگ
pdfjs-editor-colorpicker-dropdown =
    .aria-label = انتخاب‌های رنگ
pdfjs-editor-colorpicker-yellow =
    .title = زرد
pdfjs-editor-colorpicker-green =
    .title = سبز
pdfjs-editor-colorpicker-blue =
    .title = آبی
pdfjs-editor-colorpicker-pink =
    .title = صورتی
pdfjs-editor-colorpicker-red =
    .title = قرمز

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = نمایش همه
pdfjs-editor-highlight-show-all-button =
    .title = نمایش همه

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = ویرایش متن جایگزین (توضیحات تصویر)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = افزودن متن جایگزین (توضیحات تصویر)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = توضیحات خود را این‌جا بنویسید…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = توضیح کوتاه برای افرادی که نمی‌توانند تصویر را ببینند یا در صورت بارگیری نشدن تصویر.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = این متن جایگزین به‌صورت خودکار ایجاد شده است و ممکن است دقیق نباشد.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = بیشتر بدانید
pdfjs-editor-new-alt-text-create-automatically-button-label = ایجاد خودکار متن جایگزین
pdfjs-editor-new-alt-text-not-now-button = فعلاً نه
pdfjs-editor-new-alt-text-error-title = امکان ایجاد خودکار متن جایگزین وجود نداشت
pdfjs-editor-new-alt-text-error-description = لطفاً متن جایگزین را خودتان بنویسید یا بعداً دوباره تلاش کنید.
pdfjs-editor-new-alt-text-error-close-button = بستن
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = در حال دانلود مدل هوش مصنوعیِ متن جایگزین ({ $downloadedSize } از { $totalSize } مگابایت)
    .aria-valuetext = در حال دانلود مدل هوش مصنوعیِ متن جایگزین ({ $downloadedSize } از { $totalSize } مگابایت)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = متن جایگزین اضافه شد
pdfjs-editor-new-alt-text-added-button-label = متن جایگزین اضافه شد
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = فاقد متن جایگزین
pdfjs-editor-new-alt-text-missing-button-label = فاقد متن جایگزین
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = بازبینی متن جایگزین
pdfjs-editor-new-alt-text-to-review-button-label = بازبینی متن جایگزین
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = ایجادشده به‌صورت خودکار: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = تنظیمات متن جایگزین تصویر
pdfjs-image-alt-text-settings-button-label = تنظیمات متن جایگزین تصویر
pdfjs-editor-alt-text-settings-dialog-label = تنظیمات متن جایگزین تصویر
pdfjs-editor-alt-text-settings-automatic-title = متن جایگزین خودکار
pdfjs-editor-alt-text-settings-create-model-button-label = ایجاد خودکار متن جایگزین
pdfjs-editor-alt-text-settings-create-model-description = پیشنهاد توضیحاتی برای کمک به افرادی که تصویر را نمی‌بینند یا هنگامی که تصویر بارگیری نمی‌شود.
pdfjs-editor-alt-text-settings-editor-title = ویرایشگر متن جایگزین
pdfjs-editor-alt-text-settings-show-dialog-button-label = نمایش ویرایشگر متن جایگزین بلافاصله پس از افزودن تصویر
pdfjs-editor-alt-text-settings-show-dialog-description = به شما کمک می‌کند مطمئن شوید تمام تصاویر دارای متن جایگزین هستند.
pdfjs-editor-alt-text-settings-close-button = بستن

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = برجسته‌سازی اضافه شد
pdfjs-editor-freetext-added-alert = متن اضافه شد
pdfjs-editor-ink-added-alert = رسم اضافه شد
pdfjs-editor-stamp-added-alert = تصویر اضافه شد
pdfjs-editor-signature-added-alert = امضا اضافه شد

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = برجسته‌سازی حذف شد
pdfjs-editor-undo-bar-message-freetext = متن حذف شد
pdfjs-editor-undo-bar-message-ink = رسم حذف شد
pdfjs-editor-undo-bar-message-stamp = تصویر حذف شد
pdfjs-editor-undo-bar-message-signature = امضا حذف شد
pdfjs-editor-undo-bar-message-comment = نظر حذف شد
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } حاشیه‌نویسی حذف شد
       *[other] { $count } حاشیه‌نویسی حذف شد
    }
pdfjs-editor-undo-bar-undo-button =
    .title = واگرد
pdfjs-editor-undo-bar-undo-button-label = واگرد
pdfjs-editor-undo-bar-close-button =
    .title = بستن
pdfjs-editor-undo-bar-close-button-label = بستن

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = این پنجره به کاربر امکان می‌دهد امضایی برای افزودن به سند PDF ایجاد کند. کاربر می‌تواند نام (که به عنوان متن جایگزین نیز استفاده می‌شود) را ویرایش کند و به‌دلخواه امضا را برای استفاده‌های بعدی ذخیره نماید.
pdfjs-editor-add-signature-dialog-title = افزودن امضا

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = تایپ
    .title = تایپ
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = رسم
    .title = رسم
pdfjs-editor-add-signature-image-button = تصویر
    .title = تصویر

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = امضای خود را تایپ کنید
    .placeholder = امضای خود را تایپ کنید
pdfjs-editor-add-signature-draw-placeholder = امضای خود را رسم کنید
pdfjs-editor-add-signature-draw-thickness-range-label = ضخامت
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = ضخامت خط رسم: { $thickness }
pdfjs-editor-add-signature-image-placeholder = یک فایل را برای آپلود به این‌جا بکشید
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] یا فایل‌های تصویری را انتخاب کنید
       *[other] یا فایل‌های تصویری را مرور کنید
    }

## Controls

pdfjs-editor-add-signature-description-label = توضیحات (متن جایگزین)
pdfjs-editor-add-signature-description-input =
    .title = توضیحات (متن جایگزین)
pdfjs-editor-add-signature-description-default-when-drawing = امضا
pdfjs-editor-add-signature-clear-button-label = پاک کردن امضا
pdfjs-editor-add-signature-clear-button =
    .title = پاک کردن امضا
pdfjs-editor-add-signature-save-checkbox = ذخیرهٔ امضا
pdfjs-editor-add-signature-save-warning-message = به سقف ۵ امضای ذخیره‌شده رسیده‌اید. برای ذخیرهٔ بیشتر یکی را حذف کنید.
pdfjs-editor-add-signature-image-upload-error-title = آپلود تصویر ناموفق بود
pdfjs-editor-add-signature-image-upload-error-description = اتصال شبکهٔ خود را بررسی کرده یا تصویر دیگری را امتحان کنید.
pdfjs-editor-add-signature-image-no-data-error-title = تبدیل این تصویر به امضا امکان‌پذیر نیست
pdfjs-editor-add-signature-image-no-data-error-description = لطفاً آپلود تصویر دیگری را امتحان کنید.
pdfjs-editor-add-signature-error-close-button = بستن

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = انصراف
pdfjs-editor-add-signature-add-button = افزودن
pdfjs-editor-edit-signature-update-button = به‌روزرسانی

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = ویرایش نظر
pdfjs-editor-edit-comment-popup-button =
    .title = ویرایش نظر
pdfjs-editor-delete-comment-popup-button-label = حذف نظر
pdfjs-editor-delete-comment-popup-button =
    .title = حذف نظر
pdfjs-show-comment-button =
    .title = نمایش نظر

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = ویرایش نظر
pdfjs-editor-edit-comment-dialog-save-button-when-editing = به‌روزرسانی
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = افزودن نظر
pdfjs-editor-edit-comment-dialog-save-button-when-adding = افزودن
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = شروع به نوشتن کنید…
pdfjs-editor-edit-comment-dialog-cancel-button = انصراف

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = افزودن نظر

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = باز/بسته کردن نوار کناری (سند شامل بندانگشتی‌ها/طرح کلی/پیوست‌ها/لایه‌ها است)
pdfjs-toggle-views-manager-button1-label = مدیریت صفحه‌ها
pdfjs-views-manager-sidebar =
    .aria-label = نوار کناری
pdfjs-views-manager-sidebar-resizer =
    .aria-label = تغییر اندازهٔ نوار کناری
pdfjs-views-manager-view-selector-button =
    .title = نماها
pdfjs-views-manager-view-selector-button-label = نماها
pdfjs-views-manager-pages-title = صفحه‌ها
pdfjs-views-manager-outlines-title1 = طرح کلی سند
    .title = طرح کلی سند (دوبار کلیک برای باز/بسته کردن همهٔ موارد)
pdfjs-views-manager-attachments-title = پیوست‌ها
pdfjs-views-manager-layers-title1 = لایه‌ها
    .title = لایه‌ها (دوبار کلیک برای بازنشانی همهٔ لایه‌ها به حالت پیش‌فرض)
pdfjs-views-manager-pages-option-label = صفحه‌ها
pdfjs-views-manager-outlines-option-label = طرح کلی سند
pdfjs-views-manager-attachments-option-label = پیوست‌ها
pdfjs-views-manager-layers-option-label = لایه‌ها
pdfjs-views-manager-add-file-button =
    .title = افزودن فایل
pdfjs-views-manager-add-file-button-label = افزودن فایل
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } صفحه انتخاب شد
       *[other] { $count } صفحه انتخاب شد
    }
pdfjs-views-manager-pages-status-none-action-label = انتخاب صفحه‌ها
pdfjs-views-manager-pages-status-action-button-label = مدیریت
pdfjs-views-manager-pages-status-copy-button-label = کپی
pdfjs-views-manager-pages-status-cut-button-label = برش
pdfjs-views-manager-pages-status-delete-button-label = حذف
pdfjs-views-manager-pages-status-export-selected-button-label = برون‌بری انتخاب‌شده‌ها…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] ۱ صفحه برش داده شد
       *[other] { $count } صفحه برش داده شد
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] ۱ صفحه کپی شد
       *[other] { $count } صفحه کپی شد
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] ۱ صفحه حذف شد
       *[other] { $count } صفحه حذف شد
    }
pdfjs-views-manager-pages-status-waiting-ready-label = در حال آماده‌سازی فایل شما…
pdfjs-views-manager-pages-status-waiting-uploading-label = در حال آپلود فایل…
pdfjs-views-manager-status-warning-cut-label = برش انجام نشد. صفحه را تازه کنید و دوباره تلاش نمایید.
pdfjs-views-manager-status-warning-copy-label = کپی انجام نشد. صفحه را تازه کنید و دوباره تلاش نمایید.
pdfjs-views-manager-status-warning-delete-label = حذف انجام نشد. صفحه را تازه کنید و دوباره تلاش نمایید.
pdfjs-views-manager-status-warning-save-label = ذخیره انجام نشد. صفحه را تازه کنید و دوباره تلاش نمایید.
pdfjs-views-manager-status-undo-button-label = واگرد
pdfjs-views-manager-status-done-button-label = انجام شد
pdfjs-views-manager-status-close-button =
    .title = بستن
pdfjs-views-manager-status-close-button-label = بستن
pdfjs-views-manager-paste-button-label = جای‌گذاری
pdfjs-views-manager-paste-button-before =
    .title = جای‌گذاری قبل از صفحهٔ اول
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = جای‌گذاری پس از صفحهٔ { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = جدید
pdfjs-views-manager-waiting-for-file = در حال آپلود فایل…
pdfjs-toggle-views-manager-button1 =
    .title = مدیریت صفحه‌ها

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = ویژگی‌های امضای دیجیتال
    .title = ویژگی‌های امضای دیجیتال
pdfjs-digital-signature-properties-button-label = ویژگی‌های امضای دیجیتال

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = سند با یک امضای دیجیتال معتبر امضا شده است
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] سند امضا شده است اما { $count } امضای دیجیتال قابل تأیید نبود
       *[other] سند امضا شده است اما { $count } امضای دیجیتال قابل تأیید نبود
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] سند با { $count } گواهی غیرقابل‌اعتماد امضا شده است
       *[other] سند با { $count } گواهی غیرقابل‌اعتماد امضا شده است
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] سند با { $count } گواهی منقضی‌شده امضا شده است
       *[other] سند با { $count } گواهی منقضی‌شده امضا شده است
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] سند دارای { $count } امضای دیجیتال نامعتبر است
       *[other] سند دارای { $count } امضای دیجیتال نامعتبر است
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] سند با { $count } گواهی باطل‌شده امضا شده است
       *[other] سند با { $count } گواهی باطل‌شده امضا شده است
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = وضعیت: امضا تأیید شد
pdfjs-digital-signature-properties-status-invalid = وضعیت: امضا نامعتبر است
pdfjs-digital-signature-properties-status-unknown = وضعیت: عدم امکان تأیید (پشتیبانی‌نشده)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = گواهی: مورد اعتماد ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = گواهی: در دسترس نیست
pdfjs-digital-signature-properties-certificate-untrusted = گواهی: غیرقابل‌اعتماد
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = گواهی: صادرکنندهٔ ناشناخته ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = گواهی: خود-امضا ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = گواهی: صادرکنندهٔ غیرقابل‌اعتماد ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = گواهی: منقضی‌شده
pdfjs-digital-signature-properties-certificate-expired-with-date = گواهی: منقضی‌شده ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = گواهی: باطل‌شده

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = حذف امضای ذخیره‌شده
pdfjs-editor-delete-signature-button-label1 = حذف امضای ذخیره‌شده

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = ویرایش توضیحات

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = ویرایش توضیحات
