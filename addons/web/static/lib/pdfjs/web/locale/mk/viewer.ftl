# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Претходна страница
pdfjs-previous-button-label = Претходна
pdfjs-next-button =
    .title = Следна страница
pdfjs-next-button-label = Следна
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Страница
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = од { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } од { $pagesCount })
pdfjs-zoom-out-button =
    .title = Намалување
pdfjs-zoom-out-button-label = Намали
pdfjs-zoom-in-button =
    .title = Зголемување
pdfjs-zoom-in-button-label = Зголеми
pdfjs-zoom-select =
    .title = Променување на големина
pdfjs-presentation-mode-button =
    .title = Премини во презентациски режим
pdfjs-presentation-mode-button-label = Презентациски режим
pdfjs-open-file-button =
    .title = Отворање датотека
pdfjs-open-file-button-label = Отвори
pdfjs-print-button =
    .title = Печатење
pdfjs-print-button-label = Печати
pdfjs-save-button =
    .title = Снимање
pdfjs-save-button-label = Сними
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Преземање
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Преземи
pdfjs-bookmark-button =
    .title = Тековна страница (Преглед на URL од тековна страница)
pdfjs-bookmark-button-label = Тековна страница

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Алатки
pdfjs-tools-button-label = Алатки
pdfjs-first-page-button =
    .title = Оди до првата страница
pdfjs-first-page-button-label = Оди до првата страница
pdfjs-last-page-button =
    .title = Оди до последната страница
pdfjs-last-page-button-label = Оди до последната страница
pdfjs-page-rotate-cw-button =
    .title = Ротирај по стрелките на часовникот
pdfjs-page-rotate-cw-button-label = Ротирај по стрелките на часовникот
pdfjs-page-rotate-ccw-button =
    .title = Ротирај спротивно од стрелките на часовникот
pdfjs-page-rotate-ccw-button-label = Ротирај спротивно од стрелките на часовникот
pdfjs-cursor-text-select-tool-button =
    .title = Овозможи алатка за избор на текст
pdfjs-cursor-text-select-tool-button-label = Алатка за избор на текст
pdfjs-cursor-hand-tool-button =
    .title = Овозможување на рачна алатка
pdfjs-cursor-hand-tool-button-label = Рачна алатка
pdfjs-scroll-page-button =
    .title = Употреба на поместување на страница
pdfjs-scroll-page-button-label = Поместување на страница
pdfjs-scroll-vertical-button =
    .title = Употреба на вертикално поместување
pdfjs-scroll-vertical-button-label = Вертикално поместување
pdfjs-scroll-horizontal-button =
    .title = Употреба на хоризонтално поместување
pdfjs-scroll-horizontal-button-label = Хоризонтално поместување
pdfjs-scroll-wrapped-button =
    .title = Употреба на последователно поместување
pdfjs-scroll-wrapped-button-label = Последователно поместување
pdfjs-spread-none-button =
    .title = Не спојувај спротивни страници
pdfjs-spread-none-button-label = Без спојување
pdfjs-spread-odd-button =
    .title = Спој страници почнувајќи со непарен број
pdfjs-spread-odd-button-label = Непарнo спојување
pdfjs-spread-even-button =
    .title = Спој страници почнувајќи со парен број
pdfjs-spread-even-button-label = Парно спојување

## Document properties dialog

pdfjs-document-properties-button =
    .title = Својства на документот…
pdfjs-document-properties-button-label = Својства на документот…
pdfjs-document-properties-file-name = Име на датотека:
pdfjs-document-properties-file-size = Големина на датотеката:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } бајти)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } бајти)
pdfjs-document-properties-title = Наслов:
pdfjs-document-properties-author = Автор:
pdfjs-document-properties-subject = Тема:
pdfjs-document-properties-keywords = Клучни зборови:
pdfjs-document-properties-creation-date = Датум на создавање:
pdfjs-document-properties-modification-date = Датум на промена:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Автор:
pdfjs-document-properties-producer = Составувач на PDF:
pdfjs-document-properties-version = Верзија на PDF:
pdfjs-document-properties-page-count = Број на страници:
pdfjs-document-properties-page-size = Големина на страница:
pdfjs-document-properties-page-size-unit-inches = инч
pdfjs-document-properties-page-size-unit-millimeters = мм
pdfjs-document-properties-page-size-orientation-portrait = портрет
pdfjs-document-properties-page-size-orientation-landscape = пејзаж
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Писмо
pdfjs-document-properties-page-size-name-legal = Правно

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
pdfjs-document-properties-linearized = Брз мрежен преглед:
pdfjs-document-properties-linearized-yes = Да
pdfjs-document-properties-linearized-no = Не
pdfjs-document-properties-close-button = Затвори

## Print

pdfjs-print-progress-message = Документ се подготвува за печатење…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Откажи
pdfjs-printing-not-supported = Предупредување: Печатењето не е целосно поддржано во овој прелистувач.
pdfjs-printing-not-ready = Предупредување: PDF документот не е целосно вчитан за печатење.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Барање на тековниот елемент од прегледот
pdfjs-current-outline-item-button-label = Тековен елемент од прегледот
pdfjs-findbar-button =
    .title = Најди во документот
pdfjs-findbar-button-label = Најди
pdfjs-additional-layers = Дополнителни слоеви

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Иконка од страница { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Изберете страница { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Страница { $page } од { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Пронајди во документот…
    .title = Пребарување
pdfjs-find-previous-button =
    .title = Најди ја предходната појава на фразата
pdfjs-find-previous-button-label = Претходно
pdfjs-find-next-button =
    .title = Најди ја следната појава на фразата
pdfjs-find-next-button-label = Следно
pdfjs-find-highlight-checkbox = Означи сѐ
pdfjs-find-match-case-checkbox-label = Токму така
pdfjs-find-match-diacritics-checkbox-label = Вклучи дијакритички знаци
pdfjs-find-entire-word-checkbox-label = Цели зборови
pdfjs-find-reached-top = Барањето стигна до почетокот на документот и почнува од крајот
pdfjs-find-reached-bottom = Барањето стигна до крајот на документот и почнува од почеток
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } од { $total } совпаѓање
       *[other] { $current } од { $total } совпаѓања
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Повеќе од { $limit } совпаѓање
       *[other] Повеќе од { $limit } совпаѓања
    }
pdfjs-find-not-found = Фразата не е пронајдена

## Predefined zoom values

pdfjs-page-scale-width = Ширина на страница
pdfjs-page-scale-fit = Цела страница
pdfjs-page-scale-auto = Автоматска големина
pdfjs-page-scale-actual = Вистинска големина
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Страница { $page }

## Loading indicator messages

pdfjs-loading-error = Настана грешка при вчитувањето на PDF-от.
pdfjs-invalid-file-error = Невалидна или корумпирана PDF датотека.
pdfjs-missing-file-error = Недостасува PDF документ.
pdfjs-unexpected-response-error = Неочекуван одговор од серверот.
pdfjs-rendering-error = Настана грешка при прикажувањето на страницата.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } напомена]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Внесете ја лозинката за да ја отворите оваа PDF датотека.
pdfjs-password-invalid = Невалидна лозинка. Обидете се повторно.
pdfjs-password-ok-button = Во ред
pdfjs-password-cancel-button = Откажи
pdfjs-web-fonts-disabled = Интернет фонтовите се оневозможени: не може да се користат вградените PDF фонтови.

## Editing

pdfjs-editor-free-text-button =
    .title = Текст
pdfjs-editor-color-picker-free-text-input =
    .title = Промена на боја на текст
pdfjs-editor-free-text-button-label = Текст
pdfjs-editor-ink-button =
    .title = Цртање
pdfjs-editor-color-picker-ink-input =
    .title = Промена на боја за цртање
pdfjs-editor-ink-button-label = Цртај
pdfjs-editor-stamp-button =
    .title = Додавање или уредување на слики
pdfjs-editor-stamp-button-label = Додај или уреди слики
pdfjs-editor-highlight-button =
    .title = Нагласување
pdfjs-editor-highlight-button-label = Нагласи
pdfjs-highlight-floating-button1 =
    .aria-label = Нагласување
    .title = Нагласување
pdfjs-highlight-floating-button-label = Нагласи
pdfjs-comment-floating-button =
    .aria-label = Коментар
    .title = Коментар
pdfjs-comment-floating-button-label = Коментар
pdfjs-editor-comment-button =
    .aria-label = Коментар
    .title = Коментар
pdfjs-editor-comment-button-label = Коментар
pdfjs-editor-signature-button =
    .title = Додавање на потпис
pdfjs-editor-signature-button-label = Додај потпис

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Уредувач на нагласувања
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Уредувач за цртање
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Уредувач на потпис: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Уредувач на слика

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Отстранување на цртеж
pdfjs-editor-remove-freetext-button =
    .title = Отстранување на текст
pdfjs-editor-remove-stamp-button =
    .title = Отстранување на слика
pdfjs-editor-remove-highlight-button =
    .title = Отстранување на нагласувања
pdfjs-editor-remove-signature-button =
    .title = Отстранување на потпис

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Боја
pdfjs-editor-free-text-size-input = Големина
pdfjs-editor-ink-color-input = Боја
pdfjs-editor-ink-thickness-input = Дебелина
pdfjs-editor-ink-opacity-input = Прозрачност
pdfjs-editor-stamp-add-image-button =
    .title = Додавање на слика
pdfjs-editor-stamp-add-image-button-label = Додај слика
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Дебелина
pdfjs-editor-free-highlight-thickness-title =
    .title = Промени ја дебелината при нагласување на елементи што не се текст
pdfjs-editor-add-signature-container =
    .aria-label = Контрола на потписи и снимени потписи
pdfjs-editor-signature-add-signature-button =
    .title = Додавање на нов потпис
pdfjs-editor-signature-add-signature-button-label = Додај нов потпис
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Снимен потпис: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Уредувач на текст
    .default-content = Почнуи со пишување…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Коментар
       *[other] Коментари
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Затвори ја страничната лента
    .title = Затвори ја страничната лента
pdfjs-editor-comments-sidebar-close-button-label = Затвори ја страничната лента
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Гледате нешто вредно за внимание? Истакнете го и напишете коментар.
pdfjs-editor-comments-sidebar-no-comments-link = Дознајте повеќе

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Дополнителен текст
pdfjs-editor-alt-text-edit-button =
    .aria-label = Уреди го дополнителниот текст
pdfjs-editor-alt-text-dialog-label = Изберете опција
pdfjs-editor-alt-text-dialog-description = Алтернативниот текст помага кога луѓе не можат да видат сликата или кога сликата не се вчитува
pdfjs-editor-alt-text-add-description-label = Додај опис
pdfjs-editor-alt-text-add-description-description = Додајте 1-2 реченици што го објаснуваат предметот, околината, или дејствата.
pdfjs-editor-alt-text-mark-decorative-label = Означи како декоративно
pdfjs-editor-alt-text-mark-decorative-description = Ова се користи за орнаментални слики, како граници или водени жигови.
pdfjs-editor-alt-text-cancel-button = Откажи
pdfjs-editor-alt-text-save-button = Сними
pdfjs-editor-alt-text-decorative-tooltip = Означено како декоративно
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = На пример: „Момче седнува на маса за да јаде“.
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Дополнителен текст

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Горен лев ќош — промени големина
pdfjs-editor-resizer-top-middle =
    .aria-label = Горе на средина — промени големина
pdfjs-editor-resizer-top-right =
    .aria-label = Горен десен ќош — промени големина
pdfjs-editor-resizer-middle-right =
    .aria-label = Средина десно — промени големина
pdfjs-editor-resizer-bottom-right =
    .aria-label = Долен десен ќош — промени големина
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Долу на средина — промени големина
pdfjs-editor-resizer-bottom-left =
    .aria-label = Долен лев ќош — промени големина
pdfjs-editor-resizer-middle-left =
    .aria-label = Средина лево — промени големина

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Боја за нагласување
pdfjs-editor-colorpicker-button =
    .title = Менување на боја
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Избор на бои
pdfjs-editor-colorpicker-yellow =
    .title = Жолта
pdfjs-editor-colorpicker-green =
    .title = Зелена
pdfjs-editor-colorpicker-blue =
    .title = Сина
pdfjs-editor-colorpicker-pink =
    .title = Розова
pdfjs-editor-colorpicker-red =
    .title = Црвена

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Прикажи сѐ
pdfjs-editor-highlight-show-all-button =
    .title = Прикажи сѐ

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Уреди го алтернативниот текст (опис на слика)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Додај алтернативен текст (опис на слика)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Напиши опис…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Краток опис за луѓе кои не можат да ја видат сликата или кога сликата не се вчитува.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Овој алтернативен текст е креиран автоматски и може да биде неточен.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Дознајте повеќе
pdfjs-editor-new-alt-text-create-automatically-button-label = Креирај го алтернативниот текст автоматски
pdfjs-editor-new-alt-text-not-now-button = Не сега
pdfjs-editor-new-alt-text-error-title = Алтернатиовниот текст не може да се креира автоматски
pdfjs-editor-new-alt-text-error-description = Напишете Ваш алтернативен текст или обидете се повторно подоцна.
pdfjs-editor-new-alt-text-error-close-button = Затвори
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Преземање на алтернативен текст модел на ВИ ({ $downloadedSize } од { $totalSize } MB)
    .aria-valuetext = Преземање на алтернативен текст модел на ВИ ({ $downloadedSize } од { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Алтернативниот текст е додаден
pdfjs-editor-new-alt-text-added-button-label = Алтернативниот текст е додаден
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Недостасува алтернативен текст
pdfjs-editor-new-alt-text-missing-button-label = Недостасува алтернативен текст
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Прегледај го алтернативниот текст
pdfjs-editor-new-alt-text-to-review-button-label = Прегледај го алтернативниот текст
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Креирано автоматски: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Поставки за алтернативен текст на слика
pdfjs-image-alt-text-settings-button-label = Поставки за алтернативен текст на слика
pdfjs-editor-alt-text-settings-dialog-label = Поставки за алтернативен текст на слика
pdfjs-editor-alt-text-settings-automatic-title = Автоматски алтернативен текст
pdfjs-editor-alt-text-settings-create-model-button-label = Креирај го алтернативниот текст автоматски
pdfjs-editor-alt-text-settings-create-model-description = Предлага описи за да им помогне на луѓето кои не можат да ја видат сликата или кога сликата не се вчитува.
pdfjs-editor-alt-text-settings-editor-title = Уредувач на алтернативен текст
pdfjs-editor-alt-text-settings-show-dialog-button-label = Прикажи го уредувачот на алтернативен текст веднаш при додавање на слика
pdfjs-editor-alt-text-settings-show-dialog-description = Ви помага да се осигурате дека сите ваши слики имаат алтернативен текст.
pdfjs-editor-alt-text-settings-close-button = Затвори

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Нагласувањето е додадено
pdfjs-editor-freetext-added-alert = Текстот е додаден
pdfjs-editor-ink-added-alert = Цртежот е додаден
pdfjs-editor-stamp-added-alert = Сликата е додадена
pdfjs-editor-signature-added-alert = Потписот е додаден

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Нагласувањето е отстрането
pdfjs-editor-undo-bar-message-freetext = Текстот е отстранет
pdfjs-editor-undo-bar-message-ink = Цртежот е отстранет
pdfjs-editor-undo-bar-message-stamp = Сликата е отстранета
pdfjs-editor-undo-bar-message-signature = Потписот е отстранет
pdfjs-editor-undo-bar-message-comment = Коментарот е отстранет
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } напомена е отстранета
       *[other] { $count } напомени е отстранета
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Врати
pdfjs-editor-undo-bar-undo-button-label = Врати
pdfjs-editor-undo-bar-close-button =
    .title = Затвори
pdfjs-editor-undo-bar-close-button-label = Затвори

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Овој прозорец му овозможува на корисникот да креира потпис за да го додаде во PDF документ. Корисникот може да го уреди името (кое исто така служи како алтернативен текст) и опционално да го зачува потписот за повторна употреба.
pdfjs-editor-add-signature-dialog-title = Додавање на потпис

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Типкај
    .title = Типкај
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Цртај
    .title = Цртај
pdfjs-editor-add-signature-image-button = Слика
    .title = Слика

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Типкајте го Вашиот потпис
    .placeholder = Типкајте го Вашиот потпис
pdfjs-editor-add-signature-draw-placeholder = Нацртајте го Вашиот потпис
pdfjs-editor-add-signature-draw-thickness-range-label = Дебелина
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Дебелина на цртежот: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Повлечете датотека тука за да ја прикачите
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Или прелистајте датотеки со слики
       *[other] Или прелистајте датотеки со слики
    }

## Controls

pdfjs-editor-add-signature-description-label = Опис (алтернативен текст)
pdfjs-editor-add-signature-description-input =
    .title = Опис (алтернативен текст)
pdfjs-editor-add-signature-description-default-when-drawing = Потпис
pdfjs-editor-add-signature-clear-button-label = Избриши го потписот
pdfjs-editor-add-signature-clear-button =
    .title = Бришење на потписот
pdfjs-editor-add-signature-save-checkbox = Сними го потписот
pdfjs-editor-add-signature-save-warning-message = Можете да снимите најмногу 5 потписи. Отстранете еден за да снимите нов.
pdfjs-editor-add-signature-image-upload-error-title = Сликата не може да се прикачи
pdfjs-editor-add-signature-image-upload-error-description = Проверете ја мрежната врска или обидете се со друга слика.
pdfjs-editor-add-signature-image-no-data-error-title = Оваа слика не може да се конвертира во потпис
pdfjs-editor-add-signature-image-no-data-error-description = Обидете се да прикачите друга слика.
pdfjs-editor-add-signature-error-close-button = Затвори

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Откажи
pdfjs-editor-add-signature-add-button = Додај
pdfjs-editor-edit-signature-update-button = Ажурирај

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Уреди коментар
pdfjs-editor-edit-comment-popup-button =
    .title = Уреди коментар
pdfjs-editor-delete-comment-popup-button-label = Отстрани го коментарот
pdfjs-editor-delete-comment-popup-button =
    .title = Отстрани го коментарот
pdfjs-show-comment-button =
    .title = Прикажи го коментарот

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Уреди коментар
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Ажурирај
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Додај коментар
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Додај
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Започнете со пишување…
pdfjs-editor-edit-comment-dialog-cancel-button = Откажи

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Додај коментар

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Вклучи странична лента (документот содржи преглед, прилози, или слоеви)
pdfjs-toggle-views-manager-button1-label = Управувај со страниците
pdfjs-views-manager-sidebar =
    .aria-label = Странична лента
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Променувач на големината на страничната лента
pdfjs-views-manager-view-selector-button =
    .title = Погледи
pdfjs-views-manager-view-selector-button-label = Погледи
pdfjs-views-manager-pages-title = Страници
pdfjs-views-manager-outlines-title1 = Преглед на документот
    .title = Преглед на документот (двоклик за прикажување/криење на сите ставки)
pdfjs-views-manager-attachments-title = Прилози
pdfjs-views-manager-layers-title1 = Слоеви
    .title = Слоеви (двоклик за ресетирање на сите слоеви)
pdfjs-views-manager-pages-option-label = Страници
pdfjs-views-manager-outlines-option-label = Преглед на документот
pdfjs-views-manager-attachments-option-label = Прилози
pdfjs-views-manager-layers-option-label = Слоеви
pdfjs-views-manager-add-file-button =
    .title = Додај датотека
pdfjs-views-manager-add-file-button-label = Додај датотека
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } избран
       *[other] { $count } избрани
    }
pdfjs-views-manager-pages-status-none-action-label = Избери страници
pdfjs-views-manager-pages-status-action-button-label = Управувај
pdfjs-views-manager-pages-status-copy-button-label = Копирај
pdfjs-views-manager-pages-status-cut-button-label = Исечи
pdfjs-views-manager-pages-status-delete-button-label = Избриши
pdfjs-views-manager-pages-status-export-selected-button-label = Извези ги избраните…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 исечена страница
       *[other] { $count } исечени страници
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 копирана страница
       *[other] { $count } копирани страници
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 избришана страница
       *[other] { $count } избришани страници
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Вашата датотека се подготвува…
pdfjs-views-manager-pages-status-waiting-uploading-label = Датотеката се прикачува…
pdfjs-views-manager-status-warning-cut-label = Сечењето на успеа. Освежете ја страницата и обидете се повторно.
pdfjs-views-manager-status-warning-copy-label = Копирањето на успеа. Освежете ја страницата и обидете се повторно.
pdfjs-views-manager-status-warning-delete-label = Бришењето на успеа. Освежете ја страницата и обидете се повторно.
pdfjs-views-manager-status-warning-save-label = Снимањето на успеа. Освежете ја страницата и обидете се повторно.
pdfjs-views-manager-status-undo-button-label = Врати
pdfjs-views-manager-status-done-button-label = Готово
pdfjs-views-manager-status-close-button =
    .title = Затвори
pdfjs-views-manager-status-close-button-label = Затвори
pdfjs-views-manager-paste-button-label = Залепи
pdfjs-views-manager-paste-button-before =
    .title = Залепи пред првата страница
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Залепи по страница { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = НОВО
pdfjs-views-manager-waiting-for-file = Датотеката се прикачува…
pdfjs-toggle-views-manager-button1 =
    .title = Управување со страниците

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Отстрани го зачуваниот потпис
pdfjs-editor-delete-signature-button-label1 = Отстрани го зачуваниот потпис

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Уреди опис

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Уреди опис
