# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Página anterior
pdfjs-previous-button-label = Anterior
pdfjs-next-button =
    .title = Página siguiente
pdfjs-next-button-label = Siguiente
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Página
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
    .title = Aumentar
pdfjs-zoom-in-button-label = Aumentar
pdfjs-zoom-select =
    .title = Tamaño
pdfjs-presentation-mode-button =
    .title = Cambiar al modo presentación
pdfjs-presentation-mode-button-label = Modo presentación
pdfjs-open-file-button =
    .title = Abrir archivo
pdfjs-open-file-button-label = Abrir
pdfjs-print-button =
    .title = Imprimir
pdfjs-print-button-label = Imprimir
pdfjs-save-button =
    .title = Guardar
pdfjs-save-button-label = Guardar
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Descargar
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Descargar
pdfjs-bookmark-button =
    .title = Página actual (Ver URL de la página actual)
pdfjs-bookmark-button-label = Página actual

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Herramientas
pdfjs-tools-button-label = Herramientas
pdfjs-first-page-button =
    .title = Ir a la primera página
pdfjs-first-page-button-label = Ir a la primera página
pdfjs-last-page-button =
    .title = Ir a la última página
pdfjs-last-page-button-label = Ir a la última página
pdfjs-page-rotate-cw-button =
    .title = Rotar en sentido horario
pdfjs-page-rotate-cw-button-label = Rotar en sentido horario
pdfjs-page-rotate-ccw-button =
    .title = Rotar en sentido antihorario
pdfjs-page-rotate-ccw-button-label = Rotar en sentido antihorario
pdfjs-cursor-text-select-tool-button =
    .title = Activar herramienta de selección de texto
pdfjs-cursor-text-select-tool-button-label = Herramienta de selección de texto
pdfjs-cursor-hand-tool-button =
    .title = Activar herramienta de mano
pdfjs-cursor-hand-tool-button-label = Herramienta de mano
pdfjs-scroll-page-button =
    .title = Usar desplazamiento de página
pdfjs-scroll-page-button-label = Desplazamiento de página
pdfjs-scroll-vertical-button =
    .title = Usar desplazamiento vertical
pdfjs-scroll-vertical-button-label = Desplazamiento vertical
pdfjs-scroll-horizontal-button =
    .title = Usar desplazamiento horizontal
pdfjs-scroll-horizontal-button-label = Desplazamiento horizontal
pdfjs-scroll-wrapped-button =
    .title = Usar desplazamiento en bloque
pdfjs-scroll-wrapped-button-label = Desplazamiento en bloque
pdfjs-spread-none-button =
    .title = No juntar páginas en vista de libro
pdfjs-spread-none-button-label = Vista de libro
pdfjs-spread-odd-button =
    .title = Juntar las páginas partiendo de una con número impar
pdfjs-spread-odd-button-label = Vista de libro impar
pdfjs-spread-even-button =
    .title = Juntar las páginas partiendo de una con número par
pdfjs-spread-even-button-label = Vista de libro par

## Document properties dialog

pdfjs-document-properties-button =
    .title = Propiedades del documento…
pdfjs-document-properties-button-label = Propiedades del documento…
pdfjs-document-properties-file-name = Nombre de archivo:
pdfjs-document-properties-file-size = Tamaño de archivo:
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
pdfjs-document-properties-creation-date = Fecha de creación:
pdfjs-document-properties-modification-date = Fecha de modificación:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Creador:
pdfjs-document-properties-producer = Productor PDF:
pdfjs-document-properties-version = Versión PDF:
pdfjs-document-properties-page-count = Número de páginas:
pdfjs-document-properties-page-size = Tamaño de la página:
pdfjs-document-properties-page-size-unit-inches = in
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
pdfjs-document-properties-linearized = Vista rápida de la web:
pdfjs-document-properties-linearized-yes = Sí
pdfjs-document-properties-linearized-no = No
pdfjs-document-properties-close-button = Cerrar

## Print

pdfjs-print-progress-message = Preparando documento para impresión…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Cancelar
pdfjs-printing-not-supported = Advertencia: Imprimir no está totalmente soportado por este navegador.
pdfjs-printing-not-ready = Advertencia: Este PDF no se ha cargado completamente para poder imprimirse.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Cambiar barra lateral
pdfjs-toggle-sidebar-notification-button =
    .title = Alternar barra lateral (el documento contiene esquemas/adjuntos/capas)
pdfjs-toggle-sidebar-button-label = Cambiar barra lateral
pdfjs-document-outline-button =
    .title = Mostrar resumen del documento (doble clic para expandir/contraer todos los elementos)
pdfjs-document-outline-button-label = Resumen de documento
pdfjs-attachments-button =
    .title = Mostrar adjuntos
pdfjs-attachments-button-label = Adjuntos
pdfjs-layers-button =
    .title = Mostrar capas (doble clic para restablecer todas las capas al estado predeterminado)
pdfjs-layers-button-label = Capas
pdfjs-thumbs-button =
    .title = Mostrar miniaturas
pdfjs-thumbs-button-label = Miniaturas
pdfjs-current-outline-item-button =
    .title = Encontrar elemento de esquema actual
pdfjs-current-outline-item-button-label = Elemento de esquema actual
pdfjs-findbar-button =
    .title = Buscar en el documento
pdfjs-findbar-button-label = Buscar
pdfjs-additional-layers = Capas adicionales

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Página { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura de la página { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Buscar
    .placeholder = Buscar en el documento…
pdfjs-find-previous-button =
    .title = Encontrar la anterior aparición de la frase
pdfjs-find-previous-button-label = Anterior
pdfjs-find-next-button =
    .title = Encontrar la siguiente aparición de esta frase
pdfjs-find-next-button-label = Siguiente
pdfjs-find-highlight-checkbox = Resaltar todos
pdfjs-find-match-case-checkbox-label = Coincidencia de mayús./minús.
pdfjs-find-match-diacritics-checkbox-label = Coincidir diacríticos
pdfjs-find-entire-word-checkbox-label = Palabras completas
pdfjs-find-reached-top = Se alcanzó el inicio del documento, se continúa desde el final
pdfjs-find-reached-bottom = Se alcanzó el final del documento, se continúa desde el inicio
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } de { $total } coincidencia
       *[other] { $current } de { $total } coincidencias
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Más de { $limit } coincidencia
       *[other] Más de { $limit } coincidencias
    }
pdfjs-find-not-found = Frase no encontrada

## Predefined zoom values

pdfjs-page-scale-width = Anchura de la página
pdfjs-page-scale-fit = Ajuste de la página
pdfjs-page-scale-auto = Tamaño automático
pdfjs-page-scale-actual = Tamaño real
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Página { $page }

## Loading indicator messages

pdfjs-loading-error = Ocurrió un error al cargar el PDF.
pdfjs-invalid-file-error = Fichero PDF no válido o corrupto.
pdfjs-missing-file-error = No hay fichero PDF.
pdfjs-unexpected-response-error = Respuesta inesperada del servidor.
pdfjs-rendering-error = Ocurrió un error al renderizar la página.

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

pdfjs-password-label = Introduzca la contraseña para abrir este archivo PDF.
pdfjs-password-invalid = Contraseña no válida. Vuelva a intentarlo.
pdfjs-password-ok-button = Aceptar
pdfjs-password-cancel-button = Cancelar
pdfjs-web-fonts-disabled = Las tipografías web están desactivadas: es imposible usar las tipografías PDF embebidas.

## Editing

pdfjs-editor-free-text-button =
    .title = Texto
pdfjs-editor-color-picker-free-text-input =
    .title = Cambiar el color del texto
pdfjs-editor-free-text-button-label = Texto
pdfjs-editor-ink-button =
    .title = Dibujar
pdfjs-editor-color-picker-ink-input =
    .title = Cambiar el color del dibujo
pdfjs-editor-ink-button-label = Dibujar
pdfjs-editor-stamp-button =
    .title = Añadir o editar imágenes
pdfjs-editor-stamp-button-label = Añadir o editar imágenes
pdfjs-editor-highlight-button =
    .title = Resaltar
pdfjs-editor-highlight-button-label = Resaltar
pdfjs-highlight-floating-button1 =
    .title = Resaltar
    .aria-label = Resaltar
pdfjs-highlight-floating-button-label = Resaltar
pdfjs-comment-floating-button =
    .title = Comentario
    .aria-label = Comentario
pdfjs-comment-floating-button-label = Comentario
pdfjs-editor-comment-button =
    .title = Comentario
    .aria-label = Comentario
pdfjs-editor-comment-button-label = Comentario
pdfjs-editor-signature-button =
    .title = Añadir firma
pdfjs-editor-signature-button-label = Añadir firma

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor de resaltado
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editor de dibujos
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor de firmas: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editor de imágenes

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Eliminar dibujo
pdfjs-editor-remove-freetext-button =
    .title = Eliminar texto
pdfjs-editor-remove-stamp-button =
    .title = Eliminar imagen
pdfjs-editor-remove-highlight-button =
    .title = Quitar resaltado
pdfjs-editor-remove-signature-button =
    .title = Eliminar firma

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Color
pdfjs-editor-free-text-size-input = Tamaño
pdfjs-editor-ink-color-input = Color
pdfjs-editor-ink-thickness-input = Grosor
pdfjs-editor-ink-opacity-input = Opacidad
pdfjs-editor-stamp-add-image-button =
    .title = Añadir imagen
pdfjs-editor-stamp-add-image-button-label = Añadir imagen
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Grosor
pdfjs-editor-free-highlight-thickness-title =
    .title = Cambiar el grosor al resaltar elementos que no sean texto
pdfjs-editor-add-signature-container =
    .aria-label = Controles de firma y firmas guardadas
pdfjs-editor-signature-add-signature-button =
    .title = Añadir nueva firma
pdfjs-editor-signature-add-signature-button-label = Añadir nueva firma
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Firma guardada: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor de texto
    .default-content = Empiece a escribir…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Comentario
       *[other] Comentarios
    }
pdfjs-editor-comments-sidebar-close-button =
    .title = Cerrar la barra lateral
    .aria-label = Cerrar la barra lateral
pdfjs-editor-comments-sidebar-close-button-label = Cerrar la barra lateral
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = ¿Ve algo interesante? Resáltelo y deje un comentario.
pdfjs-editor-comments-sidebar-no-comments-link = Saber más

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Texto alternativo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Editar el texto alternativo
pdfjs-editor-alt-text-dialog-label = Eligir una opción
pdfjs-editor-alt-text-dialog-description = El texto alternativo (texto alternativo) ayuda cuando las personas no pueden ver la imagen o cuando no se carga.
pdfjs-editor-alt-text-add-description-label = Añadir una descripción
pdfjs-editor-alt-text-add-description-description = Intente escribir 1 o 2 frases que describan el tema, el entorno o las acciones.
pdfjs-editor-alt-text-mark-decorative-label = Marcar como decorativa
pdfjs-editor-alt-text-mark-decorative-description = Se utiliza para imágenes ornamentales, como bordes o marcas de agua.
pdfjs-editor-alt-text-cancel-button = Cancelar
pdfjs-editor-alt-text-save-button = Guardar
pdfjs-editor-alt-text-decorative-tooltip = Marcada como decorativa
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Por ejemplo: “Un joven se sienta a la mesa a comer”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Texto alternativo

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Esquina superior izquierda — redimensionar
pdfjs-editor-resizer-top-middle =
    .aria-label = Borde superior en el medio — redimensionar
pdfjs-editor-resizer-top-right =
    .aria-label = Esquina superior derecha — redimensionar
pdfjs-editor-resizer-middle-right =
    .aria-label = Borde derecho en el medio — redimensionar
pdfjs-editor-resizer-bottom-right =
    .aria-label = Esquina inferior derecha — redimensionar
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Borde inferior en el medio — redimensionar
pdfjs-editor-resizer-bottom-left =
    .aria-label = Esquina inferior izquierda — redimensionar
pdfjs-editor-resizer-middle-left =
    .aria-label = Borde izquierdo en el medio — redimensionar

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Color de resaltado
pdfjs-editor-colorpicker-button =
    .title = Cambiar color
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Opciones de color
pdfjs-editor-colorpicker-yellow =
    .title = Amarillo
pdfjs-editor-colorpicker-green =
    .title = Verde
pdfjs-editor-colorpicker-blue =
    .title = Azul
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Rojo

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Mostrar todo
pdfjs-editor-highlight-show-all-button =
    .title = Mostrar todo

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Editar texto alternativo (descripción de la imagen)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Añadir texto alternativo (descripción de la imagen)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Escribir la descripción aquí…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Breve descripción para las personas que no pueden ver la imagen o cuando la imagen no se carga.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Este texto alternativo fue creado automáticamente y puede ser inexacto.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Saber más
pdfjs-editor-new-alt-text-create-automatically-button-label = Crear texto alternativo automáticamente
pdfjs-editor-new-alt-text-not-now-button = Ahora no
pdfjs-editor-new-alt-text-error-title = No se ha podido crear el texto alternativo automáticamente
pdfjs-editor-new-alt-text-error-description = Escriba su propio texto alternativo o inténtelo de nuevo más tarde.
pdfjs-editor-new-alt-text-error-close-button = Cerrar
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Descargando el modelo de IA de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
    .aria-valuetext = Descargando el modelo de IA de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Se añadió el texto alternativo
pdfjs-editor-new-alt-text-added-button-label = Se añadió el texto alternativo
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Falta el texto alternativo
pdfjs-editor-new-alt-text-missing-button-label = Falta el texto alternativo
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Revisar el texto alternativo
pdfjs-editor-new-alt-text-to-review-button-label = Revisar el texto alternativo
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Creado automáticamente: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Ajustes del texto alternativo de la imagen
pdfjs-image-alt-text-settings-button-label = Ajustes del texto alternativo de la imagen
pdfjs-editor-alt-text-settings-dialog-label = Ajustes del texto alternativo de la imagen
pdfjs-editor-alt-text-settings-automatic-title = Texto alternativo automático
pdfjs-editor-alt-text-settings-create-model-button-label = Crear texto alternativo automáticamente
pdfjs-editor-alt-text-settings-create-model-description = Sugiere descripciones para ayudar a las personas que no pueden ver la imagen o cuando la imagen no se carga.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Modelo de IA de texto alternativo ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Se ejecuta localmente en el dispositivo para que los datos se mantengan privados. Requerido para texto alternativo automático.
pdfjs-editor-alt-text-settings-delete-model-button = Eliminar
pdfjs-editor-alt-text-settings-download-model-button = Descargar
pdfjs-editor-alt-text-settings-downloading-model-button = Descargando…
pdfjs-editor-alt-text-settings-editor-title = Editor de texto alternativo
pdfjs-editor-alt-text-settings-show-dialog-button-label = Mostrar el editor de texto alternativo inmediatamente al añadir una imagen
pdfjs-editor-alt-text-settings-show-dialog-description = Le ayuda a asegurarse de que todas sus imágenes tengan texto alternativo.
pdfjs-editor-alt-text-settings-close-button = Cerrar

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Resaltado añadido
pdfjs-editor-freetext-added-alert = Texto añadido
pdfjs-editor-ink-added-alert = Dibujo añadido
pdfjs-editor-stamp-added-alert = Imagen añadida
pdfjs-editor-signature-added-alert = Firma añadida

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Resaltado eliminado
pdfjs-editor-undo-bar-message-freetext = Texto eliminado
pdfjs-editor-undo-bar-message-ink = Dibujo eliminado
pdfjs-editor-undo-bar-message-stamp = Imagen eliminada
pdfjs-editor-undo-bar-message-signature = Firma eliminada
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } anotación eliminada
       *[other] { $count } anotaciones eliminadas
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Deshacer
pdfjs-editor-undo-bar-undo-button-label = Deshacer
pdfjs-editor-undo-bar-close-button =
    .title = Cerrar
pdfjs-editor-undo-bar-close-button-label = Cerrar

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Este modal permite al usuario crear una firma para añadirla a un documento PDF. El usuario puede editar el nombre (que también sirve como texto alternativo) y, opcionalmente, guardar la firma para usarla nuevamente.
pdfjs-editor-add-signature-dialog-title = Añadir una firma

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Escribir
    .title = Escribir
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Dibujar
    .title = Dibujar
pdfjs-editor-add-signature-image-button = Imagen
    .title = Imagen

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Escriba su firma
    .placeholder = Escriba su firma
pdfjs-editor-add-signature-draw-placeholder = Dibuje su firma
pdfjs-editor-add-signature-draw-thickness-range-label = Grosor
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Grosor del dibujo: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Arrastre un archivo aquí para cargarlo
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] O seleccione archivos de imágenes
       *[other] O seleccione archivos de imágenes
    }

## Controls

pdfjs-editor-add-signature-description-label = Descripción (texto alternativo)
pdfjs-editor-add-signature-description-input =
    .title = Descripción (texto alternativo)
pdfjs-editor-add-signature-description-default-when-drawing = Firma
pdfjs-editor-add-signature-clear-button-label = Borrar firma
pdfjs-editor-add-signature-clear-button =
    .title = Borrar firma
pdfjs-editor-add-signature-save-checkbox = Guardar firma
pdfjs-editor-add-signature-save-warning-message = Ha alcanzado el límite de 5 firmas guardadas. Elimine una para guardar más.
pdfjs-editor-add-signature-image-upload-error-title = No se ha podido subir la imagen
pdfjs-editor-add-signature-image-upload-error-description = Compruebe su conexión de red o pruebe con otra imagen.
pdfjs-editor-add-signature-image-no-data-error-title = No se puede convertir esta imagen en una firma
pdfjs-editor-add-signature-image-no-data-error-description = Por favor, intente cargar una imagen diferente.
pdfjs-editor-add-signature-error-close-button = Cerrar

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Cancelar
pdfjs-editor-add-signature-add-button = Añadir
pdfjs-editor-edit-signature-update-button = Actualizar

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Editar comentario
pdfjs-editor-edit-comment-popup-button =
    .title = Editar comentario
pdfjs-editor-delete-comment-popup-button-label = Eliminar comentario
pdfjs-editor-delete-comment-popup-button =
    .title = Eliminar comentario
pdfjs-show-comment-button =
    .title = Mostrar comentario

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Acciones
pdfjs-editor-edit-comment-actions-button =
    .title = Acciones
pdfjs-editor-edit-comment-close-button-label = Cerrar
pdfjs-editor-edit-comment-close-button =
    .title = Cerrar
pdfjs-editor-edit-comment-actions-edit-button-label = Editar
pdfjs-editor-edit-comment-actions-delete-button-label = Eliminar
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Introduzca su comentario
pdfjs-editor-edit-comment-manager-cancel-button = Cancelar
pdfjs-editor-edit-comment-manager-save-button = Guardar
# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Editar comentario
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Actualizar
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Añadir comentario
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Añadir
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Empezar a escribir…
pdfjs-editor-edit-comment-dialog-cancel-button = Cancelar

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Editar comentario

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Eliminar firma guardada
pdfjs-editor-delete-signature-button-label1 = Eliminar firma guardada

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Editar descripción

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Editar descripción
