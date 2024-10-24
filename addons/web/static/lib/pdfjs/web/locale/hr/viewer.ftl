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
    .title = Trenutna stranica (pogledajte URL s trenutne stranice)
pdfjs-bookmark-button-label = Trenutna stranica

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Alati
pdfjs-tools-button-label = Alati
pdfjs-first-page-button =
    .title = Idi na prvu stranicu
pdfjs-first-page-button-label = Idi na prvu stranicu
pdfjs-last-page-button =
    .title = Idi na posljednju stranicu
pdfjs-last-page-button-label = Idi na posljednju stranicu
pdfjs-page-rotate-cw-button =
    .title = Rotiraj u smjeru kazaljke na satu
pdfjs-page-rotate-cw-button-label = Rotiraj u smjeru kazaljke na satu
pdfjs-page-rotate-ccw-button =
    .title = Rotiraj obrnutno od smjera kazaljke na satu
pdfjs-page-rotate-ccw-button-label = Rotiraj obrnutno od smjera kazaljke na satu
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
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bajtova)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bajtova)
pdfjs-document-properties-title = Naslov:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Predmet:
pdfjs-document-properties-keywords = Ključne riječi:
pdfjs-document-properties-creation-date = Datum stvaranja:
pdfjs-document-properties-modification-date = Datum promjene:
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Stvaratelj:
pdfjs-document-properties-producer = PDF stvaratelj:
pdfjs-document-properties-version = PDF inačica:
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

## Print

pdfjs-print-progress-message = Pripremanje dokumenta za ispis…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Odustani
pdfjs-printing-not-supported = Upozorenje: Ovaj preglednik ne podržava u potpunosti ispisivanje.
pdfjs-printing-not-ready = Upozorenje: PDF nije u potpunosti učitan za ispis.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Prikaži/sakrij bočnu traku
pdfjs-toggle-sidebar-notification-button =
    .title = Prikazivanje i sklanjanje bočne trake (dokument sadrži strukturu/privitke/slojeve)
pdfjs-toggle-sidebar-button-label = Prikaži/sakrij bočnu traku
pdfjs-document-outline-button =
    .title = Prikaži strukturu dokumenta (dvostruki klik za rasklapanje/sklapanje svih stavki)
pdfjs-document-outline-button-label = Struktura dokumenta
pdfjs-attachments-button =
    .title = Prikaži privitke
pdfjs-attachments-button-label = Privitci
pdfjs-layers-button =
    .title = Prikaži slojeve (dvoklik za vraćanje svih slojeva u standardno stanje)
pdfjs-layers-button-label = Slojevi
pdfjs-thumbs-button =
    .title = Prikaži minijature
pdfjs-thumbs-button-label = Minijature
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
pdfjs-thumb-page-title =
    .title = Stranica { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Minijatura stranice { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Pronađi
    .placeholder = Pronađi u dokumentu …
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
    { NUMBER($total) ->
        [one] { $current } od { $total } rezultata
        [few] { $current } od { $total } rezultata
       *[other] { $current } od { $total } rezultata
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { NUMBER($limit) ->
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
    .alt = [{ $type } Bilješka]

## Password

pdfjs-password-label = Za otvoranje ove PDF datoteku upiši lozinku.
pdfjs-password-invalid = Neispravna lozinka. Pokušaj ponovo.
pdfjs-password-ok-button = U redu
pdfjs-password-cancel-button = Odustani
pdfjs-web-fonts-disabled = Web fontovi su deaktivirani: nije moguće koristiti ugrađene PDF fontove.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Crtanje
pdfjs-editor-ink-button-label = Crtanje
pdfjs-editor-stamp-button =
    .title = Dodajte ili uredite slike
pdfjs-editor-stamp-button-label = Dodajte ili uredite slike
pdfjs-editor-highlight-button =
    .title = Istakni
pdfjs-editor-highlight-button-label = Istakni
pdfjs-highlight-floating-button1 =
    .title = Istakni
    .aria-label = Istakni
pdfjs-highlight-floating-button-label = Istakni

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Ukloni crtež
pdfjs-editor-remove-freetext-button =
    .title = Ukloni tekst
pdfjs-editor-remove-stamp-button =
    .title = Ukloni sliku
pdfjs-editor-remove-highlight-button =
    .title = Ukloni isticanje

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
pdfjs-free-text =
    .aria-label = Uređivač teksta
pdfjs-free-text-default-content = Počni tipkati …
pdfjs-ink =
    .aria-label = Uređivač crteža
pdfjs-ink-canvas =
    .aria-label = Slika koju je izradio korisnik

## Alt-text dialog

# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button-label = Alternativni tekst
pdfjs-editor-alt-text-edit-button-label = Uredi alternativni tekst
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

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Gornji lijevi kut – promijeni veličinu
pdfjs-editor-resizer-label-top-middle = Sredina gore – promijeni veličinu
pdfjs-editor-resizer-label-top-right = Gornji desni kut – promijeni veličinu
pdfjs-editor-resizer-label-middle-right = Sredina desno – promijeni veličinu
pdfjs-editor-resizer-label-bottom-right = Donji desni kut – promijeni veličinu
pdfjs-editor-resizer-label-bottom-middle = Sredina dolje – promjeni veličinu
pdfjs-editor-resizer-label-bottom-left = Donji lijevi kut – promijeni veličinu
pdfjs-editor-resizer-label-middle-left = Sredina lijevo – promijeni veličinu
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

pdfjs-editor-new-alt-text-textarea =
    .placeholder = Ovdje upiši tvoj opis …
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ovaj je alternativni tekst stvoren automatski i može biti netočan.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Saznaj više
pdfjs-editor-new-alt-text-create-automatically-button-label = Automatski stvori alternativni tekst
pdfjs-editor-new-alt-text-error-title = Nije bilo moguće automatski izraditi alternativni tekst
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
pdfjs-editor-alt-text-settings-ai-model-description = Radi lokalno na tvom uređaju kako bi tvoji podaci ostali privatni. Potrebno za automatski alternativni tekst.
pdfjs-editor-alt-text-settings-delete-model-button = Izbriši
pdfjs-editor-alt-text-settings-download-model-button = Preuzmi
pdfjs-editor-alt-text-settings-downloading-model-button = Preuzimanje …
pdfjs-editor-alt-text-settings-editor-title = Uređivač alternativnog teksta
pdfjs-editor-alt-text-settings-show-dialog-button-label = Prikaži uređivač alternativnog teksta odmah pri dodavanju slike
pdfjs-editor-alt-text-settings-show-dialog-description = Pomaže osigurati da sve tvoje slike imaju alternativni tekst.
pdfjs-editor-alt-text-settings-close-button = Zatvori
