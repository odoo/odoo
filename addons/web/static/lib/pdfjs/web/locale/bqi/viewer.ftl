# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = بلگه دیندایی
pdfjs-previous-button-label = دیندایی
pdfjs-next-button =
    .title = بلگه نیایی
pdfjs-next-button-label = بئڌی
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = بلگه
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = ز { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } ز { $pagesCount })
pdfjs-zoom-out-button =
    .title = کۊچیر نمایی
pdfjs-zoom-out-button-label = کۊچیر نمایی
pdfjs-zoom-in-button =
    .title = گپ نمایی
pdfjs-zoom-in-button-label = گپ نمایی
pdfjs-zoom-select =
    .title = زۊم کردن
pdfjs-open-file-button =
    .title = گۊشیڌن فایل
pdfjs-open-file-button-label = گۊشیڌن
pdfjs-print-button =
    .title = چاپ
pdfjs-print-button-label = چاپ
pdfjs-save-button =
    .title = زفت
pdfjs-save-button-label = زفت
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = دانلود
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = دانلود
pdfjs-bookmark-button-label = بلگه هیم سکویی

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = ٱوزارا
pdfjs-tools-button-label = ٱوزارا
pdfjs-first-page-button =
    .title = رئڌن و بلگه نیایی
pdfjs-first-page-button-label = رئڌن و بلگه نیایی
pdfjs-last-page-button =
    .title = رئڌن و بلگه دیندایی
pdfjs-last-page-button-label = رئڌن و بلگه دیندایی
pdfjs-page-rotate-cw-button =
    .title = لر خردن ساعتگرد
pdfjs-page-rotate-cw-button-label = لر خردن ساعتگرد
pdfjs-page-rotate-ccw-button =
    .title = لر خردن خلاف ساعتگرد
pdfjs-page-rotate-ccw-button-label = لر خردن خلاف ساعتگرد
pdfjs-cursor-text-select-tool-button =
    .title = فعال کردن ٱوزار پسند هؽل
pdfjs-cursor-text-select-tool-button-label = ٱوزار پسند هؽل
pdfjs-cursor-hand-tool-button =
    .title = فعال کردن ٱوزار دست
pdfjs-cursor-hand-tool-button-label = ٱوزار دست
pdfjs-scroll-page-button =
    .title = و کار گرؽڌن اسکرۊل بلگه
pdfjs-scroll-page-button-label = اسکرۊل بلگه
pdfjs-scroll-vertical-button =
    .title = و کار گرؽڌن اسکرۊل عمۊدی
pdfjs-scroll-vertical-button-label = اسکرۊل عمۊدی
pdfjs-scroll-horizontal-button =
    .title = و کار گرؽڌن اسکرۊل اوفوقی
pdfjs-scroll-horizontal-button-label = اسکرۊل اوفوقی
pdfjs-scroll-wrapped-button =
    .title = و کار گرؽڌن اسکرۊل پؽچسته
pdfjs-scroll-wrapped-button-label = اسکرۊل پؽچسته

## Document properties dialog

pdfjs-document-properties-button =
    .title = خۊسۊسیات سند…
pdfjs-document-properties-button-label = خۊسۊسیات سند…
pdfjs-document-properties-file-name = نوم فایل:
pdfjs-document-properties-file-size = هندا فایل:
pdfjs-document-properties-title = عونوان:
pdfjs-document-properties-author = هؽل کوݩ:
pdfjs-document-properties-subject = سرتال:
pdfjs-document-properties-creation-date = تاریخ وورکل وابیڌن:
pdfjs-document-properties-modification-date = تاریخ آلشتکاری:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = وورکل کون:
pdfjs-document-properties-producer = وورکل کون PDF:
pdfjs-document-properties-version = نوسخه PDF:
pdfjs-document-properties-page-count = تئداد بلگه یل:
pdfjs-document-properties-page-size = هندا بلگه:
pdfjs-document-properties-page-size-unit-inches = اینچ
pdfjs-document-properties-page-size-unit-millimeters = میلی متر
pdfjs-document-properties-page-size-orientation-portrait = portrait
pdfjs-document-properties-page-size-orientation-landscape = landscape
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = نامه
pdfjs-document-properties-page-size-name-legal = هۊقۊقی

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
pdfjs-document-properties-linearized = نیشتن زل وب:
pdfjs-document-properties-linearized-yes = هری
pdfjs-document-properties-linearized-no = ن
pdfjs-document-properties-close-button = بستن

## Print

pdfjs-print-progress-message = ٱماڌه کردن سند سی چاپ کردن…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = لقو

## Tooltips and alt text for side panel toolbar buttons

pdfjs-findbar-button =
    .title = جوستن من سند
pdfjs-findbar-button-label = جوستن
pdfjs-additional-layers = لایه یل ازافه

## Find panel button title and messages

pdfjs-find-previous-button-label = دیندایی
pdfjs-find-next-button-label = بئڌی
pdfjs-find-highlight-checkbox = هایلایت کردن پوی

## Predefined zoom values

pdfjs-page-scale-width = پئنا بلگه
pdfjs-page-scale-fit = هندا کردن بلگه
pdfjs-page-scale-auto = زۊم کردن خوتکار
pdfjs-page-scale-actual = هندا واقعی‌
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = بلگه { $page }

## Annotations

# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-ok-button = خا
pdfjs-password-cancel-button = لقو

## Editing

pdfjs-editor-free-text-button =
    .title = هؽل
pdfjs-editor-free-text-button-label = هؽل
pdfjs-editor-ink-button =
    .title = کشیڌن
pdfjs-editor-ink-button-label = کشیڌن
pdfjs-editor-stamp-button =
    .title = ٱووردن یا آلشت شؽواتا
pdfjs-editor-stamp-button-label = ٱووردن یا آلشت شؽواتا

## Default editor aria labels

pdfjs-editor-stamp-editor =
    .aria-label = آلشتگر شؽوات

##

# Editor Parameters
pdfjs-editor-free-text-color-input = رنگ
pdfjs-editor-free-text-size-input = هندا
pdfjs-editor-ink-color-input = رنگ
pdfjs-editor-ink-thickness-input = کۊلۊفتی
pdfjs-editor-ink-opacity-input = کر بیڌن
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = کۊلۊفتی
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = آلشتگر هؽل
    .default-content = ناهاڌن پا هؽل کردن...
pdfjs-editor-comments-sidebar-no-comments-link = قلوه دووسته بۊین

## Alt-text dialog

pdfjs-editor-alt-text-cancel-button = لقو
pdfjs-editor-alt-text-save-button = زفت

## Color picker

pdfjs-editor-colorpicker-yellow =
    .title = هیل
pdfjs-editor-colorpicker-green =
    .title = ساوز
pdfjs-editor-colorpicker-blue =
    .title = کوۊ
pdfjs-editor-colorpicker-pink =
    .title = آل
pdfjs-editor-colorpicker-red =
    .title = سوئر

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = نشووݩ داڌن پوی
pdfjs-editor-highlight-show-all-button =
    .title = نشووݩ داڌن پوی

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

pdfjs-editor-new-alt-text-disclaimer-learn-more-url = قلوه دووسته بۊین
pdfjs-editor-new-alt-text-not-now-button = سکو ن
pdfjs-editor-new-alt-text-error-close-button = بستن

## "Annotations removed" bar

pdfjs-editor-undo-bar-undo-button-label = وورگندن
pdfjs-editor-undo-bar-close-button =
    .title = بستن
pdfjs-editor-undo-bar-close-button-label = بستن

## Tab panels

pdfjs-editor-add-signature-draw-thickness-range-label = کۊلۊفتی

## Controls

pdfjs-editor-add-signature-error-close-button = بستن

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = لقو
pdfjs-editor-add-signature-add-button = ٱووردن
pdfjs-editor-edit-signature-update-button = ورۊ رسۊوی

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = آلشت منشڌ
pdfjs-editor-edit-comment-popup-button =
    .title = آلشت منشڌ

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = آلشت منشڌ
pdfjs-editor-edit-comment-dialog-save-button-when-editing = ورۊ رسۊوی
pdfjs-editor-edit-comment-dialog-save-button-when-adding = ٱووردن
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = ناهاڌن پا هؽل کردن…
pdfjs-editor-edit-comment-dialog-cancel-button = لقو

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-views-manager-sidebar =
    .aria-label = نوار کلی
pdfjs-views-manager-layers-option-label = لایه یل
pdfjs-views-manager-pages-status-action-button-label = دؽوۉداری
pdfjs-views-manager-pages-status-copy-button-label = لف گیری
pdfjs-views-manager-pages-status-cut-button-label = بۊریڌن
pdfjs-views-manager-pages-status-delete-button-label = پاک کردن
pdfjs-views-manager-status-undo-button-label = وورگندن
pdfjs-views-manager-status-done-button-label = ٱنجوم وابی
pdfjs-views-manager-status-close-button =
    .title = بستن
pdfjs-views-manager-status-close-button-label = بستن
pdfjs-views-manager-paste-button-label = جا وندن
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = نۊ
