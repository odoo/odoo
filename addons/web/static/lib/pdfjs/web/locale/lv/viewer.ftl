# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Iepriekšējā lapa
pdfjs-previous-button-label = Iepriekšējā
pdfjs-next-button =
    .title = Nākamā lapa
pdfjs-next-button-label = Nākamā
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Lapa
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = no { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } no { $pagesCount })
pdfjs-zoom-out-button =
    .title = Attālināt
pdfjs-zoom-out-button-label = Attālināt
pdfjs-zoom-in-button =
    .title = Pietuvināt
pdfjs-zoom-in-button-label = Pietuvināt
pdfjs-zoom-select =
    .title = Palielinājums
pdfjs-presentation-mode-button =
    .title = Pārslēgties uz Prezentācijas režīmu
pdfjs-presentation-mode-button-label = Prezentācijas režīms
pdfjs-open-file-button =
    .title = Atvērt failu
pdfjs-open-file-button-label = Atvērt
pdfjs-print-button =
    .title = Drukāšana
pdfjs-print-button-label = Drukāt

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Rīki
pdfjs-tools-button-label = Rīki
pdfjs-first-page-button =
    .title = Iet uz pirmo lapu
pdfjs-first-page-button-label = Iet uz pirmo lapu
pdfjs-last-page-button =
    .title = Iet uz pēdējo lapu
pdfjs-last-page-button-label = Iet uz pēdējo lapu
pdfjs-page-rotate-cw-button =
    .title = Pagriezt pa pulksteni
pdfjs-page-rotate-cw-button-label = Pagriezt pa pulksteni
pdfjs-page-rotate-ccw-button =
    .title = Pagriezt pret pulksteni
pdfjs-page-rotate-ccw-button-label = Pagriezt pret pulksteni
pdfjs-cursor-text-select-tool-button =
    .title = Aktivizēt teksta izvēles rīku
pdfjs-cursor-text-select-tool-button-label = Teksta izvēles rīks
pdfjs-cursor-hand-tool-button =
    .title = Aktivēt rokas rīku
pdfjs-cursor-hand-tool-button-label = Rokas rīks
pdfjs-scroll-vertical-button =
    .title = Izmantot statenisko ritināšanu
pdfjs-scroll-vertical-button-label = Stateniskā ritināšana
pdfjs-scroll-horizontal-button =
    .title = Izmantot līmenisko ritināšanu
pdfjs-scroll-horizontal-button-label = Līmeniskā ritināšana
pdfjs-scroll-wrapped-button =
    .title = Izmantot apkļauto ritināšanu
pdfjs-scroll-wrapped-button-label = Apkļautā ritināšana
pdfjs-spread-none-button =
    .title = Nepievienoties lapu izpletumiem
pdfjs-spread-none-button-label = Neizmantot izpletumus
pdfjs-spread-odd-button =
    .title = Izmantot lapu izpletumus sākot ar nepāra numuru lapām
pdfjs-spread-odd-button-label = Nepāra izpletumi
pdfjs-spread-even-button =
    .title = Izmantot lapu izpletumus sākot ar pāra numuru lapām
pdfjs-spread-even-button-label = Pāra izpletumi

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumenta iestatījumi…
pdfjs-document-properties-button-label = Dokumenta iestatījumi…
pdfjs-document-properties-file-name = Datnes nosaukums:
pdfjs-document-properties-file-size = Faila izmērs:
pdfjs-document-properties-title = Nosaukums:
pdfjs-document-properties-author = Autors:
pdfjs-document-properties-subject = Tēma:
pdfjs-document-properties-keywords = Atslēgas vārdi:
pdfjs-document-properties-creation-date = Izveides datums:
pdfjs-document-properties-modification-date = LAbošanas datums:
pdfjs-document-properties-creator = Radītājs:
pdfjs-document-properties-producer = PDF producents:
pdfjs-document-properties-version = PDF versija:
pdfjs-document-properties-page-count = Lapu skaits:
pdfjs-document-properties-page-size = Papīra izmērs:
pdfjs-document-properties-page-size-unit-inches = collas
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = portretorientācija
pdfjs-document-properties-page-size-orientation-landscape = ainavorientācija
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Vēstule
pdfjs-document-properties-page-size-name-legal = Juridiskie teksti

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
pdfjs-document-properties-linearized = Ātrā tīmekļa skats:
pdfjs-document-properties-linearized-yes = Jā
pdfjs-document-properties-linearized-no = Nē
pdfjs-document-properties-close-button = Aizvērt
pdfjs-digital-signature-properties-view-certificate = Apskatīt sertifikātu

## Print

pdfjs-print-progress-message = Gatavo dokumentu drukāšanai...
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Atcelt
pdfjs-printing-not-supported = Uzmanību: Drukāšana no šī pārlūka darbojas tikai daļēji.
pdfjs-printing-not-ready = Uzmanību: PDF nav pilnībā ielādēts drukāšanai.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-findbar-button =
    .title = Meklēt dokumentā
pdfjs-findbar-button-label = Meklēt

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Lapas { $page } sīktēls

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Meklēt dokumentā…
    .title = Meklēt
pdfjs-find-previous-button =
    .title = Atrast iepriekšējo
pdfjs-find-previous-button-label = Iepriekšējā
pdfjs-find-next-button =
    .title = Atrast nākamo
pdfjs-find-next-button-label = Nākamā
pdfjs-find-highlight-checkbox = Izcelt visus
pdfjs-find-match-case-checkbox-label = Lielo un mazo burtu atbilstība
pdfjs-find-match-diacritics-checkbox-label = Diakritisko zīmju atbilstība
pdfjs-find-entire-word-checkbox-label = Veselus vārdus
pdfjs-find-reached-top = Sasniegts dokumenta sākums, turpinām no beigām
pdfjs-find-reached-bottom = Sasniegtas dokumenta beigas, turpinām no sākuma
pdfjs-find-not-found = Vārdkopa nav atrasta

## Predefined zoom values

pdfjs-page-scale-width = Lapas platumā
pdfjs-page-scale-fit = Ietilpinot lapu
pdfjs-page-scale-auto = Automātiskais izmērs
pdfjs-page-scale-actual = Patiesais izmērs
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## Loading indicator messages

pdfjs-loading-error = Ielādējot PDF notika kļūda.
pdfjs-invalid-file-error = Nederīga vai bojāt PDF datne.
pdfjs-missing-file-error = PDF datne nav atrasta.
pdfjs-unexpected-response-error = Negaidīa servera atbilde.
pdfjs-rendering-error = Attēlojot lapu radās kļūda

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } anotācija]

## Password

pdfjs-password-label = Ievadiet paroli, lai atvērtu PDF failu.
pdfjs-password-invalid = Nepareiza parole, mēģiniet vēlreiz.
pdfjs-password-ok-button = Labi
pdfjs-password-cancel-button = Atcelt
pdfjs-web-fonts-disabled = Tīmekļa fonti nav aktivizēti: Nevar iegult PDF fontus.

## Editing

pdfjs-editor-stamp-button =
    .title = Pievienot vai labot attēlus
pdfjs-editor-stamp-button-label = Pievienot vai labot attēlus
pdfjs-editor-signature-button =
    .title = Pievienot parakstu
pdfjs-editor-signature-button-label = Pievienot parakstu

##

pdfjs-editor-stamp-add-image-button =
    .title = Pievienot attēlu
pdfjs-editor-stamp-add-image-button-label = Pievienot attēlu
pdfjs-editor-signature-add-signature-button =
    .title = Pievienot jaunu parakstu
pdfjs-editor-signature-add-signature-button-label = Pievienot jaunu parakstu

## Alt-text dialog

pdfjs-editor-alt-text-add-description-label = Pievienot aprakstu

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Uzzināt vairāk

## Add a signature dialog

pdfjs-editor-add-signature-dialog-title = Pievienot parakstu

## Controls

pdfjs-editor-add-signature-image-upload-error-description = Jāpŗabauda savienojums ar internetu vai jāmēģina cits attēls.

## Dialog buttons

pdfjs-editor-add-signature-add-button = Pievienot

##  Edit a comment dialog

# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Pievienot piebildi
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Pievienot

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Pievienot piebildi

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-views-manager-add-file-button =
    .title = Pievienot datni
pdfjs-views-manager-add-file-button-label = Pievienot datni
