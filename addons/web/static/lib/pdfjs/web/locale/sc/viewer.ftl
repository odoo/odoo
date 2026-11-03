# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Pàgina anteriore
pdfjs-previous-button-label = S'ischeda chi b'est primu
pdfjs-next-button =
    .title = Pàgina imbeniente
pdfjs-next-button-label = Imbeniente
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Pàgina
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = de { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } de { $pagesCount })
pdfjs-zoom-out-button =
    .title = Impitica
pdfjs-zoom-out-button-label = Impitica
pdfjs-zoom-in-button =
    .title = Ismànnia
pdfjs-zoom-in-button-label = Ismànnia
pdfjs-zoom-select =
    .title = Ismànnia
pdfjs-presentation-mode-button =
    .title = Cola a sa modalidade de presentatzione
pdfjs-presentation-mode-button-label = Modalidade de presentatzione
pdfjs-open-file-button =
    .title = Aberi s'archìviu
pdfjs-open-file-button-label = Abertu
pdfjs-print-button =
    .title = Imprenta
pdfjs-print-button-label = Imprenta
pdfjs-save-button =
    .title = Sarva
pdfjs-save-button-label = Sarva
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Iscàrriga
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Iscàrriga
pdfjs-bookmark-button =
    .title = Pàgina atuale (ammustra s’URL de sa pàgina atuale)
pdfjs-bookmark-button-label = Pàgina atuale

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Istrumentos
pdfjs-tools-button-label = Istrumentos
pdfjs-first-page-button =
    .title = Bae a sa prima pàgina
pdfjs-first-page-button-label = Bae a sa prima pàgina
pdfjs-last-page-button =
    .title = Bae a s'ùrtima pàgina
pdfjs-last-page-button-label = Bae a s'ùrtima pàgina
pdfjs-page-rotate-cw-button =
    .title = Gira in sensu oràriu
pdfjs-page-rotate-cw-button-label = Gira in sensu oràriu
pdfjs-page-rotate-ccw-button =
    .title = Gira in sensu anti-oràriu
pdfjs-page-rotate-ccw-button-label = Gira in sensu anti-oràriu
pdfjs-cursor-text-select-tool-button =
    .title = Ativa s'aina de seletzione de testu
pdfjs-cursor-text-select-tool-button-label = Aina de seletzione de testu
pdfjs-cursor-hand-tool-button =
    .title = Ativa s'aina de manu
pdfjs-cursor-hand-tool-button-label = Aina de manu
pdfjs-scroll-page-button =
    .title = Imprea s'iscurrimentu de pàgina
pdfjs-scroll-page-button-label = Iscurrimentu de pàgina
pdfjs-scroll-vertical-button =
    .title = Imprea s'iscurrimentu verticale
pdfjs-scroll-vertical-button-label = Iscurrimentu verticale
pdfjs-scroll-horizontal-button =
    .title = Imprea s'iscurrimentu orizontale
pdfjs-scroll-horizontal-button-label = Iscurrimentu orizontale
pdfjs-scroll-wrapped-button =
    .title = Imprea s'iscurrimentu continu
pdfjs-scroll-wrapped-button-label = Iscurrimentu continu
pdfjs-spread-none-button-label = Pàginas individuales

## Document properties dialog

pdfjs-document-properties-button =
    .title = Propiedades de su documentu…
pdfjs-document-properties-button-label = Propiedades de su documentu…
pdfjs-document-properties-file-name = Nòmine de s'archìviu:
pdfjs-document-properties-file-size = Mannària de s'archìviu:
pdfjs-document-properties-title = Tìtulu:
pdfjs-document-properties-author = Autoria:
pdfjs-document-properties-subject = Ogetu:
pdfjs-document-properties-keywords = Faeddos crae:
pdfjs-document-properties-creation-date = Data de creatzione:
pdfjs-document-properties-modification-date = Data de modìfica:
pdfjs-document-properties-creator = Creatzione:
pdfjs-document-properties-producer = Produtore de PDF:
pdfjs-document-properties-version = Versione de PDF:
pdfjs-document-properties-page-count = Contu de pàginas:
pdfjs-document-properties-page-size = Mannària de sa pàgina:
pdfjs-document-properties-page-size-unit-inches = pòddighes
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = verticale
pdfjs-document-properties-page-size-orientation-landscape = orizontale
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Lìtera
pdfjs-document-properties-page-size-name-legal = Legale

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
pdfjs-document-properties-linearized = Visualizatzione web lestra:
pdfjs-document-properties-linearized-yes = Eja
pdfjs-document-properties-linearized-no = Nono
pdfjs-document-properties-close-button = Serra
pdfjs-digital-signature-properties-view-certificate = Ammustra su tzertificadu
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Resone: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Data e ora: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Print

pdfjs-print-progress-message = Aparitzende s'imprenta de su documentu…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Annulla
pdfjs-printing-not-supported = Atentzione: s'imprenta no est funtzionende de su totu in custu navigadore.
pdfjs-printing-not-ready = Atentzione: su PDF no est istadu carrigadu de su totu pro s'imprenta.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Agata s'elementu atuale de s'ischema
pdfjs-current-outline-item-button-label = Elementu atuale de s'ischema
pdfjs-findbar-button =
    .title = Agata in su documentu
pdfjs-findbar-button-label = Agata
pdfjs-additional-layers = Livellos additzionales

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura de sa pàgina { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Seletziona sa pàgina { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Pàgina { $page } de { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Agata in su documentu…
    .title = Agata
pdfjs-find-previous-button =
    .title = Agata s'ocurrèntzia pretzedente de sa fràsia
pdfjs-find-previous-button-label = S'ischeda chi b'est primu
pdfjs-find-next-button =
    .title = Agata s'ocurrèntzia imbeniente de sa fràsia
pdfjs-find-next-button-label = Imbeniente
pdfjs-find-highlight-checkbox = Evidèntzia totu
pdfjs-find-match-case-checkbox-label = Distinghe intre majùsculas e minùsculas
pdfjs-find-match-diacritics-checkbox-label = Respeta is diacrìticos
pdfjs-find-entire-word-checkbox-label = Faeddos intreos
pdfjs-find-reached-top = S'est lòmpidu a su cumintzu de su documentu, si sighit dae su bàsciu
pdfjs-find-reached-bottom = Acabbu de su documentu, si sighit dae s'artu
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } currispondèntzia de { $total }
       *[other] { $current } currispondèntzias de { $total }
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Prus de { $limit } currispondèntzia
       *[other] Prus de { $limit } currispondèntzias
    }
pdfjs-find-not-found = Testu no agatadu

## Predefined zoom values

pdfjs-page-scale-width = Larghesa de sa pàgina
pdfjs-page-scale-fit = Pàgina intrea
pdfjs-page-scale-auto = Ingrandimentu automàticu
pdfjs-page-scale-actual = Mannària reale
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Pàgina { $page }

## Loading indicator messages

pdfjs-loading-error = Faddina in sa càrriga de su PDF.
pdfjs-invalid-file-error = Archìviu PDF non vàlidu o corrùmpidu.
pdfjs-missing-file-error = Ammancat s'archìviu PDF.
pdfjs-unexpected-response-error = Risposta imprevista de su serbidore.
pdfjs-rendering-error = Faddina in sa visualizatzione de sa pàgina.

## Annotations

# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Inserta sa crae pro abèrrere custu archìviu PDF.
pdfjs-password-invalid = Sa crae no est curreta. Torra a nche proare.
pdfjs-password-ok-button = Andat bene
pdfjs-password-cancel-button = Annulla
pdfjs-web-fonts-disabled = Is tipografias web sunt disativadas: is tipografias incrustadas a su PDF non podent èssere impreadas.

## Editing

pdfjs-editor-free-text-button =
    .title = Testu
pdfjs-editor-color-picker-free-text-input =
    .title = Muda su colore de su testu
pdfjs-editor-free-text-button-label = Testu
pdfjs-editor-ink-button =
    .title = Disinnu
pdfjs-editor-color-picker-ink-input =
    .title = Muda su colore pro su disinnu
pdfjs-editor-ink-button-label = Disinnu
pdfjs-editor-stamp-button =
    .title = Agiunghe o modìfica immàgines
pdfjs-editor-stamp-button-label = Agiunghe o modìfica immàgines
pdfjs-editor-highlight-button =
    .title = Evidèntzia
pdfjs-editor-highlight-button-label = Evidèntzia
pdfjs-highlight-floating-button1 =
    .aria-label = Evidèntzia
    .title = Evidèntzia
pdfjs-highlight-floating-button-label = Evidèntzia
pdfjs-comment-floating-button =
    .aria-label = Cummenta
    .title = Cummenta
pdfjs-comment-floating-button-label = Cummenta
pdfjs-editor-comment-button =
    .aria-label = Cummenta
    .title = Cummenta
pdfjs-editor-comment-button-label = Cummenta
pdfjs-editor-signature-button =
    .title = Agiunghe una firma
pdfjs-editor-signature-button-label = Agiunghe una firma

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editore de sutaliniadura
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editore de disinnos
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editore de firmas: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editore de immàgines

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Boga su disinnu
pdfjs-editor-remove-freetext-button =
    .title = Boga su testu
pdfjs-editor-remove-stamp-button =
    .title = Boga s’immàgine
pdfjs-editor-remove-highlight-button =
    .title = Boga s’evidèntzia
pdfjs-editor-remove-signature-button =
    .title = Boga·nche sa firma

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Colore
pdfjs-editor-free-text-size-input = Mannària
pdfjs-editor-ink-color-input = Colore
pdfjs-editor-ink-thickness-input = Grussària
pdfjs-editor-stamp-add-image-button =
    .title = Agiunghe un’immàgine
pdfjs-editor-stamp-add-image-button-label = Agiunghe un’immàgine
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Grussària
pdfjs-editor-add-signature-container =
    .aria-label = Controllos de firma e firmas sarvadas
pdfjs-editor-signature-add-signature-button =
    .title = Agiunghe una firma noa
pdfjs-editor-signature-add-signature-button-label = Agiunghe una firma noa
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Firma sarvada: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editore de testu
    .default-content = Cumintza a iscrìere…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Cummentu
       *[other] Cummentos
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Serra sa barra laterale
    .title = Serra sa barra laterale
pdfjs-editor-comments-sidebar-close-button-label = Serra sa barra laterale
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = As rilevadu una cosa de interessu? Sinnala·dda e agiunghe unu cummentu.

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Testu alternativu
pdfjs-editor-alt-text-edit-button =
    .aria-label = Modifica su testu alternativu
pdfjs-editor-alt-text-dialog-label = Sèbera un’optzione
pdfjs-editor-alt-text-dialog-description = Su testu alternativu (“alt text”) est ùtile pro persones chi non podent bìdere s’immàgine o cando non benit carrigada.
pdfjs-editor-alt-text-add-description-label = Agiunghe una descritzione
pdfjs-editor-alt-text-mark-decorative-label = Sinnala comente decorativa
pdfjs-editor-alt-text-cancel-button = Annulla
pdfjs-editor-alt-text-save-button = Sarva
pdfjs-editor-alt-text-decorative-tooltip = Sinnalada comente decorativu

## Color picker

pdfjs-editor-colorpicker-button =
    .title = Modifica su colore
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Colores a disponimentu
pdfjs-editor-colorpicker-yellow =
    .title = Grogu
pdfjs-editor-colorpicker-green =
    .title = Birde
pdfjs-editor-colorpicker-blue =
    .title = Biaitu
pdfjs-editor-colorpicker-pink =
    .title = Rosa

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Mancat su testu alternativu
pdfjs-editor-new-alt-text-missing-button-label = Mancat su testu alternativu
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Revisiona su testu alternativu
pdfjs-editor-new-alt-text-to-review-button-label = Revisiona su testu alternativu
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Creadu in automàticu: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Cunfiguratzione de su testu alternativu de is immàgines
pdfjs-image-alt-text-settings-button-label = Cunfiguratzione de su testu alternativu de is immàgines
pdfjs-editor-alt-text-settings-dialog-label = Cunfiguratzione de su testu alternativu de is immàgines
pdfjs-editor-alt-text-settings-automatic-title = Testu alternativu automàticu
pdfjs-editor-alt-text-settings-create-model-button-label = Crea testu alternativu in automàticu
pdfjs-editor-alt-text-settings-create-model-description = Cussìgiat descritziones pro agiudare a gente chi non podet bìdere s’immàgine o cando non benit carrigada.
pdfjs-editor-alt-text-settings-editor-title = Editore de testu alternativu
pdfjs-editor-alt-text-settings-show-dialog-button-label = Mustra deretu s’editore de testu alternativu cando siat agiunta un’immàgine
pdfjs-editor-alt-text-settings-show-dialog-description = T’agiudat a assegurare chi totu is immàgines tuas tèngiant unu testu alternativu.
pdfjs-editor-alt-text-settings-close-button = Serra

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-freetext = Testu cantzelladu
pdfjs-editor-undo-bar-message-ink = Disinnu cantzelladu
pdfjs-editor-undo-bar-message-stamp = Immàgine cantzellada
pdfjs-editor-undo-bar-message-signature = Firma cantzellada
pdfjs-editor-undo-bar-undo-button =
    .title = Iscontza
pdfjs-editor-undo-bar-undo-button-label = Iscontza
pdfjs-editor-undo-bar-close-button =
    .title = Serra
pdfjs-editor-undo-bar-close-button-label = Serra

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Annulla

##  Edit a comment dialog

pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Cumintza a iscrìere…
