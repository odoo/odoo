# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Forrige side
pdfjs-previous-button-label = Forrige
pdfjs-next-button =
    .title = Neste side
pdfjs-next-button-label = Neste
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Side
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = av { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } av { $pagesCount })
pdfjs-zoom-out-button =
    .title = Zoom ut
pdfjs-zoom-out-button-label = Zoom ut
pdfjs-zoom-in-button =
    .title = Zoom inn
pdfjs-zoom-in-button-label = Zoom inn
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Bytt til presentasjonsmodus
pdfjs-presentation-mode-button-label = Presentasjonsmodus
pdfjs-open-file-button =
    .title = Åpne fil
pdfjs-open-file-button-label = Åpne
pdfjs-print-button =
    .title = Skriv ut
pdfjs-print-button-label = Skriv ut
pdfjs-save-button =
    .title = Lagre
pdfjs-save-button-label = Lagre
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Last ned
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Last ned
pdfjs-bookmark-button =
    .title = Gjeldende side (se URL fra gjeldende side)
pdfjs-bookmark-button-label = Gjeldende side

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Verktøy
pdfjs-tools-button-label = Verktøy
pdfjs-first-page-button =
    .title = Gå til første side
pdfjs-first-page-button-label = Gå til første side
pdfjs-last-page-button =
    .title = Gå til siste side
pdfjs-last-page-button-label = Gå til siste side
pdfjs-page-rotate-cw-button =
    .title = Roter med klokken
pdfjs-page-rotate-cw-button-label = Roter med klokken
pdfjs-page-rotate-ccw-button =
    .title = Roter mot klokken
pdfjs-page-rotate-ccw-button-label = Roter mot klokken
pdfjs-cursor-text-select-tool-button =
    .title = Aktiver tekstmarkeringsverktøy
pdfjs-cursor-text-select-tool-button-label = Tekstmarkeringsverktøy
pdfjs-cursor-hand-tool-button =
    .title = Aktiver handverktøy
pdfjs-cursor-hand-tool-button-label = Handverktøy
pdfjs-scroll-page-button =
    .title = Bruk siderulling
pdfjs-scroll-page-button-label = Siderulling
pdfjs-scroll-vertical-button =
    .title = Bruk vertikal rulling
pdfjs-scroll-vertical-button-label = Vertikal rulling
pdfjs-scroll-horizontal-button =
    .title = Bruk horisontal rulling
pdfjs-scroll-horizontal-button-label = Horisontal rulling
pdfjs-scroll-wrapped-button =
    .title = Bruk flersiderulling
pdfjs-scroll-wrapped-button-label = Flersiderulling
pdfjs-spread-none-button =
    .title = Vis enkeltsider
pdfjs-spread-none-button-label = Enkeltsider
pdfjs-spread-odd-button =
    .title = Vis oppslag med ulike sidenumre til venstre
pdfjs-spread-odd-button-label = Oppslag med forside
pdfjs-spread-even-button =
    .title = Vis oppslag med like sidenumre til venstre
pdfjs-spread-even-button-label = Oppslag uten forside

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumentegenskaper …
pdfjs-document-properties-button-label = Dokumentegenskaper …
pdfjs-document-properties-file-name = Filnavn:
pdfjs-document-properties-file-size = Filstørrelse:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } byte)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } byte)
pdfjs-document-properties-title = Dokumentegenskaper …
pdfjs-document-properties-author = Forfatter:
pdfjs-document-properties-subject = Emne:
pdfjs-document-properties-keywords = Nøkkelord:
pdfjs-document-properties-creation-date = Opprettet dato:
pdfjs-document-properties-modification-date = Endret dato:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Opprettet av:
pdfjs-document-properties-producer = PDF-verktøy:
pdfjs-document-properties-version = PDF-versjon:
pdfjs-document-properties-page-count = Sideantall:
pdfjs-document-properties-page-size = Sidestørrelse:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = stående
pdfjs-document-properties-page-size-orientation-landscape = liggende
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
pdfjs-document-properties-linearized = Hurtig nettvisning:
pdfjs-document-properties-linearized-yes = Ja
pdfjs-document-properties-linearized-no = Nei
pdfjs-document-properties-close-button = Lukk
pdfjs-digital-signature-properties-view-certificate = Vis sertifikat
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Grunn: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Tidsstempel: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Undersignatur ({ $count })
       *[other] Undersignaturer ({ $count })
    }

## Print

pdfjs-print-progress-message = Forbereder dokument for utskrift …
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Avbryt
pdfjs-printing-not-supported = Advarsel: Utskrift er ikke fullstendig støttet av denne nettleseren.
pdfjs-printing-not-ready = Advarsel: PDF er ikke fullstendig innlastet for utskrift.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Finn gjeldende disposisjonselement
pdfjs-current-outline-item-button-label = Gjeldende disposisjonselement
pdfjs-findbar-button =
    .title = Finn i dokumentet
pdfjs-findbar-button-label = Finn
pdfjs-additional-layers = Ytterligere lag

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatyrbilde av side { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Velg side { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Side { $page } av { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Søk i dokument…
    .title = Søk
pdfjs-find-previous-button =
    .title = Finn forrige forekomst av frasen
pdfjs-find-previous-button-label = Forrige
pdfjs-find-next-button =
    .title = Finn neste forekomst av frasen
pdfjs-find-next-button-label = Neste
pdfjs-find-highlight-checkbox = Uthev alle
pdfjs-find-match-case-checkbox-label = Skill store/små bokstaver
pdfjs-find-match-diacritics-checkbox-label = Samsvar diakritiske tegn
pdfjs-find-entire-word-checkbox-label = Hele ord
pdfjs-find-reached-top = Nådde toppen av dokumentet, fortsetter fra bunnen
pdfjs-find-reached-bottom = Nådde bunnen av dokumentet, fortsetter fra toppen
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } av { $total } treff
       *[other] { $current } av { $total } treff
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mer enn { $limit } treff
       *[other] Mer enn { $limit } treff
    }
pdfjs-find-not-found = Fant ikke teksten

## Predefined zoom values

pdfjs-page-scale-width = Sidebredde
pdfjs-page-scale-fit = Tilpass til siden
pdfjs-page-scale-auto = Automatisk zoom
pdfjs-page-scale-actual = Virkelig størrelse
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Side { $page }

## Loading indicator messages

pdfjs-loading-error = En feil oppstod ved lasting av PDF.
pdfjs-invalid-file-error = Ugyldig eller skadet PDF-fil.
pdfjs-missing-file-error = Manglende PDF-fil.
pdfjs-unexpected-response-error = Uventet serverrespons.
pdfjs-rendering-error = En feil oppstod ved opptegning av siden.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } annotasjon]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Skriv inn passordet for å åpne denne PDF-filen.
pdfjs-password-invalid = Ugyldig passord. Prøv igjen.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Avbryt
pdfjs-web-fonts-disabled = Web-fonter er avslått: Kan ikke bruke innbundne PDF-fonter.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-color-picker-free-text-input =
    .title = Endre tekstfarge
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Tegn
pdfjs-editor-color-picker-ink-input =
    .title = Endre tegnefarge
pdfjs-editor-ink-button-label = Tegn
pdfjs-editor-stamp-button =
    .title = Legg til eller rediger bilder
pdfjs-editor-stamp-button-label = Legg til eller rediger bilder
pdfjs-editor-highlight-button =
    .title = Markere
pdfjs-editor-highlight-button-label = Markere
pdfjs-highlight-floating-button1 =
    .aria-label = Markere
    .title = Markere
pdfjs-highlight-floating-button-label = Markere
pdfjs-comment-floating-button =
    .aria-label = Kommenter
    .title = Kommenter
pdfjs-comment-floating-button-label = Kommenter
pdfjs-editor-comment-button =
    .aria-label = Kommentar
    .title = Kommentar
pdfjs-editor-comment-button-label = Kommentar
pdfjs-editor-signature-button =
    .title = Legg til signatur
pdfjs-editor-signature-button-label = Legg til signatur

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Redigering av markering
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Redigering av tegninger
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Signatur-redigerer: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Bilderedigerer

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Fjern tegningen
pdfjs-editor-remove-freetext-button =
    .title = Fjern tekst
pdfjs-editor-remove-stamp-button =
    .title = Fjern bildet
pdfjs-editor-remove-highlight-button =
    .title = Fjern utheving
pdfjs-editor-remove-signature-button =
    .title = Fjern signatur

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Farge
pdfjs-editor-free-text-size-input = Størrelse
pdfjs-editor-ink-color-input = Farge
pdfjs-editor-ink-thickness-input = Tykkelse
pdfjs-editor-ink-opacity-input = Opasitet
pdfjs-editor-stamp-add-image-button =
    .title = Legg til bilde
pdfjs-editor-stamp-add-image-button-label = Legg til bilde
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Tykkelse
pdfjs-editor-free-highlight-thickness-title =
    .title = Endre tykkelse når du markerer andre elementer enn tekst
pdfjs-editor-add-signature-container =
    .aria-label = Signaturkontroller og lagrede signaturer
pdfjs-editor-signature-add-signature-button =
    .title = Legg til ny signatur
pdfjs-editor-signature-add-signature-button-label = Legg til ny signatur
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Lagret signatur: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Tekstredigering
    .default-content = Begynn å skrive…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Kommentar
       *[other] Kommentarer
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Lukk sidestolpen
    .title = Lukk sidestolpen
pdfjs-editor-comments-sidebar-close-button-label = Lukk sidestolpen
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Ser du noe verdt å merke seg? Marker det og legg igjen en kommentar.
pdfjs-editor-comments-sidebar-no-comments-link = Les mer

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternativ tekst
pdfjs-editor-alt-text-edit-button =
    .aria-label = Rediger alternativ tekst
pdfjs-editor-alt-text-dialog-label = Velg et alternativ
pdfjs-editor-alt-text-dialog-description = Alt-tekst (alternativ tekst) hjelper når folk ikke kan se bildet eller når det ikke lastes inn.
pdfjs-editor-alt-text-add-description-label = Legg til en beskrivelse
pdfjs-editor-alt-text-add-description-description = Gå etter 1-2 setninger som beskriver emnet, settingen eller handlingene.
pdfjs-editor-alt-text-mark-decorative-label = Merk som dekorativt
pdfjs-editor-alt-text-mark-decorative-description = Dette brukes til dekorative bilder, som kantlinjer eller vannmerker.
pdfjs-editor-alt-text-cancel-button = Avbryt
pdfjs-editor-alt-text-save-button = Lagre
pdfjs-editor-alt-text-decorative-tooltip = Merket som dekorativ
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = For eksempel, «En ung mann setter seg ved et bord for å spise et måltid»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativ tekst

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Øverste venstre hjørne – endre størrelse
pdfjs-editor-resizer-top-middle =
    .aria-label = Øverst i midten — endre størrelse
pdfjs-editor-resizer-top-right =
    .aria-label = Øverste høyre hjørne – endre størrelse
pdfjs-editor-resizer-middle-right =
    .aria-label = Midt til høyre – endre størrelse
pdfjs-editor-resizer-bottom-right =
    .aria-label = Nederste høyre hjørne – endre størrelse
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Nederst i midten — endre størrelse
pdfjs-editor-resizer-bottom-left =
    .aria-label = Nederste venstre hjørne – endre størrelse
pdfjs-editor-resizer-middle-left =
    .aria-label = Midt til venstre — endre størrelse

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Uthevingsfarge
pdfjs-editor-colorpicker-button =
    .title = Endre farge
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Fargevalg
pdfjs-editor-colorpicker-yellow =
    .title = Gul
pdfjs-editor-colorpicker-green =
    .title = Grønn
pdfjs-editor-colorpicker-blue =
    .title = Blå
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Rød

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Vis alle
pdfjs-editor-highlight-show-all-button =
    .title = Vis alle

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Rediger alternativ tekst (bildebeskrivelse)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Legg til alternativ tekst (bildebeskrivelse)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Skriv din beskrivelse her…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kort beskrivelse for folk som ikke kan se bildet eller når bildet ikke lastes inn.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Denne alternative teksten ble opprettet automatisk og kan være unøyaktig.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Les mer
pdfjs-editor-new-alt-text-create-automatically-button-label = Lag alternativ tekst automatisk
pdfjs-editor-new-alt-text-not-now-button = Ikke nå
pdfjs-editor-new-alt-text-error-title = Kunne ikke opprette alternativ tekst automatisk
pdfjs-editor-new-alt-text-error-description = Skriv din egen alternativ tekst eller prøv igjen senere.
pdfjs-editor-new-alt-text-error-close-button = Lukk
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Laster ned alternativ tekst AI-modell ({ $downloadedSize } av { $totalSize } MB)
    .aria-valuetext = Laster ned alternativ tekst AI-modell ({ $downloadedSize } av { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativ tekst lagt til
pdfjs-editor-new-alt-text-added-button-label = Alternativ tekst lagt til
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Mangler alternativ tekst
pdfjs-editor-new-alt-text-missing-button-label = Mangler alternativ tekst
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Gjennomgå alt-tekst
pdfjs-editor-new-alt-text-to-review-button-label = Gjennomgå alternativ tekst
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Opprettet automatisk: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Innstillinger for alternativ tekst for bilde
pdfjs-image-alt-text-settings-button-label = Innstillinger for alternativ tekst for bilde
pdfjs-editor-alt-text-settings-dialog-label = Innstillinger for alternativ tekst for bilde
pdfjs-editor-alt-text-settings-automatic-title = Automatisk alternativ tekst
pdfjs-editor-alt-text-settings-create-model-button-label = Opprett alternativ tekst automatisk
pdfjs-editor-alt-text-settings-create-model-description = Foreslår beskrivelser for å hjelpe folk som ikke kan se bildet eller når bildet ikke lastes inn.
pdfjs-editor-alt-text-settings-editor-title = Alternativ tekst-redigerer
pdfjs-editor-alt-text-settings-show-dialog-button-label = Vis alternativ tekst-redigerer direkte når du legger til et bilde
pdfjs-editor-alt-text-settings-show-dialog-description = Hjelper deg å sørge for at alle bildene dine har alternativ tekst.
pdfjs-editor-alt-text-settings-close-button = Lukk

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Utheving lagt til
pdfjs-editor-freetext-added-alert = Tekst lagt til
pdfjs-editor-ink-added-alert = Tegning lagt til
pdfjs-editor-stamp-added-alert = Bilde lagt til
pdfjs-editor-signature-added-alert = Signatur lagt til

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Markering fjernet
pdfjs-editor-undo-bar-message-freetext = Tekst fjernet
pdfjs-editor-undo-bar-message-ink = Tegning fjernet
pdfjs-editor-undo-bar-message-stamp = Bilde fjernet
pdfjs-editor-undo-bar-message-signature = Signatur fjernet
pdfjs-editor-undo-bar-message-comment = Kommentar fjernet
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } kommentar fjernet
       *[other] { $count } kommentarer fjernet
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Angre
pdfjs-editor-undo-bar-undo-button-label = Angre
pdfjs-editor-undo-bar-close-button =
    .title = Lukk
pdfjs-editor-undo-bar-close-button-label = Lukk

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Denne modalen lar brukeren lage en signatur for å legge til et PDF-dokument. Brukeren kan redigere navnet (som også fungerer som alt-teksten), og eventuelt lagre signaturen for gjentatt bruk.
pdfjs-editor-add-signature-dialog-title = Legg til en signatur

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Type
    .title = Type
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Tegn
    .title = Tegn
pdfjs-editor-add-signature-image-button = Bilde
    .title = Bilde

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Skriv inn signaturen din
    .placeholder = Skriv inn signaturen din
pdfjs-editor-add-signature-draw-placeholder = Tegn signaturen din
pdfjs-editor-add-signature-draw-thickness-range-label = Tykkelse
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Linjetykkelse: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Dra en fil her for å laste opp
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Eller velg bildefiler
       *[other] Eller velg bildefiler
    }

## Controls

pdfjs-editor-add-signature-description-label = Beskrivelse (alternativ tekst)
pdfjs-editor-add-signature-description-input =
    .title = Beskrivelse (alternativ tekst)
pdfjs-editor-add-signature-description-default-when-drawing = Signatur
pdfjs-editor-add-signature-clear-button-label = Fjern signatur
pdfjs-editor-add-signature-clear-button =
    .title = Fjern signatur
pdfjs-editor-add-signature-save-checkbox = Lagre signatur
pdfjs-editor-add-signature-save-warning-message = Du har nådd grensen på 5 lagrede signaturer. Fjern en for å lagre en ny.
pdfjs-editor-add-signature-image-upload-error-title = Kunne ikke laste opp bildet
pdfjs-editor-add-signature-image-upload-error-description = Sjekk nettverkstilkoblingen eller prøv et annet bilde.
pdfjs-editor-add-signature-image-no-data-error-title = Kan ikke konvertere dette bildet til en signatur
pdfjs-editor-add-signature-image-no-data-error-description = Prøv å laste opp et annet bilde.
pdfjs-editor-add-signature-error-close-button = Lukk

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Avbryt
pdfjs-editor-add-signature-add-button = Legg til
pdfjs-editor-edit-signature-update-button = Oppdater

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Rediger kommentar
pdfjs-editor-edit-comment-popup-button =
    .title = Rediger kommentar
pdfjs-editor-delete-comment-popup-button-label = Fjern kommentar
pdfjs-editor-delete-comment-popup-button =
    .title = Fjern kommentar
pdfjs-show-comment-button =
    .title = Vis kommentar

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Rediger kommentar
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Oppdater
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Legg til kommentar
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Legg til
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Begynn å skrive…
pdfjs-editor-edit-comment-dialog-cancel-button = Avbryt

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Legg til kommentar

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Vis/skjul sidestolpe (dokumentet inneholder miniatyrbilder/disposisjon/vedlegg/lag)
pdfjs-toggle-views-manager-button1-label = Behandle sider
pdfjs-views-manager-sidebar =
    .aria-label = Sidestolpe
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Endre størrelse på sidestolpen
pdfjs-views-manager-view-selector-button =
    .title = Visninger
pdfjs-views-manager-view-selector-button-label = Visninger
pdfjs-views-manager-pages-title = Sider
pdfjs-views-manager-outlines-title1 = Dokumentoversikt
    .title = Dokumentoversikt (dobbeltklikk for å utvide/skjule alle elementer)
pdfjs-views-manager-attachments-title = Vedlegg
pdfjs-views-manager-layers-title1 = Lag
    .title = Lag (dobbeltklikk for å tilbakestille alle lag til standardtilstand)
pdfjs-views-manager-pages-option-label = Sider
pdfjs-views-manager-outlines-option-label = Dokumentdisposisjon
pdfjs-views-manager-attachments-option-label = Vedlegg
pdfjs-views-manager-layers-option-label = Lag
pdfjs-views-manager-add-file-button =
    .title = Legg til fil
pdfjs-views-manager-add-file-button-label = Legg til fil
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } valgt
       *[other] { $count } valgt
    }
pdfjs-views-manager-pages-status-none-action-label = Velg sider
pdfjs-views-manager-pages-status-action-button-label = Behandle
pdfjs-views-manager-pages-status-copy-button-label = Kopier
pdfjs-views-manager-pages-status-cut-button-label = Klipp ut
pdfjs-views-manager-pages-status-delete-button-label = Slett
pdfjs-views-manager-pages-status-export-selected-button-label = Eksporter valgte…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 side klippet ut
       *[other] { $count } sider klippet ut
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 side kopiert
       *[other] { $count } sider kopiert
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 side slettet
       *[other] { $count } sider slettet
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Klargjør filen din …
pdfjs-views-manager-pages-status-waiting-uploading-label = Laster opp filen …
pdfjs-views-manager-status-warning-cut-label = Kunne ikke klippe ut. Oppdater siden og prøv på nytt.
pdfjs-views-manager-status-warning-copy-label = Kunne ikke kopiere. Oppdater siden og prøv på nytt.
pdfjs-views-manager-status-warning-delete-label = Kunne ikke slette. Oppdater siden og prøv på nytt.
pdfjs-views-manager-status-warning-save-label = Kunne ikke lagre. Oppdater siden og prøv på nytt.
pdfjs-views-manager-status-undo-button-label = Angre
pdfjs-views-manager-status-done-button-label = Ferdig
pdfjs-views-manager-status-close-button =
    .title = Lukk
pdfjs-views-manager-status-close-button-label = Lukk
pdfjs-views-manager-paste-button-label = Lim inn
pdfjs-views-manager-paste-button-before =
    .title = Lim inn før første side
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Lim inn etter side { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NY
pdfjs-views-manager-waiting-for-file = Laster opp filen …
pdfjs-toggle-views-manager-button1 =
    .title = Behandle sider

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Egenskaper for digital signatur
    .title = Egenskaper for digital signatur
pdfjs-digital-signature-properties-button-label = Egenskaper for digital signatur

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Dokumentet ble signert med en gyldig digital signatur
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Dokumentet er signert, men { $count } digital signatur kunne ikke verifiseres
       *[other] Dokumentet er signert, men { $count } digitale signaturer kunne ikke verifiseres
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Dokumentet er signert med { $count } sertifikat som ikke er klarert
       *[other] Dokumentet er signert med { $count } sertifikater som ikke er klarert
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Dokumentet er signert med { $count } utløpt sertifikat
       *[other] Dokumentet er signert med { $count } utløpte sertifikater
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] Dokumentet har { $count } ugyldig digital signatur
       *[other] Dokumentet har { $count } ugyldige digitale signaturer
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Dokumentet er signert med { $count } tilbakekalt sertifikat
       *[other] Dokumentet er signert med { $count } tilbakekalte sertifikater
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Status: Signatur bekreftet
pdfjs-digital-signature-properties-status-invalid = Status: Signatur ugyldig
pdfjs-digital-signature-properties-status-unknown = Status: Kan ikke bekrefte (støttes ikke)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Sertifikat: Klarert ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Sertifikat: Utilgjengelig
pdfjs-digital-signature-properties-certificate-untrusted = Sertifikat: Ikke klarert
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Sertifikat: Ukjent utsteder ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Sertifikat: Selvsignert ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Sertifikat: Ikke klarert utsteder ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Sertifikat: Utløpt
pdfjs-digital-signature-properties-certificate-expired-with-date = Sertifikat: Utløpt ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Sertifikat: Tilbakekalt

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Fjern lagret signatur
pdfjs-editor-delete-signature-button-label1 = Fjern lagret signatur

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Rediger beskrivelse

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Rediger beskrivelse
