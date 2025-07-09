# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Pjerwjejšny bok
pdfjs-previous-button-label = Slědk
pdfjs-next-button =
    .title = Pśiducy bok
pdfjs-next-button-label = Dalej
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Bok
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = z { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } z { $pagesCount })
pdfjs-zoom-out-button =
    .title = Pómjeńšyś
pdfjs-zoom-out-button-label = Pómjeńšyś
pdfjs-zoom-in-button =
    .title = Pówětšyś
pdfjs-zoom-in-button-label = Pówětšyś
pdfjs-zoom-select =
    .title = Skalěrowanje
pdfjs-presentation-mode-button =
    .title = Do prezentaciskego modusa pśejś
pdfjs-presentation-mode-button-label = Prezentaciski modus
pdfjs-open-file-button =
    .title = Dataju wócyniś
pdfjs-open-file-button-label = Wócyniś
pdfjs-print-button =
    .title = Śišćaś
pdfjs-print-button-label = Śišćaś
pdfjs-save-button =
    .title = Składowaś
pdfjs-save-button-label = Składowaś
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Ześěgnuś
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Ześěgnuś
pdfjs-bookmark-button =
    .title = Aktualny bok (URL z aktualnego boka pokazaś)
pdfjs-bookmark-button-label = Aktualny bok

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Rědy
pdfjs-tools-button-label = Rědy
pdfjs-first-page-button =
    .title = K prědnemu bokoju
pdfjs-first-page-button-label = K prědnemu bokoju
pdfjs-last-page-button =
    .title = K slědnemu bokoju
pdfjs-last-page-button-label = K slědnemu bokoju
pdfjs-page-rotate-cw-button =
    .title = Wobwjertnuś ako špěra źo
pdfjs-page-rotate-cw-button-label = Wobwjertnuś ako špěra źo
pdfjs-page-rotate-ccw-button =
    .title = Wobwjertnuś nawopaki ako špěra źo
pdfjs-page-rotate-ccw-button-label = Wobwjertnuś nawopaki ako špěra źo
pdfjs-cursor-text-select-tool-button =
    .title = Rěd za wuběranje teksta zmóžniś
pdfjs-cursor-text-select-tool-button-label = Rěd za wuběranje teksta
pdfjs-cursor-hand-tool-button =
    .title = Rucny rěd zmóžniś
pdfjs-cursor-hand-tool-button-label = Rucny rěd
pdfjs-scroll-page-button =
    .title = Kulanje boka wužywaś
pdfjs-scroll-page-button-label = Kulanje boka
pdfjs-scroll-vertical-button =
    .title = Wertikalne suwanje wužywaś
pdfjs-scroll-vertical-button-label = Wertikalne suwanje
pdfjs-scroll-horizontal-button =
    .title = Horicontalne suwanje wužywaś
pdfjs-scroll-horizontal-button-label = Horicontalne suwanje
pdfjs-scroll-wrapped-button =
    .title = Pózlažke suwanje wužywaś
pdfjs-scroll-wrapped-button-label = Pózlažke suwanje
pdfjs-spread-none-button =
    .title = Boki njezwězaś
pdfjs-spread-none-button-label = Žeden dwójny bok
pdfjs-spread-odd-button =
    .title = Boki zachopinajucy z njerownymi bokami zwězaś
pdfjs-spread-odd-button-label = Njerowne boki
pdfjs-spread-even-button =
    .title = Boki zachopinajucy z rownymi bokami zwězaś
pdfjs-spread-even-button-label = Rowne boki

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumentowe kakosći…
pdfjs-document-properties-button-label = Dokumentowe kakosći…
pdfjs-document-properties-file-name = Mě dataje:
pdfjs-document-properties-file-size = Wjelikosć dataje:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bajtow)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bajtow)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bajtow)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bajtow)
pdfjs-document-properties-title = Titel:
pdfjs-document-properties-author = Awtor:
pdfjs-document-properties-subject = Tema:
pdfjs-document-properties-keywords = Klucowe słowa:
pdfjs-document-properties-creation-date = Datum napóranja:
pdfjs-document-properties-modification-date = Datum změny:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Awtor:
pdfjs-document-properties-producer = PDF-gótowaŕ:
pdfjs-document-properties-version = PDF-wersija:
pdfjs-document-properties-page-count = Licba bokow:
pdfjs-document-properties-page-size = Wjelikosć boka:
pdfjs-document-properties-page-size-unit-inches = col
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = wusoki format
pdfjs-document-properties-page-size-orientation-landscape = prěcny format
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
pdfjs-document-properties-linearized = Fast Web View:
pdfjs-document-properties-linearized-yes = Jo
pdfjs-document-properties-linearized-no = Ně
pdfjs-document-properties-close-button = Zacyniś

## Print

pdfjs-print-progress-message = Dokument pśigótujo se za śišćanje…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Pśetergnuś
pdfjs-printing-not-supported = Warnowanje: Śišćanje njepódpěra se połnje pśez toś ten wobglědowak.
pdfjs-printing-not-ready = Warnowanje: PDF njejo se za śišćanje dopołnje zacytał.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Bócnicu pokazaś/schowaś
pdfjs-toggle-sidebar-notification-button =
    .title = Bocnicu pśešaltowaś (dokument rozrědowanje/pśipiski/warstwy wopśimujo)
pdfjs-toggle-sidebar-button-label = Bócnicu pokazaś/schowaś
pdfjs-document-outline-button =
    .title = Dokumentowe naraźenje pokazaś (dwójne kliknjenje, aby se wšykne zapiski pokazali/schowali)
pdfjs-document-outline-button-label = Dokumentowa struktura
pdfjs-attachments-button =
    .title = Pśidanki pokazaś
pdfjs-attachments-button-label = Pśidanki
pdfjs-layers-button =
    .title = Warstwy pokazaś (klikniśo dwójcy, aby wšykne warstwy na standardny staw slědk stajił)
pdfjs-layers-button-label = Warstwy
pdfjs-thumbs-button =
    .title = Miniatury pokazaś
pdfjs-thumbs-button-label = Miniatury
pdfjs-current-outline-item-button =
    .title = Aktualny rozrědowański zapisk pytaś
pdfjs-current-outline-item-button-label = Aktualny rozrědowański zapisk
pdfjs-findbar-button =
    .title = W dokumenśe pytaś
pdfjs-findbar-button-label = Pytaś
pdfjs-additional-layers = Dalšne warstwy

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Bok { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura boka { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Pytaś
    .placeholder = W dokumenśe pytaś…
pdfjs-find-previous-button =
    .title = Pjerwjejšne wustupowanje pytańskego wuraza pytaś
pdfjs-find-previous-button-label = Slědk
pdfjs-find-next-button =
    .title = Pśidujuce wustupowanje pytańskego wuraza pytaś
pdfjs-find-next-button-label = Dalej
pdfjs-find-highlight-checkbox = Wšykne wuzwignuś
pdfjs-find-match-case-checkbox-label = Na wjelikopisanje źiwaś
pdfjs-find-match-diacritics-checkbox-label = Diakritiske znamuška wužywaś
pdfjs-find-entire-word-checkbox-label = Cełe słowa
pdfjs-find-reached-top = Zachopjeńk dokumenta dostany, pókšacujo se z kóńcom
pdfjs-find-reached-bottom = Kóńc dokumenta dostany, pókšacujo se ze zachopjeńkom
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } z { $total } wótpowědnika
        [two] { $current } z { $total } wótpowědnikowu
        [few] { $current } z { $total } wótpowědnikow
       *[other] { $current } z { $total } wótpowědnikow
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Wušej { $limit } wótpowědnik
        [two] Wušej { $limit } wótpowědnika
        [few] Wušej { $limit } wótpowědniki
       *[other] Wušej { $limit } wótpowědniki
    }
pdfjs-find-not-found = Pytański wuraz njejo se namakał

## Predefined zoom values

pdfjs-page-scale-width = Šyrokosć boka
pdfjs-page-scale-fit = Wjelikosć boka
pdfjs-page-scale-auto = Awtomatiske skalěrowanje
pdfjs-page-scale-actual = Aktualna wjelikosć
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Bok { $page }

## Loading indicator messages

pdfjs-loading-error = Pśi zacytowanju PDF jo zmólka nastała.
pdfjs-invalid-file-error = Njepłaśiwa abo wobškóźona PDF-dataja.
pdfjs-missing-file-error = Felujuca PDF-dataja.
pdfjs-unexpected-response-error = Njewócakane serwerowe wótegrono.
pdfjs-rendering-error = Pśi zwobraznjanju boka jo zmólka nastała.

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
    .alt = [Typ pśipiskow: { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Zapódajśo gronidło, aby PDF-dataju wócynił.
pdfjs-password-invalid = Njepłaśiwe gronidło. Pšosym wopytajśo hyšći raz.
pdfjs-password-ok-button = W pórěźe
pdfjs-password-cancel-button = Pśetergnuś
pdfjs-web-fonts-disabled = Webpisma su znjemóžnjone: njejo móžno, zasajźone PDF-pisma wužywaś.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Kresliś
pdfjs-editor-ink-button-label = Kresliś
pdfjs-editor-stamp-button =
    .title = Wobraze pśidaś abo wobźěłaś
pdfjs-editor-stamp-button-label = Wobraze pśidaś abo wobźěłaś
pdfjs-editor-highlight-button =
    .title = Wuzwignuś
pdfjs-editor-highlight-button-label = Wuzwignuś
pdfjs-highlight-floating-button1 =
    .title = Wuzwignuś
    .aria-label = Wuzwignuś
pdfjs-highlight-floating-button-label = Wuzwignuś
pdfjs-editor-signature-button =
    .title = Signaturu pśidaś
pdfjs-editor-signature-button-label = Signaturu pśidaś

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor wuzwignjenja
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Kresleński editor
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Signaturowy editor: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Wobrazowy editor

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Kreslanku wótwónoźeś
pdfjs-editor-remove-freetext-button =
    .title = Tekst wótwónoźeś
pdfjs-editor-remove-stamp-button =
    .title = Wobraz wótwónoźeś
pdfjs-editor-remove-highlight-button =
    .title = Wuzwignjenje wótpóraś
pdfjs-editor-remove-signature-button =
    .title = Signaturu wótwónoźeś

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Barwa
pdfjs-editor-free-text-size-input = Wjelikosć
pdfjs-editor-ink-color-input = Barwa
pdfjs-editor-ink-thickness-input = Tłustosć
pdfjs-editor-ink-opacity-input = Opacita
pdfjs-editor-stamp-add-image-button =
    .title = Wobraz pśidaś
pdfjs-editor-stamp-add-image-button-label = Wobraz pśidaś
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Tłustosć
pdfjs-editor-free-highlight-thickness-title =
    .title = Tłustosć změniś, gaž se zapiski wuzwiguju, kótarež tekst njejsu
pdfjs-editor-add-signature-container =
    .aria-label = Wóźeńske elementy signaturow a skłaźone signatury
pdfjs-editor-signature-add-signature-button =
    .title = Nowu signaturu pśidaś
pdfjs-editor-signature-add-signature-button-label = Nowu signaturu pśidaś
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Skłaźona signatura: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Tekstowy editor
    .default-content = Zachopśo pisaś …
pdfjs-free-text =
    .aria-label = Tekstowy editor
pdfjs-free-text-default-content = Zachopśo pisaś…
pdfjs-ink =
    .aria-label = Kresleński editor
pdfjs-ink-canvas =
    .aria-label = Wobraz napórany wót wužywarja

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternatiwny tekst
pdfjs-editor-alt-text-edit-button =
    .aria-label = Alternatiwny tekst wobźěłaś
pdfjs-editor-alt-text-edit-button-label = Alternatiwny tekst wobźěłaś
pdfjs-editor-alt-text-dialog-label = Nastajenje wubraś
pdfjs-editor-alt-text-dialog-description = Alternatiwny tekst pomaga, gaž luźe njamógu wobraz wiźeś abo gaž se wobraz njezacytajo.
pdfjs-editor-alt-text-add-description-label = Wopisanje pśidaś
pdfjs-editor-alt-text-add-description-description = Pišćo 1 sadu abo 2 saźe, kótarejž temu, nastajenje abo akcije wopisujotej.
pdfjs-editor-alt-text-mark-decorative-label = Ako dekoratiwny markěrowaś
pdfjs-editor-alt-text-mark-decorative-description = To se za pyšnjece wobraze wužywa, na pśikład ramiki abo wódowe znamjenja.
pdfjs-editor-alt-text-cancel-button = Pśetergnuś
pdfjs-editor-alt-text-save-button = Składowaś
pdfjs-editor-alt-text-decorative-tooltip = Ako dekoratiwny markěrowany
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Na pśikład, „Młody muski za blidom sejźi, aby jěź jědł“
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternatiwny tekst

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Górjejce nalěwo – wjelikosć změniś
pdfjs-editor-resizer-label-top-middle = Górjejce wesrjejź – wjelikosć změniś
pdfjs-editor-resizer-label-top-right = Górjejce napšawo – wjelikosć změniś
pdfjs-editor-resizer-label-middle-right = Wesrjejź napšawo – wjelikosć změniś
pdfjs-editor-resizer-label-bottom-right = Dołojce napšawo – wjelikosć změniś
pdfjs-editor-resizer-label-bottom-middle = Dołojce wesrjejź – wjelikosć změniś
pdfjs-editor-resizer-label-bottom-left = Dołojce nalěwo – wjelikosć změniś
pdfjs-editor-resizer-label-middle-left = Wesrjejź nalěwo – wjelikosć změniś
pdfjs-editor-resizer-top-left =
    .aria-label = Górjejce nalěwo – wjelikosć změniś
pdfjs-editor-resizer-top-middle =
    .aria-label = Górjejce wesrjejź – wjelikosć změniś
pdfjs-editor-resizer-top-right =
    .aria-label = Górjejce napšawo – wjelikosć změniś
pdfjs-editor-resizer-middle-right =
    .aria-label = Wesrjejź napšawo – wjelikosć změniś
pdfjs-editor-resizer-bottom-right =
    .aria-label = Dołojce napšawo – wjelikosć změniś
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Dołojce wesrjejź – wjelikosć změniś
pdfjs-editor-resizer-bottom-left =
    .aria-label = Dołojce nalěwo – wjelikosć změniś
pdfjs-editor-resizer-middle-left =
    .aria-label = Wesrjejź nalěwo – wjelikosć změniś

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Barwa wuzwignjenja
pdfjs-editor-colorpicker-button =
    .title = Barwu změniś
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Wuběrk barwow
pdfjs-editor-colorpicker-yellow =
    .title = Žołty
pdfjs-editor-colorpicker-green =
    .title = Zeleny
pdfjs-editor-colorpicker-blue =
    .title = Módry
pdfjs-editor-colorpicker-pink =
    .title = Pink
pdfjs-editor-colorpicker-red =
    .title = Cerwjeny

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Wšykne pokazaś
pdfjs-editor-highlight-show-all-button =
    .title = Wšykne pokazaś

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Alternatiwny tekst wobźěłaś (wobrazowe wopisanje)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Alternatiwny tekst pśidaś (wobrazowe wopisanje)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Pišćo how swójo wopisanje…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Krotke wopisanje za luźe, kótarež njamóžośo wobraz wiźeś abo gaž se wobraz njezacytajo.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Toś ten alternatiwny tekst jo se awtomatiski napórał a jo snaź njedokradny.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Dalšne informacije
pdfjs-editor-new-alt-text-create-automatically-button-label = Alternatiwny tekst awtomatiski napóraś
pdfjs-editor-new-alt-text-not-now-button = Nic něnto
pdfjs-editor-new-alt-text-error-title = Alternatiwny tekst njedajo se awtomatiski napóraś
pdfjs-editor-new-alt-text-error-description = Pšosym pišćo swój alternatiwny tekst abo wopytajśo pózdźej hyšći raz.
pdfjs-editor-new-alt-text-error-close-button = Zacyniś
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Model KI za alternatiwny tekst se ześěgujo ({ $downloadedSize } z { $totalSize } MB)
    .aria-valuetext = Model KI za alternatiwny tekst se ześěgujo ({ $downloadedSize } z { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternatiwny tekst jo se pśidał
pdfjs-editor-new-alt-text-added-button-label = Alternatiwny tekst jo se pśidał
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Alternatiwny tekst felujo
pdfjs-editor-new-alt-text-missing-button-label = Alternatiwny tekst felujo
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Alternatiwny tekst pśeglědowaś
pdfjs-editor-new-alt-text-to-review-button-label = Alternatiwny tekst pśeglědowaś
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Awtomatiski napórany: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Nastajenja alternatiwnego wobrazowego teksta
pdfjs-image-alt-text-settings-button-label = Nastajenja alternatiwnego wobrazowego teksta
pdfjs-editor-alt-text-settings-dialog-label = Nastajenja alternatiwnego wobrazowego teksta
pdfjs-editor-alt-text-settings-automatic-title = Awtomatiski alternatiwny tekst
pdfjs-editor-alt-text-settings-create-model-button-label = Alternatiwny tekst awtomatiski napóraś
pdfjs-editor-alt-text-settings-create-model-description = Naraźujo wopisanja, aby pomagał ludam, kótarež njamóžośo wobraz wiźeś abo gaž se wobraz njezacytajo.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Model KI alternatiwnego teksta ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Běžy lokalnje na wašom rěźe, aby waše daty priwatne wóstali. Za awtomatiski alternatiwny tekst trjebny.
pdfjs-editor-alt-text-settings-delete-model-button = Lašowaś
pdfjs-editor-alt-text-settings-download-model-button = Ześěgnuś
pdfjs-editor-alt-text-settings-downloading-model-button = Ześěgujo se…
pdfjs-editor-alt-text-settings-editor-title = Editor za alternatiwny tekst
pdfjs-editor-alt-text-settings-show-dialog-button-label = Editor alternatiwnego teksta ned pokazaś, gaž se wobraz pśidawa
pdfjs-editor-alt-text-settings-show-dialog-description = Pomaga, wam wšym swójim wobrazam alternatiwny tekst pśidaś.
pdfjs-editor-alt-text-settings-close-button = Zacyniś

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Wótwónoźone wuzwignuś
pdfjs-editor-undo-bar-message-freetext = Tekst jo se wótwónoźeł
pdfjs-editor-undo-bar-message-ink = Kreslanka jo se wótwónoźeła
pdfjs-editor-undo-bar-message-stamp = Wobraz jo se wótwónoźeł
pdfjs-editor-undo-bar-message-signature = Signatura jo se wótwónoźeła
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } pśipisk jo se wótwónoźeł
        [two] { $count } pśipiska stej se wótwónoźełej
        [few] { $count } pśipiski su se wótwónoźeli
       *[other] { $count } pśipiskow jo se wótwónoźeło
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Anulěrowaś
pdfjs-editor-undo-bar-undo-button-label = Anulěrowaś
pdfjs-editor-undo-bar-close-button =
    .title = Zacyniś
pdfjs-editor-undo-bar-close-button-label = Zacyniś

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Toś ten modalny dialog wužywarjeju zmóžnja, signaturu napóraś, aby PDF-dokument pśidał. Wužywaŕ móžo mě wobźěłaś (kótarež teke ako alternatiwny tekst słužy) a pó žycenju signaturu za wóspjetne wužywanje składowaś.
pdfjs-editor-add-signature-dialog-title = Signaturu pśidaś

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Typ
    .title = Typ
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Kresliś
    .title = Kresliś
pdfjs-editor-add-signature-image-button = Wobraz
    .title = Wobraz

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Zapódajśo swóju signaturu
    .placeholder = Zapódajśo swóju signaturu
pdfjs-editor-add-signature-draw-placeholder = Kresliśo swóju signaturu
pdfjs-editor-add-signature-draw-thickness-range-label = Tłustosć
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Tłustosć kreslanki: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Śěgniśo dataju sem, aby ju nagrał
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Abo wubjeŕśo wobrazowe dataje
       *[other] Abo pśepytajśo wobrazowe dataje
    }

## Controls

pdfjs-editor-add-signature-description-label = Wopisanje (alternatiwny tekst)
pdfjs-editor-add-signature-description-input =
    .title = Wopisanje (alternatiwny tekst)
pdfjs-editor-add-signature-description-default-when-drawing = Signatura
pdfjs-editor-add-signature-clear-button-label = Signaturu lašowaś
pdfjs-editor-add-signature-clear-button =
    .title = Signaturu lašowaś
pdfjs-editor-add-signature-save-checkbox = Signaturu składowaś
pdfjs-editor-add-signature-save-warning-message = Sćo dojśpił limit 5 skłaźonych signaturow. Wótwónoźćo jadnu, aby wěcej składował.
pdfjs-editor-add-signature-image-upload-error-title = Wobraz njedajo se nagraś
pdfjs-editor-add-signature-image-upload-error-description = Pśeglědajśo swój seśowy zwisk abo wopytajśo drugi wobraz.
pdfjs-editor-add-signature-error-close-button = Zacyniś

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Pśetergnuś
pdfjs-editor-add-signature-add-button = Pśidaś
pdfjs-editor-edit-signature-update-button = Aktualizěrowaś

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Skłaźonu signaturu wótwónoźeś
pdfjs-editor-delete-signature-button-label1 = Skłaźonu signaturu wótwónoźeś

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Wopisanje wobźěłaś

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Wopisanje wobźěłaś
