# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Eine Seite zurück
pdfjs-previous-button-label = Zurück
pdfjs-next-button =
    .title = Eine Seite vor
pdfjs-next-button-label = Vor
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Seite
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = von { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } von { $pagesCount })
pdfjs-zoom-out-button =
    .title = Verkleinern
pdfjs-zoom-out-button-label = Verkleinern
pdfjs-zoom-in-button =
    .title = Vergrößern
pdfjs-zoom-in-button-label = Vergrößern
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = In Präsentationsmodus wechseln
pdfjs-presentation-mode-button-label = Präsentationsmodus
pdfjs-open-file-button =
    .title = Datei öffnen
pdfjs-open-file-button-label = Öffnen
pdfjs-print-button =
    .title = Drucken
pdfjs-print-button-label = Drucken
pdfjs-save-button =
    .title = Speichern
pdfjs-save-button-label = Speichern
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Herunterladen
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Herunterladen
pdfjs-bookmark-button =
    .title = Aktuelle Seite (URL von aktueller Seite anzeigen)
pdfjs-bookmark-button-label = Aktuelle Seite

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Werkzeuge
pdfjs-tools-button-label = Werkzeuge
pdfjs-first-page-button =
    .title = Erste Seite anzeigen
pdfjs-first-page-button-label = Erste Seite anzeigen
pdfjs-last-page-button =
    .title = Letzte Seite anzeigen
pdfjs-last-page-button-label = Letzte Seite anzeigen
pdfjs-page-rotate-cw-button =
    .title = Im Uhrzeigersinn drehen
pdfjs-page-rotate-cw-button-label = Im Uhrzeigersinn drehen
pdfjs-page-rotate-ccw-button =
    .title = Gegen Uhrzeigersinn drehen
pdfjs-page-rotate-ccw-button-label = Gegen Uhrzeigersinn drehen
pdfjs-cursor-text-select-tool-button =
    .title = Textauswahl-Werkzeug aktivieren
pdfjs-cursor-text-select-tool-button-label = Textauswahl-Werkzeug
pdfjs-cursor-hand-tool-button =
    .title = Hand-Werkzeug aktivieren
pdfjs-cursor-hand-tool-button-label = Hand-Werkzeug
pdfjs-scroll-page-button =
    .title = Seiten einzeln anordnen
pdfjs-scroll-page-button-label = Einzelseitenanordnung
pdfjs-scroll-vertical-button =
    .title = Seiten übereinander anordnen
pdfjs-scroll-vertical-button-label = Vertikale Seitenanordnung
pdfjs-scroll-horizontal-button =
    .title = Seiten nebeneinander anordnen
pdfjs-scroll-horizontal-button-label = Horizontale Seitenanordnung
pdfjs-scroll-wrapped-button =
    .title = Seiten neben- und übereinander anordnen, abhängig vom Platz
pdfjs-scroll-wrapped-button-label = Kombinierte Seitenanordnung
pdfjs-spread-none-button =
    .title = Seiten nicht nebeneinander anzeigen
pdfjs-spread-none-button-label = Einzelne Seiten
pdfjs-spread-odd-button =
    .title = Jeweils eine ungerade und eine gerade Seite nebeneinander anzeigen
pdfjs-spread-odd-button-label = Ungerade + gerade Seite
pdfjs-spread-even-button =
    .title = Jeweils eine gerade und eine ungerade Seite nebeneinander anzeigen
pdfjs-spread-even-button-label = Gerade + ungerade Seite

## Document properties dialog

pdfjs-document-properties-button =
    .title = Dokumenteigenschaften
pdfjs-document-properties-button-label = Dokumenteigenschaften…
pdfjs-document-properties-file-name = Dateiname:
pdfjs-document-properties-file-size = Dateigröße:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } Bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } Bytes)
pdfjs-document-properties-title = Titel:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Thema:
pdfjs-document-properties-keywords = Stichwörter:
pdfjs-document-properties-creation-date = Erstelldatum:
pdfjs-document-properties-modification-date = Bearbeitungsdatum:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Anwendung:
pdfjs-document-properties-producer = PDF erstellt mit:
pdfjs-document-properties-version = PDF-Version:
pdfjs-document-properties-page-count = Seitenzahl:
pdfjs-document-properties-page-size = Seitengröße:
pdfjs-document-properties-page-size-unit-inches = Zoll
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = Hochformat
pdfjs-document-properties-page-size-orientation-landscape = Querformat
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
pdfjs-document-properties-linearized = Schnelle Webanzeige:
pdfjs-document-properties-linearized-yes = Ja
pdfjs-document-properties-linearized-no = Nein
pdfjs-document-properties-close-button = Schließen

## Print

pdfjs-print-progress-message = Dokument wird für Drucken vorbereitet…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Abbrechen
pdfjs-printing-not-supported = Warnung: Die Drucken-Funktion wird durch diesen Browser nicht vollständig unterstützt.
pdfjs-printing-not-ready = Warnung: Die PDF-Datei ist nicht vollständig geladen, dies ist für das Drucken aber empfohlen.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Sidebar umschalten
pdfjs-toggle-sidebar-notification-button =
    .title = Sidebar umschalten (Dokument enthält Dokumentstruktur/Anhänge/Ebenen)
pdfjs-toggle-sidebar-button-label = Sidebar umschalten
pdfjs-document-outline-button =
    .title = Dokumentstruktur anzeigen (Doppelklicken, um alle Einträge aus- bzw. einzuklappen)
pdfjs-document-outline-button-label = Dokumentstruktur
pdfjs-attachments-button =
    .title = Anhänge anzeigen
pdfjs-attachments-button-label = Anhänge
pdfjs-layers-button =
    .title = Ebenen anzeigen (Doppelklicken, um alle Ebenen auf den Standardzustand zurückzusetzen)
pdfjs-layers-button-label = Ebenen
pdfjs-thumbs-button =
    .title = Miniaturansichten anzeigen
pdfjs-thumbs-button-label = Miniaturansichten
pdfjs-current-outline-item-button =
    .title = Aktuelles Struktur-Element finden
pdfjs-current-outline-item-button-label = Aktuelles Struktur-Element
pdfjs-findbar-button =
    .title = Dokument durchsuchen
pdfjs-findbar-button-label = Suchen
pdfjs-additional-layers = Zusätzliche Ebenen

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Seite { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniaturansicht von Seite { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Suchen
    .placeholder = Dokument durchsuchen…
pdfjs-find-previous-button =
    .title = Vorheriges Vorkommen des Suchbegriffs finden
pdfjs-find-previous-button-label = Zurück
pdfjs-find-next-button =
    .title = Nächstes Vorkommen des Suchbegriffs finden
pdfjs-find-next-button-label = Weiter
pdfjs-find-highlight-checkbox = Alle hervorheben
pdfjs-find-match-case-checkbox-label = Groß-/Kleinschreibung beachten
pdfjs-find-match-diacritics-checkbox-label = Akzente
pdfjs-find-entire-word-checkbox-label = Ganze Wörter
pdfjs-find-reached-top = Anfang des Dokuments erreicht, fahre am Ende fort
pdfjs-find-reached-bottom = Ende des Dokuments erreicht, fahre am Anfang fort
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } von { $total } Übereinstimmung
       *[other] { $current } von { $total } Übereinstimmungen
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mehr als { $limit } Übereinstimmung
       *[other] Mehr als { $limit } Übereinstimmungen
    }
pdfjs-find-not-found = Suchbegriff nicht gefunden

## Predefined zoom values

pdfjs-page-scale-width = Seitenbreite
pdfjs-page-scale-fit = Seitengröße
pdfjs-page-scale-auto = Automatischer Zoom
pdfjs-page-scale-actual = Originalgröße
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Seite { $page }

## Loading indicator messages

pdfjs-loading-error = Beim Laden der PDF-Datei trat ein Fehler auf.
pdfjs-invalid-file-error = Ungültige oder beschädigte PDF-Datei
pdfjs-missing-file-error = Fehlende PDF-Datei
pdfjs-unexpected-response-error = Unerwartete Antwort des Servers
pdfjs-rendering-error = Beim Darstellen der Seite trat ein Fehler auf.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Anlage: { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Geben Sie zum Öffnen der PDF-Datei deren Passwort ein.
pdfjs-password-invalid = Falsches Passwort. Bitte versuchen Sie es erneut.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Abbrechen
pdfjs-web-fonts-disabled = Web-Schriftarten sind deaktiviert: Eingebettete PDF-Schriftarten konnten nicht geladen werden.

## Editing

pdfjs-editor-free-text-button =
    .title = Text
pdfjs-editor-color-picker-free-text-input =
    .title = Textfarbe ändern
pdfjs-editor-free-text-button-label = Text
pdfjs-editor-ink-button =
    .title = Zeichnen
pdfjs-editor-color-picker-ink-input =
    .title = Zeichnungsfarbe ändern
pdfjs-editor-ink-button-label = Zeichnen
pdfjs-editor-stamp-button =
    .title = Grafiken hinzufügen oder bearbeiten
pdfjs-editor-stamp-button-label = Grafiken hinzufügen oder bearbeiten
pdfjs-editor-highlight-button =
    .title = Hervorheben
pdfjs-editor-highlight-button-label = Hervorheben
pdfjs-highlight-floating-button1 =
    .title = Hervorheben
    .aria-label = Hervorheben
pdfjs-highlight-floating-button-label = Hervorheben
pdfjs-comment-floating-button =
    .title = Kommentieren
    .aria-label = Kommentieren
pdfjs-comment-floating-button-label = Kommentieren
pdfjs-editor-comment-button =
    .title = Kommentar
    .aria-label = Kommentar
pdfjs-editor-comment-button-label = Kommentar
pdfjs-editor-signature-button =
    .title = Unterschrift hinzufügen
pdfjs-editor-signature-button-label = Unterschrift hinzufügen

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Hervorhebungs-Editor
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Zeichnungseditor
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Unterschrifts-Editor: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Grafik-Editor

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Zeichnung entfernen
pdfjs-editor-remove-freetext-button =
    .title = Text entfernen
pdfjs-editor-remove-stamp-button =
    .title = Grafik entfernen
pdfjs-editor-remove-highlight-button =
    .title = Hervorhebung entfernen
pdfjs-editor-remove-signature-button =
    .title = Unterschrift entfernen

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Farbe
pdfjs-editor-free-text-size-input = Größe
pdfjs-editor-ink-color-input = Farbe
pdfjs-editor-ink-thickness-input = Linienstärke
pdfjs-editor-ink-opacity-input = Deckkraft
pdfjs-editor-stamp-add-image-button =
    .title = Grafik hinzufügen
pdfjs-editor-stamp-add-image-button-label = Grafik hinzufügen
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Linienstärke
pdfjs-editor-free-highlight-thickness-title =
    .title = Linienstärke beim Hervorheben anderer Elemente als Text ändern
pdfjs-editor-add-signature-container =
    .aria-label = Signaturkontrollen und gespeicherte Signaturen
pdfjs-editor-signature-add-signature-button =
    .title = Neue Unterschrift hinzufügen
pdfjs-editor-signature-add-signature-button-label = Neue Unterschrift hinzufügen
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Gespeicherte Signatur: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Texteditor
    .default-content = Schreiben beginnen…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Kommentar
       *[other] Kommentare
    }
pdfjs-editor-comments-sidebar-close-button =
    .title = Sidebar schließen
    .aria-label = Sidebar schließen
pdfjs-editor-comments-sidebar-close-button-label = Sidebar schließen
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Haben Sie etwas Bemerkenswertes entdeckt? Heben Sie es hervor und hinterlassen Sie einen Kommentar.
pdfjs-editor-comments-sidebar-no-comments-link = Weitere Informationen

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alternativ-Text
pdfjs-editor-alt-text-edit-button =
    .aria-label = Alternativ-Text bearbeiten
pdfjs-editor-alt-text-dialog-label = Option wählen
pdfjs-editor-alt-text-dialog-description = Alt-Text (Alternativtext) hilft, wenn Personen die Grafik nicht sehen können oder wenn sie nicht geladen wird.
pdfjs-editor-alt-text-add-description-label = Beschreibung hinzufügen
pdfjs-editor-alt-text-add-description-description = Ziel sind 1-2 Sätze, die das Thema, das Szenario oder Aktionen beschreiben.
pdfjs-editor-alt-text-mark-decorative-label = Als dekorativ markieren
pdfjs-editor-alt-text-mark-decorative-description = Dies wird für Ziergrafiken wie Ränder oder Wasserzeichen verwendet.
pdfjs-editor-alt-text-cancel-button = Abbrechen
pdfjs-editor-alt-text-save-button = Speichern
pdfjs-editor-alt-text-decorative-tooltip = Als dekorativ markiert
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Zum Beispiel: "Ein junger Mann setzt sich an einen Tisch, um zu essen."
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativ-Text

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Linke obere Ecke - Größe ändern
pdfjs-editor-resizer-top-middle =
    .aria-label = Oben mittig - Größe ändern
pdfjs-editor-resizer-top-right =
    .aria-label = Rechts oben - Größe ändern
pdfjs-editor-resizer-middle-right =
    .aria-label = Mitte rechts - Größe ändern
pdfjs-editor-resizer-bottom-right =
    .aria-label = Rechte untere Ecke - Größe ändern
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Unten mittig - Größe ändern
pdfjs-editor-resizer-bottom-left =
    .aria-label = Linke untere Ecke - Größe ändern
pdfjs-editor-resizer-middle-left =
    .aria-label = Mitte links - Größe ändern

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Hervorhebungsfarbe
pdfjs-editor-colorpicker-button =
    .title = Farbe ändern
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Farbauswahl
pdfjs-editor-colorpicker-yellow =
    .title = Gelb
pdfjs-editor-colorpicker-green =
    .title = Grün
pdfjs-editor-colorpicker-blue =
    .title = Blau
pdfjs-editor-colorpicker-pink =
    .title = Pink
pdfjs-editor-colorpicker-red =
    .title = Rot

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Alle anzeigen
pdfjs-editor-highlight-show-all-button =
    .title = Alle anzeigen

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Alternativ-Text (Grafikbeschreibung) bearbeiten
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Alternativ-Text (Grafikbeschreibung) hinzufügen
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Schreiben Sie Ihre Beschreibung hier…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Kurze Beschreibung für Personen, die die Grafik nicht sehen können, oder wenn die Grafik nicht geladen wird.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Dieser Alternativ-Text wurde automatisch erstellt und könnte ungenau sein.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Weitere Informationen
pdfjs-editor-new-alt-text-create-automatically-button-label = Alternativ-Text automatisch erstellen
pdfjs-editor-new-alt-text-not-now-button = Nicht jetzt
pdfjs-editor-new-alt-text-error-title = Alternativ-Text konnte nicht automatisch erstellt werden
pdfjs-editor-new-alt-text-error-description = Bitte schreiben Sie Ihren eigenen Alternativ-Text oder versuchen Sie es später erneut.
pdfjs-editor-new-alt-text-error-close-button = Schließen
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Alternativ-Text-KI-Modell wird heruntergeladen ({ $downloadedSize } von { $totalSize } MB)
    .aria-valuetext = Alternativ-Text-KI-Modell wird heruntergeladen ({ $downloadedSize } von { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativ-Text hinzugefügt
pdfjs-editor-new-alt-text-added-button-label = Alternativ-Text hinzugefügt
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Fehlender Alternativ-Text
pdfjs-editor-new-alt-text-missing-button-label = Fehlender Alternativ-Text
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Alternativ-Text überprüfen
pdfjs-editor-new-alt-text-to-review-button-label = Alternativ-Text überprüfen
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Automatisch erstellt: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Alternativ-Text-Einstellungen für Grafiken
pdfjs-image-alt-text-settings-button-label = Alternativ-Text-Einstellungen für Grafiken
pdfjs-editor-alt-text-settings-dialog-label = Alternativ-Text-Einstellungen für Grafiken
pdfjs-editor-alt-text-settings-automatic-title = Automatischer Alternativ-Text
pdfjs-editor-alt-text-settings-create-model-button-label = Alternativ-Text automatisch erstellen
pdfjs-editor-alt-text-settings-create-model-description = Schlägt Beschreibungen vor, um Personen zu helfen, die die Grafik nicht sehen können, oder wenn die Grafik nicht geladen wird.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Alternativ-Text-KI-Modell ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Wird lokal auf Ihrem Gerät ausgeführt, sodass Ihre Daten privat bleiben. Erforderlich für automatischen Alternativ-Text.
pdfjs-editor-alt-text-settings-delete-model-button = Löschen
pdfjs-editor-alt-text-settings-download-model-button = Herunterladen
pdfjs-editor-alt-text-settings-downloading-model-button = Wird heruntergeladen…
pdfjs-editor-alt-text-settings-editor-title = Alternativ-Texteditor
pdfjs-editor-alt-text-settings-show-dialog-button-label = Alternativ-Texteditor beim Hinzufügen einer Grafik anzeigen
pdfjs-editor-alt-text-settings-show-dialog-description = Hilft Ihnen, sicherzustellen, dass alle Ihre Grafiken Alternativ-Text haben.
pdfjs-editor-alt-text-settings-close-button = Schließen

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Hervorhebung hinzugefügt
pdfjs-editor-freetext-added-alert = Text hinzugefügt
pdfjs-editor-ink-added-alert = Zeichnung hinzugefügt
pdfjs-editor-stamp-added-alert = Bild hinzugefügt
pdfjs-editor-signature-added-alert = Signatur hinzugefügt

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Hervorhebung entfernt
pdfjs-editor-undo-bar-message-freetext = Text entfernt
pdfjs-editor-undo-bar-message-ink = Zeichnung entfernt
pdfjs-editor-undo-bar-message-stamp = Grafik entfernt
pdfjs-editor-undo-bar-message-signature = Unterschrift entfernt
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } Anmerkung entfernt
       *[other] { $count } Anmerkungen entfernt
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Rückgängig
pdfjs-editor-undo-bar-undo-button-label = Rückgängig
pdfjs-editor-undo-bar-close-button =
    .title = Schließen
pdfjs-editor-undo-bar-close-button-label = Schließen

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Dieses Modal ermöglicht es dem Benutzer, eine Unterschrift zu erstellen, um sie zu einem PDF-Dokument hinzuzufügen. Der Benutzer kann den Namen bearbeiten (der auch als Alt-Text dient) und optional die Unterschrift zur wiederholten Verwendung speichern.
pdfjs-editor-add-signature-dialog-title = Unterschrift hinzufügen

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Eintippen
    .title = Eintippen
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Zeichnen
    .title = Zeichnen
pdfjs-editor-add-signature-image-button = Grafik
    .title = Grafik

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Tippen Sie Ihre Unterschrift ein
    .placeholder = Tippen Sie Ihre Unterschrift ein
pdfjs-editor-add-signature-draw-placeholder = Ihre Unterschrift zeichnen
pdfjs-editor-add-signature-draw-thickness-range-label = Linienstärke
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Zeichnungsstärke: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Datei zum Hochladen hierher ziehen
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Oder Grafikdateien wählen
       *[other] Oder Bilddateien durchsuchen
    }

## Controls

pdfjs-editor-add-signature-description-label = Beschreibung (alternativer Text)
pdfjs-editor-add-signature-description-input =
    .title = Beschreibung (alternativer Text)
pdfjs-editor-add-signature-description-default-when-drawing = Unterschrift
pdfjs-editor-add-signature-clear-button-label = Unterschrift löschen
pdfjs-editor-add-signature-clear-button =
    .title = Unterschrift löschen
pdfjs-editor-add-signature-save-checkbox = Unterschrift speichern
pdfjs-editor-add-signature-save-warning-message = Sie haben die Grenze von 5 gespeicherten Unterschriften erreicht. Entfernen Sie eine, um weitere zu speichern.
pdfjs-editor-add-signature-image-upload-error-title = Grafik konnte nicht hochgeladen werden
pdfjs-editor-add-signature-image-upload-error-description = Überprüfen Sie Ihre Netzwerkverbindung, oder versuchen Sie es mit einer anderen Grafik.
pdfjs-editor-add-signature-image-no-data-error-title = Kann Grafik nicht in eine Signatur umwandeln
pdfjs-editor-add-signature-image-no-data-error-description = Bitte versuchen Sie, eine andere Grafik hochzuladen.
pdfjs-editor-add-signature-error-close-button = Schließen

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Abbrechen
pdfjs-editor-add-signature-add-button = Hinzufügen
pdfjs-editor-edit-signature-update-button = Aktualisieren

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Kommentar bearbeiten
pdfjs-editor-edit-comment-popup-button =
    .title = Kommentar bearbeiten
pdfjs-editor-delete-comment-popup-button-label = Kommentar entfernen
pdfjs-editor-delete-comment-popup-button =
    .title = Kommentar entfernen
pdfjs-show-comment-button =
    .title = Kommentar anzeigen

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Aktionen
pdfjs-editor-edit-comment-actions-button =
    .title = Aktionen
pdfjs-editor-edit-comment-close-button-label = Schließen
pdfjs-editor-edit-comment-close-button =
    .title = Schließen
pdfjs-editor-edit-comment-actions-edit-button-label = Bearbeiten
pdfjs-editor-edit-comment-actions-delete-button-label = Löschen
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Kommentar eingeben
pdfjs-editor-edit-comment-manager-cancel-button = Abbrechen
pdfjs-editor-edit-comment-manager-save-button = Speichern
# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Kommentar bearbeiten
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Aktualisieren
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Kommentar hinzufügen
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Hinzufügen
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Schreiben beginnen…
pdfjs-editor-edit-comment-dialog-cancel-button = Abbrechen

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Kommentar bearbeiten
pdfjs-editor-add-comment-button =
    .title = Kommentar hinzufügen

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Gespeicherte Signatur entfernen
pdfjs-editor-delete-signature-button-label1 = Gespeicherte Signatur entfernen

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Beschreibung bearbeiten

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Beschreibung bearbeiten
