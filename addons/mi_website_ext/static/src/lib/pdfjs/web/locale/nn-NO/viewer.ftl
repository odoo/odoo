# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Føregåande side
pdfjs-previous-button-label = Føregåande
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
    .title = Byt til presentasjonsmodus
pdfjs-presentation-mode-button-label = Presentasjonsmodus
pdfjs-open-file-button =
    .title = Opne fil
pdfjs-open-file-button-label = Opne
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
    .title = Gjeldande side (sjå URL frå gjeldande side)
pdfjs-bookmark-button-label = Gjeldande side

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
    .title = Roter med klokka
pdfjs-page-rotate-cw-button-label = Roter med klokka
pdfjs-page-rotate-ccw-button =
    .title = Roter mot klokka
pdfjs-page-rotate-ccw-button-label = Roter mot klokka
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
    .title = Bruk fleirsiderulling
pdfjs-scroll-wrapped-button-label = Fleirsiderulling
pdfjs-spread-none-button =
    .title = Vis enkeltsider
pdfjs-spread-none-button-label = Enkeltside
pdfjs-spread-odd-button =
    .title = Vis oppslag med ulike sidenummer til venstre
pdfjs-spread-odd-button-label = Oppslag med framside
pdfjs-spread-even-button =
    .title = Vis oppslag med like sidenummmer til venstre
pdfjs-spread-even-button-label = Oppslag utan framside

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumenteigenskapar…
pdfjs-document-properties-button-label = Dokumenteigenskapar…
pdfjs-document-properties-file-name = Filnamn:
pdfjs-document-properties-file-size = Filstorleik:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } kB ({ $b } byte)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } byte)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bytes)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bytes)
pdfjs-document-properties-title = Tittel:
pdfjs-document-properties-author = Forfattar:
pdfjs-document-properties-subject = Emne:
pdfjs-document-properties-keywords = Stikkord:
pdfjs-document-properties-creation-date = Dato oppretta:
pdfjs-document-properties-modification-date = Dato endra:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Oppretta av:
pdfjs-document-properties-producer = PDF-verktøy:
pdfjs-document-properties-version = PDF-versjon:
pdfjs-document-properties-page-count = Sidetal:
pdfjs-document-properties-page-size = Sidestørrelse:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = ståande (portrait)
pdfjs-document-properties-page-size-orientation-landscape = liggande (landscape)
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Brev
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
pdfjs-document-properties-linearized = Rask nettvising:
pdfjs-document-properties-linearized-yes = Ja
pdfjs-document-properties-linearized-no = Nei
pdfjs-document-properties-close-button = Lat att

## Print

pdfjs-print-progress-message = Førebur dokumentet for utskrift…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Avbryt
pdfjs-printing-not-supported = Åtvaring: Utskrift er ikkje fullstendig støtta av denne nettlesaren.
pdfjs-printing-not-ready = Åtvaring: PDF ikkje fullstendig innlasta for utskrift.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Slå av/på sidestolpe
pdfjs-toggle-sidebar-notification-button =
    .title = Vis/gøym sidestolpe (dokumentet inneheld oversikt/vedlegg/lag)
pdfjs-toggle-sidebar-button-label = Slå av/på sidestolpe
pdfjs-document-outline-button =
    .title = Vis dokumentdisposisjonen (dobbelklikk for å utvide/gøyme alle elementa)
pdfjs-document-outline-button-label = Dokumentdisposisjon
pdfjs-attachments-button =
    .title = Vis vedlegg
pdfjs-attachments-button-label = Vedlegg
pdfjs-layers-button =
    .title = Vis lag (dobbeltklikk for å tilbakestille alle lag til standardtilstand)
pdfjs-layers-button-label = Lag
pdfjs-thumbs-button =
    .title = Vis miniatyrbilde
pdfjs-thumbs-button-label = Miniatyrbilde
pdfjs-current-outline-item-button =
    .title = Finn gjeldande disposisjonselement
pdfjs-current-outline-item-button-label = Gjeldande disposisjonselement
pdfjs-findbar-button =
    .title = Finn i dokumentet
pdfjs-findbar-button-label = Finn
pdfjs-additional-layers = Ytterlegare lag

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Side { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatyrbilde av side { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Søk
    .placeholder = Søk i dokument…
pdfjs-find-previous-button =
    .title = Finn førre førekomst av frasen
pdfjs-find-previous-button-label = Førre
pdfjs-find-next-button =
    .title = Finn neste førekomst av frasen
pdfjs-find-next-button-label = Neste
pdfjs-find-highlight-checkbox = Uthev alle
pdfjs-find-match-case-checkbox-label = Skil store/små bokstavar
pdfjs-find-match-diacritics-checkbox-label = Samsvar diakritiske teikn
pdfjs-find-entire-word-checkbox-label = Heile ord
pdfjs-find-reached-top = Nådde toppen av dokumentet, fortset frå botnen
pdfjs-find-reached-bottom = Nådde botnen av dokumentet, fortset frå toppen
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
        [one] Meir enn { $limit } treff
       *[other] Meir enn { $limit } treff
    }
pdfjs-find-not-found = Fann ikkje teksten

## Predefined zoom values

pdfjs-page-scale-width = Sidebreidde
pdfjs-page-scale-fit = Tilpass til sida
pdfjs-page-scale-auto = Automatisk skalering
pdfjs-page-scale-actual = Verkeleg storleik
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Side { $page }

## Loading indicator messages

pdfjs-loading-error = Ein feil oppstod ved lasting av PDF.
pdfjs-invalid-file-error = Ugyldig eller korrupt PDF-fil.
pdfjs-missing-file-error = Manglande PDF-fil.
pdfjs-unexpected-response-error = Uventa tenarrespons.
pdfjs-rendering-error = Ein feil oppstod under vising av sida.

## Annotations

# Variables:
#   $date (Date) - the modification date of the annotation
#   $time (Time) - the modification time of the annotation
pdfjs-annotation-date-string = { $date } { $time }
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

pdfjs-password-label = Skriv inn passordet for å opne denne PDF-fila.
pdfjs-password-invalid = Ugyldig passord. Prøv på nytt.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Avbryt
pdfjs-web-fonts-disabled = Web-skrifter er slått av: Kan ikkje bruke innbundne PDF-skrifter.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Teikne
pdfjs-editor-ink-button-label = Teikne
pdfjs-editor-stamp-button =
    .title = Legg til eller rediger bilde
pdfjs-editor-stamp-button-label = Legg til eller rediger bilde
pdfjs-editor-highlight-button =
    .title = Markere
pdfjs-editor-highlight-button-label = Markere
pdfjs-highlight-floating-button1 =
    .title = Markere
    .aria-label = Markere
pdfjs-highlight-floating-button-label = Markere
pdfjs-editor-signature-button =
    .title = Legg til signatur
pdfjs-editor-signature-button-label = Legg til signatur

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Markeringsredigerar
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Signatur-redigerar: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Bildredigerar

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Fjern teikninga
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
pdfjs-editor-free-text-size-input = Storleik
pdfjs-editor-ink-color-input = Farge
pdfjs-editor-ink-thickness-input = Tjukn
pdfjs-editor-ink-opacity-input = Ugjennomskinleg
pdfjs-editor-stamp-add-image-button =
    .title = Legg til bilde
pdfjs-editor-stamp-add-image-button-label = Legg til bilde
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Tjukn
pdfjs-editor-free-highlight-thickness-title =
    .title = Endre tjukn når du markerer andre element enn tekst
pdfjs-editor-add-signature-container =
    .aria-label = Signaturkontroll og lagra signaturar
pdfjs-editor-signature-add-signature-button =
    .title = Legg til ny signatur
pdfjs-editor-signature-add-signature-button-label = Legg til ny signatur
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Lagra signatur: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Tekstredigering
    .default-content = Begynn å skrive…
pdfjs-free-text =
    .aria-label = Tekstredigering
pdfjs-free-text-default-content = Byrje å skrive…
pdfjs-ink =
    .aria-label = Teikneredigering
pdfjs-ink-canvas =
    .aria-label = Brukarskapt bilde

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alt-tekst
pdfjs-editor-alt-text-edit-button =
    .aria-label = Rediger alt-tekst tekst
pdfjs-editor-alt-text-edit-button-label = Rediger alt-tekst tekst
pdfjs-editor-alt-text-dialog-label = Vel eit alternativ
pdfjs-editor-alt-text-dialog-description = Alt-tekst (alternativ tekst) hjelper når folk ikkje kan sjå bildet eller når det ikkje vert lasta inn.
pdfjs-editor-alt-text-add-description-label = Legg til ei skildring
pdfjs-editor-alt-text-add-description-description = Gå etter 1-2 setninger som skildrar emnet, settinga eller handlingane.
pdfjs-editor-alt-text-mark-decorative-label = Merk som dekorativt
pdfjs-editor-alt-text-mark-decorative-description = Dette vert brukt til dekorative bilde, som kantlinjer eller vassmerke.
pdfjs-editor-alt-text-cancel-button = Avbryt
pdfjs-editor-alt-text-save-button = Lagre
pdfjs-editor-alt-text-decorative-tooltip = Merkt som dekorativ
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Til dømes, «Ein ung mann set seg ved eit bord for å ete eit måltid»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alt-tekst

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Øvste venstre hjørne – endre størrelse
pdfjs-editor-resizer-label-top-middle = Øvst i midten — endre størrelse
pdfjs-editor-resizer-label-top-right = Øvste høgre hjørne – endre størrelse
pdfjs-editor-resizer-label-middle-right = Midt til høgre – endre størrelse
pdfjs-editor-resizer-label-bottom-right = Nedste høgre hjørne – endre størrelse
pdfjs-editor-resizer-label-bottom-middle = Nedst i midten — endre størrelse
pdfjs-editor-resizer-label-bottom-left = Nedste venstre hjørne – endre størrelse
pdfjs-editor-resizer-label-middle-left = Midt til venstre — endre størrelse
pdfjs-editor-resizer-top-left =
    .aria-label = Øvste venstre hjørne – endre størrelse
pdfjs-editor-resizer-top-middle =
    .aria-label = Øvst i midten — endre størrelse
pdfjs-editor-resizer-top-right =
    .aria-label = Øvste høgre hjørne – endre størrelse
pdfjs-editor-resizer-middle-right =
    .aria-label = Midt til høgre – endre størrelse
pdfjs-editor-resizer-bottom-right =
    .aria-label = Nedste høgre hjørne – endre størrelse
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Nedst i midten — endre størrelse
pdfjs-editor-resizer-bottom-left =
    .aria-label = Nedste venstre hjørne – endre størrelse
pdfjs-editor-resizer-middle-left =
    .aria-label = Midt til venstre — endre størrelse

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Uthevingsfarge
pdfjs-editor-colorpicker-button =
    .title = Endre farge
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Fargeval
pdfjs-editor-colorpicker-yellow =
    .title = Gul
pdfjs-editor-colorpicker-green =
    .title = Grøn
pdfjs-editor-colorpicker-blue =
    .title = Blå
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Raud

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Vis alle
pdfjs-editor-highlight-show-all-button =
    .title = Vis alle

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Rediger alternativ tekst (bildeskildring)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Legg til alternativ tekst (bildeskildring)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Skriv skildringa di her…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kort skildring for personar som ikkje kan sjå bildet, eller når bildet ikkje lastar inn.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Denne alternative teksten vart oppretta automatisk, og kan vere unøyaktig.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Les meir
pdfjs-editor-new-alt-text-create-automatically-button-label = Opprett alternativ tekt automatisk
pdfjs-editor-new-alt-text-not-now-button = Ikkje no
pdfjs-editor-new-alt-text-error-title = Klarte ikkje å opprette alternativ tekst automatisk
pdfjs-editor-new-alt-text-error-description = Skriv din eigen alternative tekst eller prøv igjen seinare.
pdfjs-editor-new-alt-text-error-close-button = Lat att
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Lastar ned AI-modell med alternativ tekst ({ $downloadedSize } av { $totalSize } MB)
    .aria-valuetext = Lastar ned AI-modell med alternativ tekst ({ $downloadedSize } av { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativ tekst lagt til
pdfjs-editor-new-alt-text-added-button-label = Alternativ tekst lagt til
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Manglande alternativ tekst
pdfjs-editor-new-alt-text-missing-button-label = Manglande alternativ tekst
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Vurder alternativ tekst
pdfjs-editor-new-alt-text-to-review-button-label = Vurder alternativ tekst
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Oppretta automatisk: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Alternative tekst-innstillingar for bilde
pdfjs-image-alt-text-settings-button-label = Alternative tekst-innstillingar for bilde
pdfjs-editor-alt-text-settings-dialog-label = Alternative tekst-innstillingar for bilde
pdfjs-editor-alt-text-settings-automatic-title = Automatisk alternativ tekst
pdfjs-editor-alt-text-settings-create-model-button-label = Opprett alternativ tekt automatisk
pdfjs-editor-alt-text-settings-create-model-description = Foreslår skildringar for å hjelpe folk som ikkje kan sjå bildet eller når bildet ikkje blir lasta inn.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = AI-modell for alternativ tekst ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Køyrer lokalt på eininga di slik at dataa dine blir verande private. Påkravd for automatisk alternativ tekst.
pdfjs-editor-alt-text-settings-delete-model-button = Slett
pdfjs-editor-alt-text-settings-download-model-button = Last ned
pdfjs-editor-alt-text-settings-downloading-model-button = Lastar ned…
pdfjs-editor-alt-text-settings-editor-title = Alternativ tekst-redigerar
pdfjs-editor-alt-text-settings-show-dialog-button-label = Vis alternativ tekst-redigerar direkte når du legg til eit bilde
pdfjs-editor-alt-text-settings-show-dialog-description = Hjelper deg med å sørgje for at alle bilda dine har alternativ tekst.
pdfjs-editor-alt-text-settings-close-button = Lat att

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Markering fjerna
pdfjs-editor-undo-bar-message-freetext = Tekst fjerna
pdfjs-editor-undo-bar-message-ink = Teikning fjerna
pdfjs-editor-undo-bar-message-stamp = Bilde fjerna
pdfjs-editor-undo-bar-message-signature = Signatur fjerna
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } kommentar fjerna
       *[other] { $count } kommentarar fjerna
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Angre
pdfjs-editor-undo-bar-undo-button-label = Angre
pdfjs-editor-undo-bar-close-button =
    .title = Lat att
pdfjs-editor-undo-bar-close-button-label = Lat att

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Denne modalen lèt brukaren lage ein signatur for å leggje til eit PDF-dokument. Brukaren kan redigere namnet (som også fungerer som alt-teksten), og eventuelt lagre signaturen for gjenteken bruk.
pdfjs-editor-add-signature-dialog-title = Legg til ein signatur

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Type
    .title = Type
pdfjs-editor-add-signature-image-button = Bilde
    .title = Bilde

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Skriv inn signaturen din
    .placeholder = Skriv inn signaturen din
pdfjs-editor-add-signature-draw-placeholder = Teikn signaturen din
pdfjs-editor-add-signature-draw-thickness-range-label = Tjukn
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Linjetjukn: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Drag ei fil hit for å laste opp
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Eller vel bildefiler
       *[other] Eller vel bildefiler
    }

## Controls

pdfjs-editor-add-signature-description-label = Skildring (alternativ tekst)
pdfjs-editor-add-signature-description-input =
    .title = Skildring (alternativ tekst)
pdfjs-editor-add-signature-description-default-when-drawing = Signatur
pdfjs-editor-add-signature-clear-button-label = Fjern signatur
pdfjs-editor-add-signature-clear-button =
    .title = Fjern signatur
pdfjs-editor-add-signature-save-checkbox = Lagre signatur
pdfjs-editor-add-signature-save-warning-message = Du har nådd grensa på 5 lagra signaturar. Fjern ein for å lagre ein ny.
pdfjs-editor-add-signature-image-upload-error-title = Klarte ikkje å oppdatere bilde
pdfjs-editor-add-signature-image-upload-error-description = Sjekk nettverkstilkoplinga eller prøv eit annet bilde.
pdfjs-editor-add-signature-error-close-button = Lat att

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Avbryt
pdfjs-editor-add-signature-add-button = Legg til
pdfjs-editor-edit-signature-update-button = Oppdater

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Fjern lagra signatur
pdfjs-editor-delete-signature-button-label1 = Fjern lagra signatur

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Rediger skildring

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Rediger skildring
