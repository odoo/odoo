# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Edellinen sivu
pdfjs-previous-button-label = Edellinen
pdfjs-next-button =
    .title = Seuraava sivu
pdfjs-next-button-label = Seuraava
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Sivu
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = / { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } / { $pagesCount })
pdfjs-zoom-out-button =
    .title = Loitonna
pdfjs-zoom-out-button-label = Loitonna
pdfjs-zoom-in-button =
    .title = Lähennä
pdfjs-zoom-in-button-label = Lähennä
pdfjs-zoom-select =
    .title = Suurennus
pdfjs-presentation-mode-button =
    .title = Siirry esitystilaan
pdfjs-presentation-mode-button-label = Esitystila
pdfjs-open-file-button =
    .title = Avaa tiedosto
pdfjs-open-file-button-label = Avaa
pdfjs-print-button =
    .title = Tulosta
pdfjs-print-button-label = Tulosta
pdfjs-save-button =
    .title = Tallenna
pdfjs-save-button-label = Tallenna
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Lataa
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Lataa
pdfjs-bookmark-button =
    .title = Nykyinen sivu (Näytä URL-osoite nykyiseltä sivulta)
pdfjs-bookmark-button-label = Nykyinen sivu

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Tools
pdfjs-tools-button-label = Tools
pdfjs-first-page-button =
    .title = Siirry ensimmäiselle sivulle
pdfjs-first-page-button-label = Siirry ensimmäiselle sivulle
pdfjs-last-page-button =
    .title = Siirry viimeiselle sivulle
pdfjs-last-page-button-label = Siirry viimeiselle sivulle
pdfjs-page-rotate-cw-button =
    .title = Kierrä oikealle
pdfjs-page-rotate-cw-button-label = Kierrä oikealle
pdfjs-page-rotate-ccw-button =
    .title = Kierrä vasemmalle
pdfjs-page-rotate-ccw-button-label = Kierrä vasemmalle
pdfjs-cursor-text-select-tool-button =
    .title = Käytä tekstinvalintatyökalua
pdfjs-cursor-text-select-tool-button-label = Tekstinvalintatyökalu
pdfjs-cursor-hand-tool-button =
    .title = Käytä käsityökalua
pdfjs-cursor-hand-tool-button-label = Käsityökalu
pdfjs-scroll-page-button =
    .title = Käytä sivun vieritystä
pdfjs-scroll-page-button-label = Sivun vieritys
pdfjs-scroll-vertical-button =
    .title = Käytä pystysuuntaista vieritystä
pdfjs-scroll-vertical-button-label = Pystysuuntainen vieritys
pdfjs-scroll-horizontal-button =
    .title = Käytä vaakasuuntaista vieritystä
pdfjs-scroll-horizontal-button-label = Vaakasuuntainen vieritys
pdfjs-scroll-wrapped-button =
    .title = Käytä rivittyvää vieritystä
pdfjs-scroll-wrapped-button-label = Rivittyvä vieritys
pdfjs-spread-none-button =
    .title = Älä yhdistä sivuja aukeamiksi
pdfjs-spread-none-button-label = Ei aukeamia
pdfjs-spread-odd-button =
    .title = Yhdistä sivut aukeamiksi alkaen parittomalta sivulta
pdfjs-spread-odd-button-label = Parittomalta alkavat aukeamat
pdfjs-spread-even-button =
    .title = Yhdistä sivut aukeamiksi alkaen parilliselta sivulta
pdfjs-spread-even-button-label = Parilliselta alkavat aukeamat

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumentin ominaisuudet…
pdfjs-document-properties-button-label = Dokumentin ominaisuudet…
pdfjs-document-properties-file-name = Tiedoston nimi:
pdfjs-document-properties-file-size = Tiedoston koko:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } kt ({ $b } tavua)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } Mt ({ $b } tavua)
pdfjs-document-properties-title = Otsikko:
pdfjs-document-properties-author = Tekijä:
pdfjs-document-properties-subject = Aihe:
pdfjs-document-properties-keywords = Avainsanat:
pdfjs-document-properties-creation-date = Luomispäivämäärä:
pdfjs-document-properties-modification-date = Muokkauspäivämäärä:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Luoja:
pdfjs-document-properties-producer = PDF-tuottaja:
pdfjs-document-properties-version = PDF-versio:
pdfjs-document-properties-page-count = Sivujen määrä:
pdfjs-document-properties-page-size = Sivun koko:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = pysty
pdfjs-document-properties-page-size-orientation-landscape = vaaka
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
pdfjs-document-properties-linearized = Nopea web-katselu:
pdfjs-document-properties-linearized-yes = Kyllä
pdfjs-document-properties-linearized-no = Ei
pdfjs-document-properties-close-button = Sulje

## Print

pdfjs-print-progress-message = Valmistellaan dokumenttia tulostamista varten…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Peruuta
pdfjs-printing-not-supported = Varoitus: Selain ei tue kaikkia tulostustapoja.
pdfjs-printing-not-ready = Varoitus: PDF-tiedosto ei ole vielä latautunut kokonaan, eikä sitä voi vielä tulostaa.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Näytä/piilota sivupaneeli
pdfjs-toggle-sidebar-notification-button =
    .title = Näytä/piilota sivupaneeli (dokumentissa on sisällys/liitteitä/tasoja)
pdfjs-toggle-sidebar-button-label = Näytä/piilota sivupaneeli
pdfjs-document-outline-button =
    .title = Näytä dokumentin sisällys (laajenna tai kutista kohdat kaksoisnapsauttamalla)
pdfjs-document-outline-button-label = Dokumentin sisällys
pdfjs-attachments-button =
    .title = Näytä liitteet
pdfjs-attachments-button-label = Liitteet
pdfjs-layers-button =
    .title = Näytä tasot (kaksoisnapsauta palauttaaksesi kaikki tasot oletustilaan)
pdfjs-layers-button-label = Tasot
pdfjs-thumbs-button =
    .title = Näytä pienoiskuvat
pdfjs-thumbs-button-label = Pienoiskuvat
pdfjs-current-outline-item-button =
    .title = Etsi nykyinen sisällyksen kohta
pdfjs-current-outline-item-button-label = Nykyinen sisällyksen kohta
pdfjs-findbar-button =
    .title = Etsi dokumentista
pdfjs-findbar-button-label = Etsi
pdfjs-additional-layers = Lisätasot

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Sivu { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Pienoiskuva sivusta { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Etsi
    .placeholder = Etsi dokumentista…
pdfjs-find-previous-button =
    .title = Etsi hakusanan edellinen osuma
pdfjs-find-previous-button-label = Edellinen
pdfjs-find-next-button =
    .title = Etsi hakusanan seuraava osuma
pdfjs-find-next-button-label = Seuraava
pdfjs-find-highlight-checkbox = Korosta kaikki
pdfjs-find-match-case-checkbox-label = Huomioi kirjainkoko
pdfjs-find-match-diacritics-checkbox-label = Erota tarkkeet
pdfjs-find-entire-word-checkbox-label = Kokonaiset sanat
pdfjs-find-reached-top = Päästiin dokumentin alkuun, jatketaan lopusta
pdfjs-find-reached-bottom = Päästiin dokumentin loppuun, jatketaan alusta
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } / { $total } osuma
       *[other] { $current } / { $total } osumaa
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Yli { $limit } osuma
       *[other] Yli { $limit } osumaa
    }
pdfjs-find-not-found = Hakusanaa ei löytynyt

## Predefined zoom values

pdfjs-page-scale-width = Sivun leveys
pdfjs-page-scale-fit = Koko sivu
pdfjs-page-scale-auto = Automaattinen suurennus
pdfjs-page-scale-actual = Todellinen koko
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Sivu { $page }

## Loading indicator messages

pdfjs-loading-error = Tapahtui virhe ladattaessa PDF-tiedostoa.
pdfjs-invalid-file-error = Virheellinen tai vioittunut PDF-tiedosto.
pdfjs-missing-file-error = Puuttuva PDF-tiedosto.
pdfjs-unexpected-response-error = Odottamaton vastaus palvelimelta.
pdfjs-rendering-error = Tapahtui virhe piirrettäessä sivua.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type }-merkintä]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Kirjoita PDF-tiedoston salasana.
pdfjs-password-invalid = Virheellinen salasana. Yritä uudestaan.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Peruuta
pdfjs-web-fonts-disabled = Verkkosivujen omat kirjasinlajit on estetty: ei voida käyttää upotettuja PDF-kirjasinlajeja.

## Editing

pdfjs-editor-free-text-button =
    .title = Teksti
pdfjs-editor-color-picker-free-text-input =
    .title = Muuta tekstin väriä
pdfjs-editor-free-text-button-label = Teksti
pdfjs-editor-ink-button =
    .title = Piirros
pdfjs-editor-color-picker-ink-input =
    .title = Vaihda piirustuksen väriä
pdfjs-editor-ink-button-label = Piirros
pdfjs-editor-stamp-button =
    .title = Lisää tai muokkaa kuvia
pdfjs-editor-stamp-button-label = Lisää tai muokkaa kuvia
pdfjs-editor-highlight-button =
    .title = Korostus
pdfjs-editor-highlight-button-label = Korostus
pdfjs-highlight-floating-button1 =
    .title = Korostus
    .aria-label = Korostus
pdfjs-highlight-floating-button-label = Korostus
pdfjs-comment-floating-button =
    .title = Kommentti
    .aria-label = Kommentti
pdfjs-comment-floating-button-label = Kommentti
pdfjs-editor-comment-button =
    .title = Kommentti
    .aria-label = Kommentti
pdfjs-editor-comment-button-label = Kommentti
pdfjs-editor-signature-button =
    .title = Lisää allekirjoitus
pdfjs-editor-signature-button-label = Lisää allekirjoitus

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Korostusmuokkain
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Piirustusmuokkain
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Allekirjoituksen muokkain: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Kuvamuokkain

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Poista piirros
pdfjs-editor-remove-freetext-button =
    .title = Poista teksti
pdfjs-editor-remove-stamp-button =
    .title = Poista kuva
pdfjs-editor-remove-highlight-button =
    .title = Poista korostus
pdfjs-editor-remove-signature-button =
    .title = Poista allekirjoitus

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Väri
pdfjs-editor-free-text-size-input = Koko
pdfjs-editor-ink-color-input = Väri
pdfjs-editor-ink-thickness-input = Paksuus
pdfjs-editor-ink-opacity-input = Peittävyys
pdfjs-editor-stamp-add-image-button =
    .title = Lisää kuva
pdfjs-editor-stamp-add-image-button-label = Lisää kuva
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Paksuus
pdfjs-editor-free-highlight-thickness-title =
    .title = Muuta paksuutta korostaessasi muita kohteita kuin tekstiä
pdfjs-editor-add-signature-container =
    .aria-label = Allekirjoitussäätimet ja tallennetut allekirjoitukset
pdfjs-editor-signature-add-signature-button =
    .title = Lisää uusi allekirjoitus
pdfjs-editor-signature-add-signature-button-label = Lisää uusi allekirjoitus
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Tallennettu allekirjoitus: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Tekstimuokkain
    .default-content = Aloita kirjoittaminen…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Kommentti
       *[other] Kommenttia
    }
pdfjs-editor-comments-sidebar-close-button =
    .title = Sulje sivupaneeli
    .aria-label = Sulje sivupaneeli
pdfjs-editor-comments-sidebar-close-button-label = Sulje sivupaneeli
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Näetkö jotain huomionarvoista? Korosta se ja jätä kommentti.
pdfjs-editor-comments-sidebar-no-comments-link = Lue lisää

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Vaihtoehtoinen teksti
pdfjs-editor-alt-text-edit-button =
    .aria-label = Muokkaa vaihtoehtoista tekstiä
pdfjs-editor-alt-text-dialog-label = Valitse vaihtoehto
pdfjs-editor-alt-text-dialog-description = Vaihtoehtoinen teksti ("alt-teksti") auttaa ihmisiä, jotka eivät näe kuvaa tai kun kuva ei lataudu.
pdfjs-editor-alt-text-add-description-label = Lisää kuvaus
pdfjs-editor-alt-text-add-description-description = Pyri 1-2 lauseeseen, jotka kuvaavat aihetta, ympäristöä tai toimintaa.
pdfjs-editor-alt-text-mark-decorative-label = Merkitse koristeelliseksi
pdfjs-editor-alt-text-mark-decorative-description = Tätä käytetään koristekuville, kuten reunuksille tai vesileimoille.
pdfjs-editor-alt-text-cancel-button = Peruuta
pdfjs-editor-alt-text-save-button = Tallenna
pdfjs-editor-alt-text-decorative-tooltip = Merkitty koristeelliseksi
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Esimerkiksi "Nuori mies istuu pöytään syömään aterian"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Vaihtoehtoinen teksti

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Vasen yläkulma - muuta kokoa
pdfjs-editor-resizer-top-middle =
    .aria-label = Ylhäällä keskellä - muuta kokoa
pdfjs-editor-resizer-top-right =
    .aria-label = Oikea yläkulma - muuta kokoa
pdfjs-editor-resizer-middle-right =
    .aria-label = Keskellä oikealla - muuta kokoa
pdfjs-editor-resizer-bottom-right =
    .aria-label = Oikea alakulma - muuta kokoa
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Alhaalla keskellä - muuta kokoa
pdfjs-editor-resizer-bottom-left =
    .aria-label = Vasen alakulma - muuta kokoa
pdfjs-editor-resizer-middle-left =
    .aria-label = Keskellä vasemmalla - muuta kokoa

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Korostusväri
pdfjs-editor-colorpicker-button =
    .title = Vaihda väri
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Värivalinnat
pdfjs-editor-colorpicker-yellow =
    .title = Keltainen
pdfjs-editor-colorpicker-green =
    .title = Vihreä
pdfjs-editor-colorpicker-blue =
    .title = Sininen
pdfjs-editor-colorpicker-pink =
    .title = Pinkki
pdfjs-editor-colorpicker-red =
    .title = Punainen

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Näytä kaikki
pdfjs-editor-highlight-show-all-button =
    .title = Näytä kaikki

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Muokkaa vaihtoehtoista tekstiä (kuvan kuvaus)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Lisää vaihtoehtoinen teksti (kuvan kuvaus)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Kirjoita kuvaus tähän…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Lyhyt kuvaus ihmisille, jotka eivät näe kuvaa tai kun kuva ei lataudu.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Tämä vaihtoehtoinen teksti luotiin automaattisesti, ja se voi olla epätarkka.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Lue lisää
pdfjs-editor-new-alt-text-create-automatically-button-label = Luo vaihtoehtoinen teksti automaattisesti
pdfjs-editor-new-alt-text-not-now-button = Ei nyt
pdfjs-editor-new-alt-text-error-title = Vaihtoehtotekstiä ei voitu luoda automaattisesti
pdfjs-editor-new-alt-text-error-description = Kirjoita oma vaihtoehtoinen teksti tai yritä myöhemmin uudelleen.
pdfjs-editor-new-alt-text-error-close-button = Sulje
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Ladataan vaihtoehtoisen tekstin tekoälymallia ({ $downloadedSize } / { $totalSize } Mt)
    .aria-valuetext = Ladataan vaihtoehtoisen tekstin tekoälymallia ({ $downloadedSize } / { $totalSize } Mt)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Vaihtoehtoinen teksti lisätty
pdfjs-editor-new-alt-text-added-button-label = Vaihtoehtoinen teksti lisätty
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Vaihtoehtoinen teksti puuttuu
pdfjs-editor-new-alt-text-missing-button-label = Vaihtoehtoinen teksti puuttuu
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Tarkista vaihtoehtoinen teksti
pdfjs-editor-new-alt-text-to-review-button-label = Tarkista vaihtoehtoinen teksti
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Luotu automaattisesti: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Kuvan vaihtoehtoisen tekstin asetukset
pdfjs-image-alt-text-settings-button-label = Kuvan vaihtoehtoisen tekstin asetukset
pdfjs-editor-alt-text-settings-dialog-label = Kuvan vaihtoehtoisen tekstin asetukset
pdfjs-editor-alt-text-settings-automatic-title = Automaattinen vaihtoehtoinen teksti
pdfjs-editor-alt-text-settings-create-model-button-label = Luo vaihtoehtoinen teksti automaattisesti
pdfjs-editor-alt-text-settings-create-model-description = Ehdottaa kuvauksia, jotka auttavat ihmisiä, jotka eivät näe kuvaa tai kun kuva ei lataudu.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Vaihtoehtoisen tekstin tekoälymalli ({ $totalSize } Mt)
pdfjs-editor-alt-text-settings-ai-model-description = Toimii paikallisesti laitteellasi, joten tietosi pysyvät yksityisinä. Vaadittu automaattiselle vaihtoehtoiselle tekstille.
pdfjs-editor-alt-text-settings-delete-model-button = Poista
pdfjs-editor-alt-text-settings-download-model-button = Lataa
pdfjs-editor-alt-text-settings-downloading-model-button = Ladataan…
pdfjs-editor-alt-text-settings-editor-title = Vaihtoehtoisen tekstin muokkain
pdfjs-editor-alt-text-settings-show-dialog-button-label = Näytä vaihtoehtoisen tekstin muokkain heti, kun lisäät kuvan
pdfjs-editor-alt-text-settings-show-dialog-description = Auttaa varmistamaan, että kaikissa kuvissasi on vaihtoehtoinen teksti.
pdfjs-editor-alt-text-settings-close-button = Sulje

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Korostus lisätty
pdfjs-editor-freetext-added-alert = Teksti lisätty
pdfjs-editor-ink-added-alert = Piirustus lisätty
pdfjs-editor-stamp-added-alert = Kuva lisätty
pdfjs-editor-signature-added-alert = Allekirjoitus lisätty

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Korostus poistettu
pdfjs-editor-undo-bar-message-freetext = Teksti poistettu
pdfjs-editor-undo-bar-message-ink = Piirustus poistettu
pdfjs-editor-undo-bar-message-stamp = Kuva poistettu
pdfjs-editor-undo-bar-message-signature = Allekirjoitus poistettu
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } merkintä poistettu
       *[other] { $count } merkintää poistettu
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Kumoa
pdfjs-editor-undo-bar-undo-button-label = Kumoa
pdfjs-editor-undo-bar-close-button =
    .title = Sulje
pdfjs-editor-undo-bar-close-button-label = Sulje

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Tämän ikkunan avulla käyttäjä voi luoda allekirjoituksen PDF-asiakirjaan lisättäväksi. Käyttäjä voi muokata nimeä (joka toimii myös vaihtoehtoisena tekstinä) ja valinnaisesti tallentaa allekirjoituksen toistuvaa käyttöä varten.
pdfjs-editor-add-signature-dialog-title = Lisää allekirjoitus

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Kirjoita
    .title = Kirjoita
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Piirrä
    .title = Piirrä
pdfjs-editor-add-signature-image-button = Kuva
    .title = Kuva

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Kirjoita allekirjoituksesi
    .placeholder = Kirjoita allekirjoituksesi
pdfjs-editor-add-signature-draw-placeholder = Piirrä allekirjoituksesi
pdfjs-editor-add-signature-draw-thickness-range-label = Paksuus
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Piirustuksen paksuus: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Lähetä tiedosto vetämällä se tähän
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Tai selaa kuvatiedostoja
       *[other] Tai selaa kuvatiedostoja
    }

## Controls

pdfjs-editor-add-signature-description-label = Kuvaus (vaihtoehtoinen teksti)
pdfjs-editor-add-signature-description-input =
    .title = Kuvaus (vaihtoehtoinen teksti)
pdfjs-editor-add-signature-description-default-when-drawing = Allekirjoitus
pdfjs-editor-add-signature-clear-button-label = Tyhjennä allekirjoitus
pdfjs-editor-add-signature-clear-button =
    .title = Tyhjennä allekirjoitus
pdfjs-editor-add-signature-save-checkbox = Tallenna allekirjoitus
pdfjs-editor-add-signature-save-warning-message = Olet saavuttanut viiden tallennetun allekirjoituksen rajan. Poista yksi säästääksesi lisää.
pdfjs-editor-add-signature-image-upload-error-title = Kuvaa ei voitu lähettää
pdfjs-editor-add-signature-image-upload-error-description = Tarkista verkkoyhteyden tila tai kokeile toista kuvaa.
pdfjs-editor-add-signature-image-no-data-error-title = Tätä kuvaa ei voida muuntaa allekirjoitukseksi
pdfjs-editor-add-signature-image-no-data-error-description = Yritä lähettää eri kuva.
pdfjs-editor-add-signature-error-close-button = Sulje

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Peruuta
pdfjs-editor-add-signature-add-button = Lisää
pdfjs-editor-edit-signature-update-button = Päivitä

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Muokkaa kommenttia
pdfjs-editor-edit-comment-popup-button =
    .title = Muokkaa kommenttia
pdfjs-editor-delete-comment-popup-button-label = Poista kommentti
pdfjs-editor-delete-comment-popup-button =
    .title = Poista kommentti
pdfjs-show-comment-button =
    .title = Näytä kommentti

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Toiminnot
pdfjs-editor-edit-comment-actions-button =
    .title = Toiminnot
pdfjs-editor-edit-comment-close-button-label = Sulje
pdfjs-editor-edit-comment-close-button =
    .title = Sulje
pdfjs-editor-edit-comment-actions-edit-button-label = Muokkaa
pdfjs-editor-edit-comment-actions-delete-button-label = Poista
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Kirjoita kommenttisi
pdfjs-editor-edit-comment-manager-cancel-button = Peruuta
pdfjs-editor-edit-comment-manager-save-button = Tallenna
# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Muokkaa kommenttia
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Päivitä
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Lisää kommentti
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Lisää
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Aloita kirjoittaminen…
pdfjs-editor-edit-comment-dialog-cancel-button = Peruuta

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Muokkaa kommenttia
pdfjs-editor-add-comment-button =
    .title = Lisää kommentti

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Poista tallennettu allekirjoitus
pdfjs-editor-delete-signature-button-label1 = Poista tallennettu allekirjoitus

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Muokkaa kuvausta

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Muokkaa kuvausta
