# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Páxina anterior
pdfjs-previous-button-label = Anterior
pdfjs-next-button =
    .title = Seguinte páxina
pdfjs-next-button-label = Seguinte
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Páxina
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = de { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } de { $pagesCount })
pdfjs-zoom-out-button =
    .title = Reducir
pdfjs-zoom-out-button-label = Reducir
pdfjs-zoom-in-button =
    .title = Ampliar
pdfjs-zoom-in-button-label = Ampliar
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Cambiar ao modo presentación
pdfjs-presentation-mode-button-label = Modo presentación
pdfjs-open-file-button =
    .title = Abrir ficheiro
pdfjs-open-file-button-label = Abrir
pdfjs-print-button =
    .title = Imprimir
pdfjs-print-button-label = Imprimir
pdfjs-save-button =
    .title = Gardar
pdfjs-save-button-label = Gardar
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Descargar
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Descargar
pdfjs-bookmark-button =
    .title = Páxina actual (ver o URL da páxina actual)
pdfjs-bookmark-button-label = Páxina actual

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Ferramentas
pdfjs-tools-button-label = Ferramentas
pdfjs-first-page-button =
    .title = Ir á primeira páxina
pdfjs-first-page-button-label = Ir á primeira páxina
pdfjs-last-page-button =
    .title = Ir á última páxina
pdfjs-last-page-button-label = Ir á última páxina
pdfjs-page-rotate-cw-button =
    .title = Rotar no sentido das agullas do reloxo
pdfjs-page-rotate-cw-button-label = Rotar no sentido das agullas do reloxo
pdfjs-page-rotate-ccw-button =
    .title = Rotar no sentido contrario ás agullas do reloxo
pdfjs-page-rotate-ccw-button-label = Rotar no sentido contrario ás agullas do reloxo
pdfjs-cursor-text-select-tool-button =
    .title = Activar a ferramenta de selección de texto
pdfjs-cursor-text-select-tool-button-label = Ferramenta de selección de texto
pdfjs-cursor-hand-tool-button =
    .title = Activar a ferramenta de man
pdfjs-cursor-hand-tool-button-label = Ferramenta de man
pdfjs-scroll-page-button =
    .title = Usar o desprazamento da páxina
pdfjs-scroll-page-button-label = Desprazamento da páxina
pdfjs-scroll-vertical-button =
    .title = Usar o desprazamento vertical
pdfjs-scroll-vertical-button-label = Desprazamento vertical
pdfjs-scroll-horizontal-button =
    .title = Usar o desprazamento horizontal
pdfjs-scroll-horizontal-button-label = Desprazamento horizontal
pdfjs-scroll-wrapped-button =
    .title = Usar o desprazamento en bloque
pdfjs-scroll-wrapped-button-label = Desprazamento por bloque
pdfjs-spread-none-button =
    .title = Non agrupar páxinas
pdfjs-spread-none-button-label = Ningún agrupamento
pdfjs-spread-odd-button =
    .title = Crea grupo de páxinas que comezan con números de páxina impares
pdfjs-spread-odd-button-label = Agrupamento impar
pdfjs-spread-even-button =
    .title = Crea grupo de páxinas que comezan con números de páxina pares
pdfjs-spread-even-button-label = Agrupamento par

## Document properties dialog

pdfjs-document-properties-button =
    .title = Propiedades do documento…
pdfjs-document-properties-button-label = Propiedades do documento…
pdfjs-document-properties-file-name = Nome do ficheiro:
pdfjs-document-properties-file-size = Tamaño do ficheiro:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)
pdfjs-document-properties-title = Título:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Asunto:
pdfjs-document-properties-keywords = Palabras clave:
pdfjs-document-properties-creation-date = Data de creación:
pdfjs-document-properties-modification-date = Data de modificación:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Creado por:
pdfjs-document-properties-producer = Xenerador do PDF:
pdfjs-document-properties-version = Versión de PDF:
pdfjs-document-properties-page-count = Número de páxinas:
pdfjs-document-properties-page-size = Tamaño da páxina:
pdfjs-document-properties-page-size-unit-inches = pol
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = vertical
pdfjs-document-properties-page-size-orientation-landscape = horizontal
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Carta
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
pdfjs-document-properties-linearized = Visualización rápida das páxinas web:
pdfjs-document-properties-linearized-yes = Si
pdfjs-document-properties-linearized-no = Non
pdfjs-document-properties-close-button = Pechar

## Print

pdfjs-print-progress-message = Preparando o documento para imprimir…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Cancelar
pdfjs-printing-not-supported = Aviso: A impresión non é compatíbel de todo con este navegador.
pdfjs-printing-not-ready = Aviso: O PDF non se cargou completamente para imprimirse.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Amosar/agochar a barra lateral
pdfjs-toggle-sidebar-notification-button =
    .title = Alternar barra lateral (o documento contén esquema/anexos/capas)
pdfjs-toggle-sidebar-button-label = Amosar/agochar a barra lateral
pdfjs-document-outline-button =
    .title = Amosar a estrutura do documento (dobre clic para expandir/contraer todos os elementos)
pdfjs-document-outline-button-label = Estrutura do documento
pdfjs-attachments-button =
    .title = Amosar anexos
pdfjs-attachments-button-label = Anexos
pdfjs-layers-button =
    .title = Mostrar capas (prema dúas veces para restaurar todas as capas o estado predeterminado)
pdfjs-layers-button-label = Capas
pdfjs-thumbs-button =
    .title = Amosar miniaturas
pdfjs-thumbs-button-label = Miniaturas
pdfjs-current-outline-item-button =
    .title = Atopar o elemento delimitado actualmente
pdfjs-current-outline-item-button-label = Elemento delimitado actualmente
pdfjs-findbar-button =
    .title = Atopar no documento
pdfjs-findbar-button-label = Atopar
pdfjs-additional-layers = Capas adicionais

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Páxina { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura da páxina { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Atopar
    .placeholder = Atopar no documento…
pdfjs-find-previous-button =
    .title = Atopar a anterior aparición da frase
pdfjs-find-previous-button-label = Anterior
pdfjs-find-next-button =
    .title = Atopar a seguinte aparición da frase
pdfjs-find-next-button-label = Seguinte
pdfjs-find-highlight-checkbox = Realzar todo
pdfjs-find-match-case-checkbox-label = Diferenciar maiúsculas de minúsculas
pdfjs-find-match-diacritics-checkbox-label = Distinguir os diacríticos
pdfjs-find-entire-word-checkbox-label = Palabras completas
pdfjs-find-reached-top = Chegouse ao inicio do documento, continuar desde o final
pdfjs-find-reached-bottom = Chegouse ao final do documento, continuar desde o inicio
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] Coincidencia { $current } de { $total }
       *[other] Coincidencia { $current } de { $total }
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Máis de { $limit } coincidencia
       *[other] Máis de { $limit } coincidencias
    }
pdfjs-find-not-found = Non se atopou a frase

## Predefined zoom values

pdfjs-page-scale-width = Largura da páxina
pdfjs-page-scale-fit = Axuste de páxina
pdfjs-page-scale-auto = Zoom automático
pdfjs-page-scale-actual = Tamaño actual
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Páxina { $page }

## Loading indicator messages

pdfjs-loading-error = Produciuse un erro ao cargar o PDF.
pdfjs-invalid-file-error = Ficheiro PDF danado ou non válido.
pdfjs-missing-file-error = Falta o ficheiro PDF.
pdfjs-unexpected-response-error = Resposta inesperada do servidor.
pdfjs-rendering-error = Produciuse un erro ao representar a páxina.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Anotación { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Escriba o contrasinal para abrir este ficheiro PDF.
pdfjs-password-invalid = Contrasinal incorrecto. Tente de novo.
pdfjs-password-ok-button = Aceptar
pdfjs-password-cancel-button = Cancelar
pdfjs-web-fonts-disabled = Desactiváronse as fontes web:  foi imposíbel usar as fontes incrustadas no PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Texto
pdfjs-editor-free-text-button-label = Texto
pdfjs-editor-ink-button =
    .title = Debuxo
pdfjs-editor-ink-button-label = Debuxo
pdfjs-editor-stamp-button =
    .title = Engadir ou editar imaxes
pdfjs-editor-stamp-button-label = Engadir ou editar imaxes
pdfjs-editor-highlight-button =
    .title = Destacar
pdfjs-editor-highlight-button-label = Destacar
pdfjs-highlight-floating-button1 =
    .title = Destacar
    .aria-label = Destacar
pdfjs-highlight-floating-button-label = Destacar
pdfjs-editor-signature-button =
    .title = Engadir sinatura
pdfjs-editor-signature-button-label = Engadir sinatura

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor de destacados
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editor de debuxos
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor de sinaturas: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editor de imaxes

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Eliminar debuxo
pdfjs-editor-remove-freetext-button =
    .title = Eliminar o texto
pdfjs-editor-remove-stamp-button =
    .title = Eliminar a imaxe
pdfjs-editor-remove-highlight-button =
    .title = Eliminar o resaltado
pdfjs-editor-remove-signature-button =
    .title = Eliminar sinatura

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Cor
pdfjs-editor-free-text-size-input = Tamaño
pdfjs-editor-ink-color-input = Cor
pdfjs-editor-ink-thickness-input = Grosor
pdfjs-editor-ink-opacity-input = Opacidade
pdfjs-editor-stamp-add-image-button =
    .title = Engadir imaxe
pdfjs-editor-stamp-add-image-button-label = Engadir imaxe
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Grosor
pdfjs-editor-free-highlight-thickness-title =
    .title = Cambiar o grosor ao resaltar elementos que non sexan texto
pdfjs-editor-add-signature-container =
    .aria-label = Controis de sinaturas e sinaturas gardadas
pdfjs-editor-signature-add-signature-button =
    .title = Engadir nova sinatura
pdfjs-editor-signature-add-signature-button-label = Engadir nova sinatura
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Sinatura gardada: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor de texto
    .default-content = Empeza a escribir...

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Texto alternativo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Editar o texto alternativo
pdfjs-editor-alt-text-dialog-label = Escoller unha opción
pdfjs-editor-alt-text-dialog-description = O texto alternativo (texto alt) axuda cando as persoas non poden ver a imaxe ou cando non se carga.
pdfjs-editor-alt-text-add-description-label = Engadir unha descrición
pdfjs-editor-alt-text-add-description-description = Tenta escribir 1-2 frases que describan o tema, o escenario ou as accións.
pdfjs-editor-alt-text-mark-decorative-label = Marcar como decorativo
pdfjs-editor-alt-text-mark-decorative-description = Utilízase para imaxes ornamentais, como bordos ou marcas de auga.
pdfjs-editor-alt-text-cancel-button = Cancelar
pdfjs-editor-alt-text-save-button = Gardar
pdfjs-editor-alt-text-decorative-tooltip = Marcado como decorativo
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Por exemplo, «Un mozo séntase á mesa para comer»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Texto alternativo

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Esquina superior esquerda: cambia o tamaño
pdfjs-editor-resizer-top-middle =
    .aria-label = Medio superior: cambia o tamaño
pdfjs-editor-resizer-top-right =
    .aria-label = Esquina superior dereita: cambia o tamaño
pdfjs-editor-resizer-middle-right =
    .aria-label = Medio dereito: cambia o tamaño
pdfjs-editor-resizer-bottom-right =
    .aria-label = Esquina inferior dereita: cambia o tamaño
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Abaixo medio: cambia o tamaño
pdfjs-editor-resizer-bottom-left =
    .aria-label = Esquina inferior esquerda: cambia o tamaño
pdfjs-editor-resizer-middle-left =
    .aria-label = Medio esquerdo: cambia o tamaño

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Cor de resaltado
pdfjs-editor-colorpicker-button =
    .title = Cambiar de cor
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Opcións de cor
pdfjs-editor-colorpicker-yellow =
    .title = Amarelo
pdfjs-editor-colorpicker-green =
    .title = Verde
pdfjs-editor-colorpicker-blue =
    .title = Azul
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Vermello

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Amosar todo
pdfjs-editor-highlight-show-all-button =
    .title = Amosar todo

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Editar texto alternativo (descrición da imaxe)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Engadir texto alternativo (descrición da imaxe)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Escribe a túa descrición aquí...
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Breve descrición para as persoas que non poden ver a imaxe ou cando a imaxe non carga.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Este texto alternativo creouse automaticamente e pode ser inexacto.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Máis información
pdfjs-editor-new-alt-text-create-automatically-button-label = Crea texto alternativo automaticamente
pdfjs-editor-new-alt-text-not-now-button = Agora non
pdfjs-editor-new-alt-text-error-title = Non se puido crear o texto alternativo automaticamente
pdfjs-editor-new-alt-text-error-description = Escribe o teu propio texto alternativo ou téntao de novo máis tarde.
pdfjs-editor-new-alt-text-error-close-button = Pechar
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Descargando o modelo de IA de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
    .aria-valuetext = Descargando o modelo de IA de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Texto alternativo engadido
pdfjs-editor-new-alt-text-added-button-label = Texto alternativo engadido
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Falta o texto alternativo
pdfjs-editor-new-alt-text-missing-button-label = Falta o texto alternativo
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Revisar o texto alternativo
pdfjs-editor-new-alt-text-to-review-button-label = Revisar o texto alternativo
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Creado automaticamente: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Configuración do texto alternativo da imaxe
pdfjs-image-alt-text-settings-button-label = Configuración do texto alternativo da imaxe
pdfjs-editor-alt-text-settings-dialog-label = Configuración do texto alternativo da imaxe
pdfjs-editor-alt-text-settings-automatic-title = Texto alternativo automático
pdfjs-editor-alt-text-settings-create-model-button-label = Crear texto alternativo automaticamente
pdfjs-editor-alt-text-settings-create-model-description = Suxire descricións para axudar ás persoas que non poden ver a imaxe ou cando a imaxe non se carga.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Modelo de IA de texto alternativo ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Funciona localmente no teu dispositivo para que os teus datos se manteñan privados. Necesario para o texto alternativo automático.
pdfjs-editor-alt-text-settings-delete-model-button = Eliminar
pdfjs-editor-alt-text-settings-download-model-button = Descargar
pdfjs-editor-alt-text-settings-downloading-model-button = Descargando…
pdfjs-editor-alt-text-settings-editor-title = Editor de texto alternativo
pdfjs-editor-alt-text-settings-show-dialog-button-label = Mostrar o editor de texto alternativo inmediatamente ao engadir unha imaxe
pdfjs-editor-alt-text-settings-show-dialog-description = Axúdache a asegurarte de que todas as túas imaxes teñan texto alternativo.
pdfjs-editor-alt-text-settings-close-button = Pechar

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Resaltado engadido
pdfjs-editor-freetext-added-alert = Texto engadido
pdfjs-editor-ink-added-alert = Debuxo engadido
pdfjs-editor-stamp-added-alert = Imaxe engadida
pdfjs-editor-signature-added-alert = Sinatura engadida

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Resaltado eliminado
pdfjs-editor-undo-bar-message-freetext = Texto eliminado
pdfjs-editor-undo-bar-message-ink = Debuxo eliminado
pdfjs-editor-undo-bar-message-stamp = Imaxe eliminada
pdfjs-editor-undo-bar-message-signature = Sinatura eliminada
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] Eliminouse { $count } anotación
       *[other] Elimináronse { $count } anotacións
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Desfacer
pdfjs-editor-undo-bar-undo-button-label = Desfacer
pdfjs-editor-undo-bar-close-button =
    .title = Pechar
pdfjs-editor-undo-bar-close-button-label = Pechar

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Este modal permite ao usuario crear unha sinatura para engadila a un documento PDF. O usuario pode editar o nome (que tamén serve como texto alternativo) e, opcionalmente, gardar a sinatura para usala novamente.
pdfjs-editor-add-signature-dialog-title = Engadir unha sinatura

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Tipo
    .title = Tipo
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Debuxar
    .title = Debuxar
pdfjs-editor-add-signature-image-button = Imaxe
    .title = Imaxe

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Escribe a túa sinatura
    .placeholder = Escribe a túa sinatura
pdfjs-editor-add-signature-draw-placeholder = Debuxa a túa sinatura
pdfjs-editor-add-signature-draw-thickness-range-label = Grosor
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Grosor do debuxo: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Arrastra un ficheiro aquí para cargalo
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ou selecciona ficheiros de imaxes
       *[other] Ou navega ficheiros de imaxes
    }

## Controls

pdfjs-editor-add-signature-description-label = Descrición (texto alternativo)
pdfjs-editor-add-signature-description-input =
    .title = Descrición (texto alternativo)
pdfjs-editor-add-signature-description-default-when-drawing = Sinatura
pdfjs-editor-add-signature-clear-button-label = Borrar a sinatura
pdfjs-editor-add-signature-clear-button =
    .title = Borrar a sinatura
pdfjs-editor-add-signature-save-checkbox = Gardar a sinatura
pdfjs-editor-add-signature-save-warning-message = Acadaches o límite de 5 sinaturas gardadas. Elimina unha para gardar máis.
pdfjs-editor-add-signature-image-upload-error-title = Non se puido cargar a imaxe
pdfjs-editor-add-signature-image-upload-error-description = Comproba a túa conexión de rede ou proba con outra imaxe.
pdfjs-editor-add-signature-error-close-button = Pechar

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Cancelar
pdfjs-editor-add-signature-add-button = Engadir
pdfjs-editor-edit-signature-update-button = Actualizar

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Eliminar a sinatura gardada
pdfjs-editor-delete-signature-button-label1 = Eliminar a sinatura gardada

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Editar descrición

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Editar descrición
