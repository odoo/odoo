# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Попередня сторінка
pdfjs-previous-button-label = Попередня
pdfjs-next-button =
    .title = Наступна сторінка
pdfjs-next-button-label = Наступна
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Сторінка
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = із { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } із { $pagesCount })
pdfjs-zoom-out-button =
    .title = Зменшити
pdfjs-zoom-out-button-label = Зменшити
pdfjs-zoom-in-button =
    .title = Збільшити
pdfjs-zoom-in-button-label = Збільшити
pdfjs-zoom-select =
    .title = Масштаб
pdfjs-presentation-mode-button =
    .title = Перейти в режим презентації
pdfjs-presentation-mode-button-label = Режим презентації
pdfjs-open-file-button =
    .title = Відкрити файл
pdfjs-open-file-button-label = Відкрити
pdfjs-print-button =
    .title = Друк
pdfjs-print-button-label = Друк
pdfjs-save-button =
    .title = Зберегти
pdfjs-save-button-label = Зберегти
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Завантажити
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Завантажити
pdfjs-bookmark-button =
    .title = Поточна сторінка (перегляд URL-адреси з поточної сторінки)
pdfjs-bookmark-button-label = Поточна сторінка

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Інструменти
pdfjs-tools-button-label = Інструменти
pdfjs-first-page-button =
    .title = На першу сторінку
pdfjs-first-page-button-label = На першу сторінку
pdfjs-last-page-button =
    .title = На останню сторінку
pdfjs-last-page-button-label = На останню сторінку
pdfjs-page-rotate-cw-button =
    .title = Повернути за годинниковою стрілкою
pdfjs-page-rotate-cw-button-label = Повернути за годинниковою стрілкою
pdfjs-page-rotate-ccw-button =
    .title = Повернути проти годинникової стрілки
pdfjs-page-rotate-ccw-button-label = Повернути проти годинникової стрілки
pdfjs-cursor-text-select-tool-button =
    .title = Увімкнути інструмент вибору тексту
pdfjs-cursor-text-select-tool-button-label = Інструмент вибору тексту
pdfjs-cursor-hand-tool-button =
    .title = Увімкнути інструмент "Рука"
pdfjs-cursor-hand-tool-button-label = Інструмент "Рука"
pdfjs-scroll-page-button =
    .title = Використовувати прокручування сторінки
pdfjs-scroll-page-button-label = Прокручування сторінки
pdfjs-scroll-vertical-button =
    .title = Використовувати вертикальне прокручування
pdfjs-scroll-vertical-button-label = Вертикальне прокручування
pdfjs-scroll-horizontal-button =
    .title = Використовувати горизонтальне прокручування
pdfjs-scroll-horizontal-button-label = Горизонтальне прокручування
pdfjs-scroll-wrapped-button =
    .title = Використовувати масштабоване прокручування
pdfjs-scroll-wrapped-button-label = Масштабоване прокручування
pdfjs-spread-none-button =
    .title = Не використовувати розгорнуті сторінки
pdfjs-spread-none-button-label = Без розгорнутих сторінок
pdfjs-spread-odd-button =
    .title = Розгорнуті сторінки починаються з непарних номерів
pdfjs-spread-odd-button-label = Непарні сторінки зліва
pdfjs-spread-even-button =
    .title = Розгорнуті сторінки починаються з парних номерів
pdfjs-spread-even-button-label = Парні сторінки зліва

## Document properties dialog

pdfjs-document-properties-button =
    .title = Властивості документа…
pdfjs-document-properties-button-label = Властивості документа…
pdfjs-document-properties-file-name = Назва файлу:
pdfjs-document-properties-file-size = Розмір файлу:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } кБ ({ $b } байтів)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } МБ ({ $b } байтів)
pdfjs-document-properties-title = Заголовок:
pdfjs-document-properties-author = Автор:
pdfjs-document-properties-subject = Тема:
pdfjs-document-properties-keywords = Ключові слова:
pdfjs-document-properties-creation-date = Дата створення:
pdfjs-document-properties-modification-date = Дата зміни:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Створено:
pdfjs-document-properties-producer = Виробник PDF:
pdfjs-document-properties-version = Версія PDF:
pdfjs-document-properties-page-count = Кількість сторінок:
pdfjs-document-properties-page-size = Розмір сторінки:
pdfjs-document-properties-page-size-unit-inches = дюймів
pdfjs-document-properties-page-size-unit-millimeters = мм
pdfjs-document-properties-page-size-orientation-portrait = книжкова
pdfjs-document-properties-page-size-orientation-landscape = альбомна
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
pdfjs-document-properties-linearized = Швидкий перегляд в Інтернеті:
pdfjs-document-properties-linearized-yes = Так
pdfjs-document-properties-linearized-no = Ні
pdfjs-document-properties-close-button = Закрити

## Print

pdfjs-print-progress-message = Підготовка документу до друку…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Скасувати
pdfjs-printing-not-supported = Попередження: Цей браузер не повністю підтримує друк.
pdfjs-printing-not-ready = Попередження: PDF не повністю завантажений для друку.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Знайти поточний елемент змісту
pdfjs-current-outline-item-button-label = Поточний елемент змісту
pdfjs-findbar-button =
    .title = Знайти в документі
pdfjs-findbar-button-label = Знайти
pdfjs-additional-layers = Додаткові шари

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Ескіз сторінки { $page }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Знайти в документі…
    .title = Знайти
pdfjs-find-previous-button =
    .title = Знайти попереднє входження фрази
pdfjs-find-previous-button-label = Попереднє
pdfjs-find-next-button =
    .title = Знайти наступне входження фрази
pdfjs-find-next-button-label = Наступне
pdfjs-find-highlight-checkbox = Підсвітити все
pdfjs-find-match-case-checkbox-label = З урахуванням регістру
pdfjs-find-match-diacritics-checkbox-label = Відповідність діакритичних знаків
pdfjs-find-entire-word-checkbox-label = Цілі слова
pdfjs-find-reached-top = Досягнуто початку документу, продовжено з кінця
pdfjs-find-reached-bottom = Досягнуто кінця документу, продовжено з початку
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } збіг з { $total }
        [few] { $current } збіги з { $total }
       *[many] { $current } збігів з { $total }
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Понад { $limit } збіг
        [few] Понад { $limit } збіги
       *[many] Понад { $limit } збігів
    }
pdfjs-find-not-found = Фразу не знайдено

## Predefined zoom values

pdfjs-page-scale-width = За шириною
pdfjs-page-scale-fit = Вмістити
pdfjs-page-scale-auto = Автомасштаб
pdfjs-page-scale-actual = Дійсний розмір
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Сторінка { $page }

## Loading indicator messages

pdfjs-loading-error = Під час завантаження PDF сталася помилка.
pdfjs-invalid-file-error = Недійсний або пошкоджений PDF-файл.
pdfjs-missing-file-error = Відсутній PDF-файл.
pdfjs-unexpected-response-error = Неочікувана відповідь сервера.
pdfjs-rendering-error = Під час виведення сторінки сталася помилка.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type }-анотація]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Введіть пароль для відкриття цього PDF-файлу.
pdfjs-password-invalid = Неправильний пароль. Спробуйте ще раз.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Скасувати
pdfjs-web-fonts-disabled = Вебшрифти вимкнено: неможливо використати вбудовані у PDF шрифти.

## Editing

pdfjs-editor-free-text-button =
    .title = Текст
pdfjs-editor-color-picker-free-text-input =
    .title = Змінити колір тексту
pdfjs-editor-free-text-button-label = Текст
pdfjs-editor-ink-button =
    .title = Малювати
pdfjs-editor-color-picker-ink-input =
    .title = Змінити колір малюнка
pdfjs-editor-ink-button-label = Малювати
pdfjs-editor-stamp-button =
    .title = Додати чи редагувати зображення
pdfjs-editor-stamp-button-label = Додати чи редагувати зображення
pdfjs-editor-highlight-button =
    .title = Підсвітити
pdfjs-editor-highlight-button-label = Підсвітити
pdfjs-highlight-floating-button1 =
    .aria-label = Підсвітити
    .title = Підсвітити
pdfjs-highlight-floating-button-label = Підсвітити
pdfjs-comment-floating-button =
    .aria-label = Коментувати
    .title = Коментувати
pdfjs-comment-floating-button-label = Коментувати
pdfjs-editor-comment-button =
    .aria-label = Коментар
    .title = Коментар
pdfjs-editor-comment-button-label = Коментар
pdfjs-editor-signature-button =
    .title = Додати підпис
pdfjs-editor-signature-button-label = Додати підпис

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Редактор підсвічень
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Редактор малюнків
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Редактор підпису: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Редактор зображень

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Вилучити малюнок
pdfjs-editor-remove-freetext-button =
    .title = Вилучити текст
pdfjs-editor-remove-stamp-button =
    .title = Вилучити зображення
pdfjs-editor-remove-highlight-button =
    .title = Вилучити підсвічення
pdfjs-editor-remove-signature-button =
    .title = Вилучити підпис

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Колір
pdfjs-editor-free-text-size-input = Розмір
pdfjs-editor-ink-color-input = Колір
pdfjs-editor-ink-thickness-input = Товщина
pdfjs-editor-ink-opacity-input = Прозорість
pdfjs-editor-stamp-add-image-button =
    .title = Додати зображення
pdfjs-editor-stamp-add-image-button-label = Додати зображення
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Товщина
pdfjs-editor-free-highlight-thickness-title =
    .title = Змінюйте товщину під час підсвічення елементів, крім тексту
pdfjs-editor-add-signature-container =
    .aria-label = Елементи керування підписами та збережені підписи
pdfjs-editor-signature-add-signature-button =
    .title = Додати новий підпис
pdfjs-editor-signature-add-signature-button-label = Додати новий підпис
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Збережений підпис: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Текстовий редактор
    .default-content = Напишіть щось…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Коментар
        [few] Коментарі
       *[many] Коментарі
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Закрити бічну панель
    .title = Закрити бічну панель
pdfjs-editor-comments-sidebar-close-button-label = Закрити бічну панель
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Бачите щось варте уваги? Підсвітіть і додайте коментар.
pdfjs-editor-comments-sidebar-no-comments-link = Докладніше

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Альтернативний текст
pdfjs-editor-alt-text-edit-button =
    .aria-label = Редагувати альтернативний текст
pdfjs-editor-alt-text-dialog-label = Вибрати варіант
pdfjs-editor-alt-text-dialog-description = Альтернативний текст допомагає, коли зображення не видно або коли воно не завантажується.
pdfjs-editor-alt-text-add-description-label = Додати опис
pdfjs-editor-alt-text-add-description-description = Намагайтеся створити 1-2 речення, які описують тему, обставини або дії.
pdfjs-editor-alt-text-mark-decorative-label = Позначити декоративним
pdfjs-editor-alt-text-mark-decorative-description = Використовується для декоративних зображень, наприклад рамок або водяних знаків.
pdfjs-editor-alt-text-cancel-button = Скасувати
pdfjs-editor-alt-text-save-button = Зберегти
pdfjs-editor-alt-text-decorative-tooltip = Позначено декоративним
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Наприклад, “Молодий чоловік сідає за стіл їсти”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Альтернативний текст

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Верхній лівий кут – зміна розміру
pdfjs-editor-resizer-top-middle =
    .aria-label = Вгорі посередині – зміна розміру
pdfjs-editor-resizer-top-right =
    .aria-label = Верхній правий кут – зміна розміру
pdfjs-editor-resizer-middle-right =
    .aria-label = Праворуч посередині – зміна розміру
pdfjs-editor-resizer-bottom-right =
    .aria-label = Нижній правий кут – зміна розміру
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Внизу посередині – зміна розміру
pdfjs-editor-resizer-bottom-left =
    .aria-label = Нижній лівий кут – зміна розміру
pdfjs-editor-resizer-middle-left =
    .aria-label = Ліворуч посередині – зміна розміру

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Колір підсвічення
pdfjs-editor-colorpicker-button =
    .title = Змінити колір
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Вибір кольору
pdfjs-editor-colorpicker-yellow =
    .title = Жовтий
pdfjs-editor-colorpicker-green =
    .title = Зелений
pdfjs-editor-colorpicker-blue =
    .title = Блакитний
pdfjs-editor-colorpicker-pink =
    .title = Рожевий
pdfjs-editor-colorpicker-red =
    .title = Червоний

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Показати все
pdfjs-editor-highlight-show-all-button =
    .title = Показати все

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Редагувати альтернативний текст (опис зображення)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Додати альтернативний текст (опис зображення)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Напишіть свій опис тут…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Короткий опис для людей, які не бачать зображення, або якщо зображення не завантажується.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Цей альтернативний текст створено автоматично, тому він може бути неточним.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Докладніше
pdfjs-editor-new-alt-text-create-automatically-button-label = Автоматично створювати альтернативний текст
pdfjs-editor-new-alt-text-not-now-button = Не зараз
pdfjs-editor-new-alt-text-error-title = Не вдалося автоматично створити альтернативний текст
pdfjs-editor-new-alt-text-error-description = Напишіть власний альтернативний текст або повторіть спробу пізніше.
pdfjs-editor-new-alt-text-error-close-button = Закрити
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Завантаження моделі ШІ для альтернативного тексту ({ $downloadedSize } з { $totalSize } МБ)
    .aria-valuetext = Завантаження моделі ШІ для альтернативного тексту ({ $downloadedSize } з { $totalSize } МБ)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Альтернативний текст додано
pdfjs-editor-new-alt-text-added-button-label = Альтернативний текст додано
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Відсутній альтернативний текст
pdfjs-editor-new-alt-text-missing-button-label = Відсутній альтернативний текст
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Переглянути альтернативний текст
pdfjs-editor-new-alt-text-to-review-button-label = Переглянути альтернативний текст
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Створено автоматично: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Налаштування альтернативного тексту зображення
pdfjs-image-alt-text-settings-button-label = Налаштування альтернативного тексту зображення
pdfjs-editor-alt-text-settings-dialog-label = Налаштування альтернативного тексту зображення
pdfjs-editor-alt-text-settings-automatic-title = Автоматичний альтернативний текст
pdfjs-editor-alt-text-settings-create-model-button-label = Автоматично створювати альтернативний текст
pdfjs-editor-alt-text-settings-create-model-description = Пропонує описи, щоб допомогти людям, які не бачать зображення, або якщо зображення не завантажується.
pdfjs-editor-alt-text-settings-editor-title = Редактор альтернативного тексту
pdfjs-editor-alt-text-settings-show-dialog-button-label = Показувати редактор альтернативного тексту під час додавання зображення
pdfjs-editor-alt-text-settings-show-dialog-description = Допомагає переконатися, що всі ваші зображення мають альтернативний текст.
pdfjs-editor-alt-text-settings-close-button = Закрити

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Підсвічення додано
pdfjs-editor-freetext-added-alert = Текст додано
pdfjs-editor-ink-added-alert = Малюнок додано
pdfjs-editor-stamp-added-alert = Зображення додано
pdfjs-editor-signature-added-alert = Підпис додано

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Підсвічення вилучено
pdfjs-editor-undo-bar-message-freetext = Текст вилучено
pdfjs-editor-undo-bar-message-ink = Малюнок вилучено
pdfjs-editor-undo-bar-message-stamp = Зображення вилучено
pdfjs-editor-undo-bar-message-signature = Підпис вилучено
pdfjs-editor-undo-bar-message-comment = Коментар вилучено
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } анотацію вилучено
        [few] { $count } анотації вилучено
       *[many] { $count } анотацій вилучено
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Повернути
pdfjs-editor-undo-bar-undo-button-label = Повернути
pdfjs-editor-undo-bar-close-button =
    .title = Закрити
pdfjs-editor-undo-bar-close-button-label = Закрити

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = У цьому вікні користувач може створити підпис для додавання до PDF-документа. Користувач може відредагувати назву (яка також слугує альтернативним текстом) і, за бажання, зберегти підпис для повторного використання.
pdfjs-editor-add-signature-dialog-title = Додати підпис

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Ввести
    .title = Ввести
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Малювати
    .title = Малювати
pdfjs-editor-add-signature-image-button = Зображення
    .title = Зображення

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Введіть свій підпис
    .placeholder = Введіть свій підпис
pdfjs-editor-add-signature-draw-placeholder = Намалюйте свій підпис
pdfjs-editor-add-signature-draw-thickness-range-label = Товщина
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Товщина лінії: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Перетягніть файл сюди, щоб вивантажити
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Або виберіть файли зображень
       *[other] Або перегляньте файли зображень
    }

## Controls

pdfjs-editor-add-signature-description-label = Опис (альтернативний текст)
pdfjs-editor-add-signature-description-input =
    .title = Опис (альтернативний текст)
pdfjs-editor-add-signature-description-default-when-drawing = Підпис
pdfjs-editor-add-signature-clear-button-label = Очистити підпис
pdfjs-editor-add-signature-clear-button =
    .title = Очистити підпис
pdfjs-editor-add-signature-save-checkbox = Зберегти підпис
pdfjs-editor-add-signature-save-warning-message = Ви досягли ліміту в 5 збережених підписів. Вилучіть один, щоб зберегти інший.
pdfjs-editor-add-signature-image-upload-error-title = Не вдалося вивантажити зображення
pdfjs-editor-add-signature-image-upload-error-description = Перевірте мережеве з'єднання або спробуйте інше зображення.
pdfjs-editor-add-signature-image-no-data-error-title = Не вдається конвертувати це зображення в підпис
pdfjs-editor-add-signature-image-no-data-error-description = Спробуйте вивантажити інше зображення.
pdfjs-editor-add-signature-error-close-button = Закрити

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Скасувати
pdfjs-editor-add-signature-add-button = Додати
pdfjs-editor-edit-signature-update-button = Оновити

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Редагувати коментар
pdfjs-editor-edit-comment-popup-button =
    .title = Редагувати коментар
pdfjs-editor-delete-comment-popup-button-label = Вилучити коментар
pdfjs-editor-delete-comment-popup-button =
    .title = Вилучити коментар
pdfjs-show-comment-button =
    .title = Показати коментар

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Редагувати коментар
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Оновити
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Додати коментар
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Додати
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Почніть вводити…
pdfjs-editor-edit-comment-dialog-cancel-button = Скасувати

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Додати коментар

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Перемкнути бічну панель (документ містить мініатюри/ескіз/вкладення/шари)
pdfjs-views-manager-sidebar =
    .aria-label = Бічна панель
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Зміна розміру бічної панелі
pdfjs-views-manager-view-selector-button =
    .title = Вигляд
pdfjs-views-manager-view-selector-button-label = Вигляд
pdfjs-views-manager-pages-title = Сторінки
pdfjs-views-manager-attachments-title = Вкладення
pdfjs-views-manager-pages-option-label = Сторінки
pdfjs-views-manager-outlines-option-label = Схема документа
pdfjs-views-manager-attachments-option-label = Вкладення
pdfjs-views-manager-layers-option-label = Шари
pdfjs-views-manager-add-file-button =
    .title = Додати файл
pdfjs-views-manager-add-file-button-label = Додати файл
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] Вибрано { $count }
        [few] Вибрано { $count }
       *[many] Вибрано { $count }
    }
pdfjs-views-manager-pages-status-none-action-label = Вибрати сторінки
pdfjs-views-manager-pages-status-action-button-label = Керувати
pdfjs-views-manager-pages-status-copy-button-label = Копіювати
pdfjs-views-manager-pages-status-cut-button-label = Вирізати
pdfjs-views-manager-pages-status-delete-button-label = Видалити
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 сторінку вирізано
        [few] { $count } сторінки вирізано
       *[many] { $count } сторінок вирізано
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 сторінку скопійовано
        [few] { $count } сторінки скопійовано
       *[many] { $count } сторінок скопійовано
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 сторінку видалено
        [few] { $count } сторінки видалено
       *[many] { $count } сторінок видалено
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Підготовка файлу…
pdfjs-views-manager-pages-status-waiting-uploading-label = Вивантаження файлу…
pdfjs-views-manager-status-warning-cut-label = Не вдалося вирізати. Оновіть сторінку та спробуйте ще раз.
pdfjs-views-manager-status-warning-copy-label = Не вдалося скопіювати. Оновіть сторінку та спробуйте ще раз.
pdfjs-views-manager-status-warning-delete-label = Не вдалося видалити. Оновіть сторінку та спробуйте ще раз.
pdfjs-views-manager-status-warning-save-label = Не вдалося зберегти. Оновіть сторінку та спробуйте ще раз.
pdfjs-views-manager-status-undo-button-label = Повернути
pdfjs-views-manager-status-close-button =
    .title = Закрити
pdfjs-views-manager-status-close-button-label = Закрити
pdfjs-views-manager-paste-button-label = Вставити

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Видалити збережений підпис
pdfjs-editor-delete-signature-button-label1 = Видалити збережений підпис

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Редагувати опис

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Редагувати опис
