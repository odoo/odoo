# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Tudalen Flaenorol
pdfjs-previous-button-label = Blaenorol
pdfjs-next-button =
    .title = Tudalen Nesaf
pdfjs-next-button-label = Nesaf
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Tudalen
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = o { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } o { $pagesCount })
pdfjs-zoom-out-button =
    .title = Lleihau
pdfjs-zoom-out-button-label = Lleihau
pdfjs-zoom-in-button =
    .title = Cynyddu
pdfjs-zoom-in-button-label = Cynyddu
pdfjs-zoom-select =
    .title = Chwyddo
pdfjs-presentation-mode-button =
    .title = Newid i'r Modd Cyflwyno
pdfjs-presentation-mode-button-label = Modd Cyflwyno
pdfjs-open-file-button =
    .title = Agor Ffeil
pdfjs-open-file-button-label = Agor
pdfjs-print-button =
    .title = Argraffu
pdfjs-print-button-label = Argraffu
pdfjs-save-button =
    .title = Cadw
pdfjs-save-button-label = Cadw
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Llwytho i lawr
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Llwytho i lawr
pdfjs-bookmark-button =
    .title = Tudalen Gyfredol (Gweld URL o'r Dudalen Gyfredol)
pdfjs-bookmark-button-label = Tudalen Gyfredol

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Offer
pdfjs-tools-button-label = Offer
pdfjs-first-page-button =
    .title = Mynd i'r Dudalen Gyntaf
pdfjs-first-page-button-label = Mynd i'r Dudalen Gyntaf
pdfjs-last-page-button =
    .title = Mynd i'r Dudalen Olaf
pdfjs-last-page-button-label = Mynd i'r Dudalen Olaf
pdfjs-page-rotate-cw-button =
    .title = Cylchdroi Clocwedd
pdfjs-page-rotate-cw-button-label = Cylchdroi Clocwedd
pdfjs-page-rotate-ccw-button =
    .title = Cylchdroi Gwrthglocwedd
pdfjs-page-rotate-ccw-button-label = Cylchdroi Gwrthglocwedd
pdfjs-cursor-text-select-tool-button =
    .title = Galluogi Dewis Offeryn Testun
pdfjs-cursor-text-select-tool-button-label = Offeryn Dewis Testun
pdfjs-cursor-hand-tool-button =
    .title = Galluogi Offeryn Llaw
pdfjs-cursor-hand-tool-button-label = Offeryn Llaw
pdfjs-scroll-page-button =
    .title = Defnyddio Sgrolio Tudalen
pdfjs-scroll-page-button-label = Sgrolio Tudalen
pdfjs-scroll-vertical-button =
    .title = Defnyddio Sgrolio Fertigol
pdfjs-scroll-vertical-button-label = Sgrolio Fertigol
pdfjs-scroll-horizontal-button =
    .title = Defnyddio Sgrolio Llorweddol
pdfjs-scroll-horizontal-button-label = Sgrolio Llorweddol
pdfjs-scroll-wrapped-button =
    .title = Defnyddio Sgrolio Amlapio
pdfjs-scroll-wrapped-button-label = Sgrolio Amlapio
pdfjs-spread-none-button =
    .title = Peidio uno trawsdaleniadau
pdfjs-spread-none-button-label = Dim Trawsdaleniadau
pdfjs-spread-odd-button =
    .title = Uno trawsdaleniadau gan gychwyn gyda thudalennau odrif
pdfjs-spread-odd-button-label = Trawsdaleniadau Odrif
pdfjs-spread-even-button =
    .title = Uno trawsdaleniadau gan gychwyn gyda thudalennau eilrif
pdfjs-spread-even-button-label = Trawsdaleniadau Eilrif

## Document properties dialog

pdfjs-document-properties-button =
    .title = Priodweddau Dogfen…
pdfjs-document-properties-button-label = Priodweddau Dogfen…
pdfjs-document-properties-file-name = Enw ffeil:
pdfjs-document-properties-file-size = Maint ffeil:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } beit)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } beit)
pdfjs-document-properties-title = Teitl:
pdfjs-document-properties-author = Awdur:
pdfjs-document-properties-subject = Pwnc:
pdfjs-document-properties-keywords = Allweddair:
pdfjs-document-properties-creation-date = Dyddiad Creu:
pdfjs-document-properties-modification-date = Dyddiad Addasu:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Crewr:
pdfjs-document-properties-producer = Cynhyrchydd PDF:
pdfjs-document-properties-version = Fersiwn PDF:
pdfjs-document-properties-page-count = Cyfrif Tudalen:
pdfjs-document-properties-page-size = Maint Tudalen:
pdfjs-document-properties-page-size-unit-inches = o fewn
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = portread
pdfjs-document-properties-page-size-orientation-landscape = tirlun
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Llythyr
pdfjs-document-properties-page-size-name-legal = Cyfreithiol

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
pdfjs-document-properties-linearized = Golwg Gwe Cyflym:
pdfjs-document-properties-linearized-yes = Iawn
pdfjs-document-properties-linearized-no = Na
pdfjs-document-properties-close-button = Cau
pdfjs-digital-signature-properties-view-certificate = Gweld tystysgrif
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Rheswm: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Stamp amser: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [zero] Is-lofnodion ( { $count } )
        [one] Is-lofnodion ( { $count } )
        [two] Is-lofnodion ( { $count } )
        [few] Is-lofnodion ( { $count } )
        [many] Is-lofnodion ( { $count } )
       *[other] Is-lofnodion ( { $count } )
    }

## Print

pdfjs-print-progress-message = Paratoi dogfen ar gyfer ei hargraffu…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Diddymu
pdfjs-printing-not-supported = Rhybudd: Nid yw argraffu yn cael ei gynnal yn llawn gan y porwr.
pdfjs-printing-not-ready = Rhybudd: Nid yw'r PDF wedi ei lwytho'n llawn ar gyfer argraffu.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Canfod yr Eitem Amlinellol Gyfredol
pdfjs-current-outline-item-button-label = Yr Eitem Amlinellol Gyfredol
pdfjs-findbar-button =
    .title = Canfod yn y Ddogfen
pdfjs-findbar-button-label = Canfod
pdfjs-additional-layers = Haenau Ychwanegol

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Llun Bach Tudalen { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Dewis tudalen { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Tudalen { $page } o { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Canfod yn y ddogfen…
    .title = Canfod
pdfjs-find-previous-button =
    .title = Canfod enghraifft flaenorol o'r ymadrodd
pdfjs-find-previous-button-label = Blaenorol
pdfjs-find-next-button =
    .title = Canfod enghraifft nesaf yr ymadrodd
pdfjs-find-next-button-label = Nesaf
pdfjs-find-highlight-checkbox = Amlygu Popeth
pdfjs-find-match-case-checkbox-label = Cydweddu Maint
pdfjs-find-match-diacritics-checkbox-label = Diacritigau Cyfatebol
pdfjs-find-entire-word-checkbox-label = Geiriau Cyfan
pdfjs-find-reached-top = Wedi cyrraedd brig y dudalen, parhau o'r gwaelod
pdfjs-find-reached-bottom = Wedi cyrraedd diwedd y dudalen, parhau o'r brig
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [zero] { $current } o { $total } cydweddiadau
        [one] { $current } o { $total } cydweddiad
        [two] { $current } o { $total } gydweddiad
        [few] { $current } o { $total } cydweddiad
        [many] { $current } o { $total } chydweddiad
       *[other] { $current } o { $total } cydweddiad
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [zero] Mwy nag { $limit } cydweddiadau
        [one] Mwy nag { $limit } cydweddiad
        [two] Mwy nag { $limit } gydweddiad
        [few] Mwy nag { $limit } cydweddiad
        [many] Mwy nag { $limit } chydweddiad
       *[other] Mwy nag { $limit } cydweddiad
    }
pdfjs-find-not-found = Heb ganfod ymadrodd

## Predefined zoom values

pdfjs-page-scale-width = Lled Tudalen
pdfjs-page-scale-fit = Ffit Tudalen
pdfjs-page-scale-auto = Chwyddo Awtomatig
pdfjs-page-scale-actual = Maint Gwirioneddol
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Tudalen { $page }

## Loading indicator messages

pdfjs-loading-error = Digwyddodd gwall wrth lwytho'r PDF.
pdfjs-invalid-file-error = Ffeil PDF annilys neu llwgr.
pdfjs-missing-file-error = Ffeil PDF coll.
pdfjs-unexpected-response-error = Ymateb annisgwyl gan y gweinydd.
pdfjs-rendering-error = Digwyddodd gwall wrth adeiladu'r dudalen.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Anodiad { $type } ]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Rhowch gyfrinair i agor y PDF.
pdfjs-password-invalid = Cyfrinair annilys. Ceisiwch eto.
pdfjs-password-ok-button = Iawn
pdfjs-password-cancel-button = Diddymu
pdfjs-web-fonts-disabled = Ffontiau gwe wedi eu hanalluogi: methu defnyddio ffontiau PDF mewnblanedig.

## Editing

pdfjs-editor-free-text-button =
    .title = Testun
pdfjs-editor-color-picker-free-text-input =
    .title = Newid lliw testun
pdfjs-editor-free-text-button-label = Testun
pdfjs-editor-ink-button =
    .title = Lluniadu
pdfjs-editor-color-picker-ink-input =
    .title = Newid lliw lluniadu
pdfjs-editor-ink-button-label = Lluniadu
pdfjs-editor-stamp-button =
    .title = Ychwanegu neu olygu delweddau
pdfjs-editor-stamp-button-label = Ychwanegu neu olygu delweddau
pdfjs-editor-highlight-button =
    .title = Amlygu
pdfjs-editor-highlight-button-label = Amlygu
pdfjs-highlight-floating-button1 =
    .aria-label = Amlygu
    .title = Amlygu
pdfjs-highlight-floating-button-label = Amlygu
pdfjs-comment-floating-button =
    .aria-label = Sylw
    .title = Sylw
pdfjs-comment-floating-button-label = Sylw
pdfjs-editor-comment-button =
    .aria-label = Sylw
    .title = Sylw
pdfjs-editor-comment-button-label = Sylw
pdfjs-editor-signature-button =
    .title = Ychwanegu llofnod
pdfjs-editor-signature-button-label = Ychwanegu llofnod

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Golygydd amlygu
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Golygydd lluniadu
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Golygydd llofnod: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Golygydd delweddau

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Dileu lluniad
pdfjs-editor-remove-freetext-button =
    .title = Dileu testun
pdfjs-editor-remove-stamp-button =
    .title = Dileu delwedd
pdfjs-editor-remove-highlight-button =
    .title = Tynnu amlygiad
pdfjs-editor-remove-signature-button =
    .title = Dileu llofnod

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Lliw
pdfjs-editor-free-text-size-input = Maint
pdfjs-editor-ink-color-input = Lliw
pdfjs-editor-ink-thickness-input = Trwch
pdfjs-editor-ink-opacity-input = Didreiddedd
pdfjs-editor-stamp-add-image-button =
    .title = Ychwanegu delwedd
pdfjs-editor-stamp-add-image-button-label = Ychwanegu delwedd
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Trwch
pdfjs-editor-free-highlight-thickness-title =
    .title = Newid trwch wrth amlygu eitemau heblaw testun
pdfjs-editor-add-signature-container =
    .aria-label = Rheolyddion llofnodion a llofnodion wedi'u cadw
pdfjs-editor-signature-add-signature-button =
    .title = Ychwanegu llofnod newydd
pdfjs-editor-signature-add-signature-button-label = Ychwanegu llofnod newydd
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Llofnod wedi'i gadw: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Golygydd Testun
    .default-content = Cychwyn teipio…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [zero] Sylwadau
        [one] Sylw
        [two] Sylw
        [few] Sylw
        [many] Sylw
       *[other] Sylw
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Cau'r bar ochr
    .title = Cau'r bar ochr
pdfjs-editor-comments-sidebar-close-button-label = Cau'r bar ochr
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Gweld rhywbeth nodedig? Amlygwch ef a gadael sylw.
pdfjs-editor-comments-sidebar-no-comments-link = Dysgu rhagor

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Testun amgen (alt)
pdfjs-editor-alt-text-edit-button =
    .aria-label = Golygu testun amgen
pdfjs-editor-alt-text-dialog-label = Dewisiadau
pdfjs-editor-alt-text-dialog-description = Mae testun amgen (testun alt) yn helpu pan na all pobl weld y ddelwedd neu pan nad yw'n llwytho.
pdfjs-editor-alt-text-add-description-label = Ychwanegu disgrifiad
pdfjs-editor-alt-text-add-description-description = Anelwch at 1-2 frawddeg sy'n disgrifio'r pwnc, y cefndir neu'r gweithredoedd.
pdfjs-editor-alt-text-mark-decorative-label = Marcio fel addurniadol
pdfjs-editor-alt-text-mark-decorative-description = Mae'n cael ei ddefnyddio ar gyfer delweddau addurniadol, fel borderi neu farciau dŵr.
pdfjs-editor-alt-text-cancel-button = Diddymu
pdfjs-editor-alt-text-save-button = Cadw
pdfjs-editor-alt-text-decorative-tooltip = Marcio fel addurniadol
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Er enghraifft, “Mae dyn ifanc yn eistedd wrth fwrdd i fwyta pryd bwyd”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Testun amgen (alt)

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Y gornel chwith uchaf — newid maint
pdfjs-editor-resizer-top-middle =
    .aria-label = Canol uchaf - newid maint
pdfjs-editor-resizer-top-right =
    .aria-label = Y gornel dde uchaf - newid maint
pdfjs-editor-resizer-middle-right =
    .aria-label = De canol - newid maint
pdfjs-editor-resizer-bottom-right =
    .aria-label = Y gornel dde isaf — newid maint
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Canol gwaelod — newid maint
pdfjs-editor-resizer-bottom-left =
    .aria-label = Y gornel chwith isaf — newid maint
pdfjs-editor-resizer-middle-left =
    .aria-label = Chwith canol — newid maint

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Lliw amlygu
pdfjs-editor-colorpicker-button =
    .title = Newid lliw
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Dewisiadau lliw
pdfjs-editor-colorpicker-yellow =
    .title = Melyn
pdfjs-editor-colorpicker-green =
    .title = Gwyrdd
pdfjs-editor-colorpicker-blue =
    .title = Glas
pdfjs-editor-colorpicker-pink =
    .title = Pinc
pdfjs-editor-colorpicker-red =
    .title = Coch

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Dangos y cyfan
pdfjs-editor-highlight-show-all-button =
    .title = Dangos y cyfan

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Golygu testun amgen (disgrifiad o ddelwedd)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Ychwanegwch destun amgen (disgrifiad delwedd)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Ysgrifennwch eich disgrifiad yma…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Disgrifiad byr ar gyfer pobl sydd ddim yn gallu gweld y ddelwedd neu pan nad yw'r ddelwedd yn llwytho.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Cafodd y testun amgen hwn ei greu'n awtomatig a gall fod yn anghywir.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Rhagor
pdfjs-editor-new-alt-text-create-automatically-button-label = Creu testun amgen yn awtomatig
pdfjs-editor-new-alt-text-not-now-button = Nid nawr
pdfjs-editor-new-alt-text-error-title = Methu â chreu testun amgen yn awtomatig
pdfjs-editor-new-alt-text-error-description = Ysgrifennwch eich testun amgen eich hun neu ceisiwch eto yn nes ymlaen.
pdfjs-editor-new-alt-text-error-close-button = Cau
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Wrthi'n llwytho i lawr model AI testun amgen ( { $downloadedSize } o { $totalSize } MB)
    .aria-valuetext = Wrthi'n llwytho i lawr model AI testun amgen ( { $downloadedSize } o { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Ychwanegwyd testun amgen
pdfjs-editor-new-alt-text-added-button-label = Ychwanegwyd testun amgen
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Testun amgen coll
pdfjs-editor-new-alt-text-missing-button-label = Testun amgen coll
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Adolygu'r testun amgen
pdfjs-editor-new-alt-text-to-review-button-label = Adolygu'r testun amgen
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Crëwyd yn awtomatig: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Gosodiadau testun amgen delwedd
pdfjs-image-alt-text-settings-button-label = Gosodiadau testun amgen delwedd
pdfjs-editor-alt-text-settings-dialog-label = Gosodiadau testun amgen delwedd
pdfjs-editor-alt-text-settings-automatic-title = Testun amgen awtomatig
pdfjs-editor-alt-text-settings-create-model-button-label = Creu testun amgen yn awtomatig
pdfjs-editor-alt-text-settings-create-model-description = Yn awgrymu disgrifiadau i helpu pobl sydd ddim yn gallu gweld y ddelwedd neu pan nad yw'r ddelwedd yn llwytho.
pdfjs-editor-alt-text-settings-editor-title = Golygydd testun amgen
pdfjs-editor-alt-text-settings-show-dialog-button-label = Dangoswch y golygydd testun amgen yn syth wrth ychwanegu delwedd
pdfjs-editor-alt-text-settings-show-dialog-description = Yn eich helpu i wneud yn siŵr bod gan eich holl ddelweddau destun amgen.
pdfjs-editor-alt-text-settings-close-button = Cau

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Amlygu wedi'i ychwanegu
pdfjs-editor-freetext-added-alert = Testun wedi'i ychwanegu
pdfjs-editor-ink-added-alert = Lluniadu wedi'i ychwanegu
pdfjs-editor-stamp-added-alert = Delwedd wedi'i hychwanegu
pdfjs-editor-signature-added-alert = Llofnod wedi'i ychwanegu

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Tynnwyd yr amlygu
pdfjs-editor-undo-bar-message-freetext = Tynnwyd y testun
pdfjs-editor-undo-bar-message-ink = Tynnwyd y lluniad
pdfjs-editor-undo-bar-message-stamp = Tynnwyd y ddelwedd
pdfjs-editor-undo-bar-message-signature = Llofnod wedi'i dynnu
pdfjs-editor-undo-bar-message-comment = Sylw wedi'i dynnu
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [zero] { $count } anodiad wedi'u tynnu
        [one] { $count } anodiad wedi'i dynnu
        [two] { $count } anodiad wedi'u tynnu
        [few] { $count } anodiad wedi'u tynnu
        [many] { $count } anodiad wedi'u tynnu
       *[other] { $count } anodiad wedi'u tynnu
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Dadwneud
pdfjs-editor-undo-bar-undo-button-label = Dadwneud
pdfjs-editor-undo-bar-close-button =
    .title = Cau
pdfjs-editor-undo-bar-close-button-label = Cau

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Mae'r modd hwn yn caniatáu i'r defnyddiwr greu llofnod i'w ychwanegu at ddogfen PDF. Gall y defnyddiwr olygu'r enw (sydd hefyd yn gweithredu fel y testun amgen), ac yn ddewisol cadw'r llofnod i'w ddefnyddio dro ar ôl tro.
pdfjs-editor-add-signature-dialog-title = Ychwanegu llofnod

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Math
    .title = Math
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Lluniadu
    .title = Lluniadu
pdfjs-editor-add-signature-image-button = Delwedd
    .title = Delwedd

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Teipiwch eich llofnod
    .placeholder = Teipiwch eich llofnod
pdfjs-editor-add-signature-draw-placeholder = Lluniwch eich llofnod
pdfjs-editor-add-signature-draw-thickness-range-label = Trwch
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Trwch y llinell: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Llusgwch ffeil yma i'w llwytho
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Neu ddewis ffeiliau delwedd
       *[other] Neu bori ffeiliau delwedd
    }

## Controls

pdfjs-editor-add-signature-description-label = Disgrifiad (testun amgen)
pdfjs-editor-add-signature-description-input =
    .title = Disgrifiad (testun amgen)
pdfjs-editor-add-signature-description-default-when-drawing = Llofnod
pdfjs-editor-add-signature-clear-button-label = Diddymu llofnod
pdfjs-editor-add-signature-clear-button =
    .title = Diddymu llofnod
pdfjs-editor-add-signature-save-checkbox = Cadw llofnod
pdfjs-editor-add-signature-save-warning-message = Rydych chi wedi cyrraedd y terfyn o 5 llofnod sydd wedi'u cadw. Tynnwch un i gadw rhagor
pdfjs-editor-add-signature-image-upload-error-title = Methu llwytho'r ddelwedd.
pdfjs-editor-add-signature-image-upload-error-description = Gwiriwch eich cysylltiad rhwydwaith neu rhowch gynnig ar ddelwedd arall.
pdfjs-editor-add-signature-image-no-data-error-title = Methu trosi'r ddelwedd hon yn llofnod
pdfjs-editor-add-signature-image-no-data-error-description = Ceisiwch lwytho delwedd wahanol.
pdfjs-editor-add-signature-error-close-button = Cau

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Diddymu
pdfjs-editor-add-signature-add-button = Ychwanegu
pdfjs-editor-edit-signature-update-button = Diweddaru

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Golygu sylw
pdfjs-editor-edit-comment-popup-button =
    .title = Golygu sylw
pdfjs-editor-delete-comment-popup-button-label = Tynnu sylw
pdfjs-editor-delete-comment-popup-button =
    .title = Tynnu sylw
pdfjs-show-comment-button =
    .title = Dangos sylw

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Golygu sylw
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Diweddaru
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Ychwanegu sylw
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Ychwanegu
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Cychwyn teipio…
pdfjs-editor-edit-comment-dialog-cancel-button = Diddymu

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Ychwanegu sylw

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Togl y Bar Ochr (dogfen yn cynnwys lluniau bach/amlinelliad/atodiadau/haenau)
pdfjs-toggle-views-manager-button1-label = Rheoli tudalennau
pdfjs-views-manager-sidebar =
    .aria-label = Bar Ochr
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Newid maint bar ochr
pdfjs-views-manager-view-selector-button =
    .title = Golygon
pdfjs-views-manager-view-selector-button-label = Golygon
pdfjs-views-manager-pages-title = Tudalennau
pdfjs-views-manager-outlines-title1 = Amlinelliad Dogfen
    .title = Amlinelliad dogfen (clic dwbl i ehangu/leihau pob eitem)
pdfjs-views-manager-attachments-title = Atodiadau
pdfjs-views-manager-layers-title1 = Haenau
    .title = Haenau clic dwbl i ailosod pob haen i'r cyflwr ragosodedig)
pdfjs-views-manager-pages-option-label = Tudalennau
pdfjs-views-manager-outlines-option-label = Amlinelliad dogfen
pdfjs-views-manager-attachments-option-label = Atodiadau
pdfjs-views-manager-layers-option-label = Haenau
pdfjs-views-manager-add-file-button =
    .title = Ychwanegu ffeil
pdfjs-views-manager-add-file-button-label = Ychwanegu ffeil
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [zero] { $count } wedi'u dewis
        [one] { $count } wedi'i dewis
        [two] { $count } wedi'u dewis
        [few] { $count } wedi'u dewis
        [many] { $count } wedi'u dewis
       *[other] { $count } wedi'u dewis
    }
pdfjs-views-manager-pages-status-none-action-label = Dewiswch dudalennau
pdfjs-views-manager-pages-status-action-button-label = Rheoli
pdfjs-views-manager-pages-status-copy-button-label = Copïo
pdfjs-views-manager-pages-status-cut-button-label = Torri
pdfjs-views-manager-pages-status-delete-button-label = Dileu
pdfjs-views-manager-pages-status-export-selected-button-label = Wedi dewis allforio…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [zero] { $count } tudalennau wedi'u torri
        [one] { $count } dudalen wedi'i thorri
        [two] { $count } dudalen wedi'u torri
        [few] { $count } tudalen wedi'u torri
        [many] { $count } tudalen wedi'u torri
       *[other] { $count } tudalen wedi'u torri
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [zero] { $count } tudalennau wedi'u copïo
        [one] { $count } tudalen wedi'i chopïo
        [two] { $count } tudalen wedi'u copïo
        [few] { $count } tudalen wedi'u copïo
        [many] { $count } tudalen wedi'u copïo
       *[other] { $count } tudalen wedi'u copïo
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [zero] { $count } tudalennau wedi'u dileu
        [one] { $count } tudalen wedi'i dileu
        [two] { $count } dudalen wedi'u dileu
        [few] { $count } tudalen wedi'u dileu
        [many] { $count } tudalen wedi'u dileu
       *[other] { $count } tudalen wedi'u dileu
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Yn paratoi eich ffeil…
pdfjs-views-manager-pages-status-waiting-uploading-label = Yn llwytho ffeil i fyny…
pdfjs-views-manager-status-warning-cut-label = Methu torri. Adnewyddwch y dudalen a cheisio eto.
pdfjs-views-manager-status-warning-copy-label = Methu copïo. Adnewyddwch y dudalen a cheisio eto.
pdfjs-views-manager-status-warning-delete-label = Methu dileu. Adnewyddwch y dudalen a cheisio eto.
pdfjs-views-manager-status-warning-save-label = Methu cadw. Adnewyddwch y dudalen a cheisio eto.
pdfjs-views-manager-status-undo-button-label = Dadwneud
pdfjs-views-manager-status-done-button-label = Gorffen
pdfjs-views-manager-status-close-button =
    .title = Cau
pdfjs-views-manager-status-close-button-label = Cau
pdfjs-views-manager-paste-button-label = Gludo
pdfjs-views-manager-paste-button-before =
    .title = Gludo cyn y dudalen gyntaf
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Gludo ar ôl tudalen { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NEWYDD
pdfjs-views-manager-waiting-for-file = Yn llwytho ffeil i fyny…
pdfjs-toggle-views-manager-button1 =
    .title = Rheoli tudalennau

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Priodweddau llofnod digidol
    .title = Priodweddau llofnod digidol
pdfjs-digital-signature-properties-button-label = Priodweddau llofnod digidol

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Llofnodwyd y ddogfen gyda llofnod digidol dilys
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [zero] Llofnodwyd y ddogfen ond doedd dim modd dilysu { $count } llofnod digidol
        [one] Llofnodwyd y ddogfen ond doedd dim modd dilysu { $count } llofnod digidol
        [two] Llofnodwyd y ddogfen ond doedd dim modd dilysu { $count } llofnod digidol
        [few] Llofnodwyd y ddogfen ond doedd dim modd dilysu { $count } llofnod digidol
        [many] Llofnodwyd y ddogfen ond doedd dim modd dilysu { $count } llofnod digidol
       *[other] Llofnodwyd y ddogfen ond doedd dim modd dilysu { $count } llofnod digidol
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [zero] Dogfen wedi'i llofnodi â { $count } thystysgrif does dim modd ymddiried ynddyn nhw
        [one] Dogfen wedi'i llofnodi â { $count } thystysgrif does dim modd ymddiried ynddi
        [two] Dogfen wedi'i llofnodi â { $count } thystysgrifau does dim modd ymddiried ynddyn nhw
        [few] Dogfen wedi'i llofnodi â { $count } thystysgrifau does dim modd ymddiried ynddyn nhw
        [many] Dogfen wedi'i llofnodi â { $count } thystysgrifau does dim modd ymddiried ynddyn nhw
       *[other] Dogfen wedi'i llofnodi â { $count } thystysgrifau does dim modd ymddiried ynddyn nhw
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [zero] Dogfen wedi'i llofnodi gyda { $count } tystysgrifau sydd wedi dod i ben
        [one] Dogfen wedi'i llofnodi gydag { $count } dystysgrif sydd wedi dod i ben
        [two] Dogfen wedi'i llofnodi gyda { $count } dystysgrif sydd wedi dod i ben
        [few] Dogfen wedi'i llofnodi gyda { $count } tystysgrif sydd wedi dod i ben
        [many] Dogfen wedi'i llofnodi gyda { $count } thystysgrif sydd wedi dod i ben
       *[other] Dogfen wedi'i llofnodi gyda { $count } tystysgrif sydd wedi dod i ben
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [zero] Mae gan y ddogfen { $count } llofnodion digidol annilys
        [one] Mae gan y ddogfen { $count } llofnod digidol annilys
        [two] Mae gan y ddogfen { $count } llofnod digidol annilys
        [few] Mae gan y ddogfen { $count } llofnod digidol annilys
        [many] Mae gan y ddogfen { $count } llofnod digidol annilys
       *[other] Mae gan y ddogfen { $count } llofnod digidol annilys
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [zero] Dogfen wedi'i llofnodi gyda { $count } tystysgrifau wedi'u dirymu
        [one] Dogfen wedi'i llofnodi gyda { $count } tystysgrif wedi'u dirymu
        [two] Dogfen wedi'i llofnodi gyda { $count } tystysgrif wedi'u dirymu
        [few] Dogfen wedi'i llofnodi gyda { $count } tystysgrif wedi'u dirymu
        [many] Dogfen wedi'i llofnodi gyda { $count } thystysgrif wedi'u dirymu
       *[other] Dogfen wedi'i llofnodi gyda { $count } tystysgrif wedi'u dirymu
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Statws: Llofnod wedi'i ddilysu
pdfjs-digital-signature-properties-status-invalid = Statws: Llofnod annilys
pdfjs-digital-signature-properties-status-unknown = Statws: Methu dilysu (heb ei gefnogi)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Tystysgrif: Wedi ymddiried ( { $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Tystysgrif: Ddim ar gael
pdfjs-digital-signature-properties-certificate-untrusted = Tystysgrif: Dim ymddiriedaeth
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Tystysgrif: Cyhoeddwr anhysbys ( { $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Tystysgrif: Hunan-lofnod ( { $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Tystysgrif: Cyhoeddwr heb ymddiriedaeth ( { $issuer })
pdfjs-digital-signature-properties-certificate-expired = Tystysgrif: Wedi dod i ben
pdfjs-digital-signature-properties-certificate-expired-with-date = Tystysgrif: Wedi dod i ben ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Tystysgrif: Wedi'i ddirymu

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Tynnu llofnod sydd wedi'i gadw
pdfjs-editor-delete-signature-button-label1 = Tynnwch y llofnod sydd wedi'i gadw

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Golygu disgrifiad

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Golygu disgrifiad
