# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Faqja e Mëparshme
pdfjs-previous-button-label = E mëparshmja
pdfjs-next-button =
    .title = Faqja Pasuese
pdfjs-next-button-label = Pasuesja
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Faqe
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = nga { $pagesCount } gjithsej
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } nga { $pagesCount })
pdfjs-zoom-out-button =
    .title = Zvogëlojeni
pdfjs-zoom-out-button-label = Zvogëlojeni
pdfjs-zoom-in-button =
    .title = Zmadhojeni
pdfjs-zoom-in-button-label = Zmadhojini
pdfjs-zoom-select =
    .title = Zmadhim/Zvogëlim
pdfjs-presentation-mode-button =
    .title = Kalo te Mënyra Paraqitje
pdfjs-presentation-mode-button-label = Mënyra Paraqitje
pdfjs-open-file-button =
    .title = Hapni Kartelë
pdfjs-open-file-button-label = Hape
pdfjs-print-button =
    .title = Shtypje
pdfjs-print-button-label = Shtype
pdfjs-save-button =
    .title = Ruaje
pdfjs-save-button-label = Ruaje
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Shkarkojeni
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Shkarkoje
pdfjs-bookmark-button =
    .title = Faqja e Tanishme (Shihni URL nga Faqja e Tanishme)
pdfjs-bookmark-button-label = Faqja e Tanishme

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Mjete
pdfjs-tools-button-label = Mjete
pdfjs-first-page-button =
    .title = Kaloni te Faqja e Parë
pdfjs-first-page-button-label = Kaloni te Faqja e Parë
pdfjs-last-page-button =
    .title = Kaloni te Faqja e Fundit
pdfjs-last-page-button-label = Kaloni te Faqja e Fundit
pdfjs-page-rotate-cw-button =
    .title = Rrotullojeni Në Kahun Orar
pdfjs-page-rotate-cw-button-label = Rrotulloje Në Kahun Orar
pdfjs-page-rotate-ccw-button =
    .title = Rrotullojeni Në Kahun Kundërorar
pdfjs-page-rotate-ccw-button-label = Rrotulloje Në Kahun Kundërorar
pdfjs-cursor-text-select-tool-button =
    .title = Aktivizo Mjet Përzgjedhjeje Teksti
pdfjs-cursor-text-select-tool-button-label = Mjet Përzgjedhjeje Teksti
pdfjs-cursor-hand-tool-button =
    .title = Aktivizo Mjetin Dorë
pdfjs-cursor-hand-tool-button-label = Mjeti Dorë
pdfjs-scroll-page-button =
    .title = Përdor Rrëshqitje Në Faqe
pdfjs-scroll-page-button-label = Rrëshqitje Në Faqe
pdfjs-scroll-vertical-button =
    .title = Përdor Rrëshqitje Vertikale
pdfjs-scroll-vertical-button-label = Rrëshqitje Vertikale
pdfjs-scroll-horizontal-button =
    .title = Përdor Rrëshqitje Horizontale
pdfjs-scroll-horizontal-button-label = Rrëshqitje Horizontale
pdfjs-scroll-wrapped-button =
    .title = Përdor Rrëshqitje Me Mbështjellje
pdfjs-scroll-wrapped-button-label = Rrëshqitje Me Mbështjellje

## Document properties dialog

pdfjs-document-properties-button =
    .title = Veti Dokumenti…
pdfjs-document-properties-button-label = Veti Dokumenti…
pdfjs-document-properties-file-name = Emër kartele:
pdfjs-document-properties-file-size = Madhësi kartele:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bajte)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bajte)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bajte)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bajte)
pdfjs-document-properties-title = Titull:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Subjekt:
pdfjs-document-properties-keywords = Fjalëkyçe:
pdfjs-document-properties-creation-date = Datë Krijimi:
pdfjs-document-properties-modification-date = Datë Ndryshimi:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Krijues:
pdfjs-document-properties-producer = Prodhues PDF-je:
pdfjs-document-properties-version = Version PDF-je:
pdfjs-document-properties-page-count = Numër Faqesh:
pdfjs-document-properties-page-size = Madhësi Faqeje:
pdfjs-document-properties-page-size-unit-inches = inç
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = portret
pdfjs-document-properties-page-size-orientation-landscape = së gjeri
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
pdfjs-document-properties-linearized = Parje e Shpjetë në Web:
pdfjs-document-properties-linearized-yes = Po
pdfjs-document-properties-linearized-no = Jo
pdfjs-document-properties-close-button = Mbylleni

## Print

pdfjs-print-progress-message = Po përgatitet dokumenti për shtypje…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Anuloje
pdfjs-printing-not-supported = Kujdes: Shtypja s’mbulohet plotësisht nga ky shfletues.
pdfjs-printing-not-ready = Kujdes: PDF-ja s’është ngarkuar plotësisht që ta shtypni.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Shfaqni/Fshihni Anështyllën
pdfjs-toggle-sidebar-notification-button =
    .title = Hap/Mbyll Anështylë (dokumenti përmban përvijim/nashkëngjitje/shtresa)
pdfjs-toggle-sidebar-button-label = Shfaq/Fshih Anështyllën
pdfjs-document-outline-button =
    .title = Shfaqni Përvijim Dokumenti (dyklikoni që të shfaqen/fshihen krejt elementët)
pdfjs-document-outline-button-label = Përvijim Dokumenti
pdfjs-attachments-button =
    .title = Shfaqni Bashkëngjitje
pdfjs-attachments-button-label = Bashkëngjitje
pdfjs-layers-button =
    .title = Shfaq Shtresa (dyklikoni që të rikthehen krejt shtresat në gjendjen e tyre parazgjedhje)
pdfjs-layers-button-label = Shtresa
pdfjs-thumbs-button =
    .title = Shfaqni Miniatura
pdfjs-thumbs-button-label = Miniatura
pdfjs-current-outline-item-button =
    .title = Gjej Objektin e Tanishëm të Përvijuar
pdfjs-current-outline-item-button-label = Objekt i Tanishëm i Përvijuar
pdfjs-findbar-button =
    .title = Gjeni në Dokument
pdfjs-findbar-button-label = Gjej
pdfjs-additional-layers = Shtresa Shtesë

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Faqja { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniaturë e Faqes { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Gjej
    .placeholder = Gjeni në dokument…
pdfjs-find-previous-button =
    .title = Gjeni hasjen e mëparshme të togfjalëshit
pdfjs-find-previous-button-label = E mëparshmja
pdfjs-find-next-button =
    .title = Gjeni hasjen pasuese të togfjalëshit
pdfjs-find-next-button-label = Pasuesja
pdfjs-find-highlight-checkbox = Theksoji të tëra
pdfjs-find-match-case-checkbox-label = Siç Është Shkruar
pdfjs-find-match-diacritics-checkbox-label = Me Përputhje Me Shenjat Diakritike
pdfjs-find-entire-word-checkbox-label = Fjalë të Plota
pdfjs-find-reached-top = U mbërrit në krye të dokumentit, vazhduar prej fundit
pdfjs-find-reached-bottom = U mbërrit në fund të dokumentit, vazhduar prej kreut
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } nga { $total } përputhje
       *[other] { $current } nga { $total } përputhje
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Më tepër se { $limit } përputhje
       *[other] Më tepër se { $limit } përputhje
    }
pdfjs-find-not-found = Togfjalësh që s’gjendet

## Predefined zoom values

pdfjs-page-scale-width = Gjerësi Faqeje
pdfjs-page-scale-fit = Sa Nxë Faqja
pdfjs-page-scale-auto = Zoom i Vetvetishëm
pdfjs-page-scale-actual = Madhësia Faktike
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Faqja { $page }

## Loading indicator messages

pdfjs-loading-error = Ndodhi një gabim gjatë ngarkimit të PDF-së.
pdfjs-invalid-file-error = Kartelë PDF e pavlefshme ose e dëmtuar.
pdfjs-missing-file-error = Kartelë PDF që mungon.
pdfjs-unexpected-response-error = Përgjigje shërbyesi e papritur.
pdfjs-rendering-error = Ndodhi një gabim gjatë riprodhimit të faqes.

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
    .alt = [Nënvizim { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Jepni fjalëkalimin që të hapet kjo kartelë PDF.
pdfjs-password-invalid = Fjalëkalim i pavlefshëm. Ju lutemi, riprovoni.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Anuloje
pdfjs-web-fonts-disabled = Shkronjat Web janë të çaktivizuara: s’arrihet të përdoren shkronja të trupëzuara në PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Vizatoni
pdfjs-editor-ink-button-label = Vizatoni
pdfjs-editor-stamp-button =
    .title = Shtoni ose përpunoni figura
pdfjs-editor-stamp-button-label = Shtoni ose përpunoni figura
pdfjs-editor-highlight-button =
    .title = Theksim
pdfjs-editor-highlight-button-label = Theksoje
pdfjs-highlight-floating-button1 =
    .title = Theksim
    .aria-label = Theksim
pdfjs-highlight-floating-button-label = Theksim
pdfjs-editor-signature-button =
    .title = Shtoni nënshkrim
pdfjs-editor-signature-button-label = Shtoni nënshkrim

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Përpunues theksimesh
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Përpunues vizatimesh
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Përpunues nënshkrimesh: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Përpunues figurash

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Hiq vizatim
pdfjs-editor-remove-freetext-button =
    .title = Hiq tekst
pdfjs-editor-remove-stamp-button =
    .title = Hiq figurë
pdfjs-editor-remove-highlight-button =
    .title = Hiqe theksimin
pdfjs-editor-remove-signature-button =
    .title = Hiqe nënshkrimin

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Ngjyrë
pdfjs-editor-free-text-size-input = Madhësi
pdfjs-editor-ink-color-input = Ngjyrë
pdfjs-editor-ink-thickness-input = Trashësi
pdfjs-editor-ink-opacity-input = Patejdukshmëri
pdfjs-editor-stamp-add-image-button =
    .title = Shtoni figurë
pdfjs-editor-stamp-add-image-button-label = Shtoni figurë
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Trashësi
pdfjs-editor-free-highlight-thickness-title =
    .title = Ndryshoni trashësinë kur theksoni objekte tjetër nga tekst
pdfjs-editor-add-signature-container =
    .aria-label = Kontrolle nënshkrimesh dhe nënshkrime të ruajtur
pdfjs-editor-signature-add-signature-button =
    .title = Shtoni nënshkrim të ri
pdfjs-editor-signature-add-signature-button-label = Shtoni nënshkrim të ri
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Nënshkrim i ruajtur: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Përpunues Tekstesh
    .default-content = Filloni të shtypni…
pdfjs-free-text =
    .aria-label = Përpunues Tekstesh
pdfjs-free-text-default-content = Filloni të shtypni…
pdfjs-ink =
    .aria-label = Përpunues Vizatimesh
pdfjs-ink-canvas =
    .aria-label = Figurë e krijuar nga përdoruesi

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Tekst alternativ
pdfjs-editor-alt-text-edit-button =
    .aria-label = Përpunoni tekst alternativ
pdfjs-editor-alt-text-edit-button-label = Përpunoni tekst alternativ
pdfjs-editor-alt-text-dialog-label = Zgjidhni një mundësi
pdfjs-editor-alt-text-dialog-description = Teksti alt (tekst alternativ) vjen në ndihmë kur njerëzit s’mund të shohin figurën, ose kur ajo nuk ngarkohet.
pdfjs-editor-alt-text-add-description-label = Shtoni një përshkrim
pdfjs-editor-alt-text-add-description-description = Synoni për 1-2 togfjalësha që përshkruajnë subjektin, rrethanat apo veprimet.
pdfjs-editor-alt-text-mark-decorative-label = Vëri shenjë si dekorative
pdfjs-editor-alt-text-mark-decorative-description = Kjo përdoret për figura zbukuruese, fjala vjen, anë, ose watermark-e.
pdfjs-editor-alt-text-cancel-button = Anuloje
pdfjs-editor-alt-text-save-button = Ruaje
pdfjs-editor-alt-text-decorative-tooltip = Iu vu shenjë si dekorative
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Për shembull, “Një djalosh ulet në një tryezë të hajë”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Tekst alternativ

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Cepi i sipërm majtas — ripërmasojeni
pdfjs-editor-resizer-label-top-middle = Mesi i pjesës sipër — ripërmasojeni
pdfjs-editor-resizer-label-top-right = Cepi i sipërm djathtas — ripërmasojeni
pdfjs-editor-resizer-label-middle-right = Djathtas në mes — ripërmasojeni
pdfjs-editor-resizer-label-bottom-right = Cepi i poshtëm djathtas — ripërmasojeni
pdfjs-editor-resizer-label-bottom-middle = Mesi i pjesës poshtë — ripërmasojeni
pdfjs-editor-resizer-label-bottom-left = Cepi i poshtëm — ripërmasojeni
pdfjs-editor-resizer-label-middle-left = Majtas në mes — ripërmasojeni
pdfjs-editor-resizer-top-left =
    .aria-label = Cepi i sipërm majtas — ripërmasojeni
pdfjs-editor-resizer-top-middle =
    .aria-label = Mesi i pjesës sipër — ripërmasojeni
pdfjs-editor-resizer-top-right =
    .aria-label = Cepi i sipërm djathtas — ripërmasojeni
pdfjs-editor-resizer-middle-right =
    .aria-label = Djathtas në mes — ripërmasojeni
pdfjs-editor-resizer-bottom-right =
    .aria-label = Cepi i poshtëm djathtas — ripërmasojeni
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Mesi i pjesës poshtë — ripërmasojeni
pdfjs-editor-resizer-bottom-left =
    .aria-label = Cepi i poshtëm — ripërmasojeni
pdfjs-editor-resizer-middle-left =
    .aria-label = Majtas në mes — ripërmasojeni

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Ngjyrë theksimi
pdfjs-editor-colorpicker-button =
    .title = Ndryshoni ngjyrë
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Zgjedhje ngjyre
pdfjs-editor-colorpicker-yellow =
    .title = E verdhë
pdfjs-editor-colorpicker-green =
    .title = E gjelbër
pdfjs-editor-colorpicker-blue =
    .title = Blu
pdfjs-editor-colorpicker-pink =
    .title = Rozë
pdfjs-editor-colorpicker-red =
    .title = E kuqe

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Shfaqi krejt
pdfjs-editor-highlight-show-all-button =
    .title = Shfaqi krejt

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Përpunoni tekst alternativ (përshkrim figure)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Shtoni tekst alternativ (përshkrim figure)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Shkruani këtu përshkrimin tuaj…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Përshkrim i shkurtër për persona që s’munden të shohin figurën, ose për kur figura nuk ngarkohet dot.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ky tekst alternativ qe krijuar automatikisht dhe mund të jetë i pasaktë.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Mësoni më tepër
pdfjs-editor-new-alt-text-create-automatically-button-label = Krijo automatikisht tekst alternativ
pdfjs-editor-new-alt-text-not-now-button = Jo tani
pdfjs-editor-new-alt-text-error-title = S’u krijua dot automatikisht tekst alternativ
pdfjs-editor-new-alt-text-error-description = Ju lutemi, shkruani tekstin tuaj alternativ, ose riprovoni më vonë.
pdfjs-editor-new-alt-text-error-close-button = Mbylle
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Po shkarkohet model IA teksti alternativ ({ $downloadedSize } nga { $totalSize } MB)
    .aria-valuetext = Po shkarkohet model IA teksti alternativ ({ $downloadedSize } nga { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = U shtua tekst alternativ
pdfjs-editor-new-alt-text-added-button-label = U shtua tekst alternativ
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Mungon tekst alternativ
pdfjs-editor-new-alt-text-missing-button-label = Mungon tekst alternativ
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Shqyrtoni tekst alternativ
pdfjs-editor-new-alt-text-to-review-button-label = Shqyrtoni tekst alternativ
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Krijuar automatikisht: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Rregullime teksti alternativ figure
pdfjs-image-alt-text-settings-button-label = Rregullime teksti alternativ figure
pdfjs-editor-alt-text-settings-dialog-label = Rregullime teksti alternativ figure
pdfjs-editor-alt-text-settings-automatic-title = Tekst alternativ i automatizuar
pdfjs-editor-alt-text-settings-create-model-button-label = Krijo automatikisht tekst alternativ
pdfjs-editor-alt-text-settings-create-model-description = Sugjeron përshkrime, për të ndihmuar persona që s’munden të shohin figurën, ose për kur figura nuk ngarkohet dot.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Model IA teksti alternativ ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Xhiron lokalisht në pajisjen tuaj, pra të dhënat tuaja mbeten private. E domosdoshme për tekst të automatizuar alternativ.
pdfjs-editor-alt-text-settings-delete-model-button = Fshije
pdfjs-editor-alt-text-settings-download-model-button = Shkarkoje
pdfjs-editor-alt-text-settings-downloading-model-button = Po shkarkohet…
pdfjs-editor-alt-text-settings-editor-title = Përpunues teksti alternativ
pdfjs-editor-alt-text-settings-show-dialog-button-label = Shfaq menjëherë përpunues teksti alternativ, kur shtohet një figurë
pdfjs-editor-alt-text-settings-show-dialog-description = Ju ndihmon të siguroheni se krejt figurat tuaja kanë tekst alternativ.
pdfjs-editor-alt-text-settings-close-button = Mbylle

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = U hoq theksimi
pdfjs-editor-undo-bar-message-freetext = U hoq tekst
pdfjs-editor-undo-bar-message-ink = U hoq vizatim
pdfjs-editor-undo-bar-message-stamp = U hoq figurë
pdfjs-editor-undo-bar-message-signature = Nënshkrimi u hoq
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] U hoq { $count } shënim
       *[other] U hoqën { $count } shënime
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Zhbëje
pdfjs-editor-undo-bar-undo-button-label = Zhbëje
pdfjs-editor-undo-bar-close-button =
    .title = Mbylle
pdfjs-editor-undo-bar-close-button-label = Mbylle

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Kjo dritare modale i lejon përdoruesit të krijojë një nënshkrim për ta shtuar te një dokument PDF. Përdoruesi mund të përpunojë emrin (i cili shërben edhe si tekst alternativ) dhe, nëse do, ta ruajë nënshkrimin, për ta përdorur prapë.
pdfjs-editor-add-signature-dialog-title = Shtoni një nënshkrim

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Lloj
    .title = Lloj
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Vizatoni
    .title = Vizatoni
pdfjs-editor-add-signature-image-button = Figurë
    .title = Figurë

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Shtypni nënshkrimin tuaj
    .placeholder = Shtypni nënshkrimin tuaj
pdfjs-editor-add-signature-draw-placeholder = Vizatoni nënshkrimin tuaj
pdfjs-editor-add-signature-draw-thickness-range-label = Trashësi
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Trashësi vizatimi: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Tërhiqni këtu një kartelë për ngarkim
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ose zgjidhni kartelë figure
       *[other] Ose zgjidhni kartelë figure
    }

## Controls

pdfjs-editor-add-signature-description-label = Përshkrim (tekst alternativ)
pdfjs-editor-add-signature-description-input =
    .title = Përshkrim (tekst alternativ)
pdfjs-editor-add-signature-description-default-when-drawing = Nënshkrim
pdfjs-editor-add-signature-clear-button-label = Spastroje nënshkrimin
pdfjs-editor-add-signature-clear-button =
    .title = Spastroje nënshkrimin
pdfjs-editor-add-signature-save-checkbox = Ruaje nënshkrimin
pdfjs-editor-add-signature-save-warning-message = Keni mbërritur në kufirin e 5 nënshkrimeve të ruajtura. Që të ruani tjetër, hiqni një.
pdfjs-editor-add-signature-image-upload-error-title = S’u ngarkua dot figurë
pdfjs-editor-add-signature-image-upload-error-description = Kontrolloni lidhjen tuaj në rrjet, ose provoni figurë tjetër.
pdfjs-editor-add-signature-error-close-button = Mbylle

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Anuloje
pdfjs-editor-add-signature-add-button = Shtoje
pdfjs-editor-edit-signature-update-button = Përditësoje

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Hiqe nënshkrimin e ruajtur
pdfjs-editor-delete-signature-button-label1 = Hiqe nënshkrimin e ruajtur

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Përpunoni përshkrimin

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Përpunoni përshkrimin
