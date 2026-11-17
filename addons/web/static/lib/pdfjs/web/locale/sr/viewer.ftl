# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Претходна страница
pdfjs-previous-button-label = Претходна
pdfjs-next-button =
    .title = Следећа страница
pdfjs-next-button-label = Следећа
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
    .title = Умањи
pdfjs-zoom-out-button-label = Умањи
pdfjs-zoom-in-button =
    .title = Увеличај
pdfjs-zoom-in-button-label = Увеличај
pdfjs-zoom-select =
    .title = Увеличавање
pdfjs-presentation-mode-button =
    .title = Промени на приказ у режиму презентације
pdfjs-presentation-mode-button-label = Режим презентације
pdfjs-open-file-button =
    .title = Отвори датотеку
pdfjs-open-file-button-label = Отвори
pdfjs-print-button =
    .title = Штампај
pdfjs-print-button-label = Штампај
pdfjs-save-button =
    .title = Сачувај
pdfjs-save-button-label = Сачувај
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Преузми
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Преузми
pdfjs-bookmark-button =
    .title = Тренутна страница (погледајте URL са тренутне странице)
pdfjs-bookmark-button-label = Тренутна страница

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Алатке
pdfjs-tools-button-label = Алатке
pdfjs-first-page-button =
    .title = Иди на прву страницу
pdfjs-first-page-button-label = Иди на прву страницу
pdfjs-last-page-button =
    .title = Иди на последњу страницу
pdfjs-last-page-button-label = Иди на последњу страницу
pdfjs-page-rotate-cw-button =
    .title = Ротирај у смеру казаљке на сату
pdfjs-page-rotate-cw-button-label = Ротирај у смеру казаљке на сату
pdfjs-page-rotate-ccw-button =
    .title = Ротирај у смеру супротном од казаљке на сату
pdfjs-page-rotate-ccw-button-label = Ротирај у смеру супротном од казаљке на сату
pdfjs-cursor-text-select-tool-button =
    .title = Омогући алат за селектовање текста
pdfjs-cursor-text-select-tool-button-label = Алат за селектовање текста
pdfjs-cursor-hand-tool-button =
    .title = Омогући алат за померање
pdfjs-cursor-hand-tool-button-label = Алат за померање
pdfjs-scroll-page-button =
    .title = Користи скроловање по омоту
pdfjs-scroll-page-button-label = Скроловање странице
pdfjs-scroll-vertical-button =
    .title = Користи вертикално скроловање
pdfjs-scroll-vertical-button-label = Вертикално скроловање
pdfjs-scroll-horizontal-button =
    .title = Користи хоризонтално скроловање
pdfjs-scroll-horizontal-button-label = Хоризонтално скроловање
pdfjs-scroll-wrapped-button =
    .title = Користи скроловање по омоту
pdfjs-scroll-wrapped-button-label = Скроловање по омоту
pdfjs-spread-none-button =
    .title = Немој спајати ширења страница
pdfjs-spread-none-button-label = Без распростирања
pdfjs-spread-odd-button =
    .title = Споји ширења страница које почињу непарним бројем
pdfjs-spread-odd-button-label = Непарна распростирања
pdfjs-spread-even-button =
    .title = Споји ширења страница које почињу парним бројем
pdfjs-spread-even-button-label = Парна распростирања

## Document properties dialog

pdfjs-document-properties-button =
    .title = Параметри документа…
pdfjs-document-properties-button-label = Параметри документа…
pdfjs-document-properties-file-name = Име датотеке:
pdfjs-document-properties-file-size = Величина датотеке:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } бајтова)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } бајтова)
pdfjs-document-properties-title = Наслов:
pdfjs-document-properties-author = Аутор:
pdfjs-document-properties-subject = Тема:
pdfjs-document-properties-keywords = Кључне речи:
pdfjs-document-properties-creation-date = Датум креирања:
pdfjs-document-properties-modification-date = Датум модификације:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Стваралац:
pdfjs-document-properties-producer = PDF произвођач:
pdfjs-document-properties-version = PDF верзија:
pdfjs-document-properties-page-count = Број страница:
pdfjs-document-properties-page-size = Величина странице:
pdfjs-document-properties-page-size-unit-inches = ин
pdfjs-document-properties-page-size-unit-millimeters = мм
pdfjs-document-properties-page-size-orientation-portrait = усправно
pdfjs-document-properties-page-size-orientation-landscape = водоравно
pdfjs-document-properties-page-size-name-a-three = А3
pdfjs-document-properties-page-size-name-a-four = А4
pdfjs-document-properties-page-size-name-letter = Слово
pdfjs-document-properties-page-size-name-legal = Права

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
pdfjs-document-properties-linearized = Брз веб приказ:
pdfjs-document-properties-linearized-yes = Да
pdfjs-document-properties-linearized-no = Не
pdfjs-document-properties-close-button = Затвори
pdfjs-digital-signature-properties-view-certificate = Прикажи сертификат
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Разлог: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Временски жиг: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Подпотпис ({ $count })
        [few] Подпотписа ({ $count })
       *[other] Подпотписа ({ $count })
    }

## Print

pdfjs-print-progress-message = Припремам документ за штампање…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Откажи
pdfjs-printing-not-supported = Упозорење: Штампање није у потпуности подржано у овом прегледачу.
pdfjs-printing-not-ready = Упозорење: PDF није у потпуности учитан за штампу.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Пронађите тренутни елемент структуре
pdfjs-current-outline-item-button-label = Тренутна контура
pdfjs-findbar-button =
    .title = Пронађи у документу
pdfjs-findbar-button-label = Пронађи
pdfjs-additional-layers = Додатни слојеви

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Сличица од странице { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Изабери страницу { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Страница { $page } од { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Пронађи у документу…
    .title = Пронађи
pdfjs-find-previous-button =
    .title = Пронађи претходно појављивање фразе
pdfjs-find-previous-button-label = Претходна
pdfjs-find-next-button =
    .title = Пронађи следеће појављивање фразе
pdfjs-find-next-button-label = Следећа
pdfjs-find-highlight-checkbox = Истакнути све
pdfjs-find-match-case-checkbox-label = Подударања
pdfjs-find-match-diacritics-checkbox-label = Дијакритика
pdfjs-find-entire-word-checkbox-label = Целе речи
pdfjs-find-reached-top = Достигнут врх документа, наставио са дна
pdfjs-find-reached-bottom = Достигнуто дно документа, наставио са врха
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } од { $total } поклапања
        [few] { $current } од { $total } поклапања
       *[other] { $current } од { $total } поклапања
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Више од { $limit } поклапања
        [few] Више од { $limit } поклапања
       *[other] Више од { $limit } поклапања
    }
pdfjs-find-not-found = Фраза није пронађена

## Predefined zoom values

pdfjs-page-scale-width = Ширина странице
pdfjs-page-scale-fit = Прилагоди страницу
pdfjs-page-scale-auto = Аутоматско увеличавање
pdfjs-page-scale-actual = Стварна величина
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Страница { $page }

## Loading indicator messages

pdfjs-loading-error = Дошло је до грешке приликом учитавања PDF-а.
pdfjs-invalid-file-error = PDF датотека је неважећа или је оштећена.
pdfjs-missing-file-error = Недостаје PDF датотека.
pdfjs-unexpected-response-error = Неочекиван одговор од сервера.
pdfjs-rendering-error = Дошло је до грешке приликом рендеровања ове странице.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } коментар]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Унесите лозинку да бисте отворили овај PDF докуменат.
pdfjs-password-invalid = Неисправна лозинка. Покушајте поново.
pdfjs-password-ok-button = У реду
pdfjs-password-cancel-button = Откажи
pdfjs-web-fonts-disabled = Веб фонтови су онемогућени: не могу користити уграђене PDF фонтове.

## Editing

pdfjs-editor-free-text-button =
    .title = Текст
pdfjs-editor-color-picker-free-text-input =
    .title = Промени боју текста
pdfjs-editor-free-text-button-label = Текст
pdfjs-editor-ink-button =
    .title = Цртај
pdfjs-editor-color-picker-ink-input =
    .title = Промени боју цртежа
pdfjs-editor-ink-button-label = Цртај
pdfjs-editor-stamp-button =
    .title = Додај или уреди слике
pdfjs-editor-stamp-button-label = Додај или уреди слике
pdfjs-editor-highlight-button =
    .title = Означи
pdfjs-editor-highlight-button-label = Означи
pdfjs-highlight-floating-button1 =
    .aria-label = Означи
    .title = Означи
pdfjs-highlight-floating-button-label = Означи
pdfjs-comment-floating-button =
    .aria-label = Коментар
    .title = Коментар
pdfjs-comment-floating-button-label = Напомена
pdfjs-editor-comment-button =
    .aria-label = Коментар
    .title = Коментар
pdfjs-editor-comment-button-label = Коментар
pdfjs-editor-signature-button =
    .title = Додај потпис
pdfjs-editor-signature-button-label = Додај потпис

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Уређивач истицања
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Уређивач цртања
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Уређивач потписа: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Уређивач слика

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Уклони цртеж
pdfjs-editor-remove-freetext-button =
    .title = Уклони текст
pdfjs-editor-remove-stamp-button =
    .title = Уклони слику
pdfjs-editor-remove-highlight-button =
    .title = Уклони ознаку
pdfjs-editor-remove-signature-button =
    .title = Уклони потпис

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Боја
pdfjs-editor-free-text-size-input = Величина
pdfjs-editor-ink-color-input = Боја
pdfjs-editor-ink-thickness-input = Дебљина
pdfjs-editor-ink-opacity-input = Опацитет
pdfjs-editor-stamp-add-image-button =
    .title = Додај слику
pdfjs-editor-stamp-add-image-button-label = Додај слику
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Дебљина
pdfjs-editor-free-highlight-thickness-title =
    .title = Промени дебљину при означавању других ставки сем текста
pdfjs-editor-add-signature-container =
    .aria-label = Контроле потписа и сачувани потписи
pdfjs-editor-signature-add-signature-button =
    .title = Додај нови потпис
pdfjs-editor-signature-add-signature-button-label = Додај нови потпис
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Сачувани потпис: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Уређивач текста
    .default-content = Почни куцати…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Напомена
        [few] Напомене
       *[other] Напомене
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Затвори бочну површ
    .title = Затвори бочну површ
pdfjs-editor-comments-sidebar-close-button-label = Затвори бочну површ
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Видите нешто вредно пажње? Истакните то и оставите напомену.
pdfjs-editor-comments-sidebar-no-comments-link = Сазнајте више

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Алтернативни текст
pdfjs-editor-alt-text-edit-button =
    .aria-label = Уреди алтернативни текст
pdfjs-editor-alt-text-dialog-label = Одабери опцију
pdfjs-editor-alt-text-dialog-description = Алтернативни текст помаже слепим и слабовидим особама или када се слика не учита.
pdfjs-editor-alt-text-add-description-label = Додај опис
pdfjs-editor-alt-text-add-description-description = Сажмите у 1-2 реченице које описују предмет, окружење или радње.
pdfjs-editor-alt-text-mark-decorative-label = Означи као украсно
pdfjs-editor-alt-text-mark-decorative-description = Ово је за украсне слике, као што су ивице или водени печати.
pdfjs-editor-alt-text-cancel-button = Откажи
pdfjs-editor-alt-text-save-button = Сачувај
pdfjs-editor-alt-text-decorative-tooltip = Означено као украсно
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = На пример: „Младић седа за сто да једе“
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Алтернативни текст

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Горњи леви угао — промени величину
pdfjs-editor-resizer-top-middle =
    .aria-label = Средина горе — промени величину
pdfjs-editor-resizer-top-right =
    .aria-label = Горњи десни угао — промени величину
pdfjs-editor-resizer-middle-right =
    .aria-label = Средина десно — промени величину
pdfjs-editor-resizer-bottom-right =
    .aria-label = Доњи десни угао — промени величину
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Средина доле — промени величину
pdfjs-editor-resizer-bottom-left =
    .aria-label = Доњи леви угао — промени величину
pdfjs-editor-resizer-middle-left =
    .aria-label = Средина лево — промени величину

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Боја означавања
pdfjs-editor-colorpicker-button =
    .title = Промени боју
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Избор боја
pdfjs-editor-colorpicker-yellow =
    .title = Жута
pdfjs-editor-colorpicker-green =
    .title = Зелена
pdfjs-editor-colorpicker-blue =
    .title = Плава
pdfjs-editor-colorpicker-pink =
    .title = Розе
pdfjs-editor-colorpicker-red =
    .title = Црвена

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Прикажи све
pdfjs-editor-highlight-show-all-button =
    .title = Прикажи све

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Уреди алтернативни текст (опис слике)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Додај алтернативни текст (опис слике)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Напиши опис овде…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Кратак опис за слепе и слабовиде људе или када се слика не успе учитати.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Овај алтернативни текст је направљен аутоматски и може бити нетачан.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Сазнајте више
pdfjs-editor-new-alt-text-create-automatically-button-label = Прави алтернативни текст аутоматски
pdfjs-editor-new-alt-text-not-now-button = Не сада
pdfjs-editor-new-alt-text-error-title = Није могуће самостално направити алтернативни текст
pdfjs-editor-new-alt-text-error-description = Напишите сопствени алтернативни текст или покушајте поново касније.
pdfjs-editor-new-alt-text-error-close-button = Затвори
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Преузимање ВИ модела за алтернативни текст ({ $downloadedSize } од { $totalSize } MB)
    .aria-valuetext = Преузимање ВИ модела за алтернативни текст ({ $downloadedSize } од { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Алтернативни текст је додат
pdfjs-editor-new-alt-text-added-button-label = Алтернативни текст је додат
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Недостаје алтернативни текст
pdfjs-editor-new-alt-text-missing-button-label = Недостаје алтернативни текст
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Прегледај алтернативни текст
pdfjs-editor-new-alt-text-to-review-button-label = Прегледај алтернативни текст
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Аутоматски направљено: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Подешавања алтернативног текста слике
pdfjs-image-alt-text-settings-button-label = Подешавања алтернативног текста слике
pdfjs-editor-alt-text-settings-dialog-label = Подешавања алтернативног текста слике
pdfjs-editor-alt-text-settings-automatic-title = Аутоматски алтернативни текст
pdfjs-editor-alt-text-settings-create-model-button-label = Аутоматски прави алтернативни текст
pdfjs-editor-alt-text-settings-create-model-description = Предлаже описе како би се помогло људима који не виде слику или када се слика не учита.
pdfjs-editor-alt-text-settings-editor-title = Уређивач алтернативног текста
pdfjs-editor-alt-text-settings-show-dialog-button-label = Прикажи уређивач алтернативног текста одмах при додавању слике
pdfjs-editor-alt-text-settings-show-dialog-description = Помаже вам да све ваше слике имају алтернативни текст.
pdfjs-editor-alt-text-settings-close-button = Затвори

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Истицање је додато
pdfjs-editor-freetext-added-alert = Текст је додат
pdfjs-editor-ink-added-alert = Цртеж је додат
pdfjs-editor-stamp-added-alert = Слика је додата
pdfjs-editor-signature-added-alert = Потпис је додат

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Истицање је уклоњено
pdfjs-editor-undo-bar-message-freetext = Текст је уклоњен
pdfjs-editor-undo-bar-message-ink = Цртеж је уклоњен
pdfjs-editor-undo-bar-message-stamp = Слика је уклоњена
pdfjs-editor-undo-bar-message-signature = Потпис је уклоњен
pdfjs-editor-undo-bar-message-comment = Коментар је уклоњен
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] Уклоњена је { $count } забелешка
        [few] Уклоњене су { $count } забелешке
       *[other] Уклоњено је { $count } забелешки
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Опозови
pdfjs-editor-undo-bar-undo-button-label = Опозови
pdfjs-editor-undo-bar-close-button =
    .title = Затвори
pdfjs-editor-undo-bar-close-button-label = Затвори

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Овај прозор омогућава кориснику да направи потпис који ће додати у ПДФ документ. Корисник може да уреди име (које такође служи као алтернативни текст) и опционо сачува потпис за поновну употребу.
pdfjs-editor-add-signature-dialog-title = Додај потпис

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Куцај
    .title = Куцај
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Цртај
    .title = Цртај
pdfjs-editor-add-signature-image-button = Слика
    .title = Слика

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Укуцајте свој потпис
    .placeholder = Укуцајте свој потпис
pdfjs-editor-add-signature-draw-placeholder = Нацртајте свој потпис
pdfjs-editor-add-signature-draw-thickness-range-label = Дебљина
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Дебљина цртања: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Превуците датотеку овде за отпремање
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Или изаберите датотеке слика
       *[other] Или потражите датотеке слика
    }

## Controls

pdfjs-editor-add-signature-description-label = Опис (алтернативни текст)
pdfjs-editor-add-signature-description-input =
    .title = Опис (алтернативни текст)
pdfjs-editor-add-signature-description-default-when-drawing = Потпис
pdfjs-editor-add-signature-clear-button-label = Обриши потпис
pdfjs-editor-add-signature-clear-button =
    .title = Обриши потпис
pdfjs-editor-add-signature-save-checkbox = Сачувај потпис
pdfjs-editor-add-signature-save-warning-message = Достигли сте ограничење од 5 сачуваних потписа. Уклоните један да бисте сачували више.
pdfjs-editor-add-signature-image-upload-error-title = Није могуће отпремити слику
pdfjs-editor-add-signature-image-upload-error-description = Проверите своју мрежну везу или покушајте са другом сликом.
pdfjs-editor-add-signature-image-no-data-error-title = Ова слика се не може претворити у потпис
pdfjs-editor-add-signature-image-no-data-error-description = Покушајте да отпремите другу слику.
pdfjs-editor-add-signature-error-close-button = Затвори

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Откажи
pdfjs-editor-add-signature-add-button = Додај
pdfjs-editor-edit-signature-update-button = Ажурирај

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Уреди коментар
pdfjs-editor-edit-comment-popup-button =
    .title = Уреди коментар
pdfjs-editor-delete-comment-popup-button-label = Уклони коментар
pdfjs-editor-delete-comment-popup-button =
    .title = Уклони коментар
pdfjs-show-comment-button =
    .title = Прикажи напомену

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Уреди напомену
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Ажурирај
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Додај напомену
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Додај
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Почните да куцате…
pdfjs-editor-edit-comment-dialog-cancel-button = Откажи

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Додај напомену

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Прикажи/сакриј бочну површ (документ садржи умањене сличице/оквир/прилоге/слојеве)
pdfjs-toggle-views-manager-button1-label = Управљај страницама
pdfjs-views-manager-sidebar =
    .aria-label = Бочна површ
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Промена величине бочне површи
pdfjs-views-manager-view-selector-button =
    .title = Прегледи
pdfjs-views-manager-view-selector-button-label = Прегледи
pdfjs-views-manager-pages-title = Странице
pdfjs-views-manager-outlines-title1 = Контура документа
    .title = Контура документа (двоклик за ширење/скупљање свих ставки)
pdfjs-views-manager-attachments-title = Прилози
pdfjs-views-manager-layers-title1 = Слојеви
    .title = Слојеви (двоклик за враћање свих слојева у подразумевано стање)
pdfjs-views-manager-pages-option-label = Странице
pdfjs-views-manager-outlines-option-label = Контура документа
pdfjs-views-manager-attachments-option-label = Прилози
pdfjs-views-manager-layers-option-label = Слојеви
pdfjs-views-manager-add-file-button =
    .title = Додај датотеку
pdfjs-views-manager-add-file-button-label = Додај датотеку
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] Изабрана је { $count } страница
        [few] Изабране су { $count } странице
       *[other] Изабрано је { $count } страница
    }
pdfjs-views-manager-pages-status-none-action-label = Изаберите странице
pdfjs-views-manager-pages-status-action-button-label = Управљај
pdfjs-views-manager-pages-status-copy-button-label = Умножи
pdfjs-views-manager-pages-status-cut-button-label = Исеци
pdfjs-views-manager-pages-status-delete-button-label = Обриши
pdfjs-views-manager-pages-status-export-selected-button-label = Извези изабрано…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] Исечена је 1 страница
        [few] Исечене су { $count } странице
       *[other] Исечено је { $count } страница
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] Умножена је 1 страница
        [few] Умножене су { $count } странице
       *[other] Умножено је { $count } страница
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] Обрисана је 1 страница
        [few] Обрисане су { $count } странице
       *[other] Обрисано је { $count } страница
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Припремам датотеку…
pdfjs-views-manager-pages-status-waiting-uploading-label = Отпремам датотеку…
pdfjs-views-manager-status-warning-cut-label = Не могу да исечем. Освежите страницу и покушајте поново.
pdfjs-views-manager-status-warning-copy-label = Не могу да умножим. Освежите страницу и покушајте поново.
pdfjs-views-manager-status-warning-delete-label = Не могу да обришем. Освежите страницу и покушајте поново.
pdfjs-views-manager-status-warning-save-label = Не могу да сачувам. Освежите страницу и покушајте поново.
pdfjs-views-manager-status-undo-button-label = Опозови
pdfjs-views-manager-status-done-button-label = Готово
pdfjs-views-manager-status-close-button =
    .title = Затвори
pdfjs-views-manager-status-close-button-label = Затвори
pdfjs-views-manager-paste-button-label = Убаци
pdfjs-views-manager-paste-button-before =
    .title = Убаци пре прве странице
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Убаци после странице { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = НОВО
pdfjs-views-manager-waiting-for-file = Отпремам датотеку…
pdfjs-toggle-views-manager-button1 =
    .title = Управљај страницама

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Својства дигиталног потписа
    .title = Својства дигиталног потписа
pdfjs-digital-signature-properties-button-label = Својства дигиталног потписа

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Документ је потписан исправним дигиталним потписом
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Документ је потписан, али { $count } дигитални потпис није могао да се потврди
        [few] Документ је потписан, али { $count } дигитална потписа нису могли да се потврде
       *[other] Документ је потписан, али { $count } дигиталних потписа није могло да се потврде
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Документ је потписан са { $count } сертификатом који није поуздан
        [few] Документ је потписан са { $count } сертификата који нису поуздани
       *[other] Документ је потписан са { $count } сертификата који нису поуздани
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Документ је потписан са { $count } истеклим сертификатом
        [few] Документ је потписан са { $count } истекла сертификата
       *[other] Документ је потписан са { $count } истеклих сертификата
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] Документ има { $count } неважећи дигитални потпис
        [few] Документ има { $count } неважећа дигитална потписа
       *[other] Документ има { $count } неважећих дигиталних потписа
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Документ је потписан са { $count } опозваним сертификатом
        [few] Документ је потписан са { $count } опозвана сертификата
       *[other] Документ је потписан са { $count } опозваних сертификата
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Статус: потврђен потпис
pdfjs-digital-signature-properties-status-invalid = Статус: неважећи потпис
pdfjs-digital-signature-properties-status-unknown = Статус: није могуће потврдити (неподржано)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Сертификат: поуздан ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Сертификат: недоступан
pdfjs-digital-signature-properties-certificate-untrusted = Сертификат: неповерљив
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Сертификат: непознат издавач ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Сертификат: самопотписан ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Сертификат: неповерљив издавач ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Сертификат: истекао
pdfjs-digital-signature-properties-certificate-expired-with-date = Сертификат: истекао ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Сертификат: опозван

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Уклони сачувани потпис
pdfjs-editor-delete-signature-button-label1 = Уклони сачувани потпис

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Уреди опис

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Уреди опис
