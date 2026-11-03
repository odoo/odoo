# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Алдыңғы парақ
pdfjs-previous-button-label = Алдыңғысы
pdfjs-next-button =
    .title = Келесі парақ
pdfjs-next-button-label = Келесі
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Парақ
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = { $pagesCount } ішінен
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = (парақ { $pageNumber }, { $pagesCount } ішінен)
pdfjs-zoom-out-button =
    .title = Кішірейту
pdfjs-zoom-out-button-label = Кішірейту
pdfjs-zoom-in-button =
    .title = Үлкейту
pdfjs-zoom-in-button-label = Үлкейту
pdfjs-zoom-select =
    .title = Масштаб
pdfjs-presentation-mode-button =
    .title = Презентация режиміне ауысу
pdfjs-presentation-mode-button-label = Презентация режимі
pdfjs-open-file-button =
    .title = Файлды ашу
pdfjs-open-file-button-label = Ашу
pdfjs-print-button =
    .title = Баспаға шығару
pdfjs-print-button-label = Баспаға шығару
pdfjs-save-button =
    .title = Сақтау
pdfjs-save-button-label = Сақтау
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Жүктеп алу
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Жүктеп алу
pdfjs-bookmark-button =
    .title = Ағымдағы бет (Ағымдағы беттен URL адресін көру)
pdfjs-bookmark-button-label = Ағымдағы бет

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Құралдар
pdfjs-tools-button-label = Құралдар
pdfjs-first-page-button =
    .title = Алғашқы параққа өту
pdfjs-first-page-button-label = Алғашқы параққа өту
pdfjs-last-page-button =
    .title = Соңғы параққа өту
pdfjs-last-page-button-label = Соңғы параққа өту
pdfjs-page-rotate-cw-button =
    .title = Сағат тілі бағытымен айналдыру
pdfjs-page-rotate-cw-button-label = Сағат тілі бағытымен бұру
pdfjs-page-rotate-ccw-button =
    .title = Сағат тілі бағытына қарсы бұру
pdfjs-page-rotate-ccw-button-label = Сағат тілі бағытына қарсы бұру
pdfjs-cursor-text-select-tool-button =
    .title = Мәтінді таңдау құралын іске қосу
pdfjs-cursor-text-select-tool-button-label = Мәтінді таңдау құралы
pdfjs-cursor-hand-tool-button =
    .title = Қол құралын іске қосу
pdfjs-cursor-hand-tool-button-label = Қол құралы
pdfjs-scroll-page-button =
    .title = Беттерді айналдыруды пайдалану
pdfjs-scroll-page-button-label = Беттерді айналдыру
pdfjs-scroll-vertical-button =
    .title = Вертикалды айналдыруды қолдану
pdfjs-scroll-vertical-button-label = Вертикалды айналдыру
pdfjs-scroll-horizontal-button =
    .title = Горизонталды айналдыруды қолдану
pdfjs-scroll-horizontal-button-label = Горизонталды айналдыру
pdfjs-scroll-wrapped-button =
    .title = Масштабталатын айналдыруды қолдану
pdfjs-scroll-wrapped-button-label = Масштабталатын айналдыру
pdfjs-spread-none-button =
    .title = Жазық беттер режимін қолданбау
pdfjs-spread-none-button-label = Жазық беттер режимсіз
pdfjs-spread-odd-button =
    .title = Жазық беттер тақ нөмірлі беттерден басталады
pdfjs-spread-odd-button-label = Тақ нөмірлі беттер сол жақтан
pdfjs-spread-even-button =
    .title = Жазық беттер жұп нөмірлі беттерден басталады
pdfjs-spread-even-button-label = Жұп нөмірлі беттер сол жақтан

## Document properties dialog

pdfjs-document-properties-button =
    .title = Құжат қасиеттері…
pdfjs-document-properties-button-label = Құжат қасиеттері…
pdfjs-document-properties-file-name = Файл аты:
pdfjs-document-properties-file-size = Файл өлшемі:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } КБ ({ $b } байт)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } МБ ({ $b } байт)
pdfjs-document-properties-title = Тақырыбы:
pdfjs-document-properties-author = Авторы:
pdfjs-document-properties-subject = Тақырыбы:
pdfjs-document-properties-keywords = Кілт сөздер:
pdfjs-document-properties-creation-date = Жасалған күні:
pdfjs-document-properties-modification-date = Түзету күні:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Жасаған:
pdfjs-document-properties-producer = PDF өндірген:
pdfjs-document-properties-version = PDF нұсқасы:
pdfjs-document-properties-page-count = Беттер саны:
pdfjs-document-properties-page-size = Бет өлшемі:
pdfjs-document-properties-page-size-unit-inches = дюйм
pdfjs-document-properties-page-size-unit-millimeters = мм
pdfjs-document-properties-page-size-orientation-portrait = тік
pdfjs-document-properties-page-size-orientation-landscape = жатық
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
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name }, { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = Жылдам Web көрінісі:
pdfjs-document-properties-linearized-yes = Иә
pdfjs-document-properties-linearized-no = Жоқ
pdfjs-document-properties-close-button = Жабу
pdfjs-digital-signature-properties-view-certificate = Сертификатты қарау
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Себебі: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Күн мен уақыт белгісі: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Ішкі қолтаңба ({ $count })
       *[other] Ішкі қолтаңбалар ({ $count })
    }

## Print

pdfjs-print-progress-message = Құжатты баспаға шығару үшін дайындау…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Бас тарту
pdfjs-printing-not-supported = Ескерту: Баспаға шығаруды бұл браузер толығымен қолдамайды.
pdfjs-printing-not-ready = Ескерту: Баспаға шығару үшін, бұл PDF толығымен жүктеліп алынбады.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Құрылымның ағымдағы элементін табу
pdfjs-current-outline-item-button-label = Құрылымның ағымдағы элементі
pdfjs-findbar-button =
    .title = Құжаттан табу
pdfjs-findbar-button-label = Табу
pdfjs-additional-layers = Қосымша қабаттар

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = { $page } парағы үшін кіші көрінісі
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = { $page } бетін таңдау
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Бет { $page }/{ $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Құжаттан табу…
    .title = Табу
pdfjs-find-previous-button =
    .title = Осы сөздердің мәтіннен алдыңғы кездесуін табу
pdfjs-find-previous-button-label = Алдыңғысы
pdfjs-find-next-button =
    .title = Осы сөздердің мәтіннен келесі кездесуін табу
pdfjs-find-next-button-label = Келесі
pdfjs-find-highlight-checkbox = Барлығын түспен ерекшелеу
pdfjs-find-match-case-checkbox-label = Регистрді ескеру
pdfjs-find-match-diacritics-checkbox-label = Диакритиканы ескеру
pdfjs-find-entire-word-checkbox-label = Сөздер толығымен
pdfjs-find-reached-top = Құжаттың басына жеттік, соңынан бастап жалғастырамыз
pdfjs-find-reached-bottom = Құжаттың соңына жеттік, басынан бастап жалғастырамыз
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } сәйкестік, барлығы { $total }
       *[other] { $current } сәйкестік, барлығы { $total }
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] { $limit } сәйкестіктен көп
       *[other] { $limit } сәйкестіктен көп
    }
pdfjs-find-not-found = Сөз(дер) табылмады

## Predefined zoom values

pdfjs-page-scale-width = Парақ ені
pdfjs-page-scale-fit = Парақты сыйдыру
pdfjs-page-scale-auto = Автомасштабтау
pdfjs-page-scale-actual = Нақты өлшемі
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Бет { $page }

## Loading indicator messages

pdfjs-loading-error = PDF жүктеу кезінде қате кетті.
pdfjs-invalid-file-error = Зақымдалған немесе қате PDF файл.
pdfjs-missing-file-error = PDF файлы жоқ.
pdfjs-unexpected-response-error = Сервердің күтпеген жауабы.
pdfjs-rendering-error = Парақты өңдеу кезінде қате кетті.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } аңдатпасы]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Бұл PDF файлын ашу үшін парольді енгізіңіз.
pdfjs-password-invalid = Пароль дұрыс емес. Қайталап көріңіз.
pdfjs-password-ok-button = ОК
pdfjs-password-cancel-button = Бас тарту
pdfjs-web-fonts-disabled = Веб қаріптері сөндірілген: құрамына енгізілген PDF қаріптерін қолдану мүмкін емес.

## Editing

pdfjs-editor-free-text-button =
    .title = Мәтін
pdfjs-editor-color-picker-free-text-input =
    .title = Мәтін түсін өзгерту
pdfjs-editor-free-text-button-label = Мәтін
pdfjs-editor-ink-button =
    .title = Сурет салу
pdfjs-editor-color-picker-ink-input =
    .title = Сызба түсін өзгерту
pdfjs-editor-ink-button-label = Сурет салу
pdfjs-editor-stamp-button =
    .title = Суреттерді қосу немесе түзету
pdfjs-editor-stamp-button-label = Суреттерді қосу немесе түзету
pdfjs-editor-highlight-button =
    .title = Ерекшелеу
pdfjs-editor-highlight-button-label = Ерекшелеу
pdfjs-highlight-floating-button1 =
    .aria-label = Ерекшелеу
    .title = Ерекшелеу
pdfjs-highlight-floating-button-label = Ерекшелеу
pdfjs-comment-floating-button =
    .aria-label = Түсіндірме
    .title = Түсіндірме
pdfjs-comment-floating-button-label = Түсіндірме
pdfjs-editor-comment-button =
    .aria-label = Түсіндірме
    .title = Түсіндірме
pdfjs-editor-comment-button-label = Түсіндірме
pdfjs-editor-signature-button =
    .title = Қолтаңбаны қосу
pdfjs-editor-signature-button-label = Қолтаңбаны қосу

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Ерекшелеу түзеткіші
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Сурет салу түзеткіші
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Қолтаңба түзеткіші: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Сурет редакторы

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Сызбаны өшіру
pdfjs-editor-remove-freetext-button =
    .title = Мәтінді өшіру
pdfjs-editor-remove-stamp-button =
    .title = Суретті өшіру
pdfjs-editor-remove-highlight-button =
    .title = Түспен ерекшелеуді өшіру
pdfjs-editor-remove-signature-button =
    .title = Қолтаңбаны өшіру

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Түс
pdfjs-editor-free-text-size-input = Өлшемі
pdfjs-editor-ink-color-input = Түс
pdfjs-editor-ink-thickness-input = Қалыңдығы
pdfjs-editor-ink-opacity-input = Мөлдірсіздігі
pdfjs-editor-stamp-add-image-button =
    .title = Суретті қосу
pdfjs-editor-stamp-add-image-button-label = Суретті қосу
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Қалыңдығы
pdfjs-editor-free-highlight-thickness-title =
    .title = Мәтіннен басқа элементтерді ерекшелеу кезінде қалыңдықты өзгерту
pdfjs-editor-add-signature-container =
    .aria-label = Қолтаңбаларды басқару және сақталған қолтаңбалар
pdfjs-editor-signature-add-signature-button =
    .title = Жаңа қолтаңбаны қосу
pdfjs-editor-signature-add-signature-button-label = Жаңа қолтаңбаны қосу
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Сақталған қолтаңба: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Мәтін түзеткіші
    .default-content = Теріп бастаңыз…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Түсіндірмелер
       *[other] Түсіндірмелер
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Бүйір панелін жабу
    .title = Бүйір панелін жабу
pdfjs-editor-comments-sidebar-close-button-label = Бүйір панелін жабу
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Назар аударарлық бірдеңе көрдіңіз бе? Оны ерекшелеп, түсіндірме қалдырыңыз.
pdfjs-editor-comments-sidebar-no-comments-link = Көбірек білу

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Балама мәтін
pdfjs-editor-alt-text-edit-button =
    .aria-label = Балама мәтінді өңдеу
pdfjs-editor-alt-text-dialog-label = Опцияны таңдау
pdfjs-editor-alt-text-dialog-description = Балама мәтін адамдар суретті көре алмағанда немесе ол жүктелмегенде көмектеседі.
pdfjs-editor-alt-text-add-description-label = Сипаттаманы қосу
pdfjs-editor-alt-text-add-description-description = Тақырыпты, баптауды немесе әрекетті сипаттайтын 1-2 сөйлемді қолдануға тырысыңыз.
pdfjs-editor-alt-text-mark-decorative-label = Декоративті деп белгілеу
pdfjs-editor-alt-text-mark-decorative-description = Бұл жиектер немесе су белгілері сияқты оюлық суреттер үшін пайдаланылады.
pdfjs-editor-alt-text-cancel-button = Бас тарту
pdfjs-editor-alt-text-save-button = Сақтау
pdfjs-editor-alt-text-decorative-tooltip = Декоративті деп белгіленген
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Мысалы, "Жас жігіт тамақ ішу үшін үстел басына отырады"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Балама мәтін

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Жоғарғы сол жақ бұрыш — өлшемін өзгерту
pdfjs-editor-resizer-top-middle =
    .aria-label = Жоғарғы ортасы — өлшемін өзгерту
pdfjs-editor-resizer-top-right =
    .aria-label = Жоғарғы оң жақ бұрыш — өлшемін өзгерту
pdfjs-editor-resizer-middle-right =
    .aria-label = Ортаңғы оң жақ — өлшемін өзгерту
pdfjs-editor-resizer-bottom-right =
    .aria-label = Төменгі оң жақ бұрыш — өлшемін өзгерту
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Төменгі ортасы — өлшемін өзгерту
pdfjs-editor-resizer-bottom-left =
    .aria-label = Төменгі сол жақ бұрыш — өлшемін өзгерту
pdfjs-editor-resizer-middle-left =
    .aria-label = Ортаңғы сол жақ — өлшемін өзгерту

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Ерекшелеу түсі
pdfjs-editor-colorpicker-button =
    .title = Түсті өзгерту
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Түс таңдаулары
pdfjs-editor-colorpicker-yellow =
    .title = Сары
pdfjs-editor-colorpicker-green =
    .title = Жасыл
pdfjs-editor-colorpicker-blue =
    .title = Көк
pdfjs-editor-colorpicker-pink =
    .title = Қызғылт
pdfjs-editor-colorpicker-red =
    .title = Қызыл

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Барлығын көрсету
pdfjs-editor-highlight-show-all-button =
    .title = Барлығын көрсету

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Балама мәтінді өңдеу (сурет сипаттамасы)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Балама мәтінді қосу (сурет сипаттамасы)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Сипаттамаңызды осында жазыңыз…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Суретті көре алмайтын адамдар үшін немесе сурет жүктелмеген кезіне арналған қысқаша сипаттама.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Бұл балама мәтін автоматты түрде жасалды және дәлсіз болуы мүмкін.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Көбірек білу
pdfjs-editor-new-alt-text-create-automatically-button-label = Балама мәтінді автоматты түрде жасау
pdfjs-editor-new-alt-text-not-now-button = Қазір емес
pdfjs-editor-new-alt-text-error-title = Балама мәтінді автоматты түрде жасау мүмкін болмады
pdfjs-editor-new-alt-text-error-description = Өзіңіздің балама мәтініңізді жазыңыз немесе кейінірек қайталап көріңіз.
pdfjs-editor-new-alt-text-error-close-button = Жабу
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Балама мәтін үшін ЖИ моделі жүктеп алынуда ({ $downloadedSize }/{ $totalSize } МБ)
    .aria-valuetext = Балама мәтін үшін ЖИ моделі жүктеп алынуда ({ $downloadedSize }/{ $totalSize } МБ)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Балама мәтін қосылды
pdfjs-editor-new-alt-text-added-button-label = Балама мәтін қосылды
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Балама мәтін жоқ
pdfjs-editor-new-alt-text-missing-button-label = Балама мәтін жоқ
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Балама мәтінге пікір қалдыру
pdfjs-editor-new-alt-text-to-review-button-label = Балама мәтінге пікір қалдыру
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Автоматты түрде жасалды: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Суреттің балама мәтінінің баптаулары
pdfjs-image-alt-text-settings-button-label = Суреттің балама мәтінінің баптаулары
pdfjs-editor-alt-text-settings-dialog-label = Суреттің балама мәтінінің баптаулары
pdfjs-editor-alt-text-settings-automatic-title = Автоматты балама мәтін
pdfjs-editor-alt-text-settings-create-model-button-label = Балама мәтінді автоматты түрде жасау
pdfjs-editor-alt-text-settings-create-model-description = Суретті көре алмайтын адамдар үшін немесе сурет жүктелмеген кезіне арналған сипаттамаларды ұсынады.
pdfjs-editor-alt-text-settings-editor-title = Баламалы мәтін редакторы
pdfjs-editor-alt-text-settings-show-dialog-button-label = Суретті қосқанда балама мәтін редакторын бірден көрсету
pdfjs-editor-alt-text-settings-show-dialog-description = Барлық суреттерде балама мәтін бар екеніне көз жеткізуге көмектеседі.
pdfjs-editor-alt-text-settings-close-button = Жабу

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Ерекшелеу қосылды
pdfjs-editor-freetext-added-alert = Мәтін қосылды
pdfjs-editor-ink-added-alert = Сызба қосылды
pdfjs-editor-stamp-added-alert = Сурет қосылды
pdfjs-editor-signature-added-alert = Қолтаңба қосылды

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Ерекшелеу өшірілді
pdfjs-editor-undo-bar-message-freetext = Мәтін өшірілді
pdfjs-editor-undo-bar-message-ink = Сызба өшірілді
pdfjs-editor-undo-bar-message-stamp = Сурет өшірілді
pdfjs-editor-undo-bar-message-signature = Қолтаңба өшірілді
pdfjs-editor-undo-bar-message-comment = Түсіндірме өшірілді
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } анимация өшірілді
       *[other] { $count } анимация өшірілді
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Болдырмау
pdfjs-editor-undo-bar-undo-button-label = Болдырмау
pdfjs-editor-undo-bar-close-button =
    .title = Жабу
pdfjs-editor-undo-bar-close-button-label = Жабу

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Бұл модальді терезе пайдаланушыға PDF құжатына қосу үшін қолтаңба жасауға мүмкіндік береді. Пайдаланушы өз атын (ол балама мәтін ретінде де қолданылады) өңдей алады және қолтаңбаны кейін қайта пайдалану үшін сақтай алады.
pdfjs-editor-add-signature-dialog-title = Қолтаңба қосу

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Енгізу
    .title = Енгізу
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Сурет салу
    .title = Сурет салу
pdfjs-editor-add-signature-image-button = Сурет
    .title = Сурет

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Қолтаңбаңызды теріңіз
    .placeholder = Қолтаңбаңызды теріңіз
pdfjs-editor-add-signature-draw-placeholder = Қолтаңбаңызды сызыңыз
pdfjs-editor-add-signature-draw-thickness-range-label = Қалыңдығы
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Сызба қалыңздығы: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Жүктеп жіберу үшін файлды осы жерге сүйреңіз
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Немесе сурет файлдарын таңдаңыз
       *[other] Немесе сурет файлдарын шолыңыз
    }

## Controls

pdfjs-editor-add-signature-description-label = Сипаттама (балама мәтін)
pdfjs-editor-add-signature-description-input =
    .title = Сипаттама (балама мәтін)
pdfjs-editor-add-signature-description-default-when-drawing = Қолтаңба
pdfjs-editor-add-signature-clear-button-label = Қолтаңбаны өшіру
pdfjs-editor-add-signature-clear-button =
    .title = Қолтаңбаны өшіру
pdfjs-editor-add-signature-save-checkbox = Қолтаңбаны сақтау
pdfjs-editor-add-signature-save-warning-message = Сақталған 5 қолтаңбаның шегіне жеттіңіз. Көбірек сақтау үшін біреуін алып тастаңыз.
pdfjs-editor-add-signature-image-upload-error-title = Суретті жүктеп жіберу мүмкін емес.
pdfjs-editor-add-signature-image-upload-error-description = Желі байланысын тексеріңіз немесе басқа бейнені қолданып көріңіз.
pdfjs-editor-add-signature-image-no-data-error-title = Бұл суретті қолтаңбаға түрлендіру мүмкін емес
pdfjs-editor-add-signature-image-no-data-error-description = Басқа суретті жүктеп салып көріңіз.
pdfjs-editor-add-signature-error-close-button = Жабу

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Бас тарту
pdfjs-editor-add-signature-add-button = Қосу
pdfjs-editor-edit-signature-update-button = Жаңарту

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Түсіндірмені түзету
pdfjs-editor-edit-comment-popup-button =
    .title = Түсіндірмені түзету
pdfjs-editor-delete-comment-popup-button-label = Түсіндірмені өшіру
pdfjs-editor-delete-comment-popup-button =
    .title = Түсіндірмені өшіру
pdfjs-show-comment-button =
    .title = Түсіндірмені көрсету

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Түсіндірмені түзету
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Жаңарту
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Түсіндірмені қосу
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Қосу
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Теріп бастаңыз…
pdfjs-editor-edit-comment-dialog-cancel-button = Бас тарту

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Пікір қосу

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Бүйір панелін көрсету/жасыру (құжатта кіші көріністер/құрылымы/салынымдар/қабаттар бар)
pdfjs-toggle-views-manager-button1-label = Беттерді басқару
pdfjs-views-manager-sidebar =
    .aria-label = Бүйір панелі
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Бүйір панелінің өлшемін өзгертуші
pdfjs-views-manager-view-selector-button =
    .title = Көріністер
pdfjs-views-manager-view-selector-button-label = Көріністер
pdfjs-views-manager-pages-title = Беттер
pdfjs-views-manager-outlines-title1 = Құжат құрылымы
    .title = Құжат құрылымы (барлық нәрселерді жаю/жию үшін қос шерту)
pdfjs-views-manager-attachments-title = Салынымдар
pdfjs-views-manager-layers-title1 = Қабаттар
    .title = Қабаттар (барлық нәрселерді жаю/жию үшін қос шерту)
pdfjs-views-manager-pages-option-label = Беттер
pdfjs-views-manager-outlines-option-label = Құжаттың құрылымы
pdfjs-views-manager-attachments-option-label = Салынымдар
pdfjs-views-manager-layers-option-label = Қабаттар
pdfjs-views-manager-add-file-button =
    .title = Файлды қосу
pdfjs-views-manager-add-file-button-label = Файлды қосу
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } таңдалды
       *[other] { $count } таңдалды
    }
pdfjs-views-manager-pages-status-none-action-label = Беттерді таңдау
pdfjs-views-manager-pages-status-action-button-label = Басқару
pdfjs-views-manager-pages-status-copy-button-label = Көшіріп алу
pdfjs-views-manager-pages-status-cut-button-label = Қиып алу
pdfjs-views-manager-pages-status-delete-button-label = Өшіру
pdfjs-views-manager-pages-status-export-selected-button-label = Таңдалғанды экспорттау…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 бет қиып алынды
       *[other] { $count } қиып алынды
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 бет көшірілді
       *[other] { $count } бет көшірілді
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 бет өшірілді
       *[other] { $count } бет өшірілді
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Файлыңыз дайындалуда…
pdfjs-views-manager-pages-status-waiting-uploading-label = Файл жүктеп салынуда…
pdfjs-views-manager-status-warning-cut-label = Қиып алу мүмкін болмады. Бетті жаңартып, қайталап көріңіз.
pdfjs-views-manager-status-warning-copy-label = Көшіру мүмкін болмады. Бетті жаңартып, қайталап көріңіз.
pdfjs-views-manager-status-warning-delete-label = Өшіру мүмкін болмады. Бетті жаңартып, қайталап көріңіз.
pdfjs-views-manager-status-warning-save-label = Сақтау мүмкін болмады. Бетті жаңартып, қайталап көріңіз.
pdfjs-views-manager-status-undo-button-label = Болдырмау
pdfjs-views-manager-status-done-button-label = Дайын
pdfjs-views-manager-status-close-button =
    .title = Жабу
pdfjs-views-manager-status-close-button-label = Жабу
pdfjs-views-manager-paste-button-label = Кірістіру
pdfjs-views-manager-paste-button-before =
    .title = Бірінші беттің алдына кірістіру
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = { $page } бетінен кейін кірістіру
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = ЖАҢА
pdfjs-views-manager-waiting-for-file = Файл жүктеп салынуда…
pdfjs-toggle-views-manager-button1 =
    .title = Беттерді басқару

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Цифрлық қолтаңба қасиеттері
    .title = Цифрлық қолтаңба қасиеттері
pdfjs-digital-signature-properties-button-label = Цифрлық қолтаңба қасиеттері

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Құжатқа жарамды цифрлық қолтаңбамен қол қойылған
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Құжатқа қол қойылған, бірақ { $count } цифрлық қолтаңбаны тексеру мүмкін болмады
       *[other] Құжатқа қол қойылған, бірақ { $count } цифрлық қолтаңбаны тексеру мүмкін болмады
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Құжатқа сенімсіз { $count } сертификатпен қол қойылған
       *[other] Құжатқа сенімсіз { $count } сертификатпен қол қойылған
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Құжатқа мерзімі өткен { $count } сертификатпен қол қойылған
       *[other] Құжатқа мерзімі өткен { $count } сертификатпен қол қойылған
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] Құжатта { $count } жарамсыз цифрлық қолтаңба бар
       *[other] Құжатта { $count } жарамсыз цифрлық қолтаңба бар
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Құжатқа қайтарылған { $count } сертификатпен қол қойылған
       *[other] Құжатқа қайтарылған { $count } сертификатпен қол қойылған
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Қалып-күй: Қолтаңба тексерілді
pdfjs-digital-signature-properties-status-invalid = Қалып-күй: Қолтаңба жарамсыз
pdfjs-digital-signature-properties-status-unknown = Қалып-күй: Тексеру мүмкін емес (қолдау көрсетілмейді)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Сертификат: Сенімді ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Сертификат: Қолжетімсіз
pdfjs-digital-signature-properties-certificate-untrusted = Сертификат: Сенімсіз
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Сертификат: Белгісіз шығарушы ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Сертификат: Өздігінен қол қойылған ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Сертификат: Сенімсіз шығарушы ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Сертификат: Мерзімі өткен
pdfjs-digital-signature-properties-certificate-expired-with-date = Сертификат: Мерзімі өткен ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Сертификат: Қайтарылған

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Сақталған қолтаңбаны өшіру
pdfjs-editor-delete-signature-button-label1 = Сақталған қолтаңбаны өшіру

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Сипаттаманы түзету

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Сипаттаманы түзету
