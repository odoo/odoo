# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = پچھلا ورقہ
pdfjs-previous-button-label = پچھلا
pdfjs-next-button =
    .title = اڳلا ورقہ
pdfjs-next-button-label = اڳلا
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = ورقہ
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = { $pagesCount } دا
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } دا { $pagesCount })
pdfjs-zoom-out-button =
    .title = زوم آؤٹ
pdfjs-zoom-out-button-label = زوم آؤٹ
pdfjs-zoom-in-button =
    .title = زوم اِن
pdfjs-zoom-in-button-label = زوم اِن
pdfjs-zoom-select =
    .title = زوم
pdfjs-presentation-mode-button =
    .title = پریزنٹیشن موڈ تے سوئچ کرو
pdfjs-presentation-mode-button-label = پریزنٹیشن موڈ
pdfjs-open-file-button =
    .title = فائل کھولو
pdfjs-open-file-button-label = کھولو
pdfjs-print-button =
    .title = چھاپو
pdfjs-print-button-label = چھاپو
pdfjs-save-button =
    .title = ہتھیکڑا کرو
pdfjs-save-button-label = ہتھیکڑا کرو
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = ڈاؤن لوڈ
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = ڈاؤن لوڈ
pdfjs-bookmark-button =
    .title = موجودہ ورقہ (موجودہ ورقے کنوں یوآرایل ݙیکھو)
pdfjs-bookmark-button-label = موجودہ ورقہ

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = اوزار
pdfjs-tools-button-label = اوزار
pdfjs-first-page-button =
    .title = پہلے ورقے تے ونڄو
pdfjs-first-page-button-label = پہلے ورقے تے ونڄو
pdfjs-last-page-button =
    .title = چھیکڑی ورقے تے ونڄو
pdfjs-last-page-button-label = چھیکڑی ورقے تے ونڄو
pdfjs-page-rotate-cw-button =
    .title = گھڑی وانگوں گھماؤ
pdfjs-page-rotate-cw-button-label = گھڑی وانگوں گھماؤ
pdfjs-page-rotate-ccw-button =
    .title = گھڑی تے اُپٹھ گھماؤ
pdfjs-page-rotate-ccw-button-label = گھڑی تے اُپٹھ گھماؤ
pdfjs-cursor-text-select-tool-button =
    .title = متن منتخب کݨ والا آلہ فعال بݨاؤ
pdfjs-cursor-text-select-tool-button-label = متن منتخب کرݨ والا آلہ
pdfjs-cursor-hand-tool-button =
    .title = ہینڈ ٹول فعال بݨاؤ
pdfjs-cursor-hand-tool-button-label = ہینڈ ٹول
pdfjs-scroll-page-button =
    .title = پیج سکرولنگ استعمال کرو
pdfjs-scroll-page-button-label = پیج سکرولنگ
pdfjs-scroll-vertical-button =
    .title = عمودی سکرولنگ استعمال کرو
pdfjs-scroll-vertical-button-label = عمودی سکرولنگ
pdfjs-scroll-horizontal-button =
    .title = افقی سکرولنگ استعمال کرو
pdfjs-scroll-horizontal-button-label = افقی سکرولنگ
pdfjs-scroll-wrapped-button =
    .title = ویڑھی ہوئی سکرولنگ استعمال کرو
pdfjs-scroll-wrapped-button-label = وہڑھی ہوئی سکرولنگ
pdfjs-spread-none-button =
    .title = پیج سپریڈز وِچ شامل نہ تھیوو۔
pdfjs-spread-none-button-label = کوئی پولھ کائنی
pdfjs-spread-odd-button =
    .title = طاق نمبر والے ورقیاں دے نال شروع تھیوݨ والے پیج سپریڈز وِچ شامل تھیوو۔
pdfjs-spread-odd-button-label = تاک پھیلاؤ
pdfjs-spread-even-button =
    .title = جفت نمر والے ورقیاں نال شروع تھیوݨ والے پیج سپریڈز وِ شامل تھیوو۔
pdfjs-spread-even-button-label = جفت پھیلاؤ

## Document properties dialog

pdfjs-document-properties-button =
    .title = دستاویز خواص…
pdfjs-document-properties-button-label = دستاویز خواص …
pdfjs-document-properties-file-name = فائل دا ناں:
pdfjs-document-properties-file-size = فائل دا سائز:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } بائٹاں)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } بائٹاں)
pdfjs-document-properties-title = عنوان:
pdfjs-document-properties-author = تخلیق کار:
pdfjs-document-properties-subject = موضوع:
pdfjs-document-properties-keywords = کلیدی الفاظ:
pdfjs-document-properties-creation-date = تخلیق دی تاریخ:
pdfjs-document-properties-modification-date = ترمیم دی تاریخ:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = تخلیق کار:
pdfjs-document-properties-producer = PDF پیدا کار:
pdfjs-document-properties-version = PDF ورژن:
pdfjs-document-properties-page-count = ورقہ شماری:
pdfjs-document-properties-page-size = ورقہ دی سائز:
pdfjs-document-properties-page-size-unit-inches = وِچ
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = عمودی انداز
pdfjs-document-properties-page-size-orientation-landscape = افقى انداز
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = لیٹر
pdfjs-document-properties-page-size-name-legal = قنونی

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit } ({ $orientation })
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name }, { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = تکھا ویب نظارہ:
pdfjs-document-properties-linearized-yes = جیا
pdfjs-document-properties-linearized-no = کو
pdfjs-document-properties-close-button = بند کرو
pdfjs-digital-signature-properties-view-certificate = سرٹیفکیٹ ݙیکھو۔
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = وجہ: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = ٹائم سٹیمپ: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] ذیلی دستخط ({ $count })
       *[other] ذیلی دستخطاں ({ $count })
    }

## Print

pdfjs-print-progress-message = چھاپݨ کیتے دستاویز تیار تھیندے پئے ہن …
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = منسوخ کرو
pdfjs-printing-not-supported = چتاوݨی: چھپائی ایں براؤزر تے پوری طراں معاونت شدہ کائنی۔
pdfjs-printing-not-ready = چتاوݨی: PDF چھپائی کیتے پوری طراں لوڈ نئیں تھئی۔

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = موجودہ آؤٹ لائن آئٹم لبھو
pdfjs-current-outline-item-button-label = موجودہ آؤٹ لائن آئٹم
pdfjs-findbar-button =
    .title = دستاویز وِچ لبھو
pdfjs-findbar-button-label = لبھو
pdfjs-additional-layers = اضافی پرتاں

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = ورقے دا تھمبنیل { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = صفحہ { $page } منتخب کرو۔
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = صفحہ { $page } از { $total }۔

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = دستاویز وِچ لبھو …
    .title = لبھو
pdfjs-find-previous-button =
    .title = فقرے دا پچھلا واقعہ لبھو
pdfjs-find-previous-button-label = پچھلا
pdfjs-find-next-button =
    .title = فقرے دا اڳلا واقعہ لبھو
pdfjs-find-next-button-label = اڳلا
pdfjs-find-highlight-checkbox = تمام نشابر کرو
pdfjs-find-match-case-checkbox-label = حروف مشابہ کرو
pdfjs-find-match-diacritics-checkbox-label = ڈائیکرٹکس مشابہ کرو
pdfjs-find-entire-word-checkbox-label = تمام الفاظ
pdfjs-find-reached-top = ورقے دے شروع تے پُج ڳیا، تلوں جاری کیتا ڳیا
pdfjs-find-reached-bottom = ورقے دے پاند تے پُڄ ڳیا، اُتوں شروع کیتا ڳیا
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $total } وِچوں { $current } مشابہ
       *[other] { $total } وِچوں { $current } مشابے
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] { $limit } توں ودھ مماثلت۔
       *[other] { $limit } توں ودھ مماثلتاں۔
    }
pdfjs-find-not-found = فقرہ نئیں ملیا

## Predefined zoom values

pdfjs-page-scale-width = ورقے دی چوڑائی
pdfjs-page-scale-fit = ورقہ فٹنگ
pdfjs-page-scale-auto = آپوں آپ زوم
pdfjs-page-scale-actual = اصل میچا
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = ورقہ { $page }

## Loading indicator messages

pdfjs-loading-error = PDF لوڈ کریندے ویلھے نقص آ ڳیا۔
pdfjs-invalid-file-error = غلط یا خراب شدہ PDF فائل۔
pdfjs-missing-file-error = PDF فائل غائب ہے۔
pdfjs-unexpected-response-error = سرور دا غیر متوقع جواب۔
pdfjs-rendering-error = ورقہ رینڈر کریندے ویلھے ہک خرابی پیش آڳئی۔

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } تشریح]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = ایہ PDF فائل کھولݨ کیتے پاس ورڈ درج کرو۔
pdfjs-password-invalid = غلط پاس ورڈ: براہ مہربانی ولدا کوشش کرو۔
pdfjs-password-ok-button = ٹھیک ہے
pdfjs-password-cancel-button = منسوخ کرو
pdfjs-web-fonts-disabled = ویب فونٹس غیر فعال ہن: ایمبیڈڈ PDF  فونٹس استعمال کرݨ کنوں قاصر ہن

## Editing

pdfjs-editor-free-text-button =
    .title = متن
pdfjs-editor-color-picker-free-text-input =
    .title = متن دا رنگ بدلو۔
pdfjs-editor-free-text-button-label = متن
pdfjs-editor-ink-button =
    .title = چھکو
pdfjs-editor-color-picker-ink-input =
    .title = ڈرائنگ دا رنگ بدلو۔
pdfjs-editor-ink-button-label = چھکو
pdfjs-editor-stamp-button =
    .title = تصویراں کوں شامل کرو یا ترمیم کرو
pdfjs-editor-stamp-button-label = تصویراں کوں شامل کرو یا ترمیم کرو
pdfjs-editor-highlight-button =
    .title = نمایاں کرو
pdfjs-editor-highlight-button-label = نمایاں کرو
pdfjs-highlight-floating-button1 =
    .aria-label = نمایاں کرو
    .title = نمایاں کرو
pdfjs-highlight-floating-button-label = نمایاں کرو
pdfjs-comment-floating-button =
    .aria-label = تبصرہ۔
    .title = تبصرہ۔
pdfjs-comment-floating-button-label = تبصرہ۔
pdfjs-editor-comment-button =
    .aria-label = تبصرہ
    .title = تبصرہ
pdfjs-editor-comment-button-label = تبصرہ۔
pdfjs-editor-signature-button =
    .title = دستخط شامل کرو۔
pdfjs-editor-signature-button-label = دستخط شامل کرو۔

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = نشابر ایڈیٹر۔
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = ڈرائنگ ایڈیٹر۔
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = دستخط ایڈیٹر: { $description }۔
pdfjs-editor-stamp-editor =
    .aria-label = تصویر ایڈیٹر۔

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = ڈرائینگ ہٹاؤ
pdfjs-editor-remove-freetext-button =
    .title = متن ہٹاؤ
pdfjs-editor-remove-stamp-button =
    .title = تصویر ہٹاؤ
pdfjs-editor-remove-highlight-button =
    .title = نمایاں ہٹاؤ
pdfjs-editor-remove-signature-button =
    .title = دستخط ہٹاؤ۔

##

# Editor Parameters
pdfjs-editor-free-text-color-input = رنگ
pdfjs-editor-free-text-size-input = سائز
pdfjs-editor-ink-color-input = رنگ
pdfjs-editor-ink-thickness-input = ٹھولھ
pdfjs-editor-ink-opacity-input = دھندلاپن
pdfjs-editor-stamp-add-image-button =
    .title = تصویر شامل کرو
pdfjs-editor-stamp-add-image-button-label = تصویر شامل کرو
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = مُٹاݨ
pdfjs-editor-free-highlight-thickness-title =
    .title = متن توں ان٘ج ٻئے شئیں کوں نمایاں کرݨ ویلے مُٹاݨ کوں بدلو
pdfjs-editor-add-signature-container =
    .aria-label = دستخط کنٹرولز تے محفوظ دستخط۔
pdfjs-editor-signature-add-signature-button =
    .title = نواں دستخط شامل کرو۔
pdfjs-editor-signature-add-signature-button-label = نواں دستخط شامل کرو۔
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = محفوظ دستخط: { $description }۔
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = ٹیکسٹ ایڈیٹر
    .default-content = ٹائپنگ شروع کرو …
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] تبصرہ
       *[other] تبصرے
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = سائیڈبار بند کرو۔
    .title = سائیڈبار بند کرو۔
pdfjs-editor-comments-sidebar-close-button-label = سائیڈبار بند کرو۔
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = کوئی اہم گلھ نظر آئی؟ اونکوں ہائی لائٹ کرو تے تبصرہ چھوڑو۔
pdfjs-editor-comments-sidebar-no-comments-link = ٻیا سکھو

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alt متن
pdfjs-editor-alt-text-edit-button =
    .aria-label = alt متن وِچ ترمیم کرو
pdfjs-editor-alt-text-dialog-label = ہِک اختیار چُݨو
pdfjs-editor-alt-text-dialog-description = Alt متن (متبادل متن) اِیں ویلے مَدَت کرین٘دا ہِے جہڑیلے لوک تصویر کوں نِھیں ݙیکھ سڳدے یا جہڑیلے اِیہ لوڈ کائنی تِھین٘دا۔
pdfjs-editor-alt-text-add-description-label = تفصیل شامل کرو
pdfjs-editor-alt-text-add-description-description = 1-2 جملیاں دا مقصد جہڑے موضوع، ترتیب، یا اعمال کوں بیان کرین٘دے ہِن۔
pdfjs-editor-alt-text-mark-decorative-label = آرائشی طور تے نشان زد کرو
pdfjs-editor-alt-text-mark-decorative-description = اِیہ آرائشی تصویراں کِیتے استعمال تِھین٘دا ہِے، جیویں بارڈر یا واٹر مارکس۔
pdfjs-editor-alt-text-cancel-button = منسوخ
pdfjs-editor-alt-text-save-button = محفوظ
pdfjs-editor-alt-text-decorative-tooltip = آرائشی دے طور تے نشان زد تِھی ڳِیا
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = مثال دے طور تے، "ہِک جؤان کھاݨاں کھاوݨ کِیتے میز اُتّے ٻیٹھا ہِے"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alt متن

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = اُتلی کَھٻّی نُکّڑ — سائز بدلو
pdfjs-editor-resizer-top-middle =
    .aria-label = اُتلا وِچلا — سائز بدلو
pdfjs-editor-resizer-top-right =
    .aria-label = اُتلی سَڄّی نُکَّڑ — سائز بدلو
pdfjs-editor-resizer-middle-right =
    .aria-label = وِچلا سڄّا — سائز بدلو
pdfjs-editor-resizer-bottom-right =
    .aria-label = تلوِیں سَڄّی نُکَّڑ — سائز بدلو
pdfjs-editor-resizer-bottom-middle =
    .aria-label = تلواں وِچلا — سائز بدلو
pdfjs-editor-resizer-bottom-left =
    .aria-label = تلوِیں کَھٻّی نُکّڑ — سائز بدلو
pdfjs-editor-resizer-middle-left =
    .aria-label = وِچلا کَھٻّا — سائز بدلو

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = نشابر رنگ
pdfjs-editor-colorpicker-button =
    .title = رنگ بدلو
pdfjs-editor-colorpicker-dropdown =
    .aria-label = رنگ اختیارات
pdfjs-editor-colorpicker-yellow =
    .title = پیلا
pdfjs-editor-colorpicker-green =
    .title = ساوا
pdfjs-editor-colorpicker-blue =
    .title = نیلا
pdfjs-editor-colorpicker-pink =
    .title = گلابی
pdfjs-editor-colorpicker-red =
    .title = لال

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = سارے ݙکھاؤ
pdfjs-editor-highlight-show-all-button =
    .title = سارے ݙکھاؤ

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = آلٹ عبارت وچ تبدیلی کرو (تصویر تفصیل)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = آلٹ عبارت شامل کرو (تصویر تفصیل)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = اتھ آپݨی وضاحت لکھو۔۔۔
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = اُنہاں لوکاں کیتے مختصر تفصیل جہڑے تصویر کائنی ݙیکھ سڳدے یا ڄݙݨ تصویر لوڈ کائبی تھیندی۔
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = آلٹ عبارت خودکار تخلیق تھئی ہے تے غلط تھی سڳدی ہے۔
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = ٻیا سِکھو
pdfjs-editor-new-alt-text-create-automatically-button-label = آلٹ عبارت خودکار بݨاؤ
pdfjs-editor-new-alt-text-not-now-button = ہݨ کائناں
pdfjs-editor-new-alt-text-error-title = آلٹ عبارت خودکار نہ بݨاؤ
pdfjs-editor-new-alt-text-error-description = سوہݨا، آپݨی آلٹ عبارت لکھو یا ولدا بعد وچ کوشش کرو۔
pdfjs-editor-new-alt-text-error-close-button = بند کرو
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = آلٹ عبارت اے آئی ماڈل({ $totalSize }ایم بی دے { $downloadedSize }) ڈاؤن لوڈ تھیندا پئے
    .aria-valuetext = آلٹ عبارت اے آئی ماڈل({ $totalSize }ایم بی دے { $downloadedSize }) ڈاؤن لوڈ تھیندا پئے
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = آلٹ عبارت شامل تھی ڳئی
pdfjs-editor-new-alt-text-added-button-label = آلٹ عبارت شامل تھی ڳئی
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = متبادل عبارت غائب ہے
pdfjs-editor-new-alt-text-missing-button-label = متبادل عبارت غائب ہے
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = alt متن تے نظرثانی کرو
pdfjs-editor-new-alt-text-to-review-button-label = alt متن تے نظرثانی کرو
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = خودکار تخلیق تھئی: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = تصویر آلٹ عبارت ترتیباں
pdfjs-image-alt-text-settings-button-label = تصویر آلٹ عبارت ترتیباں
pdfjs-editor-alt-text-settings-dialog-label = تصویر آلٹ عبارت ترتیباں
pdfjs-editor-alt-text-settings-automatic-title = خودکار آلٹ عبارت
pdfjs-editor-alt-text-settings-create-model-button-label = آلٹ عبارت خودکار بݨاؤ
pdfjs-editor-alt-text-settings-create-model-description = اُنہاں لوکاں دی مدد کیتے  تفصیل تجویز کرو جہڑے تصویر کائنی ݙیکھ سڳدے یا ڄݙݨ تصویر لوڈ کائبی تھیندی۔
pdfjs-editor-alt-text-settings-editor-title = متبادل ٹیکسٹ ایڈیٹر
pdfjs-editor-alt-text-settings-show-dialog-button-label = تصویر شامل کرݨ ویلے فوری طور تے آلٹ ٹیکسٹ ایڈیٹر ݙکھاؤ
pdfjs-editor-alt-text-settings-show-dialog-description = ایہ تہاکوں یقینی بݨاوݨ وچ مدد کریندے جو تہاݙیاں ساریاں تصویراں وچ آلٹ عبارت ہے۔
pdfjs-editor-alt-text-settings-close-button = بند کرو

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = ہائی لائٹ شامل تھئی
pdfjs-editor-freetext-added-alert = متن شامل تھیا
pdfjs-editor-ink-added-alert = ڈرائنگ شامل تھئی
pdfjs-editor-stamp-added-alert = تصویر شامل تھئی
pdfjs-editor-signature-added-alert = دستخط شامل تھئی

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = ہائی لائٹ مٹائی ڳئی
pdfjs-editor-undo-bar-message-freetext = متن مٹایا ڳیا
pdfjs-editor-undo-bar-message-ink = ڈرائنگ مٹائی ڳئی
pdfjs-editor-undo-bar-message-stamp = تصویر مٹائی ڳئی
pdfjs-editor-undo-bar-message-signature = دستخط مٹائے ڳئے
pdfjs-editor-undo-bar-message-comment = تبصرہ مٹایا ڳیا
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } تشریح مٹائی ڳئی
       *[other] { $count } تشریحیں مٹائی ڳئیاں
    }
pdfjs-editor-undo-bar-undo-button =
    .title = کیتا اݨ کیتا
pdfjs-editor-undo-bar-undo-button-label = کیتا اݨ کیتا
pdfjs-editor-undo-bar-close-button =
    .title = بند کرو
pdfjs-editor-undo-bar-close-button-label = بند کرو

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = ایہ مکالمہ صارف کوں PDF دستاویز وِچ شامل کرݨ کیتے دستخط بݨاوݨ دی اجازت ݙیندا ہے۔ صارف ناں وِچ ترمیم کر سڳدا ہے (جیڑھا alt متن دے طور تے وی کم کریندا ہے)، تے اختیاری طور تے دستخط کوں ٻار ٻار ورتݨ کیتے محفوظ کر سڳدا ہے۔
pdfjs-editor-add-signature-dialog-title = دستخط شامل کرو۔

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = ٹائپ کرو
    .title = ٹائپ کرو
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = چھکو
    .title = چھکو
pdfjs-editor-add-signature-image-button = تصویر
    .title = تصویر

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = اپݨے دستخط ٹائپ کرو
    .placeholder = اپݨے دستخط ٹائپ کرو
pdfjs-editor-add-signature-draw-placeholder = اپݨے دستخط ڈراو کرو
pdfjs-editor-add-signature-draw-thickness-range-label = موٹائی۔
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = ڈرائنگ دی ٹھولھ: { $thickness }
pdfjs-editor-add-signature-image-placeholder = اپ لوڈ کرݨ کیتے فائل اتھے سٹو
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] یا تصویر فائلاں چݨو
       *[other] یا تصویر فائلاں براؤز کرو
    }

## Controls

pdfjs-editor-add-signature-description-label = تفصیل (alt متن)
pdfjs-editor-add-signature-description-input =
    .title = تفصیل (alt متن)
pdfjs-editor-add-signature-description-default-when-drawing = دستخط
pdfjs-editor-add-signature-clear-button-label = دستخط صاف کرو
pdfjs-editor-add-signature-clear-button =
    .title = دستخط صاف کرو
pdfjs-editor-add-signature-save-checkbox = دستخط محفوظ کرو
pdfjs-editor-add-signature-save-warning-message = تساں 5 محفوظ شدہ دستخطاں دی حد تک پُج ڳئے ہو۔ ٻئے محفوظ کرݨ کیتے ہک مٹاو۔
pdfjs-editor-add-signature-image-upload-error-title = تصویر اپ لوڈ نہ تھئی
pdfjs-editor-add-signature-image-upload-error-description = اپݨا نیٹ ورک کنکشن چیک کرو یا ٻئی تصویر آزماو۔
pdfjs-editor-add-signature-image-no-data-error-title = تصویر کوں دستخط اچ تبدیل نہیں کر سڳیا
pdfjs-editor-add-signature-image-no-data-error-description = ٻئی تصویر اپ لوڈ کرݨ دی کوشش کرو۔
pdfjs-editor-add-signature-error-close-button = بند کرو

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = منسوخ کرو۔
pdfjs-editor-add-signature-add-button = شامل کرو
pdfjs-editor-edit-signature-update-button = اپ ڈیٹ کرو۔

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = تبصرہ ایڈٹ کرو
pdfjs-editor-edit-comment-popup-button =
    .title = تبصرہ ایڈٹ کرو
pdfjs-editor-delete-comment-popup-button-label = تبصرہ مٹاو
pdfjs-editor-delete-comment-popup-button =
    .title = تبصرہ مٹاو
pdfjs-show-comment-button =
    .title = تبصرہ ݙکھاو

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = تبصرہ ایڈٹ کرو
pdfjs-editor-edit-comment-dialog-save-button-when-editing = اپ ڈیٹ کرو
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = تبصرہ شامل کرو
pdfjs-editor-edit-comment-dialog-save-button-when-adding = شامل کرو
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = ٹائپ کرݨ شروع کرو
pdfjs-editor-edit-comment-dialog-cancel-button = منسوخ

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = تبصرہ شامل کرو

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = سائیڈ بار ٹوگل کرو (دستاویز اچ تھمب نیلز/آؤٹ لائن/منسلکات/پرتاں شامل ہن)
pdfjs-toggle-views-manager-button1-label = صفحیاں دا انتظام کرو
pdfjs-views-manager-sidebar =
    .aria-label = بغلی بار
pdfjs-views-manager-sidebar-resizer =
    .aria-label = سائیڈ بار دا ری سائزر
pdfjs-views-manager-view-selector-button =
    .title = نظارے
pdfjs-views-manager-view-selector-button-label = نظارے
pdfjs-views-manager-pages-title = ورقے
pdfjs-views-manager-outlines-title1 = دستاویز دا آؤٹ لائن
    .title = دستاویز دا آؤٹ لائن (سارے آئٹمز کوں پھیلاؤن یا سمیٹݨ کیتے ڈبل کلک کرو)
pdfjs-views-manager-attachments-title = منسلکات
pdfjs-views-manager-layers-title1 = پرتاں
    .title = پرتاں (سارے پرتاں کوں ڈیفالٹ حالت تے واپس کرݨ کیتے ڈبل کلک کرو)
pdfjs-views-manager-pages-option-label = ورقے
pdfjs-views-manager-outlines-option-label = دستاویز دا آؤٹ لائن
pdfjs-views-manager-attachments-option-label = منسلکات
pdfjs-views-manager-layers-option-label = پرتاں
pdfjs-views-manager-add-file-button =
    .title = فائل شامل کرو
pdfjs-views-manager-add-file-button-label = فائل شامل کرو
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } منتخب
       *[other] { $count } منتخب
    }
pdfjs-views-manager-pages-status-none-action-label = ورقے منتخب کرو
pdfjs-views-manager-pages-status-action-button-label = بندوبست کرو
pdfjs-views-manager-pages-status-copy-button-label = کاپی کرو
pdfjs-views-manager-pages-status-cut-button-label = کٹ کرو
pdfjs-views-manager-pages-status-delete-button-label = مٹاو
pdfjs-views-manager-pages-status-export-selected-button-label = منتخب کوں ایکسپورٹ کرو…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 ورقہ کٹیا ڳیا
       *[other] { $count } ورقے کٹے ڳئے
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 ورقہ کاپی کیتا ڳیا
       *[other] { $count } ورقے کاپی کیتے ڳئے
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 ورقہ مٹایا ڳیا
       *[other] { $count } ورقے مٹائے ڳئے
    }
pdfjs-views-manager-pages-status-waiting-ready-label = تہاݙی فائل تیار کیتی پئی اے…
pdfjs-views-manager-pages-status-waiting-uploading-label = فائل اپ لوڈ تھیندی پئی اے…
pdfjs-views-manager-status-warning-cut-label = کٹ نئیں سڳیا. ورقہ ریفریش کرو تے دوبارہ کوشش کرو.
pdfjs-views-manager-status-warning-copy-label = کاپی نئیں سڳیا. ورقہ ریفریش کرو تے دوبارہ کوشش کرو.
pdfjs-views-manager-status-warning-delete-label = مٹاو نئیں سڳیا. ورقہ ریفریش کرو تے دوبارہ کوشش کرو.
pdfjs-views-manager-status-warning-save-label = محفوظ نئیں سڳیا. ورقہ ریفریش کرو تے دوبارہ کوشش کرو.
pdfjs-views-manager-status-undo-button-label = کیتا اݨ کیتا
pdfjs-views-manager-status-done-button-label = تھی ڳیا
pdfjs-views-manager-status-close-button =
    .title = بند کرو
pdfjs-views-manager-status-close-button-label = بند کرو
pdfjs-views-manager-paste-button-label = پیسٹ کرو
pdfjs-views-manager-paste-button-before =
    .title = پہلے ورقے توں پہلے پیسٹ کرو
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = ورقے { $page } دے بعد پیسٹ کرو
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = نواں
pdfjs-views-manager-waiting-for-file = فائل اپ لوڈ تھیندی پئی اے…
pdfjs-toggle-views-manager-button1 =
    .title = ورقے منیج کرو

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = ڈیجیٹل دستخط دیاں خصوصیات
    .title = ڈیجیٹل دستخط دیاں خصوصیات
pdfjs-digital-signature-properties-button-label = ڈیجیٹل دستخط دیاں خصوصیات

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = دستاویز تے درست ڈیجیٹل دستخط کیتے ڳئے ہن
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] دستاویز تے دستخط ہن پر { $count } ڈیجیٹل دستخط دی تصدیق نئیں سڳی
       *[other] دستاویز تے دستخط ہن پر { $count } ڈیجیٹل دستخطاں دی تصدیق نئیں سڳی
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] دستاویز تے { $count } سرٹیفیکیٹ نال دستخط ہن جیڑھا بھروسے آلا نئیں
       *[other] دستاویز تے { $count } سرٹیفیکیٹاں نال دستخط ہن جیڑھے بھروسے آلے نئیں
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] دستاویز تے { $count } میعاد گزرا سرٹیفیکیٹ نال دستخط ہن
       *[other] دستاویز تے { $count } میعاد گزرے سرٹیفیکیٹاں نال دستخط ہن
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] دستاویز وچ { $count } غلط ڈیجیٹل دستخط ہے
       *[other] دستاویز وچ { $count } غلط ڈیجیٹل دستخط ہن
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] دستاویز تے { $count } منسوخ سرٹیفیکیٹ نال دستخط ہن
       *[other] دستاویز تے { $count } منسوخ سرٹیفیکیٹاں نال دستخط ہن
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = حال: دستخط دی تصدیق تھی ڳئی اے
pdfjs-digital-signature-properties-status-invalid = حال: دستخط غلط ہے
pdfjs-digital-signature-properties-status-unknown = حال: تصدیق نئیں تھی سڳی (غیر تعاون یافتہ)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = سرٹیفیکیٹ: بھروسے آلا ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = سرٹیفیکیٹ: دستیاب نئیں
pdfjs-digital-signature-properties-certificate-untrusted = سرٹیفیکیٹ: بھروسے آلا نئیں
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = سرٹیفیکیٹ: نامعلوم جاری کنندہ ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = سرٹیفیکیٹ: خود دستخط شدہ ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = سرٹیفیکیٹ: بھروسے آلا نئیں جاری کنندہ ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = سرٹیفیکیٹ: میعاد گزر ڳیا
pdfjs-digital-signature-properties-certificate-expired-with-date = سرٹیفیکیٹ: میعاد گزر ڳیا ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = سرٹیفیکیٹ: منسوخ

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = محفوظ شدہ دستخط ہٹاؤ
pdfjs-editor-delete-signature-button-label1 = محفوظ شدہ دستخط ہٹاؤ

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = تفصیل ایڈٹ کرو

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = تفصیل ایڈٹ کرو
