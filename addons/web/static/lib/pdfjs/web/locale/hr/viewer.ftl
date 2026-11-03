# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Prethodna stranica
pdfjs-previous-button-label = Prethodna
pdfjs-next-button =
    .title = Sljedeća stranica
pdfjs-next-button-label = Sljedeća
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Stranica
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = od { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } od { $pagesCount })
pdfjs-zoom-out-button =
    .title = Umanji
pdfjs-zoom-out-button-label = Umanji
pdfjs-zoom-in-button =
    .title = Uvećaj
pdfjs-zoom-in-button-label = Uvećaj
pdfjs-zoom-select =
    .title = Zumiranje
pdfjs-presentation-mode-button =
    .title = Prebaci u modus prezentacija
pdfjs-presentation-mode-button-label = Modus prezentacija
pdfjs-open-file-button =
    .title = Otvori datoteku
pdfjs-open-file-button-label = Otvori
pdfjs-print-button =
    .title = Ispiši
pdfjs-print-button-label = Ispiši
pdfjs-save-button =
    .title = Spremi
pdfjs-save-button-label = Spremi
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Preuzimanja
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Preuzimanja
pdfjs-bookmark-button =
    .title = Trenutačna stranica (pogledaj URL s trenutačne stranice)
pdfjs-bookmark-button-label = Trenutačna stranica

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Alati
pdfjs-tools-button-label = Alati
pdfjs-first-page-button =
    .title = Idi na prvu stranicu
pdfjs-first-page-button-label = Idi na prvu stranicu
pdfjs-last-page-button =
    .title = Idi na zadnju stranicu
pdfjs-last-page-button-label = Idi na zadnju stranicu
pdfjs-page-rotate-cw-button =
    .title = Okreni nadesno
pdfjs-page-rotate-cw-button-label = Okreni nadesno
pdfjs-page-rotate-ccw-button =
    .title = Okreni nalijevo
pdfjs-page-rotate-ccw-button-label = Okreni nalijevo
pdfjs-cursor-text-select-tool-button =
    .title = Aktiviraj alat za biranje teksta
pdfjs-cursor-text-select-tool-button-label = Alat za označavanje teksta
pdfjs-cursor-hand-tool-button =
    .title = Aktiviraj ručni alat
pdfjs-cursor-hand-tool-button-label = Ručni alat
pdfjs-scroll-page-button =
    .title = Koristi klizanje stranice
pdfjs-scroll-page-button-label = Klizanje stranice
pdfjs-scroll-vertical-button =
    .title = Koristi okomito pomicanje
pdfjs-scroll-vertical-button-label = Okomito pomicanje
pdfjs-scroll-horizontal-button =
    .title = Koristi vodoravno pomicanje
pdfjs-scroll-horizontal-button-label = Vodoravno pomicanje
pdfjs-scroll-wrapped-button =
    .title = Koristi kontinuirani raspored stranica
pdfjs-scroll-wrapped-button-label = Kontinuirani raspored stranica
pdfjs-spread-none-button =
    .title = Ne izrađuj duplerice
pdfjs-spread-none-button-label = Pojedinačne stranice
pdfjs-spread-odd-button =
    .title = Izradi duplerice koje počinju s neparnim stranicama
pdfjs-spread-odd-button-label = Neparne duplerice
pdfjs-spread-even-button =
    .title = Izradi duplerice koje počinju s parnim stranicama
pdfjs-spread-even-button-label = Parne duplerice

## Document properties dialog

pdfjs-document-properties-button =
    .title = Svojstva dokumenta …
pdfjs-document-properties-button-label = Svojstva dokumenta …
pdfjs-document-properties-file-name = Ime datoteke:
pdfjs-document-properties-file-size = Veličina datoteke:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bajtova)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bajtova)
pdfjs-document-properties-title = Naslov:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Predmet:
pdfjs-document-properties-keywords = Ključne riječi:
pdfjs-document-properties-creation-date = Datum stvaranja:
pdfjs-document-properties-modification-date = Datum promjene:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Stvaratelj:
pdfjs-document-properties-producer = PDF stvaratelj:
pdfjs-document-properties-version = PDF verzija:
pdfjs-document-properties-page-count = Broj stranica:
pdfjs-document-properties-page-size = Dimenzije stranice:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = uspravno
pdfjs-document-properties-page-size-orientation-landscape = položeno
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
pdfjs-document-properties-linearized = Brzi web pregled:
pdfjs-document-properties-linearized-yes = Da
pdfjs-document-properties-linearized-no = Ne
pdfjs-document-properties-close-button = Zatvori
pdfjs-digital-signature-properties-view-certificate = Pogledaj certifikat

## Print

pdfjs-print-progress-message = Pripremanje dokumenta za ispis…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Odustani
pdfjs-printing-not-supported = Upozorenje: Ovaj preglednik ne podržava u potpunosti ispisivanje.
pdfjs-printing-not-ready = Upozorenje: PDF nije u potpunosti učitan za ispis.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Pronađi trenutačni element strukture
pdfjs-current-outline-item-button-label = Trenutačni element strukture
pdfjs-findbar-button =
    .title = Pronađi u dokumentu
pdfjs-findbar-button-label = Pronađi
pdfjs-additional-layers = Dodatni slojevi

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Minijatura stranice { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Odaberi stranicu { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Stranica { $page } od { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Pronađi u dokumentu …
    .title = Pronađi
pdfjs-find-previous-button =
    .title = Pronađi prethodno pojavljivanje ovog izraza
pdfjs-find-previous-button-label = Prethodno
pdfjs-find-next-button =
    .title = Pronađi sljedeće pojavljivanje ovog izraza
pdfjs-find-next-button-label = Dalje
pdfjs-find-highlight-checkbox = Istankni sve
pdfjs-find-match-case-checkbox-label = Razlikovanje velikih i malih slova
pdfjs-find-match-diacritics-checkbox-label = Razlikuj dijakritičke znakove
pdfjs-find-entire-word-checkbox-label = Cijele riječi
pdfjs-find-reached-top = Dosegnut početak dokumenta, nastavak s kraja
pdfjs-find-reached-bottom = Dosegnut kraj dokumenta, nastavak s početka
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } od { $total } rezultata
        [few] { $current } od { $total } rezultata
       *[other] { $current } od { $total } rezultata
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Više od { $limit } rezultat
        [few] Više od { $limit } rezultata
       *[other] Više od { $limit } rezultata
    }
pdfjs-find-not-found = Izraz nije pronađen

## Predefined zoom values

pdfjs-page-scale-width = Prilagodi širini prozora
pdfjs-page-scale-fit = Prilagodi veličini prozora
pdfjs-page-scale-auto = Automatsko zumiranje
pdfjs-page-scale-actual = Stvarna veličina
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Stranica { $page }

## Loading indicator messages

pdfjs-loading-error = Došlo je do greške pri učitavanju PDF-a.
pdfjs-invalid-file-error = Neispravna ili oštećena PDF datoteka.
pdfjs-missing-file-error = Nedostaje PDF datoteka.
pdfjs-unexpected-response-error = Neočekivani odgovor servera.
pdfjs-rendering-error = Došlo je do greške prilikom iscrtavanja stranice.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } Bilješka]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Za otvoranje ove PDF datoteku upiši lozinku.
pdfjs-password-invalid = Neispravna lozinka. Pokušaj ponovo.
pdfjs-password-ok-button = U redu
pdfjs-password-cancel-button = Odustani
pdfjs-web-fonts-disabled = Web fontovi su deaktivirani: nije moguće koristiti ugrađene PDF fontove.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-color-picker-free-text-input =
    .title = Promijeni boju teksta
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Crtanje
pdfjs-editor-color-picker-ink-input =
    .title = Promijeni boju crteža
pdfjs-editor-ink-button-label = Crtanje
pdfjs-editor-stamp-button =
    .title = Dodaj ili uredi slike
pdfjs-editor-stamp-button-label = Dodaj ili uredi slike
pdfjs-editor-highlight-button =
    .title = Istakni
pdfjs-editor-highlight-button-label = Istakni
pdfjs-highlight-floating-button1 =
    .aria-label = Istakni
    .title = Istakni
pdfjs-highlight-floating-button-label = Istakni
pdfjs-comment-floating-button =
    .aria-label = Komentiraj
    .title = Komentiraj
pdfjs-comment-floating-button-label = Komentiraj
pdfjs-editor-comment-button =
    .aria-label = Komentar
    .title = Komentar
pdfjs-editor-comment-button-label = Komentar
pdfjs-editor-signature-button =
    .title = Dodaj potpis
pdfjs-editor-signature-button-label = Dodaj potpis

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Uređivač za isticanje teksta
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Uređivač crteža
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Uređivač potpisa: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Uređivač slika

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Ukloni crtež
pdfjs-editor-remove-freetext-button =
    .title = Ukloni tekst
pdfjs-editor-remove-stamp-button =
    .title = Ukloni sliku
pdfjs-editor-remove-highlight-button =
    .title = Ukloni isticanje
pdfjs-editor-remove-signature-button =
    .title = Ukloni potpis

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Boja
pdfjs-editor-free-text-size-input = Veličina
pdfjs-editor-ink-color-input = Boja
pdfjs-editor-ink-thickness-input = Debljina
pdfjs-editor-ink-opacity-input = Neprozirnost
pdfjs-editor-stamp-add-image-button =
    .title = Dodaj sliku
pdfjs-editor-stamp-add-image-button-label = Dodaj sliku
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Debljina
pdfjs-editor-free-highlight-thickness-title =
    .title = Promjeni debljinu pri isticanju drugih stavki osim teksta
pdfjs-editor-add-signature-container =
    .aria-label = Kontrole potpisa i spremljeni potpisi
pdfjs-editor-signature-add-signature-button =
    .title = Dodaj novi potpis
pdfjs-editor-signature-add-signature-button-label = Dodaj novi potpis
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Spremljeni potpis: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Uređivač teksta
    .default-content = Počni tipkati …
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Komentar
        [few] Komentara
       *[other] Komentara
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Zatvori bočnu traku
    .title = Zatvori bočnu traku
pdfjs-editor-comments-sidebar-close-button-label = Zatvori bočnu traku
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Vidiš nešto vrijedno pažnje? Istakni to i ostavi komentar.
pdfjs-editor-comments-sidebar-no-comments-link = Saznaj više

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternativni tekst
pdfjs-editor-alt-text-edit-button =
    .aria-label = Uredi alternativni tekst
pdfjs-editor-alt-text-dialog-label = Odaberi jednu opciju
pdfjs-editor-alt-text-dialog-description = Alternativni tekst pomaže slijepim osobama ili kada se slika ne učita.
pdfjs-editor-alt-text-add-description-label = Dodaj opis
pdfjs-editor-alt-text-add-description-description = Sažmi sadržaj predmeta, okruženje ili radnje u jednoj ili dvije rečenice.
pdfjs-editor-alt-text-mark-decorative-label = Označi kao ukrasno
pdfjs-editor-alt-text-mark-decorative-description = Ovo se koristi za ukrasne slike, poput rubova ili vodenih žigova.
pdfjs-editor-alt-text-cancel-button = Odustani
pdfjs-editor-alt-text-save-button = Spremi
pdfjs-editor-alt-text-decorative-tooltip = Označeno kao ukrasno
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Na primjer, „Mladić sjeda za stol kako bi jeo”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativni tekst

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Gornji lijevi kut – promijeni veličinu
pdfjs-editor-resizer-top-middle =
    .aria-label = Sredina gore – promijeni veličinu
pdfjs-editor-resizer-top-right =
    .aria-label = Gornji desni kut – promijeni veličinu
pdfjs-editor-resizer-middle-right =
    .aria-label = Sredina desno – promijeni veličinu
pdfjs-editor-resizer-bottom-right =
    .aria-label = Donji desni kut – promijeni veličinu
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Sredina dolje – promjeni veličinu
pdfjs-editor-resizer-bottom-left =
    .aria-label = Donji lijevi kut – promijeni veličinu
pdfjs-editor-resizer-middle-left =
    .aria-label = Sredina lijevo – promijeni veličinu

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Boja isticanja
pdfjs-editor-colorpicker-button =
    .title = Promjeni boju
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Izbor boja
pdfjs-editor-colorpicker-yellow =
    .title = Žuta
pdfjs-editor-colorpicker-green =
    .title = Zelena
pdfjs-editor-colorpicker-blue =
    .title = Plava
pdfjs-editor-colorpicker-pink =
    .title = Ružičasta
pdfjs-editor-colorpicker-red =
    .title = Crvena

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Prikaži sve
pdfjs-editor-highlight-show-all-button =
    .title = Prikaži sve

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Uredi alternativni tekst (opis slike)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Dodaj alternativni tekst (opis slike)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Ovdje upiši tvoj opis …
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kratki opis koji pomažu osobama koji ne mogu vidjeti sliku ili kada se slika ne učita.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ovaj je alternativni tekst stvoren automatski i može biti netočan.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Saznaj više
pdfjs-editor-new-alt-text-create-automatically-button-label = Automatski stvori alternativni tekst
pdfjs-editor-new-alt-text-not-now-button = Ne sada
pdfjs-editor-new-alt-text-error-title = Nije bilo moguće automatski izraditi alternativni tekst
pdfjs-editor-new-alt-text-error-description = Napiši vlastiti alternativni tekst ili pokušaj kasnije ponovo.
pdfjs-editor-new-alt-text-error-close-button = Zatvori
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Preuzimanje alternativnog teksta UI modela ({ $downloadedSize } od { $totalSize } MB)
    .aria-valuetext = Preuzimanje alternativnog teksta UI modela ({ $downloadedSize } od { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativni tekst je dodan
pdfjs-editor-new-alt-text-added-button-label = Alternativni tekst je dodan
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Nedostaje alternativni tekst
pdfjs-editor-new-alt-text-missing-button-label = Nedostaje alternativni tekst
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Pregledaj alternativni tekst
pdfjs-editor-new-alt-text-to-review-button-label = Pregledaj alternativni tekst
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Stvoreno automatski: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Postavke alternativnog teksta slike
pdfjs-image-alt-text-settings-button-label = Postavke alternativnog teksta slike
pdfjs-editor-alt-text-settings-dialog-label = Postavke alternativnog teksta slike
pdfjs-editor-alt-text-settings-automatic-title = Automatski alternativni tekst
pdfjs-editor-alt-text-settings-create-model-button-label = Stvori alternativni tekst automatski
pdfjs-editor-alt-text-settings-create-model-description = Predlaže opise koji pomažu osobama koji ne mogu vidjeti sliku ili kada se slika ne učita.
pdfjs-editor-alt-text-settings-editor-title = Uređivač alternativnog teksta
pdfjs-editor-alt-text-settings-show-dialog-button-label = Prikaži uređivač alternativnog teksta odmah pri dodavanju slike
pdfjs-editor-alt-text-settings-show-dialog-description = Pomaže osigurati da sve tvoje slike imaju alternativni tekst.
pdfjs-editor-alt-text-settings-close-button = Zatvori

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Isticanje je dodano
pdfjs-editor-freetext-added-alert = Tekst je dodan
pdfjs-editor-ink-added-alert = Crtež je dodan
pdfjs-editor-stamp-added-alert = Slika je dodana
pdfjs-editor-signature-added-alert = Potpis je dodan

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Isticanje uklonjeno
pdfjs-editor-undo-bar-message-freetext = Tekst uklonjen
pdfjs-editor-undo-bar-message-ink = Crtež uklonjen
pdfjs-editor-undo-bar-message-stamp = Slika uklonjena
pdfjs-editor-undo-bar-message-signature = Potpis uklonjen
pdfjs-editor-undo-bar-message-comment = Komentar je uklonjen
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } pribilješka uklonjena
        [few] { $count } pribilješke uklonjene
       *[other] { $count } pribilješki uklonjeno
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Poništi
pdfjs-editor-undo-bar-undo-button-label = Poništi
pdfjs-editor-undo-bar-close-button =
    .title = Zatvori
pdfjs-editor-undo-bar-close-button-label = Zatvori

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Ovaj prozor omogućuje korisniku stvoriti potpis i dodati ga u PDF dokument. Korisnik može urediti ime (koje služi i kao alternativni tekst) i opcionalno spremiti potpis za ponovnu upotrebu.
pdfjs-editor-add-signature-dialog-title = Dodaj potpis

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Utipkaj
    .title = Utipkaj
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Crtaj
    .title = Crtaj
pdfjs-editor-add-signature-image-button = Slika
    .title = Slika

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Utipkaj svoj potpis
    .placeholder = Utipkaj svoj potpis
pdfjs-editor-add-signature-draw-placeholder = Nacrtaj svoj potpis
pdfjs-editor-add-signature-draw-thickness-range-label = Debljina
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Debljina crtanja: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Povuci datoteku za prijenos ovamo
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ili odaberi slikovne datoteke
       *[other] Ili odaberi slikovne datoteke
    }

## Controls

pdfjs-editor-add-signature-description-label = Opis (alternativni tekst)
pdfjs-editor-add-signature-description-input =
    .title = Opis (alternativni tekst)
pdfjs-editor-add-signature-description-default-when-drawing = Potpis
pdfjs-editor-add-signature-clear-button-label = Izbriši potpis
pdfjs-editor-add-signature-clear-button =
    .title = Izbriši potpis
pdfjs-editor-add-signature-save-checkbox = Spremi potpis
pdfjs-editor-add-signature-save-warning-message = Dosegnuto je ograničenje od 5 spremljenih potpisa. Za spremanje novih ukloni jedan potpis.
pdfjs-editor-add-signature-image-upload-error-title = Nije moguće prenijeti sliku
pdfjs-editor-add-signature-image-upload-error-description = Provjeri mrežnu vezu ili pokušaj s jednom drugom slikom.
pdfjs-editor-add-signature-image-no-data-error-title = Ova se slika ne može pretvoriti u potpis
pdfjs-editor-add-signature-image-no-data-error-description = Probaj prenijeti jednu drugu sliku.
pdfjs-editor-add-signature-error-close-button = Zatvori

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Odustani
pdfjs-editor-add-signature-add-button = Dodaj
pdfjs-editor-edit-signature-update-button = Aktualiziraj

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Uredi komentar
pdfjs-editor-edit-comment-popup-button =
    .title = Uredi komentar
pdfjs-editor-delete-comment-popup-button-label = Ukloni komentar
pdfjs-editor-delete-comment-popup-button =
    .title = Ukloni komentar
pdfjs-show-comment-button =
    .title = Prikaži komentar

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Uredi komentar
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Aktualiziraj
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Dodaj komentar
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Dodaj
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Počni tipkati …
pdfjs-editor-edit-comment-dialog-cancel-button = Odustani

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Dodaj komentar

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-button1-label = Upravljaj stranicama
pdfjs-views-manager-sidebar =
    .aria-label = Bočna traka
pdfjs-views-manager-view-selector-button =
    .title = Prikazi
pdfjs-views-manager-view-selector-button-label = Prikazi
pdfjs-views-manager-pages-title = Stranice
pdfjs-views-manager-outlines-title1 = Struktura dokumenta
    .title = Struktura dokumenta (sažmi/proširi sve stavke dvostrukim klikom)
pdfjs-views-manager-attachments-title = Privici
pdfjs-views-manager-layers-title1 = Slojevi
    .title = Slojevi (ponovo postavi sve slojeve na zadano stanje dvostrukim klikom)
pdfjs-views-manager-pages-option-label = Stranice
pdfjs-views-manager-outlines-option-label = Struktura dokumenta
pdfjs-views-manager-attachments-option-label = Privici
pdfjs-views-manager-layers-option-label = Slojevi
pdfjs-views-manager-add-file-button =
    .title = Dodaj datoteku
pdfjs-views-manager-add-file-button-label = Dodaj datoteku
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } odabrana
        [few] { $count } odabrane
       *[other] { $count } odabranih
    }
pdfjs-views-manager-pages-status-none-action-label = Odaberi stranice
pdfjs-views-manager-pages-status-action-button-label = Upravljaj
pdfjs-views-manager-pages-status-copy-button-label = Kopiraj
pdfjs-views-manager-pages-status-cut-button-label = Izreži
pdfjs-views-manager-pages-status-delete-button-label = Izbriši
pdfjs-views-manager-status-warning-cut-label = Nije moguće izrezati. Osvježi stranicu i pokušaj ponovo.
pdfjs-views-manager-status-warning-copy-label = Nije moguće kopirati. Osvježi stranicu i pokušaj ponovo.
pdfjs-views-manager-status-warning-delete-label = Nije moguće izbrisati. Osvježi stranicu i pokušaj ponovo.
pdfjs-views-manager-status-warning-save-label = Nije moguće spremiti. Osvježi stranicu i pokušaj ponovo.
pdfjs-views-manager-status-undo-button-label = Poništi
pdfjs-views-manager-status-done-button-label = Gotovo
pdfjs-views-manager-status-close-button =
    .title = Zatvori
pdfjs-views-manager-status-close-button-label = Zatvori
pdfjs-views-manager-paste-button-label = Umetni
pdfjs-views-manager-paste-button-before =
    .title = Umetni prije prve stranice
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Umetni nakon stranice { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NOVO
pdfjs-toggle-views-manager-button1 =
    .title = Upravljaj stranicama

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Ukloni spremljeni potpis
pdfjs-editor-delete-signature-button-label1 = Ukloni spremljeni potpis

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Uredi opis

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Uredi opis
