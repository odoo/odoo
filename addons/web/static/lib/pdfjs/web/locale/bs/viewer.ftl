# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Prethodna strana
pdfjs-previous-button-label = Prethodna
pdfjs-next-button =
    .title = Sljedeća strna
pdfjs-next-button-label = Sljedeća
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Strana
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
    .title = Uvećanje
pdfjs-presentation-mode-button =
    .title = Prebaci se u prezentacijski režim
pdfjs-presentation-mode-button-label = Prezentacijski režim
pdfjs-open-file-button =
    .title = Otvori fajl
pdfjs-open-file-button-label = Otvori
pdfjs-print-button =
    .title = Štampaj
pdfjs-print-button-label = Štampaj
pdfjs-save-button =
    .title = Sačuvaj
pdfjs-save-button-label = Sačuvaj
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Preuzmi
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Preuzmi
pdfjs-bookmark-button =
    .title = Trenutna stranica (Prikaži URL sa trenutne stranice)
pdfjs-bookmark-button-label = Trenutna stranica

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Alati
pdfjs-tools-button-label = Alati
pdfjs-first-page-button =
    .title = Idi na prvu stranu
pdfjs-first-page-button-label = Idi na prvu stranu
pdfjs-last-page-button =
    .title = Idi na zadnju stranu
pdfjs-last-page-button-label = Idi na zadnju stranu
pdfjs-page-rotate-cw-button =
    .title = Rotiraj u smjeru kazaljke na satu
pdfjs-page-rotate-cw-button-label = Rotiraj u smjeru kazaljke na satu
pdfjs-page-rotate-ccw-button =
    .title = Rotiraj suprotno smjeru kazaljke na satu
pdfjs-page-rotate-ccw-button-label = Rotiraj suprotno smjeru kazaljke na satu
pdfjs-cursor-text-select-tool-button =
    .title = Omogući alat za označavanje teksta
pdfjs-cursor-text-select-tool-button-label = Alat za označavanje teksta
pdfjs-cursor-hand-tool-button =
    .title = Omogući ručni alat
pdfjs-cursor-hand-tool-button-label = Ručni alat
pdfjs-scroll-page-button =
    .title = Koristite pomicanje stranice
pdfjs-scroll-page-button-label = Pomicanje stranice
pdfjs-scroll-vertical-button =
    .title = Koristite vertikalno pomicanje
pdfjs-scroll-vertical-button-label = Vertikalno pomicanje
pdfjs-scroll-horizontal-button =
    .title = Koristite horizontalno pomicanje
pdfjs-scroll-horizontal-button-label = Horizontalno pomicanje
pdfjs-scroll-wrapped-button =
    .title = Koristite omotno pomicanje
pdfjs-scroll-wrapped-button-label = Omotno pomicanje
pdfjs-spread-none-button =
    .title = Ne izrađuj duplerice
pdfjs-spread-none-button-label = Bez duplerica
pdfjs-spread-odd-button =
    .title = Izradi duplerice koje počinju s neparnim stranicama
pdfjs-spread-odd-button-label = Neparne duplerice
pdfjs-spread-even-button =
    .title = Izradi duplerice koje počinju s parnim stranicama
pdfjs-spread-even-button-label = Parne duplerice

## Document properties dialog

pdfjs-document-properties-button =
    .title = Svojstva dokumenta...
pdfjs-document-properties-button-label = Svojstva dokumenta...
pdfjs-document-properties-file-name = Naziv fajla:
pdfjs-document-properties-file-size = Veličina fajla:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bajtova)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bajtova)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bajta)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bajta)
pdfjs-document-properties-title = Naslov:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Predmet:
pdfjs-document-properties-keywords = Ključne riječi:
pdfjs-document-properties-creation-date = Datum kreiranja:
pdfjs-document-properties-modification-date = Datum promjene:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Kreator:
pdfjs-document-properties-producer = PDF stvaratelj:
pdfjs-document-properties-version = PDF verzija:
pdfjs-document-properties-page-count = Broj stranica:
pdfjs-document-properties-page-size = Veličina stranice:
pdfjs-document-properties-page-size-unit-inches = u
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = uspravno
pdfjs-document-properties-page-size-orientation-landscape = vodoravno
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Pismo
pdfjs-document-properties-page-size-name-legal = Pravni

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

pdfjs-print-progress-message = Pripremam dokument za štampu…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Otkaži
pdfjs-printing-not-supported = Upozorenje: Štampanje nije u potpunosti podržano u ovom browseru.
pdfjs-printing-not-ready = Upozorenje: PDF nije u potpunosti učitan za štampanje.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Uključi/isključi bočnu traku
pdfjs-toggle-sidebar-notification-button =
    .title = Uključi/isključi bočnu traku (dokument sadrži obris/priloge/slojeve)
pdfjs-toggle-sidebar-button-label = Uključi/isključi bočnu traku
pdfjs-document-outline-button =
    .title = Prikaži outline dokumenta (dvoklik za skupljanje/širenje svih stavki)
pdfjs-document-outline-button-label = Konture dokumenta
pdfjs-attachments-button =
    .title = Prikaži priloge
pdfjs-attachments-button-label = Prilozi
pdfjs-layers-button =
    .title = Prikaži slojeve (dvostruki klik da biste vratili sve slojeve na zadano stanje)
pdfjs-layers-button-label = Slojevi
pdfjs-thumbs-button =
    .title = Prikaži thumbnailove
pdfjs-thumbs-button-label = Thumbnailovi
pdfjs-current-outline-item-button =
    .title = Pronađi trenutnu stavku strukture
pdfjs-current-outline-item-button-label = Trenutna stavka strukture
pdfjs-findbar-button =
    .title = Pronađi u dokumentu
pdfjs-findbar-button-label = Pronađi
pdfjs-additional-layers = Dodatni slojevi

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Strana { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Thumbnail strane { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Pronađi
    .placeholder = Pronađi u dokumentu…
pdfjs-find-previous-button =
    .title = Pronađi prethodno pojavljivanje fraze
pdfjs-find-previous-button-label = Prethodno
pdfjs-find-next-button =
    .title = Pronađi sljedeće pojavljivanje fraze
pdfjs-find-next-button-label = Sljedeće
pdfjs-find-highlight-checkbox = Označi sve
pdfjs-find-match-case-checkbox-label = Osjetljivost na karaktere
pdfjs-find-match-diacritics-checkbox-label = Podudaranje dijakritika
pdfjs-find-entire-word-checkbox-label = Cijele riječi
pdfjs-find-reached-top = Dostigao sam vrh dokumenta, nastavljam sa dna
pdfjs-find-reached-bottom = Dostigao sam kraj dokumenta, nastavljam sa vrha
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } od { $total } podudaranje
        [few] { $current } od { $total } podudaranja
       *[other] { $current } od { $total } podudaranja
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Više od { $limit } podudaranja
        [few] Više od { $limit } podudaranja
       *[other] Više od { $limit } podudaranja
    }
pdfjs-find-not-found = Fraza nije pronađena

## Predefined zoom values

pdfjs-page-scale-width = Širina strane
pdfjs-page-scale-fit = Uklopi stranu
pdfjs-page-scale-auto = Automatsko uvećanje
pdfjs-page-scale-actual = Stvarna veličina
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Stranica { $page }

## Loading indicator messages

pdfjs-loading-error = Došlo je do greške prilikom učitavanja PDF-a.
pdfjs-invalid-file-error = Neispravan ili oštećen PDF fajl.
pdfjs-missing-file-error = Nedostaje PDF fajl.
pdfjs-unexpected-response-error = Neočekivani odgovor servera.
pdfjs-rendering-error = Došlo je do greške prilikom renderiranja strane.

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
    .alt = [{ $type } pribilješka]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Upišite lozinku da biste otvorili ovaj PDF fajl.
pdfjs-password-invalid = Pogrešna lozinka. Pokušajte ponovo.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Otkaži
pdfjs-web-fonts-disabled = Web fontovi su onemogućeni: nemoguće koristiti ubačene PDF fontove.

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
    .title = Istaknite
pdfjs-editor-highlight-button-label = Istaknite
pdfjs-highlight-floating-button1 =
    .title = Istaknite
    .aria-label = Istaknite
pdfjs-highlight-floating-button-label = Istaknite
pdfjs-editor-signature-button =
    .title = Dodaj potpis
pdfjs-editor-signature-button-label = Dodaj potpis

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Uređivač istaknutih elemenata
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
    .title = Ukloni istaknuti dio
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
    .title = Promijenite debljinu prilikom označavanja stavki koje nisu tekst
pdfjs-editor-add-signature-container =
    .aria-label = Kontrole potpisa i sačuvani potpisi
pdfjs-editor-signature-add-signature-button =
    .title = Dodaj novi potpis
pdfjs-editor-signature-add-signature-button-label = Dodaj novi potpis
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Sačuvani potpis: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Uređivač teksta
    .default-content = Počnite kucati…
pdfjs-free-text =
    .aria-label = Uređivač teksta
pdfjs-free-text-default-content = Počnite kucati…
pdfjs-ink =
    .aria-label = Uređivač crtanja
pdfjs-ink-canvas =
    .aria-label = Slika koju je kreirao korisnik

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternativni tekst
pdfjs-editor-alt-text-edit-button =
    .aria-label = Uredi alternativni tekst
pdfjs-editor-alt-text-edit-button-label = Uredi alternativni tekst
pdfjs-editor-alt-text-dialog-label = Odaberite opciju
pdfjs-editor-alt-text-dialog-description = Alternativni tekst (Alt tekst) pomaže kada ljudi ne mogu vidjeti sliku ili kada se ona ne učitava.
pdfjs-editor-alt-text-add-description-label = Dodajte opis
pdfjs-editor-alt-text-add-description-description = Ciljajte na 1-2 rečenice koje opisuju temu, okruženje ili radnju.
pdfjs-editor-alt-text-mark-decorative-label = Označi kao dekorativno
pdfjs-editor-alt-text-mark-decorative-description = Ovo se koristi za ukrasne slike, poput okvira ili vodenih žigova.
pdfjs-editor-alt-text-cancel-button = Otkaži
pdfjs-editor-alt-text-save-button = Sačuvaj
pdfjs-editor-alt-text-decorative-tooltip = Označeno kao dekorativno
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Na primjer, „Mladić sjeda za stol da jede obrok“
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativni tekst

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Gornji lijevi ugao — promjena veličine
pdfjs-editor-resizer-label-top-middle = Gore u sredini — promijeni veličinu
pdfjs-editor-resizer-label-top-right = Gornji desni ugao — promijeni veličinu
pdfjs-editor-resizer-label-middle-right = Sredina desno — promijeni veličinu
pdfjs-editor-resizer-label-bottom-right = Donji desni ugao — promijeni veličinu
pdfjs-editor-resizer-label-bottom-middle = Donji srednji dio — promijeni veličinu
pdfjs-editor-resizer-label-bottom-left = Donji lijevi ugao — promijeni veličinu
pdfjs-editor-resizer-label-middle-left = Sredina lijevo — promijeni veličinu
pdfjs-editor-resizer-top-left =
    .aria-label = Gornji lijevi ugao — promjena veličine
pdfjs-editor-resizer-top-middle =
    .aria-label = Gore u sredini — promijeni veličinu
pdfjs-editor-resizer-top-right =
    .aria-label = Gornji desni ugao — promijeni veličinu
pdfjs-editor-resizer-middle-right =
    .aria-label = Sredina desno — promijeni veličinu
pdfjs-editor-resizer-bottom-right =
    .aria-label = Donji desni ugao — promijeni veličinu
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Donji srednji dio — promijeni veličinu
pdfjs-editor-resizer-bottom-left =
    .aria-label = Donji lijevi ugao — promijeni veličinu
pdfjs-editor-resizer-middle-left =
    .aria-label = Sredina lijevo — promijeni veličinu

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Boja isticanja
pdfjs-editor-colorpicker-button =
    .title = Promijeni boju
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Izbor boja
pdfjs-editor-colorpicker-yellow =
    .title = Žuta
pdfjs-editor-colorpicker-green =
    .title = Zelena
pdfjs-editor-colorpicker-blue =
    .title = Plava
pdfjs-editor-colorpicker-pink =
    .title = Roza
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
    .placeholder = Ovdje napišite svoj opis…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kratak opis za osobe koje ne mogu vidjeti sliku ili kada se slika ne učitava.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ovaj alternativni tekst je kreiran automatski i moguće je da je netačan.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Saznajte više
pdfjs-editor-new-alt-text-create-automatically-button-label = Automatski kreiraj alternativni tekst
pdfjs-editor-new-alt-text-not-now-button = Ne sada
pdfjs-editor-new-alt-text-error-title = Nije moguće automatski kreirati alternativni tekst
pdfjs-editor-new-alt-text-error-description = Molimo vas da napišete vlastiti alternativni tekst ili pokušate ponovo kasnije.
pdfjs-editor-new-alt-text-error-close-button = Zatvori
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Preuzimanje alternativnog tekstualnog AI modela ({ $downloadedSize } od { $totalSize } MB)
    .aria-valuetext = Preuzimanje alternativnog tekstualnog AI modela ({ $downloadedSize } od { $totalSize } MB)
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
    .aria-label = Alternativni tekst recenzije
pdfjs-editor-new-alt-text-to-review-button-label = Alternativni tekst recenzije
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Automatski kreirano: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Postavke alternativnog teksta slike
pdfjs-image-alt-text-settings-button-label = Postavke alternativnog teksta slike
pdfjs-editor-alt-text-settings-dialog-label = Postavke alternativnog teksta slike
pdfjs-editor-alt-text-settings-automatic-title = Automatski alternativni tekst
pdfjs-editor-alt-text-settings-create-model-button-label = Automatski kreiraj alternativni tekst
pdfjs-editor-alt-text-settings-create-model-description = Predlaže opise kako bi pomogao ljudima koji ne vide sliku ili kada se slika ne učitava.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Alternativni tekst AI model ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Radi lokalno na vašem uređaju tako da vaši podaci ostaju privatni. Potrebno za automatski alternativni tekst.
pdfjs-editor-alt-text-settings-delete-model-button = Izbriši
pdfjs-editor-alt-text-settings-download-model-button = Preuzmi
pdfjs-editor-alt-text-settings-downloading-model-button = Preuzimam…
pdfjs-editor-alt-text-settings-editor-title = Uređivač alternativnog teksta
pdfjs-editor-alt-text-settings-show-dialog-button-label = Odmah prikaži uređivač alternativnog teksta prilikom dodavanja slike
pdfjs-editor-alt-text-settings-show-dialog-description = Pomaže vam da osigurate da sve vaše slike imaju alternativni tekst.
pdfjs-editor-alt-text-settings-close-button = Zatvori

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Istaknuto je uklonjeno
pdfjs-editor-undo-bar-message-freetext = Tekst uklonjen
pdfjs-editor-undo-bar-message-ink = Crtež uklonjen
pdfjs-editor-undo-bar-message-stamp = Slika uklonjena
pdfjs-editor-undo-bar-message-signature = Potpis uklonjen
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } bilješka uklonjena
        [few] { $count } bilješke uklonjene
       *[other] { $count } bilješki uklonjeno
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Poništi
pdfjs-editor-undo-bar-undo-button-label = Poništi
pdfjs-editor-undo-bar-close-button =
    .title = Zatvori
pdfjs-editor-undo-bar-close-button-label = Zatvori

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Ovaj modalni prozor omogućava korisniku da kreira potpis koji će dodati PDF dokumentu. Korisnik može urediti ime (koje služi i kao alternativni tekst) i opcionalno sačuvati potpis za ponovnu upotrebu.
pdfjs-editor-add-signature-dialog-title = Dodaj potpis

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Ukucaj
    .title = Ukucaj
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Napiši
    .title = Napiši
pdfjs-editor-add-signature-image-button = Slika
    .title = Slika

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Ukucajte svoj potpis
    .placeholder = Ukucajte svoj potpis
pdfjs-editor-add-signature-draw-placeholder = Napišite svoj potpis
pdfjs-editor-add-signature-draw-thickness-range-label = Debljina
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Debljina pisanja: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Prevucite datoteku ovdje da biste je učitali
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ili odaberite slikovne datoteke
       *[other] Ili pregledajte slikovne datoteke
    }

## Controls

pdfjs-editor-add-signature-description-label = Opis (alternativni tekst)
pdfjs-editor-add-signature-description-input =
    .title = Opis (alternativni tekst)
pdfjs-editor-add-signature-description-default-when-drawing = Potpis
pdfjs-editor-add-signature-clear-button-label = Očisti potpis
pdfjs-editor-add-signature-clear-button =
    .title = Očisti potpis
pdfjs-editor-add-signature-save-checkbox = Sačuvaj potpis
pdfjs-editor-add-signature-save-warning-message = Dostigli ste ograničenje od 5 sačuvanih potpisa. Uklonite jedan da biste sačuvali više.
pdfjs-editor-add-signature-image-upload-error-title = Nije moguće učitati sliku
pdfjs-editor-add-signature-image-upload-error-description = Provjerite mrežnu vezu ili pokušajte s drugom slikom.
pdfjs-editor-add-signature-image-no-data-error-title = Nije moguće pretvoriti ovu sliku u potpis
pdfjs-editor-add-signature-image-no-data-error-description = Molimo pokušajte učitati drugu sliku.
pdfjs-editor-add-signature-error-close-button = Zatvori

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Otkaži
pdfjs-editor-add-signature-add-button = Dodaj
pdfjs-editor-edit-signature-update-button = Ažuriraj

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Radnje
pdfjs-editor-edit-comment-actions-button =
    .title = Radnje
pdfjs-editor-edit-comment-close-button-label = Zatvori
pdfjs-editor-edit-comment-close-button =
    .title = Zatvori
pdfjs-editor-edit-comment-actions-edit-button-label = Uredi
pdfjs-editor-edit-comment-actions-delete-button-label = Izbriši
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Unesite svoj komentar
pdfjs-editor-edit-comment-manager-cancel-button = Otkaži
pdfjs-editor-edit-comment-manager-save-button = Sačuvaj

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Uredi komentar

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Ukloni sačuvani potpis
pdfjs-editor-delete-signature-button-label1 = Ukloni sačuvani potpis

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Uredi opis

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Uredi opis
