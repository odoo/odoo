# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Forrige side
pdfjs-previous-button-label = Forrige
pdfjs-next-button =
    .title = Næste side
pdfjs-next-button-label = Næste
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Side
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = af { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } af { $pagesCount })
pdfjs-zoom-out-button =
    .title = Zoom ud
pdfjs-zoom-out-button-label = Zoom ud
pdfjs-zoom-in-button =
    .title = Zoom ind
pdfjs-zoom-in-button-label = Zoom ind
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Skift til fuldskærmsvisning
pdfjs-presentation-mode-button-label = Fuldskærmsvisning
pdfjs-open-file-button =
    .title = Åbn fil
pdfjs-open-file-button-label = Åbn
pdfjs-print-button =
    .title = Udskriv
pdfjs-print-button-label = Udskriv
pdfjs-save-button =
    .title = Gem
pdfjs-save-button-label = Gem
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Hent
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Hent
pdfjs-bookmark-button =
    .title = Aktuel side (vis URL fra den aktuelle side)
pdfjs-bookmark-button-label = Aktuel side

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Funktioner
pdfjs-tools-button-label = Funktioner
pdfjs-first-page-button =
    .title = Gå til første side
pdfjs-first-page-button-label = Gå til første side
pdfjs-last-page-button =
    .title = Gå til sidste side
pdfjs-last-page-button-label = Gå til sidste side
pdfjs-page-rotate-cw-button =
    .title = Roter med uret
pdfjs-page-rotate-cw-button-label = Roter med uret
pdfjs-page-rotate-ccw-button =
    .title = Roter mod uret
pdfjs-page-rotate-ccw-button-label = Roter mod uret
pdfjs-cursor-text-select-tool-button =
    .title = Aktiver markeringsværktøj
pdfjs-cursor-text-select-tool-button-label = Markeringsværktøj
pdfjs-cursor-hand-tool-button =
    .title = Aktiver håndværktøj
pdfjs-cursor-hand-tool-button-label = Håndværktøj
pdfjs-scroll-page-button =
    .title = Brug sidescrolling
pdfjs-scroll-page-button-label = Sidescrolling
pdfjs-scroll-vertical-button =
    .title = Brug vertikal scrolling
pdfjs-scroll-vertical-button-label = Vertikal scrolling
pdfjs-scroll-horizontal-button =
    .title = Brug horisontal scrolling
pdfjs-scroll-horizontal-button-label = Horisontal scrolling
pdfjs-scroll-wrapped-button =
    .title = Brug ombrudt scrolling
pdfjs-scroll-wrapped-button-label = Ombrudt scrolling
pdfjs-spread-none-button =
    .title = Vis enkeltsider
pdfjs-spread-none-button-label = Enkeltsider
pdfjs-spread-odd-button =
    .title = Vis opslag med ulige sidenumre til venstre
pdfjs-spread-odd-button-label = Opslag med forside
pdfjs-spread-even-button =
    .title = Vis opslag med lige sidenumre til venstre
pdfjs-spread-even-button-label = Opslag uden forside

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumentegenskaber…
pdfjs-document-properties-button-label = Dokumentegenskaber…
pdfjs-document-properties-file-name = Filnavn:
pdfjs-document-properties-file-size = Filstørrelse:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bytes)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bytes)
pdfjs-document-properties-title = Titel:
pdfjs-document-properties-author = Forfatter:
pdfjs-document-properties-subject = Emne:
pdfjs-document-properties-keywords = Nøgleord:
pdfjs-document-properties-creation-date = Oprettet:
pdfjs-document-properties-modification-date = Redigeret:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Program:
pdfjs-document-properties-producer = PDF-producent:
pdfjs-document-properties-version = PDF-version:
pdfjs-document-properties-page-count = Antal sider:
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
pdfjs-document-properties-linearized = Hurtig web-visning:
pdfjs-document-properties-linearized-yes = Ja
pdfjs-document-properties-linearized-no = Nej
pdfjs-document-properties-close-button = Luk

## Print

pdfjs-print-progress-message = Forbereder dokument til udskrivning…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Annuller
pdfjs-printing-not-supported = Advarsel: Udskrivning er ikke fuldt understøttet af browseren.
pdfjs-printing-not-ready = Advarsel: PDF-filen er ikke fuldt indlæst til udskrivning.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Slå sidepanel til eller fra
pdfjs-toggle-sidebar-notification-button =
    .title = Slå sidepanel til eller fra (dokumentet indeholder disposition/vedhæftede filer/lag)
pdfjs-toggle-sidebar-button-label = Slå sidepanel til eller fra
pdfjs-document-outline-button =
    .title = Vis dokumentets disposition (dobbeltklik for at udvide/sammenfolde alle elementer)
pdfjs-document-outline-button-label = Dokument-disposition
pdfjs-attachments-button =
    .title = Vis vedhæftede filer
pdfjs-attachments-button-label = Vedhæftede filer
pdfjs-layers-button =
    .title = Vis lag (dobbeltklik for at nulstille alle lag til standard-tilstanden)
pdfjs-layers-button-label = Lag
pdfjs-thumbs-button =
    .title = Vis miniaturer
pdfjs-thumbs-button-label = Miniaturer
pdfjs-current-outline-item-button =
    .title = Find det aktuelle dispositions-element
pdfjs-current-outline-item-button-label = Aktuelt dispositions-element
pdfjs-findbar-button =
    .title = Find i dokument
pdfjs-findbar-button-label = Find
pdfjs-additional-layers = Yderligere lag

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Side { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniature af side { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Find
    .placeholder = Find i dokument…
pdfjs-find-previous-button =
    .title = Find den forrige forekomst
pdfjs-find-previous-button-label = Forrige
pdfjs-find-next-button =
    .title = Find den næste forekomst
pdfjs-find-next-button-label = Næste
pdfjs-find-highlight-checkbox = Fremhæv alle
pdfjs-find-match-case-checkbox-label = Forskel på store og små bogstaver
pdfjs-find-match-diacritics-checkbox-label = Diakritiske tegn
pdfjs-find-entire-word-checkbox-label = Hele ord
pdfjs-find-reached-top = Toppen af siden blev nået, fortsatte fra bunden
pdfjs-find-reached-bottom = Bunden af siden blev nået, fortsatte fra toppen
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } af { $total } forekomst
       *[other] { $current } af { $total } forekomster
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mere end { $limit } forekomst
       *[other] Mere end { $limit } forekomster
    }
pdfjs-find-not-found = Der blev ikke fundet noget

## Predefined zoom values

pdfjs-page-scale-width = Sidebredde
pdfjs-page-scale-fit = Tilpas til side
pdfjs-page-scale-auto = Automatisk zoom
pdfjs-page-scale-actual = Faktisk størrelse
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Side { $page }

## Loading indicator messages

pdfjs-loading-error = Der opstod en fejl ved indlæsning af PDF-filen.
pdfjs-invalid-file-error = PDF-filen er ugyldig eller ødelagt.
pdfjs-missing-file-error = Manglende PDF-fil.
pdfjs-unexpected-response-error = Uventet svar fra serveren.
pdfjs-rendering-error = Der opstod en fejl ved generering af siden.

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
    .alt = [{ $type }kommentar]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Angiv adgangskode til at åbne denne PDF-fil.
pdfjs-password-invalid = Ugyldig adgangskode. Prøv igen.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Fortryd
pdfjs-web-fonts-disabled = Webskrifttyper er deaktiverede. De indlejrede skrifttyper i PDF-filen kan ikke anvendes.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-color-picker-free-text-input =
    .title = Skift tekstfarve
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Tegn
pdfjs-editor-color-picker-ink-input =
    .title = Skift tegne-farve
pdfjs-editor-ink-button-label = Tegn
pdfjs-editor-stamp-button =
    .title = Tilføj eller rediger billeder
pdfjs-editor-stamp-button-label = Tilføj eller rediger billeder
pdfjs-editor-highlight-button =
    .title = Fremhæv
pdfjs-editor-highlight-button-label = Fremhæv
pdfjs-highlight-floating-button1 =
    .title = Fremhæv
    .aria-label = Fremhæv
pdfjs-highlight-floating-button-label = Fremhæv
pdfjs-comment-floating-button =
    .title = Kommentar
    .aria-label = Kommentar
pdfjs-comment-floating-button-label = Kommentar
pdfjs-editor-signature-button =
    .title = Tilføj signatur
pdfjs-editor-signature-button-label = Tilføj signatur

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Redigering af fremhævning
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Redigering af tegninger
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Redigering af signatur: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Redigering af billeder

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Fjern tegning
pdfjs-editor-remove-freetext-button =
    .title = Fjern tekst
pdfjs-editor-remove-stamp-button =
    .title = Fjern billede
pdfjs-editor-remove-highlight-button =
    .title = Fjern fremhævning
pdfjs-editor-remove-signature-button =
    .title = Fjern signatur

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Farve
pdfjs-editor-free-text-size-input = Størrelse
pdfjs-editor-ink-color-input = Farve
pdfjs-editor-ink-thickness-input = Tykkelse
pdfjs-editor-ink-opacity-input = Uigennemsigtighed
pdfjs-editor-stamp-add-image-button =
    .title = Tilføj billede
pdfjs-editor-stamp-add-image-button-label = Tilføj billede
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Tykkelse
pdfjs-editor-free-highlight-thickness-title =
    .title = Ændr tykkelse, når andre elementer end tekst fremhæves
pdfjs-editor-add-signature-container =
    .aria-label = Indstillinger for signaturer og gemte signaturer
pdfjs-editor-signature-add-signature-button =
    .title = Tilføj ny signatur
pdfjs-editor-signature-add-signature-button-label = Tilføj ny signatur
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Gemt signatur: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Teksteditor
    .default-content = Begynd at skrive…
pdfjs-free-text =
    .aria-label = Teksteditor
pdfjs-free-text-default-content = Begynd at skrive…
pdfjs-ink =
    .aria-label = Tegnings-editor
pdfjs-ink-canvas =
    .aria-label = Brugeroprettet billede

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternativ tekst
pdfjs-editor-alt-text-edit-button =
    .aria-label = Rediger alternativ tekst
pdfjs-editor-alt-text-edit-button-label = Rediger alternativ tekst
pdfjs-editor-alt-text-dialog-label = Vælg en indstilling
pdfjs-editor-alt-text-dialog-description = Alternativ tekst hjælper folk, som ikke kan se billedet eller når det ikke indlæses.
pdfjs-editor-alt-text-add-description-label = Tilføj en beskrivelse
pdfjs-editor-alt-text-add-description-description = Sigt efter en eller to sætninger, der beskriver emnet, omgivelserne eller handlinger.
pdfjs-editor-alt-text-mark-decorative-label = Marker som dekorativ
pdfjs-editor-alt-text-mark-decorative-description = Dette bruges for dekorative billeder som rammer eller vandmærker.
pdfjs-editor-alt-text-cancel-button = Annuller
pdfjs-editor-alt-text-save-button = Gem
pdfjs-editor-alt-text-decorative-tooltip = Markeret som dekorativ
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = For eksempel: "En ung mand sætter sig ved et bord for at spise et måltid mad"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativ tekst

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Øverste venstre hjørne — tilpas størrelse
pdfjs-editor-resizer-label-top-middle = Øverste i midten — tilpas størrelse
pdfjs-editor-resizer-label-top-right = Øverste højre hjørne — tilpas størrelse
pdfjs-editor-resizer-label-middle-right = Midten til højre — tilpas størrelse
pdfjs-editor-resizer-label-bottom-right = Nederste højre hjørne - tilpas størrelse
pdfjs-editor-resizer-label-bottom-middle = Nederst i midten - tilpas størrelse
pdfjs-editor-resizer-label-bottom-left = Nederste venstre hjørne - tilpas størrelse
pdfjs-editor-resizer-label-middle-left = Midten til venstre — tilpas størrelse
pdfjs-editor-resizer-top-left =
    .aria-label = Øverste venstre hjørne — tilpas størrelse
pdfjs-editor-resizer-top-middle =
    .aria-label = Øverste i midten — tilpas størrelse
pdfjs-editor-resizer-top-right =
    .aria-label = Øverste højre hjørne — tilpas størrelse
pdfjs-editor-resizer-middle-right =
    .aria-label = Midten til højre — tilpas størrelse
pdfjs-editor-resizer-bottom-right =
    .aria-label = Nederste højre hjørne - tilpas størrelse
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Nederst i midten - tilpas størrelse
pdfjs-editor-resizer-bottom-left =
    .aria-label = Nederste venstre hjørne - tilpas størrelse
pdfjs-editor-resizer-middle-left =
    .aria-label = Midten til venstre — tilpas størrelse

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Fremhævningsfarve
pdfjs-editor-colorpicker-button =
    .title = Skift farve
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Farvevalg
pdfjs-editor-colorpicker-yellow =
    .title = Gul
pdfjs-editor-colorpicker-green =
    .title = Grøn
pdfjs-editor-colorpicker-blue =
    .title = Blå
pdfjs-editor-colorpicker-pink =
    .title = Lyserød
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
pdfjs-editor-new-alt-text-dialog-edit-label = Rediger alternativ tekst (billedbeskrivelse)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Tilføj alternativ tekst (billedbeskrivelse)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Skriv din beskrivelse her...
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kort beskrivelse til personer, der ikke kan se billedet, eller når billedet ikke indlæses.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Denne alternative tekst blev oprettet automatisk og kan være upræcis.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Læs mere
pdfjs-editor-new-alt-text-create-automatically-button-label = Opret alternativ tekst automatisk
pdfjs-editor-new-alt-text-not-now-button = Ikke nu
pdfjs-editor-new-alt-text-error-title = Kunne ikke oprette alternativ tekst automatisk
pdfjs-editor-new-alt-text-error-description = Skriv din egen alternative tekst, eller prøv igen senere.
pdfjs-editor-new-alt-text-error-close-button = Luk
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Henter alternativ tekst AI-model ({ $downloadedSize } af { $totalSize } MB)
    .aria-valuetext = Henter alternativ tekst AI-model ({ $downloadedSize } af { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativ tekst tilføjet
pdfjs-editor-new-alt-text-added-button-label = Alternativ tekst tilføjet
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Mangler alternativ tekst
pdfjs-editor-new-alt-text-missing-button-label = Mangler alternativ tekst
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Gennemgå alternativ tekst
pdfjs-editor-new-alt-text-to-review-button-label = Gennemgå alternativ tekst
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Oprettet automatisk: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Indstillinger for alternativ tekst til billeder
pdfjs-image-alt-text-settings-button-label = Indstillinger for alternativ tekst til billeder
pdfjs-editor-alt-text-settings-dialog-label = Indstillinger for alternativ tekst til billeder
pdfjs-editor-alt-text-settings-automatic-title = Automatisk alternativ tekst
pdfjs-editor-alt-text-settings-create-model-button-label = Opret alternativ tekst automatisk
pdfjs-editor-alt-text-settings-create-model-description = Foreslår beskrivelser for at hjælpe folk, der ikke kan se billedet, eller når billedet ikke indlæses.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = AI-model til at oprette alternative tekster ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Kører lokalt på din enhed, så dine data forbliver private. Påkrævet for at anvende automatisk alternativ tekst.
pdfjs-editor-alt-text-settings-delete-model-button = Slet
pdfjs-editor-alt-text-settings-download-model-button = Hent
pdfjs-editor-alt-text-settings-downloading-model-button = Henter…
pdfjs-editor-alt-text-settings-editor-title = Redigering af alternativ tekst
pdfjs-editor-alt-text-settings-show-dialog-button-label = Vis redigering af alternativ tekst med det samme, når et billede tilføjes
pdfjs-editor-alt-text-settings-show-dialog-description = Hjælper dig med at sikre, at alle dine billeder har alternativ tekst.
pdfjs-editor-alt-text-settings-close-button = Luk

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Fremhævning tilføjet
pdfjs-editor-freetext-added-alert = Tekst tilføjet
pdfjs-editor-ink-added-alert = Tegning tilføjet
pdfjs-editor-stamp-added-alert = Billede tilføjet
pdfjs-editor-signature-added-alert = Signatur tilføjet

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Fremhævning fjernet
pdfjs-editor-undo-bar-message-freetext = Tekst fjernet
pdfjs-editor-undo-bar-message-ink = Tegning fjernet
pdfjs-editor-undo-bar-message-stamp = Billede fjernet
pdfjs-editor-undo-bar-message-signature = Signatur fjernet
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } kommentar fjernet
       *[other] { $count } kommentarer fjernet
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Fortryd
pdfjs-editor-undo-bar-undo-button-label = Fortryd
pdfjs-editor-undo-bar-close-button =
    .title = Luk
pdfjs-editor-undo-bar-close-button-label = Luk

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Modal-vinduet gør det muligt for brugeren at oprette en signatur, som kan føjes til PDF-dokumenter. Brugeren kan redigere navnet (der også fungerer som alternativ tekst) og eventuelt gemme signaturen, så den kan bruges igen.
pdfjs-editor-add-signature-dialog-title = Tilføj en signatur

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Indtast
    .title = Indtast
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Tegn
    .title = Tegn
pdfjs-editor-add-signature-image-button = Billede
    .title = Billede

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Indtast din signatur
    .placeholder = Indtast din signatur
pdfjs-editor-add-signature-draw-placeholder = Tegn din signatur
pdfjs-editor-add-signature-draw-thickness-range-label = Tykkelse
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Linjetykkelse: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Træk en fil herhen for at uploade den
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Eller vælg billedfiler
       *[other] Eller vælg billedfiler
    }

## Controls

pdfjs-editor-add-signature-description-label = Beskrivelse (alternativ tekst)
pdfjs-editor-add-signature-description-input =
    .title = Beskrivelse (alternativ tekst)
pdfjs-editor-add-signature-description-default-when-drawing = Underskrift
pdfjs-editor-add-signature-clear-button-label = Ryd signatur
pdfjs-editor-add-signature-clear-button =
    .title = Ryd signatur
pdfjs-editor-add-signature-save-checkbox = Gem signatur
pdfjs-editor-add-signature-save-warning-message = Du har nået grænsen på 5 gemte signaturer. Fjern en for at tilføje en ny.
pdfjs-editor-add-signature-image-upload-error-title = Kunne ikke uploade billede
pdfjs-editor-add-signature-image-upload-error-description = Kontroller din netværksforbindelse eller prøv med et andet billede.
pdfjs-editor-add-signature-image-no-data-error-title = Kan ikke konvertere dette billede til en signatur
pdfjs-editor-add-signature-image-no-data-error-description = Prøv at uploade et andet billede.
pdfjs-editor-add-signature-error-close-button = Luk

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Annuller
pdfjs-editor-add-signature-add-button = Tilføj
pdfjs-editor-edit-signature-update-button = Opdater

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Handlinger
pdfjs-editor-edit-comment-actions-button =
    .title = Handlinger
pdfjs-editor-edit-comment-close-button-label = Luk
pdfjs-editor-edit-comment-close-button =
    .title = Luk
pdfjs-editor-edit-comment-actions-edit-button-label = Rediger
pdfjs-editor-edit-comment-actions-delete-button-label = Slet
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Indtast din kommentar
pdfjs-editor-edit-comment-manager-cancel-button = Annuller
pdfjs-editor-edit-comment-manager-save-button = Gem

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Rediger kommentar

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Fjern gemt signatur
pdfjs-editor-delete-signature-button-label1 = Fjern gemt signatur

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Rediger beskrivelse

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Rediger beskrivelse
