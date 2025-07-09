# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Предыдущая страница
pdfjs-previous-button-label = Предыдущая
pdfjs-next-button =
    .title = Следующая страница
pdfjs-next-button-label = Следующая
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Страница
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = из { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } из { $pagesCount })
pdfjs-zoom-out-button =
    .title = Уменьшить
pdfjs-zoom-out-button-label = Уменьшить
pdfjs-zoom-in-button =
    .title = Увеличить
pdfjs-zoom-in-button-label = Увеличить
pdfjs-zoom-select =
    .title = Масштаб
pdfjs-presentation-mode-button =
    .title = Перейти в режим презентации
pdfjs-presentation-mode-button-label = Режим презентации
pdfjs-open-file-button =
    .title = Открыть файл
pdfjs-open-file-button-label = Открыть
pdfjs-print-button =
    .title = Печать
pdfjs-print-button-label = Печать
pdfjs-save-button =
    .title = Сохранить
pdfjs-save-button-label = Сохранить
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Загрузить
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Загрузить
pdfjs-bookmark-button =
    .title = Текущая страница (просмотр URL-адреса с текущей страницы)
pdfjs-bookmark-button-label = Текущая страница

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Инструменты
pdfjs-tools-button-label = Инструменты
pdfjs-first-page-button =
    .title = Перейти на первую страницу
pdfjs-first-page-button-label = Перейти на первую страницу
pdfjs-last-page-button =
    .title = Перейти на последнюю страницу
pdfjs-last-page-button-label = Перейти на последнюю страницу
pdfjs-page-rotate-cw-button =
    .title = Повернуть по часовой стрелке
pdfjs-page-rotate-cw-button-label = Повернуть по часовой стрелке
pdfjs-page-rotate-ccw-button =
    .title = Повернуть против часовой стрелки
pdfjs-page-rotate-ccw-button-label = Повернуть против часовой стрелки
pdfjs-cursor-text-select-tool-button =
    .title = Включить Инструмент «Выделение текста»
pdfjs-cursor-text-select-tool-button-label = Инструмент «Выделение текста»
pdfjs-cursor-hand-tool-button =
    .title = Включить Инструмент «Рука»
pdfjs-cursor-hand-tool-button-label = Инструмент «Рука»
pdfjs-scroll-page-button =
    .title = Использовать прокрутку страниц
pdfjs-scroll-page-button-label = Прокрутка страниц
pdfjs-scroll-vertical-button =
    .title = Использовать вертикальную прокрутку
pdfjs-scroll-vertical-button-label = Вертикальная прокрутка
pdfjs-scroll-horizontal-button =
    .title = Использовать горизонтальную прокрутку
pdfjs-scroll-horizontal-button-label = Горизонтальная прокрутка
pdfjs-scroll-wrapped-button =
    .title = Использовать масштабируемую прокрутку
pdfjs-scroll-wrapped-button-label = Масштабируемая прокрутка
pdfjs-spread-none-button =
    .title = Не использовать режим разворотов страниц
pdfjs-spread-none-button-label = Без разворотов страниц
pdfjs-spread-odd-button =
    .title = Развороты начинаются с нечётных номеров страниц
pdfjs-spread-odd-button-label = Нечётные страницы слева
pdfjs-spread-even-button =
    .title = Развороты начинаются с чётных номеров страниц
pdfjs-spread-even-button-label = Чётные страницы слева

## Document properties dialog

pdfjs-document-properties-button =
    .title = Свойства документа…
pdfjs-document-properties-button-label = Свойства документа…
pdfjs-document-properties-file-name = Имя файла:
pdfjs-document-properties-file-size = Размер файла:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } КБ ({ $b } байт)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } МБ ({ $b } байт)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } КБ ({ $size_b } байт)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } МБ ({ $size_b } байт)
pdfjs-document-properties-title = Заголовок:
pdfjs-document-properties-author = Автор:
pdfjs-document-properties-subject = Тема:
pdfjs-document-properties-keywords = Ключевые слова:
pdfjs-document-properties-creation-date = Дата создания:
pdfjs-document-properties-modification-date = Дата изменения:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Приложение:
pdfjs-document-properties-producer = Производитель PDF:
pdfjs-document-properties-version = Версия PDF:
pdfjs-document-properties-page-count = Число страниц:
pdfjs-document-properties-page-size = Размер страницы:
pdfjs-document-properties-page-size-unit-inches = дюймов
pdfjs-document-properties-page-size-unit-millimeters = мм
pdfjs-document-properties-page-size-orientation-portrait = книжная
pdfjs-document-properties-page-size-orientation-landscape = альбомная
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
pdfjs-document-properties-linearized = Быстрый просмотр в Web:
pdfjs-document-properties-linearized-yes = Да
pdfjs-document-properties-linearized-no = Нет
pdfjs-document-properties-close-button = Закрыть

## Print

pdfjs-print-progress-message = Подготовка документа к печати…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Отмена
pdfjs-printing-not-supported = Предупреждение: В этом браузере не полностью поддерживается печать.
pdfjs-printing-not-ready = Предупреждение: PDF не полностью загружен для печати.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Показать/скрыть боковую панель
pdfjs-toggle-sidebar-notification-button =
    .title = Показать/скрыть боковую панель (документ имеет содержание/вложения/слои)
pdfjs-toggle-sidebar-button-label = Показать/скрыть боковую панель
pdfjs-document-outline-button =
    .title = Показать содержание документа (двойной щелчок, чтобы развернуть/свернуть все элементы)
pdfjs-document-outline-button-label = Содержание документа
pdfjs-attachments-button =
    .title = Показать вложения
pdfjs-attachments-button-label = Вложения
pdfjs-layers-button =
    .title = Показать слои (дважды щёлкните, чтобы сбросить все слои к состоянию по умолчанию)
pdfjs-layers-button-label = Слои
pdfjs-thumbs-button =
    .title = Показать миниатюры
pdfjs-thumbs-button-label = Миниатюры
pdfjs-current-outline-item-button =
    .title = Найти текущий элемент структуры
pdfjs-current-outline-item-button-label = Текущий элемент структуры
pdfjs-findbar-button =
    .title = Найти в документе
pdfjs-findbar-button-label = Найти
pdfjs-additional-layers = Дополнительные слои

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Страница { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Миниатюра страницы { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Найти
    .placeholder = Найти в документе…
pdfjs-find-previous-button =
    .title = Найти предыдущее вхождение фразы в текст
pdfjs-find-previous-button-label = Назад
pdfjs-find-next-button =
    .title = Найти следующее вхождение фразы в текст
pdfjs-find-next-button-label = Далее
pdfjs-find-highlight-checkbox = Подсветить все
pdfjs-find-match-case-checkbox-label = С учётом регистра
pdfjs-find-match-diacritics-checkbox-label = С учётом диакритических знаков
pdfjs-find-entire-word-checkbox-label = Слова целиком
pdfjs-find-reached-top = Достигнут верх документа, продолжено снизу
pdfjs-find-reached-bottom = Достигнут конец документа, продолжено сверху
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } из { $total } совпадения
        [few] { $current } из { $total } совпадений
       *[many] { $current } из { $total } совпадений
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Более { $limit } совпадения
        [few] Более { $limit } совпадений
       *[many] Более { $limit } совпадений
    }
pdfjs-find-not-found = Фраза не найдена

## Predefined zoom values

pdfjs-page-scale-width = По ширине страницы
pdfjs-page-scale-fit = По размеру страницы
pdfjs-page-scale-auto = Автоматически
pdfjs-page-scale-actual = Реальный размер
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Страница { $page }

## Loading indicator messages

pdfjs-loading-error = При загрузке PDF произошла ошибка.
pdfjs-invalid-file-error = Некорректный или повреждённый PDF-файл.
pdfjs-missing-file-error = PDF-файл отсутствует.
pdfjs-unexpected-response-error = Неожиданный ответ сервера.
pdfjs-rendering-error = При создании страницы произошла ошибка.

## Annotations

# Variables:
#   $date (Date) - the modification date of the annotation
#   $time (Time) - the modification time of the annotation
pdfjs-annotation-date-string = { $date }, { $time }
# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Аннотация { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Введите пароль, чтобы открыть этот PDF-файл.
pdfjs-password-invalid = Неверный пароль. Пожалуйста, попробуйте снова.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Отмена
pdfjs-web-fonts-disabled = Веб-шрифты отключены: не удалось задействовать встроенные PDF-шрифты.

## Editing

pdfjs-editor-free-text-button =
    .title = Текст
pdfjs-editor-free-text-button-label = Текст
pdfjs-editor-ink-button =
    .title = Рисовать
pdfjs-editor-ink-button-label = Рисовать
pdfjs-editor-stamp-button =
    .title = Добавить или изменить изображения
pdfjs-editor-stamp-button-label = Добавить или изменить изображения
pdfjs-editor-highlight-button =
    .title = Выделение
pdfjs-editor-highlight-button-label = Выделение
pdfjs-highlight-floating-button1 =
    .title = Выделение
    .aria-label = Выделение
pdfjs-highlight-floating-button-label = Выделение
pdfjs-editor-signature-button =
    .title = Добавить подпись
pdfjs-editor-signature-button-label = Добавить подпись

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Редактор выделения
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Редактор изображений
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Редактор подписи: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Редактор изображений

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Удалить рисунок
pdfjs-editor-remove-freetext-button =
    .title = Удалить текст
pdfjs-editor-remove-stamp-button =
    .title = Удалить изображение
pdfjs-editor-remove-highlight-button =
    .title = Удалить выделение
pdfjs-editor-remove-signature-button =
    .title = Удалить подпись

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Цвет
pdfjs-editor-free-text-size-input = Размер
pdfjs-editor-ink-color-input = Цвет
pdfjs-editor-ink-thickness-input = Толщина
pdfjs-editor-ink-opacity-input = Прозрачность
pdfjs-editor-stamp-add-image-button =
    .title = Добавить изображение
pdfjs-editor-stamp-add-image-button-label = Добавить изображение
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Толщина
pdfjs-editor-free-highlight-thickness-title =
    .title = Изменить толщину при выделении элементов, кроме текста
pdfjs-editor-add-signature-container =
    .aria-label = Управление подписями и сохраненные подписи
pdfjs-editor-signature-add-signature-button =
    .title = Добавить новую подпись
pdfjs-editor-signature-add-signature-button-label = Добавить новую подпись
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Сохранённая подпись: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Текстовый редактор
    .default-content = Начните ввод...
pdfjs-free-text =
    .aria-label = Текстовый редактор
pdfjs-free-text-default-content = Начните вводить…
pdfjs-ink =
    .aria-label = Редактор рисования
pdfjs-ink-canvas =
    .aria-label = Созданное пользователем изображение

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Альтернативный текст
pdfjs-editor-alt-text-edit-button =
    .aria-label = Изменить альтернативный текст
pdfjs-editor-alt-text-edit-button-label = Изменить альтернативный текст
pdfjs-editor-alt-text-dialog-label = Выберите вариант
pdfjs-editor-alt-text-dialog-description = Альтернативный текст помогает, когда люди не видят изображение или оно не загружается.
pdfjs-editor-alt-text-add-description-label = Добавить описание
pdfjs-editor-alt-text-add-description-description = Старайтесь составлять 1–2 предложения, описывающих предмет, обстановку или действия.
pdfjs-editor-alt-text-mark-decorative-label = Отметить как декоративное
pdfjs-editor-alt-text-mark-decorative-description = Используется для декоративных изображений, таких как рамки или водяные знаки.
pdfjs-editor-alt-text-cancel-button = Отменить
pdfjs-editor-alt-text-save-button = Сохранить
pdfjs-editor-alt-text-decorative-tooltip = Помечен как декоративный
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Например: «Молодой человек садится за стол, чтобы поесть»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Альтернативный текст

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Левый верхний угол — изменить размер
pdfjs-editor-resizer-label-top-middle = Вверху посередине — изменить размер
pdfjs-editor-resizer-label-top-right = Верхний правый угол — изменить размер
pdfjs-editor-resizer-label-middle-right = В центре справа — изменить размер
pdfjs-editor-resizer-label-bottom-right = Нижний правый угол — изменить размер
pdfjs-editor-resizer-label-bottom-middle = Внизу посередине — изменить размер
pdfjs-editor-resizer-label-bottom-left = Нижний левый угол — изменить размер
pdfjs-editor-resizer-label-middle-left = В центре слева — изменить размер
pdfjs-editor-resizer-top-left =
    .aria-label = Левый верхний угол — изменить размер
pdfjs-editor-resizer-top-middle =
    .aria-label = Вверху посередине — изменить размер
pdfjs-editor-resizer-top-right =
    .aria-label = Верхний правый угол — изменить размер
pdfjs-editor-resizer-middle-right =
    .aria-label = В центре справа — изменить размер
pdfjs-editor-resizer-bottom-right =
    .aria-label = Нижний правый угол — изменить размер
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Внизу посередине — изменить размер
pdfjs-editor-resizer-bottom-left =
    .aria-label = Нижний левый угол — изменить размер
pdfjs-editor-resizer-middle-left =
    .aria-label = В центре слева — изменить размер

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Цвет выделения
pdfjs-editor-colorpicker-button =
    .title = Изменить цвет
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Выбор цвета
pdfjs-editor-colorpicker-yellow =
    .title = Жёлтый
pdfjs-editor-colorpicker-green =
    .title = Зелёный
pdfjs-editor-colorpicker-blue =
    .title = Синий
pdfjs-editor-colorpicker-pink =
    .title = Розовый
pdfjs-editor-colorpicker-red =
    .title = Красный

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Показать все
pdfjs-editor-highlight-show-all-button =
    .title = Показать все

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Изменить альтернативный текст (описание изображения)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Добавить альтернативный текст (описание изображения)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Напишите здесь своё описание…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Короткое описание для людей, которые не видят изображение, или если изображение не загружается.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Этот альтернативный текст был создан автоматически и может быть неточным.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Подробнее
pdfjs-editor-new-alt-text-create-automatically-button-label = Автоматически создавать альтернативный текст
pdfjs-editor-new-alt-text-not-now-button = Не сейчас
pdfjs-editor-new-alt-text-error-title = Не удалось автоматически создать альтернативный текст
pdfjs-editor-new-alt-text-error-description = Пожалуйста, напишите свой альтернативный текст или попробуйте ещё раз позже.
pdfjs-editor-new-alt-text-error-close-button = Закрыть
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Загрузка модели ИИ для альтернативного текста ({ $downloadedSize } из { $totalSize } МБ)
    .aria-valuetext = Загрузка модели ИИ для альтернативного текста ({ $downloadedSize } из { $totalSize } МБ)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Альтернативный текст добавлен
pdfjs-editor-new-alt-text-added-button-label = Альтернативный текст добавлен
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Отсутствует альтернативный текст
pdfjs-editor-new-alt-text-missing-button-label = Отсутствует альтернативный текст
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Оценить альтернативный текст
pdfjs-editor-new-alt-text-to-review-button-label = Оценить альтернативный текст
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Создано автоматически: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Настройки альтернативного текста для изображения
pdfjs-image-alt-text-settings-button-label = Настройки альтернативного текста для изображения
pdfjs-editor-alt-text-settings-dialog-label = Настройки альтернативного текста для изображения
pdfjs-editor-alt-text-settings-automatic-title = Автоматический альтернативный текст
pdfjs-editor-alt-text-settings-create-model-button-label = Автоматически создавать альтернативный текст
pdfjs-editor-alt-text-settings-create-model-description = Предлагает описания, чтобы помочь людям, которые не видят изображение, или если изображение не загружается.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = ИИ-модель альтернативного текста ({ $totalSize } МБ)
pdfjs-editor-alt-text-settings-ai-model-description = Запускается локально на вашем устройстве, поэтому ваши данные остаются конфиденциальными. Требуется для автоматического альтернативного текста.
pdfjs-editor-alt-text-settings-delete-model-button = Удалить
pdfjs-editor-alt-text-settings-download-model-button = Загрузить
pdfjs-editor-alt-text-settings-downloading-model-button = Загрузка…
pdfjs-editor-alt-text-settings-editor-title = Редактор альтернативного текста
pdfjs-editor-alt-text-settings-show-dialog-button-label = Сразу показывать редактор альтернативного текста при добавлении изображения
pdfjs-editor-alt-text-settings-show-dialog-description = Помогает вам убедиться, что все ваши изображения имеют альтернативный текст.
pdfjs-editor-alt-text-settings-close-button = Закрыть

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Выделение удалено
pdfjs-editor-undo-bar-message-freetext = Текст удалён
pdfjs-editor-undo-bar-message-ink = Рисунок удалён
pdfjs-editor-undo-bar-message-stamp = Изображение удалено
pdfjs-editor-undo-bar-message-signature = Подпись удалена
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } аннотация удалена
        [few] { $count } аннотации удалены
       *[many] { $count } аннотаций удалены
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Отменить
pdfjs-editor-undo-bar-undo-button-label = Отменить
pdfjs-editor-undo-bar-close-button =
    .title = Закрыть
pdfjs-editor-undo-bar-close-button-label = Закрыть

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Это окно позволяет пользователю создать подпись для добавления в PDF-документ. Пользователь может отредактировать имя (которое также используется в качестве альтернативного текста) и, по желанию, сохранить подпись для повторного использования.
pdfjs-editor-add-signature-dialog-title = Добавить подпись

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Ввод
    .title = Ввод
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Рисовать
    .title = Рисовать
pdfjs-editor-add-signature-image-button = Изображение
    .title = Изображение

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Введите свою подпись
    .placeholder = Введите свою подпись
pdfjs-editor-add-signature-draw-placeholder = Нарисуйте свою подпись
pdfjs-editor-add-signature-draw-thickness-range-label = Толщина
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Толщина рисунка: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Перетащите сюда файл для загрузки
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Или просмотрите файлы изображений
       *[other] Или просмотрите файлы изображений
    }

## Controls

pdfjs-editor-add-signature-description-label = Описание (альтернативный текст)
pdfjs-editor-add-signature-description-input =
    .title = Описание (альтернативный текст)
pdfjs-editor-add-signature-description-default-when-drawing = Подпись
pdfjs-editor-add-signature-clear-button-label = Удалить подпись
pdfjs-editor-add-signature-clear-button =
    .title = Удалить подпись
pdfjs-editor-add-signature-save-checkbox = Сохранить подпись
pdfjs-editor-add-signature-save-warning-message = Вы достигли лимита в 5 сохранённых подписей. Удалите одну, чтобы сохранить другие.
pdfjs-editor-add-signature-image-upload-error-title = Не удалось загрузить изображение
pdfjs-editor-add-signature-image-upload-error-description = Проверьте подключение к сети или попробуйте другое изображение.
pdfjs-editor-add-signature-error-close-button = Закрыть

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Отмена
pdfjs-editor-add-signature-add-button = Добавить
pdfjs-editor-edit-signature-update-button = Обновить

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Удалить сохранённую подпись
pdfjs-editor-delete-signature-button-label1 = Удалить сохранённую подпись

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Изменить описание

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Изменить описание
