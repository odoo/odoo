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
pdfjs-document-properties-title = Ime:
pdfjs-document-properties-author = Avtor:
pdfjs-document-properties-subject = Tema:
pdfjs-document-properties-keywords = Ključne besede:
pdfjs-document-properties-creation-date = Datum nastanka:
pdfjs-document-properties-modification-date = Datum spremembe:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
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
pdfjs-document-properties-linearized = Hitri spletni ogled:
pdfjs-document-properties-linearized-yes = Da
pdfjs-document-properties-linearized-no = Ne
pdfjs-document-properties-close-button = Zapri
pdfjs-digital-signature-properties-view-certificate = Ogled digitalnega potrdila
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Razlog: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Časovni žig: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Podpodpis ({ $count })
        [two] Podpodpisi ({ $count })
        [few] Podpodpisi ({ $count })
       *[other] Podpodpisi ({ $count })
    }

## Print

pdfjs-print-progress-message = Priprava dokumenta na tiskanje …
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Prekliči
pdfjs-printing-not-supported = Opozorilo: ta brskalnik ne podpira vseh možnosti tiskanja.
pdfjs-printing-not-ready = Opozorilo: PDF ni v celoti naložen za tiskanje.

## Tooltips and alt text for side panel toolbar buttons

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
pdfjs-thumb-page-canvas =
    .aria-label = Sličica strani { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Izberi stran { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Stran { $page } od { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Najdi v dokumentu …
    .title = Najdi
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
pdfjs-find-reached-bottom = Dosežen konec dokumenta, nadaljevanje od začetka
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
pdfjs-editor-color-picker-free-text-input =
    .title = Spremeni barvo besedila
pdfjs-editor-free-text-button-label = Besedilo
pdfjs-editor-ink-button =
    .title = Riši
pdfjs-editor-color-picker-ink-input =
    .title = Spremeni barvo risbe
pdfjs-editor-ink-button-label = Riši
pdfjs-editor-stamp-button =
    .title = Dodajanje ali urejanje slik
pdfjs-editor-stamp-button-label = Dodajanje ali urejanje slik
pdfjs-editor-highlight-button =
    .title = Označevalnik
pdfjs-editor-highlight-button-label = Označevalnik
pdfjs-highlight-floating-button1 =
    .aria-label = Označi
    .title = Označi
pdfjs-highlight-floating-button-label = Označi
pdfjs-comment-floating-button =
    .aria-label = Komentiraj
    .title = Komentiraj
pdfjs-comment-floating-button-label = Komentiraj
pdfjs-editor-comment-button =
    .aria-label = Komentiraj
    .title = Komentiraj
pdfjs-editor-comment-button-label = Komentiraj
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
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Komentar
        [two] Komentarja
        [few] Komentarji
       *[other] Komentarji
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Zapri stransko vrstico
    .title = Zapri stransko vrstico
pdfjs-editor-comments-sidebar-close-button-label = Zapri stransko vrstico
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Ste zasledili kaj omembe vrednega? Narišite oznako in dopišite komentar.
pdfjs-editor-comments-sidebar-no-comments-link = Več o tem

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Nadomestno besedilo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Uredi nadomestno besedilo
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
pdfjs-editor-undo-bar-message-comment = Komentar odstranjen
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
pdfjs-editor-add-signature-image-no-data-error-title = Te slike ni mogoče pretvoriti v podpis
pdfjs-editor-add-signature-image-no-data-error-description = Poskusite naložiti drugo sliko.
pdfjs-editor-add-signature-error-close-button = Zapri

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Prekliči
pdfjs-editor-add-signature-add-button = Dodaj
pdfjs-editor-edit-signature-update-button = Spremeni

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Uredi komentar
pdfjs-editor-edit-comment-popup-button =
    .title = Uredi komentar
pdfjs-editor-delete-comment-popup-button-label = Odstrani komentar
pdfjs-editor-delete-comment-popup-button =
    .title = Odstrani komentar
pdfjs-show-comment-button =
    .title = Pokaži komentar

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Uredi komentar
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Spremeni
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Dodaj komentar
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Dodaj
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Začnite tipkati …
pdfjs-editor-edit-comment-dialog-cancel-button = Prekliči

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Dodaj komentar

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Preklopi stransko vrstico (dokument vsebuje sličice/oris/priponke/plasti)
pdfjs-toggle-views-manager-button1-label = Upravljanje strani
pdfjs-views-manager-sidebar =
    .aria-label = Stranska vrstica
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Sprememba velikosti stranske vrstice
pdfjs-views-manager-view-selector-button =
    .title = Pogledi
pdfjs-views-manager-view-selector-button-label = Pogledi
pdfjs-views-manager-pages-title = Strani
pdfjs-views-manager-outlines-title1 = Oris dokumenta
    .title = Oris dokumenta (dvokliknite za razširitev ali strnitev vseh elementov)
pdfjs-views-manager-attachments-title = Priponke
pdfjs-views-manager-layers-title1 = Plasti
    .title = Plasti (dvokliknite za ponastavitev vseh plasti na privzeto stanje)
pdfjs-views-manager-pages-option-label = Strani
pdfjs-views-manager-outlines-option-label = Oris dokumenta
pdfjs-views-manager-attachments-option-label = Priponke
pdfjs-views-manager-layers-option-label = Plasti
pdfjs-views-manager-add-file-button =
    .title = Dodaj datoteko
pdfjs-views-manager-add-file-button-label = Dodaj datoteko
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } izbrana
        [two] { $count } izbrani
        [few] { $count } izbrane
       *[other] { $count } izbranih
    }
pdfjs-views-manager-pages-status-none-action-label = Izberite strani
pdfjs-views-manager-pages-status-action-button-label = Upravljaj
pdfjs-views-manager-pages-status-copy-button-label = Kopiraj
pdfjs-views-manager-pages-status-cut-button-label = Izreži
pdfjs-views-manager-pages-status-delete-button-label = Izbriši
pdfjs-views-manager-pages-status-export-selected-button-label = Izvozi izbor …
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] { $count } stran izrezana
        [two] { $count } strani izrezani
        [few] { $count } strani izrezane
       *[other] { $count } strani izrezanih
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] { $count } stran kopirana
        [two] { $count } strani kopirani
        [few] { $count } strani kopirane
       *[other] { $count } strani kopiranih
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] { $count } stran izbrisana
        [two] { $count } strani izbrisani
        [few] { $count } strani izbrisane
       *[other] { $count } strani izbrisanih
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Pripravljanje datoteke za vas …
pdfjs-views-manager-pages-status-waiting-uploading-label = Nalaganje datoteke …
pdfjs-views-manager-status-warning-cut-label = Izrezovanje ni bilo mogoče. Osvežite stran in poskusite znova.
pdfjs-views-manager-status-warning-copy-label = Kopiranje ni bilo mogoče. Osvežite stran in poskusite znova.
pdfjs-views-manager-status-warning-delete-label = Brisanje ni bilo mogoče. Osvežite stran in poskusite znova.
pdfjs-views-manager-status-warning-save-label = Shranjevanje ni bilo mogoče. Osvežite stran in poskusite znova.
pdfjs-views-manager-status-undo-button-label = Razveljavi
pdfjs-views-manager-status-done-button-label = Končano
pdfjs-views-manager-status-close-button =
    .title = Zapri
pdfjs-views-manager-status-close-button-label = Zapri
pdfjs-views-manager-paste-button-label = Prilepi
pdfjs-views-manager-paste-button-before =
    .title = Prilepi pred prvo stran
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Prilepi za stranjo { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NOVO
pdfjs-views-manager-waiting-for-file = Nalaganje datoteke …
pdfjs-toggle-views-manager-button1 =
    .title = Upravljanje strani

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Lastnosti digitalnega podpisa
    .title = Lastnosti digitalnega podpisa
pdfjs-digital-signature-properties-button-label = Lastnosti digitalnega podpisa

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Dokument je bil podpisan z veljavnim digitalnim podpisom
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Dokument je podpisan, vendar { $count } digitalnega podpisa ni bilo mogoče preveriti
        [two] Dokument je podpisan, vendar { $count } digitalnih podpisov ni bilo mogoče preveriti
        [few] Dokument je podpisan, vendar { $count } digitalnih podpisov ni bilo mogoče preveriti
       *[other] Dokument je podpisan, vendar { $count } digitalnih podpisov ni bilo mogoče preveriti
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Dokument je podpisan z { $count } digitalnim potrdilom, ki ni zaupanja vredno
        [two] Dokument je podpisan z { $count } digitalnima potrdiloma, ki nista zaupanja vredni
        [few] Dokument je podpisan s { $count } digitalnimi potrdili, ki niso zaupanja vredna
       *[other] Dokument je podpisan s { $count } digitalnimi potrdili, ki niso zaupanja vredna
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Dokument je podpisan z { $count } pretečenim digitalnim potrdilom
        [two] Dokument je podpisan z { $count } pretečenima digitalnima potrdiloma
        [few] Dokument je podpisan s { $count } pretečenimi digitalnimi potrdili
       *[other] Dokument je podpisan s { $count } pretečenimi digitalnimi potrdili
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] Dokument vsebuje { $count } neveljaven digitalni podpis
        [two] Dokument vsebuje { $count } neveljavna digitalna podpisa
        [few] Dokument vsebuje { $count } neveljavne digitalne podpise
       *[other] Dokument vsebuje { $count } neveljavnih digitalnih podpisov
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Dokument je podpisan z { $count } preklicanim digitalnim potrdilom
        [two] Dokument je podpisan z { $count } preklicanima digitalnima potrdiloma
        [few] Dokument je podpisan s { $count } preklicanimi digitalnimi potrdili
       *[other] Dokument je podpisan s { $count } preklicanimi digitalnimi potrdili
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Stanje: podpis preverjen
pdfjs-digital-signature-properties-status-invalid = Stanje: podpis neveljaven
pdfjs-digital-signature-properties-status-unknown = Stanje: podpisa ni mogoče preveriti (nepodprt)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Digitalno potrdilo: zaupanja vredno ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Digitalno potrdilo: ni na voljo
pdfjs-digital-signature-properties-certificate-untrusted = Digitalno potrdilo: ni zaupanja vredno
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Digitalno potrdilo: neznan izdajatelj ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Digitalno potrdilo: samopodpisano ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Digitalno potrdilo: izdajatelj ni zaupanja vreden ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Digitalno potrdilo: pretečeno
pdfjs-digital-signature-properties-certificate-expired-with-date = Digitalno potrdilo: pretečeno ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Digitalno potrdilo: preklicano

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Odstrani shranjen podpis
pdfjs-editor-delete-signature-button-label1 = Odstrani shranjen podpis

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Uredi opis

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Uredi opis
