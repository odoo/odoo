# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Նախորդ էջը
pdfjs-previous-button-label = Նախորդը
pdfjs-next-button =
    .title = Հաջորդ էջը
pdfjs-next-button-label = Հաջորդը
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Էջ.
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = -ը՝ { $pagesCount }-ից
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber }-ը { $pagesCount })-ից
pdfjs-zoom-out-button =
    .title = Փոքրացնել
pdfjs-zoom-out-button-label = Փոքրացնել
pdfjs-zoom-in-button =
    .title = Խոշորացնել
pdfjs-zoom-in-button-label = Խոշորացնել
pdfjs-zoom-select =
    .title = Դիտափոխում
pdfjs-presentation-mode-button =
    .title = Անցնել Ներկայացման եղանակին
pdfjs-presentation-mode-button-label = Ներկայացման եղանակ
pdfjs-open-file-button =
    .title = Բացել նիշք
pdfjs-open-file-button-label = Բացել
pdfjs-print-button =
    .title = Տպել
pdfjs-print-button-label = Տպել
pdfjs-save-button =
    .title = Պահպանել
pdfjs-save-button-label = Պահպանել
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Ներբեռնել
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Ներբեռնել
pdfjs-bookmark-button =
    .title = Ընթացիկ էջ (Դիտել URL-ը ընթացիկ էջից)
pdfjs-bookmark-button-label = Ընթացիկ էջ

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Գործիքներ
pdfjs-tools-button-label = Գործիքներ
pdfjs-first-page-button =
    .title = Անցնել առաջին էջին
pdfjs-first-page-button-label = Անցնել առաջին էջին
pdfjs-last-page-button =
    .title = Անցնել վերջին էջին
pdfjs-last-page-button-label = Անցնել վերջին էջին
pdfjs-page-rotate-cw-button =
    .title = Պտտել ըստ ժամացույցի սլաքի
pdfjs-page-rotate-cw-button-label = Պտտել ըստ ժամացույցի սլաքի
pdfjs-page-rotate-ccw-button =
    .title = Պտտել հակառակ ժամացույցի սլաքի
pdfjs-page-rotate-ccw-button-label = Պտտել հակառակ ժամացույցի սլաքի
pdfjs-cursor-text-select-tool-button =
    .title = Միացնել գրույթ ընտրելու գործիքը
pdfjs-cursor-text-select-tool-button-label = Գրույթը ընտրելու գործիք
pdfjs-cursor-hand-tool-button =
    .title = Միացնել Ձեռքի գործիքը
pdfjs-cursor-hand-tool-button-label = Ձեռքի գործիք
pdfjs-scroll-page-button =
    .title = Օգտագործեք էջի գլորումը
pdfjs-scroll-page-button-label = Էջի գլորում
pdfjs-scroll-vertical-button =
    .title = Օգտագործել ուղղահայաց ոլորում
pdfjs-scroll-vertical-button-label = Ուղղահայաց ոլորում
pdfjs-scroll-horizontal-button =
    .title = Օգտագործել հորիզոնական ոլորում
pdfjs-scroll-horizontal-button-label = Հորիզոնական ոլորում
pdfjs-scroll-wrapped-button =
    .title = Օգտագործել փաթաթված ոլորում
pdfjs-scroll-wrapped-button-label = Փաթաթված ոլորում
pdfjs-spread-none-button =
    .title = Մի միացեք էջի վերածածկերին
pdfjs-spread-none-button-label = Չկա վերածածկեր
pdfjs-spread-odd-button =
    .title = Միացեք էջի վերածածկերին սկսելով՝ կենտ համարակալված էջերով
pdfjs-spread-odd-button-label = Կենտ վերածածկեր
pdfjs-spread-even-button =
    .title = Միացեք էջի վերածածկերին սկսելով՝ զույգ համարակալված էջերով
pdfjs-spread-even-button-label = Զույգ վերածածկեր

## Document properties dialog

pdfjs-document-properties-button =
    .title = Փաստաթղթի հատկությունները…
pdfjs-document-properties-button-label = Փաստաթղթի հատկությունները…
pdfjs-document-properties-file-name = Նիշքի անունը.
pdfjs-document-properties-file-size = Նիշք չափը.
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } ԿԲ ({ $b } բայթ)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } ՄԲ ({ $b } բայթ)
pdfjs-document-properties-title = Վերնագիր.
pdfjs-document-properties-author = Հեղինակ․
pdfjs-document-properties-subject = Վերնագիր.
pdfjs-document-properties-keywords = Հիմնաբառ.
pdfjs-document-properties-creation-date = Ստեղծելու ամսաթիվը.
pdfjs-document-properties-modification-date = Փոփոխելու ամսաթիվը.
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Ստեղծող.
pdfjs-document-properties-producer = PDF-ի հեղինակը.
pdfjs-document-properties-version = PDF-ի տարբերակը.
pdfjs-document-properties-page-count = Էջերի քանակը.
pdfjs-document-properties-page-size = Էջի չափը.
pdfjs-document-properties-page-size-unit-inches = ում
pdfjs-document-properties-page-size-unit-millimeters = մմ
pdfjs-document-properties-page-size-orientation-portrait = ուղղաձիգ
pdfjs-document-properties-page-size-orientation-landscape = հորիզոնական
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Նամակ
pdfjs-document-properties-page-size-name-legal = Օրինական

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
pdfjs-document-properties-linearized = Արագ վեբ դիտում․
pdfjs-document-properties-linearized-yes = Այո
pdfjs-document-properties-linearized-no = Ոչ
pdfjs-document-properties-close-button = Փակել

## Print

pdfjs-print-progress-message = Նախապատրաստում է փաստաթուղթը տպելուն...
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Չեղարկել
pdfjs-printing-not-supported = Զգուշացում. Տպելը ամբողջությամբ չի աջակցվում դիտարկիչի կողմից։
pdfjs-printing-not-ready = Զգուշացում. PDF-ը ամբողջությամբ չի բեռնավորվել տպելու համար:

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Բացել/Փակել կողագոտին
pdfjs-toggle-sidebar-notification-button =
    .title = Փոխարկել Կողագոտին (փաստաթուղթը պարունակում է ուրվագիծ/կցորդներ)
pdfjs-toggle-sidebar-button-label = Բացել/Փակել կողագոտին
pdfjs-document-outline-button =
    .title = Ցուցադրել փաստաթղթի ուրվագիծը (կրկնակի սեղմեք՝ միավորները ընդարձակելու/կոծկելու համար)
pdfjs-document-outline-button-label = Փաստաթղթի բովանդակությունը
pdfjs-attachments-button =
    .title = Ցուցադրել կցորդները
pdfjs-attachments-button-label = Կցորդներ
pdfjs-layers-button =
    .title = Ցուցադրել շերտերը (կրկնակի սեղմեք բոլոր շերտերը սկզբնական վիճակին վերականգնելու համար)
pdfjs-layers-button-label = Շերտեր
pdfjs-thumbs-button =
    .title = Ցուցադրել մանրապատկերը
pdfjs-thumbs-button-label = Մանրապատկերը
pdfjs-current-outline-item-button =
    .title = Գտեք ընթացիկ ուրվագծային տարրը
pdfjs-current-outline-item-button-label = Ընթացիկ ուրվագծային տարր
pdfjs-findbar-button =
    .title = Գտնել փաստաթղթում
pdfjs-findbar-button-label = Որոնում
pdfjs-additional-layers = Լրացուցիչ շերտեր

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Էջը { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Էջի մանրապատկերը { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Որոնում
    .placeholder = Գտնել փաստաթղթում...
pdfjs-find-previous-button =
    .title = Գտնել անրահայտության նախորդ հանդիպումը
pdfjs-find-previous-button-label = Նախորդը
pdfjs-find-next-button =
    .title = Գտիր արտահայտության հաջորդ հանդիպումը
pdfjs-find-next-button-label = Հաջորդը
pdfjs-find-highlight-checkbox = Գունանշել բոլորը
pdfjs-find-match-case-checkbox-label = Մեծ(փոքր)ատառ հաշվի առնել
pdfjs-find-match-diacritics-checkbox-label = Համապատասխանեցնել տարբերիչները
pdfjs-find-entire-word-checkbox-label = Ամբողջ բառերը
pdfjs-find-reached-top = Հասել եք փաստաթղթի վերևին, կշարունակվի ներքևից
pdfjs-find-reached-bottom = Հասել եք փաստաթղթի վերջին, կշարունակվի վերևից
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current }՝ { $total } համընկնումից
       *[other] { $current } of { $total } համընկնումներից
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Ավելի քան { $limit } համընկնում
       *[other] Ավելի քան { $limit } համընկնումներ
    }
pdfjs-find-not-found = Արտահայտությունը չգտնվեց

## Predefined zoom values

pdfjs-page-scale-width = Էջի լայնքը
pdfjs-page-scale-fit = Ձգել էջը
pdfjs-page-scale-auto = Ինքնաշխատ
pdfjs-page-scale-actual = Իրական չափը
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Էջ { $page }

## Loading indicator messages

pdfjs-loading-error = Սխալ՝ PDF ֆայլը բացելիս։
pdfjs-invalid-file-error = Սխալ կամ վնասված PDF ֆայլ:
pdfjs-missing-file-error = PDF ֆայլը բացակայում է:
pdfjs-unexpected-response-error = Սպասարկիչի անսպասելի պատասխան:
pdfjs-rendering-error = Սխալ՝ էջը ստեղծելիս:

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } Ծանոթություն]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Մուտքագրեք PDF-ի գաղտնաբառը:
pdfjs-password-invalid = Գաղտնաբառը սխալ է: Կրկին փորձեք:
pdfjs-password-ok-button = Լավ
pdfjs-password-cancel-button = Չեղարկել
pdfjs-web-fonts-disabled = Վեբ-տառատեսակները անջատված են. հնարավոր չէ օգտագործել ներկառուցված PDF տառատեսակները:

## Editing

pdfjs-editor-free-text-button =
    .title = Գրվածք
pdfjs-editor-color-picker-free-text-input =
    .title = Փոխել տեքստի գույնը
pdfjs-editor-free-text-button-label = Գրվածք
pdfjs-editor-ink-button =
    .title = Նկարել
pdfjs-editor-color-picker-ink-input =
    .title = Փոխել նկարելու գույնը
pdfjs-editor-ink-button-label = Նկարել
pdfjs-editor-stamp-button =
    .title = Հավելել կամ խմբագրել պատկերներ
pdfjs-editor-stamp-button-label = Հավելել կամ խմբագրել պատկերներ
pdfjs-editor-highlight-button =
    .title = Գունանշում
pdfjs-editor-highlight-button-label = Գունանշում
pdfjs-highlight-floating-button1 =
    .title = Գունանշում
    .aria-label = Գունանշում
pdfjs-highlight-floating-button-label = Գունանշում
pdfjs-comment-floating-button =
    .title = Մեկնաբանություն
    .aria-label = Մեկնաբանություն
pdfjs-comment-floating-button-label = Մեկնաբանություն
pdfjs-editor-signature-button =
    .title = Ավելացնել ստորագրություն
pdfjs-editor-signature-button-label = Ավելացնել ստորագրություն

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Գունանշել խմբագիրը
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Նկարելու խմբագիր
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Ստորագրության խմբագիր՝ { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Պատկերի խմբագիր

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Հեռացնել նկարումը
pdfjs-editor-remove-freetext-button =
    .title = Հեռացնել գրվածքը
pdfjs-editor-remove-stamp-button =
    .title = Հեռացնել պատկերը
pdfjs-editor-remove-highlight-button =
    .title = Հեռացնել գունանշումը
pdfjs-editor-remove-signature-button =
    .title = Հեռացնել ստորագրությունը

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Գույն
pdfjs-editor-free-text-size-input = Չափ
pdfjs-editor-ink-color-input = Գույն
pdfjs-editor-ink-thickness-input = Հաստություն
pdfjs-editor-ink-opacity-input = Մգություն
pdfjs-editor-stamp-add-image-button =
    .title = Հավելել պատկեր
pdfjs-editor-stamp-add-image-button-label = Հավելել պատկեր
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Հաստություն
pdfjs-editor-free-highlight-thickness-title =
    .title = Փոխել հաստությունը տեքստից բացի այլ տարրեր նշելիս
pdfjs-editor-add-signature-container =
    .aria-label = Ստորագրության կառավարման տարրեր և պահպանված ստորագրություններ
pdfjs-editor-signature-add-signature-button =
    .title = Ավելացնել նոր ստորագրություն
pdfjs-editor-signature-add-signature-button-label = Ավելացնել նոր ստորագրություն
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Պահպանված ստորագրություն՝ { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Գրվածքի խմբագիր
    .default-content = Սկսեք մուտքագրել...

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Այլընտրանքային գրվածք
pdfjs-editor-alt-text-edit-button =
    .aria-label = Խմբագրել այլընտրանքային գրվածքը
pdfjs-editor-alt-text-dialog-label = Ընտրեք տառատեսակը
pdfjs-editor-alt-text-dialog-description = Այլընտրանքային տեքստը (alternative text) օգնում է, երբ մարդիկ չեն կարողանում տեսնել պատկերը կամ երբ այն չի բեռնվում։
pdfjs-editor-alt-text-add-description-label = Հավելել նկարագրություն
pdfjs-editor-alt-text-add-description-description = Ձգտեք գրել 1-2 նախադասություն, որոնք նկարագրում են թեման, միջավայրը կամ գործողությունները։
pdfjs-editor-alt-text-mark-decorative-label = Նշել որպես դեկորատիվ
pdfjs-editor-alt-text-mark-decorative-description = Սա օգտագործվում է դեկորատիվ պատկերների համար, ինչպիսիք են եզրագծերը կամ ջրանիշերը։
pdfjs-editor-alt-text-cancel-button = Չեղարկել
pdfjs-editor-alt-text-save-button = Պահպանել
pdfjs-editor-alt-text-decorative-tooltip = Նշել որպես դեկորատիվ
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Օրինակ՝ «Մի երիտասարդ նստում է սեղանի շուրջ՝ ուտելու»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Այլընտրանքային գրվածք

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Վերին ձախ անկյուն՝ չափափոխել
pdfjs-editor-resizer-top-middle =
    .aria-label = Վերևի մեջտեղում՝ չափափոխել
pdfjs-editor-resizer-top-right =
    .aria-label = Վերին ձախ անկյուն՝ չափափոխել
pdfjs-editor-resizer-middle-right =
    .aria-label = Մեջտեղի աջ կողմում՝ չափափոխել
pdfjs-editor-resizer-bottom-right =
    .aria-label = Վերին ձախ անկյուն՝ չափափոխել
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Վերևի մեջտեղում՝ չափափոխել
pdfjs-editor-resizer-bottom-left =
    .aria-label = Վերին ձախ անկյուն՝ չափափոխել
pdfjs-editor-resizer-middle-left =
    .aria-label = Մեջտեղի ձախ կողմում՝ չափափոխել

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Գունանշման գույն
pdfjs-editor-colorpicker-button =
    .title = Փոխել գույնը
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Գույների ընտրություն
pdfjs-editor-colorpicker-yellow =
    .title = Դեղին
pdfjs-editor-colorpicker-green =
    .title = Կանաչ
pdfjs-editor-colorpicker-blue =
    .title = Կապույտ
pdfjs-editor-colorpicker-pink =
    .title = Վարդագույն
pdfjs-editor-colorpicker-red =
    .title = Կարմիր

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Ցուցադրել բոլորը
pdfjs-editor-highlight-show-all-button =
    .title = Ցուցադրել բոլորը

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Խմբագրել այլընտրանքային տեքստը (պատկերի նկարագրությունը)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Ավելացնել այլընտրանքային գրվածք (պատկերի նկարագրություն)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Գրեք ձեր նկարագրությունն այստեղ…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Կարճ նկարագրություն նրանց համար, ովքեր չեն կարող տեսնել պատկերը կամ երբ պատկերը չի բեռնվում։
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Այս այլընտրանքային տեքստը ստեղծվել է ինքնաշխատ և կարող է սխալ լինել։
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Իմանալ ավելին
pdfjs-editor-new-alt-text-create-automatically-button-label = Ինքնաշխատ ստեղծել այլընտրանքային գրվածք
pdfjs-editor-new-alt-text-not-now-button = Ոչ հիմա
pdfjs-editor-new-alt-text-error-title = Հնարավոր չէ ինքնաշխատ ստեղծել այլընտրանքային գրվածք
pdfjs-editor-new-alt-text-error-description = Խնդրում ենք գրել ձեր սեփական այլընտրանքային տեքստը կամ փորձել կրկին ավելի ուշ։
pdfjs-editor-new-alt-text-error-close-button = Փակել
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Ներբեռնվում է այլընտրանքային գրվածքի ահեստական բանականության մոդելը ({ $downloadedSize }՝ { $totalSize } ՄԲ-ից)
    .aria-valuetext = Ներբեռնվում է այլընտրանքային գրվածքի ահեստական բանականության մոդելը ({ $downloadedSize }՝ { $totalSize } ՄԲ-ից)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Այլընտրանքային գրվածքն ավելացված է
pdfjs-editor-new-alt-text-added-button-label = Այլընտրանքային գրվածքն ավելացված է
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Այլընտրանքային գրվածքը բացակայում է
pdfjs-editor-new-alt-text-missing-button-label = Այլընտրանքային գրվածքը բացակայում է
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Վերանայել այլընտրանքային գրվածքը
pdfjs-editor-new-alt-text-to-review-button-label = Վերանայել այլընտրանքային գրվածքը
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Ստեղծվել է ինքնաշխատվ՝ { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Պատկերի այլընտրանքային գրվածքի կարգավորումներ
pdfjs-image-alt-text-settings-button-label = Պատկերի այլընտրանքային գրվածքի կարգավորումներ
pdfjs-editor-alt-text-settings-dialog-label = Պատկերի այլընտրանքային գրվածքի կարգավորումներ
pdfjs-editor-alt-text-settings-automatic-title = Ինքնաշխատ այլընտրանքային գրվածք
pdfjs-editor-alt-text-settings-create-model-button-label = Ինքնաշխատ ստեղծել այլընտրանքային գրվածք
pdfjs-editor-alt-text-settings-create-model-description = Կարճ նկարագրություն նրանց համար, ովքեր չեն կարող տեսնել պատկերը կամ երբ պատկերը չի բեռնվում։
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Այլընտրանքային գրվածքի արհեստական բանականության մոդել ({ $totalSize } ՄԲ)
pdfjs-editor-alt-text-settings-ai-model-description = Աշխատում է տեղայնորեն ձեր սարքի վրա, որպեսզի ձեր տվյալները մնան գաղտնի: Պահանջվում է ինքնաշխատ այլընտրանքային գրվածքի համար:
pdfjs-editor-alt-text-settings-delete-model-button = Ջնջել
pdfjs-editor-alt-text-settings-download-model-button = Ներբեռնել
pdfjs-editor-alt-text-settings-downloading-model-button = Ներբեռնվում է…
pdfjs-editor-alt-text-settings-editor-title = Այլընտրանքային գրվածքի խմբագիր
pdfjs-editor-alt-text-settings-show-dialog-button-label = Պատկեր ավելացնելիս անմիջապես ցուցադրել այլընտրանքային գրվածքի խմբագիրը
pdfjs-editor-alt-text-settings-show-dialog-description = Օգնում է  համոզվել, որ ձեր բոլոր պատկերներն ունեն այլընտրանքային գրվածք։
pdfjs-editor-alt-text-settings-close-button = Փակել

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Գունանշումը ավելացվել է
pdfjs-editor-freetext-added-alert = Գրվածքը ավելացվել է
pdfjs-editor-ink-added-alert = Նկարումը ավելացվել է
pdfjs-editor-stamp-added-alert = Պատկերն ավելացված է
pdfjs-editor-signature-added-alert = Ստորագրությունն ավելացված է

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Գունանշումը հեռացված է
pdfjs-editor-undo-bar-message-freetext = Գրվածքը հեռացվել է
pdfjs-editor-undo-bar-message-ink = Նկարվածը հեռացվել է
pdfjs-editor-undo-bar-message-stamp = Պատկերը հեռացվել է
pdfjs-editor-undo-bar-message-signature = Ստորագրությունը հեռացված է
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } մեկնաբանությունը հեռացվել է
       *[other] { $count } մեկնաբանությունները հեռացվել են
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Հետարկել
pdfjs-editor-undo-bar-undo-button-label = Հետարկել
pdfjs-editor-undo-bar-close-button =
    .title = Փակել
pdfjs-editor-undo-bar-close-button-label = Փակել

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Այս յուրահատկությունը հնարավորություն է տալիս օգտվողին ստեղծել ստորագրություն՝ PDF փաստաթղթում ավելացնելու համար: Օգտվողը կարող է խմբագրել անունը (որը նաև ծառայում է որպես alt տեքստ) և լրացուցիչ պահպանել այն՝ հետագա օգտագործման համար:
pdfjs-editor-add-signature-dialog-title = Ավելացնել ստորագրություն

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Տեսակ
    .title = Տեսակ
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Նկարել
    .title = Նկարել
pdfjs-editor-add-signature-image-button = Պատկեր
    .title = Պատկեր

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Մուտքագրեք ձեր ստորագրությունը
    .placeholder = Մուտքագրեք ձեր ստորագրությունը
pdfjs-editor-add-signature-draw-placeholder = Նկարեք ձեր ստորագրությունը
pdfjs-editor-add-signature-draw-thickness-range-label = Հաստություն
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Նկաելու հաստությունը՝ { $thickness }
pdfjs-editor-add-signature-image-placeholder = Քաշեք ֆայլը այստեղ՝ վերբեռնելու համար
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Կամ ընտրեք պատկերի ֆայլը
       *[other] Կամ ընտրեք պատկերի ֆայլերը
    }

## Controls

pdfjs-editor-add-signature-description-label = Նկարագրություն (այլընտրանքային գրվածք)
pdfjs-editor-add-signature-description-input =
    .title = Նկարագրություն (այլընտրանքային գրվածք)
pdfjs-editor-add-signature-description-default-when-drawing = Ստորագրություն
pdfjs-editor-add-signature-clear-button-label = Մաքրել ստորագրությունը
pdfjs-editor-add-signature-clear-button =
    .title = Մաքրել ստորագրությունը
pdfjs-editor-add-signature-save-checkbox = Պահպանել ստորագրությունը
pdfjs-editor-add-signature-save-warning-message = Դուք հասել եք պահպանված ստորագրությունների 5 սահմանաչափին։ Հեռացրեք մեկը՝ ավելին պահպանելու համար։
pdfjs-editor-add-signature-image-upload-error-title = Չհաջողվեց վերբեռնել պատկերը
pdfjs-editor-add-signature-image-upload-error-description = Ստուգեք ձեր ցանցային կապակցումը կամ փորձեք մեկ այլ պատկեր։
pdfjs-editor-add-signature-image-no-data-error-title = Այս պատկերը հնարավոր չէ վերածել ստորագրության
pdfjs-editor-add-signature-image-no-data-error-description = Խնդրում եմ փորձեք վերբեռնել այլ պատկեր։
pdfjs-editor-add-signature-error-close-button = Փակել

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Չեղարկել
pdfjs-editor-add-signature-add-button = Ավելացնել
pdfjs-editor-edit-signature-update-button = Թարմացնել

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Գործողություններ
pdfjs-editor-edit-comment-actions-button =
    .title = Գործողություններ
pdfjs-editor-edit-comment-close-button-label = Փակել
pdfjs-editor-edit-comment-close-button =
    .title = Փակել
pdfjs-editor-edit-comment-actions-edit-button-label = Խմբագրել
pdfjs-editor-edit-comment-actions-delete-button-label = Ջնջել
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Մուտքագրեք ձեր մեկնաբանությունը
pdfjs-editor-edit-comment-manager-cancel-button = Չեղարկել
pdfjs-editor-edit-comment-manager-save-button = Պահպանել

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Խմբագրել մեկնաբանությունը

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Հեռացնել պահպանված ստորագրությունը
pdfjs-editor-delete-signature-button-label1 = Հեռացնել պահպանված ստորագրությունը

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Խմբագրել նկարագրությունը

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Խմբագրել նկարագրությունը
