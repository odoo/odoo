# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Prejšnja stran
pdfjs-previous-button-label = Nazaj
pdfjs-next-button =
    .title = Naslednja stran
pdfjs-next-button-label = Naprej
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Stran
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = od { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } od { $pagesCount })
pdfjs-zoom-out-button =
    .title = Pomanjšaj
pdfjs-zoom-out-button-label = Pomanjšaj
pdfjs-zoom-in-button =
    .title = Povečaj
pdfjs-zoom-in-button-label = Povečaj
pdfjs-zoom-select =
    .title = Povečava
pdfjs-presentation-mode-button =
    .title = Preklopi v način predstavitve
pdfjs-presentation-mode-button-label = Način predstavitve
pdfjs-open-file-button =
    .title = Odpri datoteko
pdfjs-open-file-button-label = Odpri
pdfjs-print-button =
    .title = Natisni
pdfjs-print-button-label = Natisni
pdfjs-save-button =
    .title = Shrani
pdfjs-save-button-label = Shrani
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Prenesi
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Prenesi
pdfjs-bookmark-button =
    .title = Trenutna stran (prikaži URL, ki vodi do trenutne strani)
pdfjs-bookmark-button-label = Na trenutno stran

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Orodja
pdfjs-tools-button-label = Orodja
pdfjs-first-page-button =
    .title = Pojdi na prvo stran
pdfjs-first-page-button-label = Pojdi na prvo stran
pdfjs-last-page-button =
    .title = Pojdi na zadnjo stran
pdfjs-last-page-button-label = Pojdi na zadnjo stran
pdfjs-page-rotate-cw-button =
    .title = Zavrti v smeri urnega kazalca
pdfjs-page-rotate-cw-button-label = Zavrti v smeri urnega kazalca
pdfjs-page-rotate-ccw-button =
    .title = Zavrti v nasprotni smeri urnega kazalca
pdfjs-page-rotate-ccw-button-label = Zavrti v nasprotni smeri urnega kazalca
pdfjs-cursor-text-select-tool-button =
    .title = Omogoči orodje za izbor besedila
pdfjs-cursor-text-select-tool-button-label = Orodje za izbor besedila
pdfjs-cursor-hand-tool-button =
    .title = Omogoči roko
pdfjs-cursor-hand-tool-button-label = Roka
pdfjs-scroll-page-button =
    .title = Uporabi drsenje po strani
pdfjs-scroll-page-button-label = Drsenje po strani
pdfjs-scroll-vertical-button =
    .title = Uporabi navpično drsenje
pdfjs-scroll-vertical-button-label = Navpično drsenje
pdfjs-scroll-horizontal-button =
    .title = Uporabi vodoravno drsenje
pdfjs-scroll-horizontal-button-label = Vodoravno drsenje
pdfjs-scroll-wrapped-button =
    .title = Uporabi ovito drsenje
pdfjs-scroll-wrapped-button-label = Ovito drsenje
pdfjs-spread-none-button =
    .title = Ne združuj razponov strani
pdfjs-spread-none-button-label = Brez razponov
pdfjs-spread-odd-button =
    .title = Združuj razpone strani z začetkom pri lihih straneh
pdfjs-spread-odd-button-label = Lihi razponi
pdfjs-spread-even-button =
    .title = Združuj razpone strani z začetkom pri sodih straneh
pdfjs-spread-even-button-label = Sodi razponi

## Document properties dialog

pdfjs-document-properties-button =
    .title = Lastnosti dokumenta …
pdfjs-document-properties-button-label = Lastnosti dokumenta …
pdfjs-document-properties-file-name = Ime datoteke:
pdfjs-document-properties-file-size = Velikost datoteke:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bajtov)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bajtov)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bajtov)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bajtov)
pdfjs-document-properties-title = Ime:
pdfjs-document-properties-author = Avtor:
pdfjs-document-properties-subject = Tema:
pdfjs-document-properties-keywords = Ključne besede:
pdfjs-document-properties-creation-date = Datum nastanka:
pdfjs-document-properties-modification-date = Datum spremembe:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Ustvaril:
pdfjs-document-properties-producer = Izdelovalec PDF:
pdfjs-document-properties-version = Različica PDF:
pdfjs-document-properties-page-count = Število strani:
pdfjs-document-properties-page-size = Velikost strani:
pdfjs-document-properties-page-size-unit-inches = palcev
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = pokončno
pdfjs-document-properties-page-size-orientation-landscape = ležeče
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Pismo
pdfjs-document-properties-page-size-name-legal = Pravno

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
pdfjs-document-properties-linearized = Hitri spletni ogled:
pdfjs-document-properties-linearized-yes = Da
pdfjs-document-properties-linearized-no = Ne
pdfjs-document-properties-close-button = Zapri

## Print

pdfjs-print-progress-message = Priprava dokumenta na tiskanje …
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Prekliči
pdfjs-printing-not-supported = Opozorilo: ta brskalnik ne podpira vseh možnosti tiskanja.
pdfjs-printing-not-ready = Opozorilo: PDF ni v celoti naložen za tiskanje.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Preklopi stransko vrstico
pdfjs-toggle-sidebar-notification-button =
    .title = Preklopi stransko vrstico (dokument vsebuje oris/priponke/plasti)
pdfjs-toggle-sidebar-button-label = Preklopi stransko vrstico
pdfjs-document-outline-button =
    .title = Prikaži oris dokumenta (dvokliknite za razširitev/strnitev vseh predmetov)
pdfjs-document-outline-button-label = Oris dokumenta
pdfjs-attachments-button =
    .title = Prikaži priponke
pdfjs-attachments-button-label = Priponke
pdfjs-layers-button =
    .title = Prikaži plasti (dvokliknite za ponastavitev vseh plasti na privzeto stanje)
pdfjs-layers-button-label = Plasti
pdfjs-thumbs-button =
    .title = Prikaži sličice
pdfjs-thumbs-button-label = Sličice
pdfjs-current-outline-item-button =
    .title = Najdi trenutni predmet orisa
pdfjs-current-outline-item-button-label = Trenutni predmet orisa
pdfjs-findbar-button =
    .title = Iskanje po dokumentu
pdfjs-findbar-button-label = Najdi
pdfjs-additional-layers = Dodatne plasti

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Stran { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Sličica strani { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Najdi
    .placeholder = Najdi v dokumentu …
pdfjs-find-previous-button =
    .title = Najdi prejšnjo ponovitev iskanega
pdfjs-find-previous-button-label = Najdi nazaj
pdfjs-find-next-button =
    .title = Najdi naslednjo ponovitev iskanega
pdfjs-find-next-button-label = Najdi naprej
pdfjs-find-highlight-checkbox = Označi vse
pdfjs-find-match-case-checkbox-label = Razlikuj velike/male črke
pdfjs-find-match-diacritics-checkbox-label = Razlikuj diakritične znake
pdfjs-find-entire-word-checkbox-label = Cele besede
pdfjs-find-reached-top = Dosežen začetek dokumenta iz smeri konca
pdfjs-find-reached-bottom = Doseženo konec dokumenta iz smeri začetka
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] Zadetek { $current } od { $total }
        [two] Zadetek { $current } od { $total }
        [few] Zadetek { $current } od { $total }
       *[other] Zadetek { $current } od { $total }
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Več kot { $limit } zadetek
        [two] Več kot { $limit } zadetka
        [few] Več kot { $limit } zadetki
       *[other] Več kot { $limit } zadetkov
    }
pdfjs-find-not-found = Iskanega ni mogoče najti

## Predefined zoom values

pdfjs-page-scale-width = Širina strani
pdfjs-page-scale-fit = Prilagodi stran
pdfjs-page-scale-auto = Samodejno
pdfjs-page-scale-actual = Dejanska velikost
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Stran { $page }

## Loading indicator messages

pdfjs-loading-error = Med nalaganjem datoteke PDF je prišlo do napake.
pdfjs-invalid-file-error = Neveljavna ali pokvarjena datoteka PDF.
pdfjs-missing-file-error = Ni datoteke PDF.
pdfjs-unexpected-response-error = Nepričakovan odgovor strežnika.
pdfjs-rendering-error = Med pripravljanjem strani je prišlo do napake!

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
    .alt = [Opomba vrste { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Vnesite geslo za odpiranje te datoteke PDF.
pdfjs-password-invalid = Neveljavno geslo. Poskusite znova.
pdfjs-password-ok-button = V redu
pdfjs-password-cancel-button = Prekliči
pdfjs-web-fonts-disabled = Spletne pisave so onemogočene: vgradnih pisav za PDF ni mogoče uporabiti.

## Editing

pdfjs-editor-free-text-button =
    .title = Besedilo
pdfjs-editor-free-text-button-label = Besedilo
pdfjs-editor-ink-button =
    .title = Riši
pdfjs-editor-ink-button-label = Riši
pdfjs-editor-stamp-button =
    .title = Dodajanje ali urejanje slik
pdfjs-editor-stamp-button-label = Dodajanje ali urejanje slik
pdfjs-editor-highlight-button =
    .title = Označevalnik
pdfjs-editor-highlight-button-label = Označevalnik
pdfjs-highlight-floating-button1 =
    .title = Označi
    .aria-label = Označi
pdfjs-highlight-floating-button-label = Označi
pdfjs-editor-signature-button =
    .title = Dodaj podpis
pdfjs-editor-signature-button-label = Dodaj podpis

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Urejevalnik označb
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Urejevalnik risb
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Urejevalnik podpisov: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Urejevalnik slik

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Odstrani risbo
pdfjs-editor-remove-freetext-button =
    .title = Odstrani besedilo
pdfjs-editor-remove-stamp-button =
    .title = Odstrani sliko
pdfjs-editor-remove-highlight-button =
    .title = Odstrani označbo
pdfjs-editor-remove-signature-button =
    .title = Odstrani podpis

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Barva
pdfjs-editor-free-text-size-input = Velikost
pdfjs-editor-ink-color-input = Barva
pdfjs-editor-ink-thickness-input = Debelina
pdfjs-editor-ink-opacity-input = Neprosojnost
pdfjs-editor-stamp-add-image-button =
    .title = Dodaj sliko
pdfjs-editor-stamp-add-image-button-label = Dodaj sliko
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Debelina
pdfjs-editor-free-highlight-thickness-title =
    .title = Spremeni debelino pri označevanju nebesedilnih elementov
pdfjs-editor-add-signature-container =
    .aria-label = Kontrolniki za podpise in shranjeni podpisi
pdfjs-editor-signature-add-signature-button =
    .title = Dodaj nov podpis
pdfjs-editor-signature-add-signature-button-label = Dodaj nov podpis
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Shranjen podpis: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Urejevalnik besedila
    .default-content = Začnite tipkati …
pdfjs-free-text =
    .aria-label = Urejevalnik besedila
pdfjs-free-text-default-content = Začnite tipkati …
pdfjs-ink =
    .aria-label = Urejevalnik risanja
pdfjs-ink-canvas =
    .aria-label = Uporabnikova slika

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Nadomestno besedilo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Uredi nadomestno besedilo
pdfjs-editor-alt-text-edit-button-label = Uredi nadomestno besedilo
pdfjs-editor-alt-text-dialog-label = Izberite možnost
pdfjs-editor-alt-text-dialog-description = Nadomestno besedilo se prikaže tistim, ki ne vidijo slike, ali če se ta ne naloži.
pdfjs-editor-alt-text-add-description-label = Dodaj opis
pdfjs-editor-alt-text-add-description-description = Poskušajte v enem ali dveh stavkih opisati motiv, okolje ali dejanja.
pdfjs-editor-alt-text-mark-decorative-label = Označi kot okrasno
pdfjs-editor-alt-text-mark-decorative-description = Uporablja se za slike, ki služijo samo okrasu, na primer obrobe ali vodne žige.
pdfjs-editor-alt-text-cancel-button = Prekliči
pdfjs-editor-alt-text-save-button = Shrani
pdfjs-editor-alt-text-decorative-tooltip = Označeno kot okrasno
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Na primer: "Mladenič sedi za mizo pri jedi"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Nadomestno besedilo

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Zgornji levi kot – spremeni velikost
pdfjs-editor-resizer-label-top-middle = Zgoraj na sredini – spremeni velikost
pdfjs-editor-resizer-label-top-right = Zgornji desni kot – spremeni velikost
pdfjs-editor-resizer-label-middle-right = Desno na sredini – spremeni velikost
pdfjs-editor-resizer-label-bottom-right = Spodnji desni kot – spremeni velikost
pdfjs-editor-resizer-label-bottom-middle = Spodaj na sredini – spremeni velikost
pdfjs-editor-resizer-label-bottom-left = Spodnji levi kot – spremeni velikost
pdfjs-editor-resizer-label-middle-left = Levo na sredini – spremeni velikost
pdfjs-editor-resizer-top-left =
    .aria-label = Zgornji levi kot – spremeni velikost
pdfjs-editor-resizer-top-middle =
    .aria-label = Zgoraj na sredini – spremeni velikost
pdfjs-editor-resizer-top-right =
    .aria-label = Zgornji desni kot – spremeni velikost
pdfjs-editor-resizer-middle-right =
    .aria-label = Desno na sredini – spremeni velikost
pdfjs-editor-resizer-bottom-right =
    .aria-label = Spodnji desni kot – spremeni velikost
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Spodaj na sredini – spremeni velikost
pdfjs-editor-resizer-bottom-left =
    .aria-label = Spodnji levi kot – spremeni velikost
pdfjs-editor-resizer-middle-left =
    .aria-label = Levo na sredini – spremeni velikost

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Barva označbe
pdfjs-editor-colorpicker-button =
    .title = Spremeni barvo
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Izbira barve
pdfjs-editor-colorpicker-yellow =
    .title = Rumena
pdfjs-editor-colorpicker-green =
    .title = Zelena
pdfjs-editor-colorpicker-blue =
    .title = Modra
pdfjs-editor-colorpicker-pink =
    .title = Roza
pdfjs-editor-colorpicker-red =
    .title = Rdeča

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Prikaži vse
pdfjs-editor-highlight-show-all-button =
    .title = Prikaži vse

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Uredi nadomestno besedilo (opis slike)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Dodaj nadomestno besedilo (opis slike)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Tukaj napišite svoj opis …
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kratek opis za ljudi, ki ne morejo videti slike, ali za primer, ko se slika ne naloži.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = To nadomestno besedilo je bilo ustvarjeno samodejno in je lahko netočno.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Več o tem
pdfjs-editor-new-alt-text-create-automatically-button-label = Samodejno ustvari nadomestno besedilo
pdfjs-editor-new-alt-text-not-now-button = Ne zdaj
pdfjs-editor-new-alt-text-error-title = Nadomestnega besedila ni bilo mogoče samodejno ustvariti
pdfjs-editor-new-alt-text-error-description = Sestavite svoje nadomestno besedilo ali poskusite znova pozneje.
pdfjs-editor-new-alt-text-error-close-button = Zapri
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Prenašanje modela UI za nadomestno besedilo ({ $downloadedSize } od { $totalSize } MB)
    .aria-valuetext = Prenašanje modela UI za nadomestno besedilo ({ $downloadedSize } od { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Nadomestno besedilo dodano
pdfjs-editor-new-alt-text-added-button-label = Nadomestno besedilo dodano
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Nadomestno besedilo manjka
pdfjs-editor-new-alt-text-missing-button-label = Nadomestno besedilo manjka
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Oceni nadomestno besedilo
pdfjs-editor-new-alt-text-to-review-button-label = Oceni nadomestno besedilo
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Samodejno ustvarjeno: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Nastavitve nadomestnega besedila slike
pdfjs-image-alt-text-settings-button-label = Nastavitve nadomestnega besedila slike
pdfjs-editor-alt-text-settings-dialog-label = Nastavitve nadomestnega besedila slike
pdfjs-editor-alt-text-settings-automatic-title = Samodejno nadomestno besedilo
pdfjs-editor-alt-text-settings-create-model-button-label = Samodejno ustvari nadomestno besedilo
pdfjs-editor-alt-text-settings-create-model-description = Predlaga opise za pomoč ljudem, ki ne morejo videti slike, ali za primer, ko se slika ne naloži.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Model UI za nadomestno besedilo ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Izvaja se lokalno na vaši napravi, tako da vaši podatki ostajajo zasebni. Zahtevano za samodejno nadomestno besedilo.
pdfjs-editor-alt-text-settings-delete-model-button = Izbriši
pdfjs-editor-alt-text-settings-download-model-button = Prenesi
pdfjs-editor-alt-text-settings-downloading-model-button = Prenašanje ...
pdfjs-editor-alt-text-settings-editor-title = Urejevalnik nadomestnega besedila
pdfjs-editor-alt-text-settings-show-dialog-button-label = Ob dodajanju slike takoj prikaži urejevalnik nadomestnega besedila
pdfjs-editor-alt-text-settings-show-dialog-description = Pomaga vam zagotoviti, da imajo vse vaše slike nadomestno besedilo.
pdfjs-editor-alt-text-settings-close-button = Zapri

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Označba dodana
pdfjs-editor-freetext-added-alert = Besedilo dodano
pdfjs-editor-ink-added-alert = Risba dodana
pdfjs-editor-stamp-added-alert = Slika dodana
pdfjs-editor-signature-added-alert = Podpis dodan

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Označba odstranjena
pdfjs-editor-undo-bar-message-freetext = Besedilo odstranjeno
pdfjs-editor-undo-bar-message-ink = Risba odstranjena
pdfjs-editor-undo-bar-message-stamp = Slika odstranjena
pdfjs-editor-undo-bar-message-signature = Podpis odstranjen
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } označba odstranjena
        [two] { $count } označbi odstranjeni
        [few] { $count } označbe odstranjene
       *[other] { $count } označb odstranjenih
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Razveljavi
pdfjs-editor-undo-bar-undo-button-label = Razveljavi
pdfjs-editor-undo-bar-close-button =
    .title = Zapri
pdfjs-editor-undo-bar-close-button-label = Zapri

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Ta način omogoča uporabniku ustvariti podpis, ki ga želi dodati dokumentu PDF. Uporabnik lahko uredi ime (ki se uporablja tudi kot nadomestno besedilo) in podpis po želji shrani za ponovno uporabo.
pdfjs-editor-add-signature-dialog-title = Dodaj podpis

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Natipkaj
    .title = Natipkaj
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Nariši
    .title = Nariši
pdfjs-editor-add-signature-image-button = Slika
    .title = Slika

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Natipkajte svoj podpis
    .placeholder = Natipkajte svoj podpis
pdfjs-editor-add-signature-draw-placeholder = Narišite svoj podpis
pdfjs-editor-add-signature-draw-thickness-range-label = Debelina
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Debelina peresa: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Povlecite datoteko sem za nalaganje
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ali prebrskajte slikovne datoteke
       *[other] Ali prebrskajte slikovne datoteke
    }

## Controls

pdfjs-editor-add-signature-description-label = Opis (nadomestno besedilo)
pdfjs-editor-add-signature-description-input =
    .title = Opis (nadomestno besedilo)
pdfjs-editor-add-signature-description-default-when-drawing = Podpis
pdfjs-editor-add-signature-clear-button-label = Pobriši podpis
pdfjs-editor-add-signature-clear-button =
    .title = Pobriši podpis
pdfjs-editor-add-signature-save-checkbox = Shrani podpis
pdfjs-editor-add-signature-save-warning-message = Dosegli ste omejitev 5 shranjenih podpisov. Če želite shraniti novega, enega odstranite.
pdfjs-editor-add-signature-image-upload-error-title = Slike ni bilo mogoče naložiti
pdfjs-editor-add-signature-image-upload-error-description = Preverite svojo povezavo z omrežjem ali poskusite z drugo sliko.
pdfjs-editor-add-signature-error-close-button = Zapri

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Prekliči
pdfjs-editor-add-signature-add-button = Dodaj
pdfjs-editor-edit-signature-update-button = Spremeni

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Odstrani shranjen podpis
pdfjs-editor-delete-signature-button-label1 = Odstrani shranjen podpis

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Uredi opis

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Uredi opis
