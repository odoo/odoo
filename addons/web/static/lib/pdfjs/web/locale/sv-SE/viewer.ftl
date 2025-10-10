# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Föregående sida
pdfjs-previous-button-label = Föregående
pdfjs-next-button =
    .title = Nästa sida
pdfjs-next-button-label = Nästa
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Sida
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = av { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } av { $pagesCount })
pdfjs-zoom-out-button =
    .title = Zooma ut
pdfjs-zoom-out-button-label = Zooma ut
pdfjs-zoom-in-button =
    .title = Zooma in
pdfjs-zoom-in-button-label = Zooma in
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Byt till presentationsläge
pdfjs-presentation-mode-button-label = Presentationsläge
pdfjs-open-file-button =
    .title = Öppna fil
pdfjs-open-file-button-label = Öppna
pdfjs-print-button =
    .title = Skriv ut
pdfjs-print-button-label = Skriv ut
pdfjs-save-button =
    .title = Spara
pdfjs-save-button-label = Spara
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Hämta
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Hämta
pdfjs-bookmark-button =
    .title = Aktuell sida (Visa URL från aktuell sida)
pdfjs-bookmark-button-label = Aktuell sida

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Verktyg
pdfjs-tools-button-label = Verktyg
pdfjs-first-page-button =
    .title = Gå till första sidan
pdfjs-first-page-button-label = Gå till första sidan
pdfjs-last-page-button =
    .title = Gå till sista sidan
pdfjs-last-page-button-label = Gå till sista sidan
pdfjs-page-rotate-cw-button =
    .title = Rotera medurs
pdfjs-page-rotate-cw-button-label = Rotera medurs
pdfjs-page-rotate-ccw-button =
    .title = Rotera moturs
pdfjs-page-rotate-ccw-button-label = Rotera moturs
pdfjs-cursor-text-select-tool-button =
    .title = Aktivera textmarkeringsverktyg
pdfjs-cursor-text-select-tool-button-label = Textmarkeringsverktyg
pdfjs-cursor-hand-tool-button =
    .title = Aktivera handverktyg
pdfjs-cursor-hand-tool-button-label = Handverktyg
pdfjs-scroll-page-button =
    .title = Använd sidrullning
pdfjs-scroll-page-button-label = Sidrullning
pdfjs-scroll-vertical-button =
    .title = Använd vertikal rullning
pdfjs-scroll-vertical-button-label = Vertikal rullning
pdfjs-scroll-horizontal-button =
    .title = Använd horisontell rullning
pdfjs-scroll-horizontal-button-label = Horisontell rullning
pdfjs-scroll-wrapped-button =
    .title = Använd överlappande rullning
pdfjs-scroll-wrapped-button-label = Överlappande rullning
pdfjs-spread-none-button =
    .title = Visa enkelsidor
pdfjs-spread-none-button-label = Enkelsidor
pdfjs-spread-odd-button =
    .title = Visa uppslag med olika sidnummer till vänster
pdfjs-spread-odd-button-label = Uppslag med framsida
pdfjs-spread-even-button =
    .title = Visa uppslag med lika sidnummer till vänster
pdfjs-spread-even-button-label = Uppslag utan framsida

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumentegenskaper…
pdfjs-document-properties-button-label = Dokumentegenskaper…
pdfjs-document-properties-file-name = Filnamn:
pdfjs-document-properties-file-size = Filstorlek:
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
pdfjs-document-properties-kb = { $size_kb } kB ({ $size_b } byte)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } byte)
pdfjs-document-properties-title = Titel:
pdfjs-document-properties-author = Författare:
pdfjs-document-properties-subject = Ämne:
pdfjs-document-properties-keywords = Nyckelord:
pdfjs-document-properties-creation-date = Skapades:
pdfjs-document-properties-modification-date = Ändrades:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Skapare:
pdfjs-document-properties-producer = PDF-producent:
pdfjs-document-properties-version = PDF-version:
pdfjs-document-properties-page-count = Sidantal:
pdfjs-document-properties-page-size = Pappersstorlek:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = porträtt
pdfjs-document-properties-page-size-orientation-landscape = landskap
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
pdfjs-document-properties-linearized = Snabb webbvisning:
pdfjs-document-properties-linearized-yes = Ja
pdfjs-document-properties-linearized-no = Nej
pdfjs-document-properties-close-button = Stäng

## Print

pdfjs-print-progress-message = Förbereder sidor för utskrift…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Avbryt
pdfjs-printing-not-supported = Varning: Utskrifter stöds inte helt av den här webbläsaren.
pdfjs-printing-not-ready = Varning: PDF:en är inte klar för utskrift.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Visa/dölj sidofält
pdfjs-toggle-sidebar-notification-button =
    .title = Växla sidofält (dokumentet innehåller dokumentstruktur/bilagor/lager)
pdfjs-toggle-sidebar-button-label = Visa/dölj sidofält
pdfjs-document-outline-button =
    .title = Visa dokumentdisposition (dubbelklicka för att expandera/komprimera alla objekt)
pdfjs-document-outline-button-label = Dokumentöversikt
pdfjs-attachments-button =
    .title = Visa Bilagor
pdfjs-attachments-button-label = Bilagor
pdfjs-layers-button =
    .title = Visa lager (dubbelklicka för att återställa alla lager till standardläge)
pdfjs-layers-button-label = Lager
pdfjs-thumbs-button =
    .title = Visa miniatyrer
pdfjs-thumbs-button-label = Miniatyrer
pdfjs-current-outline-item-button =
    .title = Hitta aktuellt dispositionsobjekt
pdfjs-current-outline-item-button-label = Aktuellt dispositionsobjekt
pdfjs-findbar-button =
    .title = Sök i dokument
pdfjs-findbar-button-label = Sök
pdfjs-additional-layers = Ytterligare lager

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Sida { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatyr av sida { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Sök
    .placeholder = Sök i dokument…
pdfjs-find-previous-button =
    .title = Hitta föregående förekomst av frasen
pdfjs-find-previous-button-label = Föregående
pdfjs-find-next-button =
    .title = Hitta nästa förekomst av frasen
pdfjs-find-next-button-label = Nästa
pdfjs-find-highlight-checkbox = Markera alla
pdfjs-find-match-case-checkbox-label = Matcha versal/gemen
pdfjs-find-match-diacritics-checkbox-label = Matcha diakritiska tecken
pdfjs-find-entire-word-checkbox-label = Hela ord
pdfjs-find-reached-top = Nådde början av dokumentet, började från slutet
pdfjs-find-reached-bottom = Nådde slutet på dokumentet, började från början
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } av { $total } match
       *[other] { $current } av { $total } matchningar
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mer än { $limit } matchning
       *[other] Fler än { $limit } matchningar
    }
pdfjs-find-not-found = Frasen hittades inte

## Predefined zoom values

pdfjs-page-scale-width = Sidbredd
pdfjs-page-scale-fit = Anpassa sida
pdfjs-page-scale-auto = Automatisk zoom
pdfjs-page-scale-actual = Verklig storlek
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Sida { $page }

## Loading indicator messages

pdfjs-loading-error = Ett fel uppstod vid laddning av PDF-filen.
pdfjs-invalid-file-error = Ogiltig eller korrupt PDF-fil.
pdfjs-missing-file-error = Saknad PDF-fil.
pdfjs-unexpected-response-error = Oväntat svar från servern.
pdfjs-rendering-error = Ett fel uppstod vid visning av sidan.

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
    .alt = [{ $type }-annotering]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Skriv in lösenordet för att öppna PDF-filen.
pdfjs-password-invalid = Ogiltigt lösenord. Försök igen.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Avbryt
pdfjs-web-fonts-disabled = Webbtypsnitt är inaktiverade: kan inte använda inbäddade PDF-typsnitt.

## Editing

pdfjs-editor-free-text-button =
    .title = Text
pdfjs-editor-color-picker-free-text-input =
    .title = Ändra textfärg
pdfjs-editor-free-text-button-label = Text
pdfjs-editor-ink-button =
    .title = Rita
pdfjs-editor-color-picker-ink-input =
    .title = Ändra ritningsfärg
pdfjs-editor-ink-button-label = Rita
pdfjs-editor-stamp-button =
    .title = Lägg till eller redigera bilder
pdfjs-editor-stamp-button-label = Lägg till eller redigera bilder
pdfjs-editor-highlight-button =
    .title = Markera
pdfjs-editor-highlight-button-label = Markera
pdfjs-highlight-floating-button1 =
    .title = Markera
    .aria-label = Markera
pdfjs-highlight-floating-button-label = Markera
pdfjs-comment-floating-button =
    .title = Kommentar
    .aria-label = Kommentar
pdfjs-comment-floating-button-label = Kommentar
pdfjs-editor-signature-button =
    .title = Lägg till signatur
pdfjs-editor-signature-button-label = Lägg till signatur

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Markeringsredigerare
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Ritredigerare
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Signaturredigerare: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Bildredigerare

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Ta bort ritning
pdfjs-editor-remove-freetext-button =
    .title = Ta bort text
pdfjs-editor-remove-stamp-button =
    .title = Ta bort bild
pdfjs-editor-remove-highlight-button =
    .title = Ta bort markering
pdfjs-editor-remove-signature-button =
    .title = Ta bort signatur

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Färg
pdfjs-editor-free-text-size-input = Storlek
pdfjs-editor-ink-color-input = Färg
pdfjs-editor-ink-thickness-input = Tjocklek
pdfjs-editor-ink-opacity-input = Opacitet
pdfjs-editor-stamp-add-image-button =
    .title = Lägg till bild
pdfjs-editor-stamp-add-image-button-label = Lägg till bild
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Tjocklek
pdfjs-editor-free-highlight-thickness-title =
    .title = Ändra tjocklek när du markerar andra objekt än text
pdfjs-editor-add-signature-container =
    .aria-label = Signaturkontroller och sparade signaturer
pdfjs-editor-signature-add-signature-button =
    .title = Lägg till ny signatur
pdfjs-editor-signature-add-signature-button-label = Lägg till ny signatur
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Sparad signatur: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Textredigerare
    .default-content = Börja skriva…
pdfjs-free-text =
    .aria-label = Textredigerare
pdfjs-free-text-default-content = Börja skriva…
pdfjs-ink =
    .aria-label = Ritredigerare
pdfjs-ink-canvas =
    .aria-label = Användarskapad bild

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternativ text
pdfjs-editor-alt-text-edit-button =
    .aria-label = Redigera alternativ text
pdfjs-editor-alt-text-edit-button-label = Redigera alternativ text
pdfjs-editor-alt-text-dialog-label = Välj ett alternativ
pdfjs-editor-alt-text-dialog-description = Alt text (alternativ text) hjälper till när människor inte kan se bilden eller när den inte laddas.
pdfjs-editor-alt-text-add-description-label = Lägg till en beskrivning
pdfjs-editor-alt-text-add-description-description = Sikta på 1-2 meningar som beskriver ämnet, miljön eller handlingen.
pdfjs-editor-alt-text-mark-decorative-label = Markera som dekorativ
pdfjs-editor-alt-text-mark-decorative-description = Detta används för dekorativa bilder, som kanter eller vattenstämplar.
pdfjs-editor-alt-text-cancel-button = Avbryt
pdfjs-editor-alt-text-save-button = Spara
pdfjs-editor-alt-text-decorative-tooltip = Märkt som dekorativ
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Till exempel, "En ung man sätter sig vid ett bord för att äta en måltid"
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativ text

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Det övre vänstra hörnet — ändra storlek
pdfjs-editor-resizer-label-top-middle = Överst i mitten — ändra storlek
pdfjs-editor-resizer-label-top-right = Det övre högra hörnet — ändra storlek
pdfjs-editor-resizer-label-middle-right = Mitten höger — ändra storlek
pdfjs-editor-resizer-label-bottom-right = Nedre högra hörnet — ändra storlek
pdfjs-editor-resizer-label-bottom-middle = Nedre mitten — ändra storlek
pdfjs-editor-resizer-label-bottom-left = Nedre vänstra hörnet — ändra storlek
pdfjs-editor-resizer-label-middle-left = Mitten till vänster — ändra storlek
pdfjs-editor-resizer-top-left =
    .aria-label = Det övre vänstra hörnet — ändra storlek
pdfjs-editor-resizer-top-middle =
    .aria-label = Överst i mitten — ändra storlek
pdfjs-editor-resizer-top-right =
    .aria-label = Det övre högra hörnet — ändra storlek
pdfjs-editor-resizer-middle-right =
    .aria-label = Mitten höger — ändra storlek
pdfjs-editor-resizer-bottom-right =
    .aria-label = Nedre högra hörnet — ändra storlek
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Nedre mitten — ändra storlek
pdfjs-editor-resizer-bottom-left =
    .aria-label = Nedre vänstra hörnet — ändra storlek
pdfjs-editor-resizer-middle-left =
    .aria-label = Mitten till vänster — ändra storlek

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Markeringsfärg
pdfjs-editor-colorpicker-button =
    .title = Ändra färg
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Färgval
pdfjs-editor-colorpicker-yellow =
    .title = Gul
pdfjs-editor-colorpicker-green =
    .title = Grön
pdfjs-editor-colorpicker-blue =
    .title = Blå
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Röd

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Visa alla
pdfjs-editor-highlight-show-all-button =
    .title = Visa alla

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Redigera alternativ text (bildbeskrivning)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Lägg till alternativ text (bildbeskrivning)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Skriv din beskrivning här…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kort beskrivning för personer som inte kan se bilden eller när bilden inte laddas.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Denna alternativa text skapades automatiskt och kan vara felaktig.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Läs mer
pdfjs-editor-new-alt-text-create-automatically-button-label = Skapa alternativ text automatiskt
pdfjs-editor-new-alt-text-not-now-button = Inte nu
pdfjs-editor-new-alt-text-error-title = Det gick inte att skapa alternativ text automatiskt
pdfjs-editor-new-alt-text-error-description = Skriv din egna alternativa text eller försök igen senare.
pdfjs-editor-new-alt-text-error-close-button = Stäng
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Hämtar AI-modell med alternativ text ({ $downloadedSize } av { $totalSize } MB)
    .aria-valuetext = Hämtar AI-modell med alternativ text ({ $downloadedSize } av { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativ text tillagd
pdfjs-editor-new-alt-text-added-button-label = Alternativ text tillagd
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Saknar alternativ text
pdfjs-editor-new-alt-text-missing-button-label = Saknar alternativ text
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Granska alternativ text
pdfjs-editor-new-alt-text-to-review-button-label = Granska alternativ text
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Skapas automatiskt: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Alternativ textinställningar för bild
pdfjs-image-alt-text-settings-button-label = Alternativ textinställningar för bild
pdfjs-editor-alt-text-settings-dialog-label = Alternativ textinställningar för bild
pdfjs-editor-alt-text-settings-automatic-title = Automatisk alternativ text
pdfjs-editor-alt-text-settings-create-model-button-label = Skapa alternativ text automatiskt
pdfjs-editor-alt-text-settings-create-model-description = Föreslår beskrivningar för att hjälpa personer som inte kan se bilden eller när bilden inte laddas.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = AI-modell för alternativ text ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Körs lokalt på din enhet så att din data förblir privat. Krävs för automatisk alternativ text.
pdfjs-editor-alt-text-settings-delete-model-button = Ta bort
pdfjs-editor-alt-text-settings-download-model-button = Hämta
pdfjs-editor-alt-text-settings-downloading-model-button = Hämtar…
pdfjs-editor-alt-text-settings-editor-title = Alternativ textredigerare
pdfjs-editor-alt-text-settings-show-dialog-button-label = Visa alternativ textredigerare direkt när du lägger till en bild
pdfjs-editor-alt-text-settings-show-dialog-description = Hjälper dig att se till att alla dina bilder har alternativ text.
pdfjs-editor-alt-text-settings-close-button = Stäng

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Markering tillagd
pdfjs-editor-freetext-added-alert = Text tillagd
pdfjs-editor-ink-added-alert = Ritning tillagd
pdfjs-editor-stamp-added-alert = Bild tillagd
pdfjs-editor-signature-added-alert = Signatur tillagd

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Markering borttagen
pdfjs-editor-undo-bar-message-freetext = Text borttagen
pdfjs-editor-undo-bar-message-ink = Ritning borttagen
pdfjs-editor-undo-bar-message-stamp = Bild borttagen
pdfjs-editor-undo-bar-message-signature = Signatur borttagen
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } anteckning har tagits bort
       *[other] { $count } anteckningar har tagits bort
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Ångra
pdfjs-editor-undo-bar-undo-button-label = Ångra
pdfjs-editor-undo-bar-close-button =
    .title = Stäng
pdfjs-editor-undo-bar-close-button-label = Stäng

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Denna modal tillåter användaren att skapa en signatur för att lägga till i ett PDF-dokument. Användaren kan redigera namnet (som också fungerar som alternativ text) och eventuellt spara signaturen för upprepad användning.
pdfjs-editor-add-signature-dialog-title = Lägg till en signatur

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Typ
    .title = Typ
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Rita
    .title = Rita
pdfjs-editor-add-signature-image-button = Bild
    .title = Bild

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Skriv din signatur
    .placeholder = Skriv din signatur
pdfjs-editor-add-signature-draw-placeholder = Rita din signatur
pdfjs-editor-add-signature-draw-thickness-range-label = Tjocklek
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Ritningstjocklek: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Dra en fil hit för att ladda upp
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Eller välj bildfiler
       *[other] Eller bläddra bland bildfiler
    }

## Controls

pdfjs-editor-add-signature-description-label = Beskrivning (alternativ text)
pdfjs-editor-add-signature-description-input =
    .title = Beskrivning (alternativ text)
pdfjs-editor-add-signature-description-default-when-drawing = Signatur
pdfjs-editor-add-signature-clear-button-label = Rensa signatur
pdfjs-editor-add-signature-clear-button =
    .title = Rensa signatur
pdfjs-editor-add-signature-save-checkbox = Spara signatur
pdfjs-editor-add-signature-save-warning-message = Du har nått gränsen på 5 sparade signaturer. Ta bort en för att spara fler.
pdfjs-editor-add-signature-image-upload-error-title = Det gick inte att ladda upp bilden
pdfjs-editor-add-signature-image-upload-error-description = Kontrollera din nätverksanslutning eller försök med en annan bild.
pdfjs-editor-add-signature-image-no-data-error-title = Det går inte att konvertera den här bilden till en signatur
pdfjs-editor-add-signature-image-no-data-error-description = Prova att ladda upp en annan bild.
pdfjs-editor-add-signature-error-close-button = Stäng

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Avbryt
pdfjs-editor-add-signature-add-button = Lägg till
pdfjs-editor-edit-signature-update-button = Uppdatera

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Åtgärder
pdfjs-editor-edit-comment-actions-button =
    .title = Åtgärder
pdfjs-editor-edit-comment-close-button-label = Stäng
pdfjs-editor-edit-comment-close-button =
    .title = Stäng
pdfjs-editor-edit-comment-actions-edit-button-label = Redigera
pdfjs-editor-edit-comment-actions-delete-button-label = Ta bort
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Ange din kommentar
pdfjs-editor-edit-comment-manager-cancel-button = Avbryt
pdfjs-editor-edit-comment-manager-save-button = Spara

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Redigera kommentar

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Ta bort sparad signatur
pdfjs-editor-delete-signature-button-label1 = Ta bort sparad signatur

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Redigera beskrivning

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Redigera beskrivning
