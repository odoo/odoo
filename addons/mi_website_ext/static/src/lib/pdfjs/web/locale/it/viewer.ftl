# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Pagina precedente
pdfjs-previous-button-label = Precedente
pdfjs-next-button =
    .title = Pagina successiva
pdfjs-next-button-label = Successiva
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Pagina
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = di { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } di { $pagesCount })
pdfjs-zoom-out-button =
    .title = Riduci zoom
pdfjs-zoom-out-button-label = Riduci zoom
pdfjs-zoom-in-button =
    .title = Aumenta zoom
pdfjs-zoom-in-button-label = Aumenta zoom
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Passa alla modalità presentazione
pdfjs-presentation-mode-button-label = Modalità presentazione
pdfjs-open-file-button =
    .title = Apri file
pdfjs-open-file-button-label = Apri
pdfjs-print-button =
    .title = Stampa
pdfjs-print-button-label = Stampa
pdfjs-save-button =
    .title = Salva
pdfjs-save-button-label = Salva
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Scarica
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Scarica
pdfjs-bookmark-button =
    .title = Pagina corrente (mostra URL della pagina corrente)
pdfjs-bookmark-button-label = Pagina corrente

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Strumenti
pdfjs-tools-button-label = Strumenti
pdfjs-first-page-button =
    .title = Vai alla prima pagina
pdfjs-first-page-button-label = Vai alla prima pagina
pdfjs-last-page-button =
    .title = Vai all’ultima pagina
pdfjs-last-page-button-label = Vai all’ultima pagina
pdfjs-page-rotate-cw-button =
    .title = Ruota in senso orario
pdfjs-page-rotate-cw-button-label = Ruota in senso orario
pdfjs-page-rotate-ccw-button =
    .title = Ruota in senso antiorario
pdfjs-page-rotate-ccw-button-label = Ruota in senso antiorario
pdfjs-cursor-text-select-tool-button =
    .title = Attiva strumento di selezione testo
pdfjs-cursor-text-select-tool-button-label = Strumento di selezione testo
pdfjs-cursor-hand-tool-button =
    .title = Attiva strumento mano
pdfjs-cursor-hand-tool-button-label = Strumento mano
pdfjs-scroll-page-button =
    .title = Utilizza scorrimento pagine
pdfjs-scroll-page-button-label = Scorrimento pagine
pdfjs-scroll-vertical-button =
    .title = Scorri le pagine in verticale
pdfjs-scroll-vertical-button-label = Scorrimento verticale
pdfjs-scroll-horizontal-button =
    .title = Scorri le pagine in orizzontale
pdfjs-scroll-horizontal-button-label = Scorrimento orizzontale
pdfjs-scroll-wrapped-button =
    .title = Scorri le pagine in verticale, disponendole da sinistra a destra e andando a capo automaticamente
pdfjs-scroll-wrapped-button-label = Scorrimento con a capo automatico
pdfjs-spread-none-button =
    .title = Non raggruppare pagine
pdfjs-spread-none-button-label = Nessun raggruppamento
pdfjs-spread-odd-button =
    .title = Crea gruppi di pagine che iniziano con numeri di pagina dispari
pdfjs-spread-odd-button-label = Raggruppamento dispari
pdfjs-spread-even-button =
    .title = Crea gruppi di pagine che iniziano con numeri di pagina pari
pdfjs-spread-even-button-label = Raggruppamento pari

## Document properties dialog

pdfjs-document-properties-button =
    .title = Proprietà del documento…
pdfjs-document-properties-button-label = Proprietà del documento…
pdfjs-document-properties-file-name = Nome file:
pdfjs-document-properties-file-size = Dimensione file:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } byte)
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
pdfjs-document-properties-title = Titolo:
pdfjs-document-properties-author = Autore:
pdfjs-document-properties-subject = Oggetto:
pdfjs-document-properties-keywords = Parole chiave:
pdfjs-document-properties-creation-date = Data creazione:
pdfjs-document-properties-modification-date = Data modifica:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Autore originale:
pdfjs-document-properties-producer = Produttore PDF:
pdfjs-document-properties-version = Versione PDF:
pdfjs-document-properties-page-count = Conteggio pagine:
pdfjs-document-properties-page-size = Dimensioni pagina:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = verticale
pdfjs-document-properties-page-size-orientation-landscape = orizzontale
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Lettera
pdfjs-document-properties-page-size-name-legal = Legale

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
pdfjs-document-properties-linearized = Visualizzazione web veloce:
pdfjs-document-properties-linearized-yes = Sì
pdfjs-document-properties-linearized-no = No
pdfjs-document-properties-close-button = Chiudi

## Print

pdfjs-print-progress-message = Preparazione documento per la stampa…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Annulla
pdfjs-printing-not-supported = Attenzione: la stampa non è completamente supportata da questo browser.
pdfjs-printing-not-ready = Attenzione: il PDF non è ancora stato caricato completamente per la stampa.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Attiva/disattiva barra laterale
pdfjs-toggle-sidebar-notification-button =
    .title = Attiva/disattiva barra laterale (il documento contiene struttura/allegati/livelli)
pdfjs-toggle-sidebar-button-label = Attiva/disattiva barra laterale
pdfjs-document-outline-button =
    .title = Visualizza la struttura del documento (doppio clic per visualizzare/comprimere tutti gli elementi)
pdfjs-document-outline-button-label = Struttura documento
pdfjs-attachments-button =
    .title = Visualizza allegati
pdfjs-attachments-button-label = Allegati
pdfjs-layers-button =
    .title = Visualizza livelli (doppio clic per ripristinare tutti i livelli allo stato predefinito)
pdfjs-layers-button-label = Livelli
pdfjs-thumbs-button =
    .title = Mostra le miniature
pdfjs-thumbs-button-label = Miniature
pdfjs-current-outline-item-button =
    .title = Trova elemento struttura corrente
pdfjs-current-outline-item-button-label = Elemento struttura corrente
pdfjs-findbar-button =
    .title = Trova nel documento
pdfjs-findbar-button-label = Trova
pdfjs-additional-layers = Livelli aggiuntivi

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Pagina { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura della pagina { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Trova
    .placeholder = Trova nel documento…
pdfjs-find-previous-button =
    .title = Trova l’occorrenza precedente del testo da cercare
pdfjs-find-previous-button-label = Precedente
pdfjs-find-next-button =
    .title = Trova l’occorrenza successiva del testo da cercare
pdfjs-find-next-button-label = Successivo
pdfjs-find-highlight-checkbox = Evidenzia
pdfjs-find-match-case-checkbox-label = Maiuscole/minuscole
pdfjs-find-match-diacritics-checkbox-label = Segni diacritici
pdfjs-find-entire-word-checkbox-label = Parole intere
pdfjs-find-reached-top = Raggiunto l’inizio della pagina, continua dalla fine
pdfjs-find-reached-bottom = Raggiunta la fine della pagina, continua dall’inizio
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } di { $total } corrispondenza
       *[other] { $current } di { $total } corrispondenze
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Più di una { $limit } corrispondenza
       *[other] Più di { $limit } corrispondenze
    }
pdfjs-find-not-found = Testo non trovato

## Predefined zoom values

pdfjs-page-scale-width = Larghezza pagina
pdfjs-page-scale-fit = Adatta a una pagina
pdfjs-page-scale-auto = Zoom automatico
pdfjs-page-scale-actual = Dimensioni effettive
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Pagina { $page }

## Loading indicator messages

pdfjs-loading-error = Si è verificato un errore durante il caricamento del PDF.
pdfjs-invalid-file-error = File PDF non valido o danneggiato.
pdfjs-missing-file-error = File PDF non disponibile.
pdfjs-unexpected-response-error = Risposta imprevista del server
pdfjs-rendering-error = Si è verificato un errore durante il rendering della pagina.

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
    .alt = [Annotazione: { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Inserire la password per aprire questo file PDF.
pdfjs-password-invalid = Password non corretta. Riprova.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Annulla
pdfjs-web-fonts-disabled = I web font risultano disattivati: impossibile utilizzare i caratteri incorporati nel PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Testo
pdfjs-editor-free-text-button-label = Testo
pdfjs-editor-ink-button =
    .title = Disegno
pdfjs-editor-ink-button-label = Disegno
pdfjs-editor-stamp-button =
    .title = Aggiungi o rimuovi immagine
pdfjs-editor-stamp-button-label = Aggiungi o rimuovi immagine
pdfjs-editor-highlight-button =
    .title = Evidenzia
pdfjs-editor-highlight-button-label = Evidenzia
pdfjs-highlight-floating-button1 =
    .title = Evidenzia
    .aria-label = Evidenzia
pdfjs-highlight-floating-button-label = Evidenzia
pdfjs-editor-signature-button =
    .title = Aggiungi firma
pdfjs-editor-signature-button-label = Aggiungi firma

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Modifica evidenziazioni
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Modifica disegni
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor firme: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Modifica immagini

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Rimuovi disegno
pdfjs-editor-remove-freetext-button =
    .title = Rimuovi testo
pdfjs-editor-remove-stamp-button =
    .title = Rimuovi immagine
pdfjs-editor-remove-highlight-button =
    .title = Rimuovi evidenziazione
pdfjs-editor-remove-signature-button =
    .title = Rimuovi firma

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Colore
pdfjs-editor-free-text-size-input = Dimensione
pdfjs-editor-ink-color-input = Colore
pdfjs-editor-ink-thickness-input = Spessore
pdfjs-editor-ink-opacity-input = Opacità
pdfjs-editor-stamp-add-image-button =
    .title = Aggiungi immagine
pdfjs-editor-stamp-add-image-button-label = Aggiungi immagine
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Spessore
pdfjs-editor-free-highlight-thickness-title =
    .title = Modifica lo spessore della selezione per elementi non testuali
pdfjs-editor-add-signature-container =
    .aria-label = Controlli firma e firme salvate
pdfjs-editor-signature-add-signature-button =
    .title = Aggiungi nuova firma
pdfjs-editor-signature-add-signature-button-label = Aggiungi nuova firma
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Firma salvata: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor di testo
    .default-content = Inizia a digitare…
pdfjs-free-text =
    .aria-label = Editor di testo
pdfjs-free-text-default-content = Inizia a digitare…
pdfjs-ink =
    .aria-label = Editor disegni
pdfjs-ink-canvas =
    .aria-label = Immagine creata dall’utente

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Testo alternativo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Modifica testo alternativo
pdfjs-editor-alt-text-edit-button-label = Modifica testo alternativo
pdfjs-editor-alt-text-dialog-label = Scegli un’opzione
pdfjs-editor-alt-text-dialog-description = Il testo alternativo (“alt text”) aiuta quando le persone non possono vedere l’immagine o quando l’immagine non viene caricata.
pdfjs-editor-alt-text-add-description-label = Aggiungi una descrizione
pdfjs-editor-alt-text-add-description-description = Punta a una o due frasi che descrivono l’argomento, l’ambientazione o le azioni.
pdfjs-editor-alt-text-mark-decorative-label = Contrassegna come decorativa
pdfjs-editor-alt-text-mark-decorative-description = Viene utilizzato per immagini ornamentali, come bordi o filigrane.
pdfjs-editor-alt-text-cancel-button = Annulla
pdfjs-editor-alt-text-save-button = Salva
pdfjs-editor-alt-text-decorative-tooltip = Contrassegnata come decorativa
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Ad esempio, “Un giovane si siede a tavola per mangiare”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Testo alternativo

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Angolo in alto a sinistra — ridimensiona
pdfjs-editor-resizer-label-top-middle = Lato superiore nel mezzo — ridimensiona
pdfjs-editor-resizer-label-top-right = Angolo in alto a destra — ridimensiona
pdfjs-editor-resizer-label-middle-right = Lato destro nel mezzo — ridimensiona
pdfjs-editor-resizer-label-bottom-right = Angolo in basso a destra — ridimensiona
pdfjs-editor-resizer-label-bottom-middle = Lato inferiore nel mezzo — ridimensiona
pdfjs-editor-resizer-label-bottom-left = Angolo in basso a sinistra — ridimensiona
pdfjs-editor-resizer-label-middle-left = Lato sinistro nel mezzo — ridimensiona
pdfjs-editor-resizer-top-left =
    .aria-label = Angolo in alto a sinistra — ridimensiona
pdfjs-editor-resizer-top-middle =
    .aria-label = Lato superiore nel mezzo — ridimensiona
pdfjs-editor-resizer-top-right =
    .aria-label = Angolo in alto a destra — ridimensiona
pdfjs-editor-resizer-middle-right =
    .aria-label = Lato destro nel mezzo — ridimensiona
pdfjs-editor-resizer-bottom-right =
    .aria-label = Angolo in basso a destra — ridimensiona
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Lato inferiore nel mezzo — ridimensiona
pdfjs-editor-resizer-bottom-left =
    .aria-label = Angolo in basso a sinistra — ridimensiona
pdfjs-editor-resizer-middle-left =
    .aria-label = Lato sinistro nel mezzo — ridimensiona

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Colore evidenziatore
pdfjs-editor-colorpicker-button =
    .title = Cambia colore
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Colori disponibili
pdfjs-editor-colorpicker-yellow =
    .title = Giallo
pdfjs-editor-colorpicker-green =
    .title = Verde
pdfjs-editor-colorpicker-blue =
    .title = Blu
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Rosso

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Mostra tutto
pdfjs-editor-highlight-show-all-button =
    .title = Mostra tutto

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Modifica testo alternativo (descrizione dell’immagine)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Aggiungi testo alternativo (descrizione dell’immagine)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Scrivi qui la tua descrizione…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Breve descrizione per le persone che non possono vedere l’immagine, o mostrata quando l’immagine non si carica.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Questo testo alternativo è stato creato automaticamente e potrebbe non essere accurato.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Ulteriori informazioni
pdfjs-editor-new-alt-text-create-automatically-button-label = Crea automaticamente testo alternativo
pdfjs-editor-new-alt-text-not-now-button = Non adesso
pdfjs-editor-new-alt-text-error-title = Impossibile creare automaticamente il testo alternativo
pdfjs-editor-new-alt-text-error-description = Scrivi il testo alternativo o riprova più tardi.
pdfjs-editor-new-alt-text-error-close-button = Chiudi
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Download in corso del modello IA per il testo alternativo ({ $downloadedSize } di { $totalSize } MB)
    .aria-valuetext = Download in corso del modello IA per il testo alternativo ({ $downloadedSize } di { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Aggiunto testo alternativo
pdfjs-editor-new-alt-text-added-button-label = Aggiunto testo alternativo
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Testo alternativo mancante
pdfjs-editor-new-alt-text-missing-button-label = Testo alternativo mancante
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Verifica testo alternativo
pdfjs-editor-new-alt-text-to-review-button-label = Verifica testo alternativo
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Creato automaticamente: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Impostazioni testo alternativo per le immagini
pdfjs-image-alt-text-settings-button-label = Impostazioni testo alternativo per le immagini
pdfjs-editor-alt-text-settings-dialog-label = Impostazioni testo alternativo per le immagini
pdfjs-editor-alt-text-settings-automatic-title = Testo alternativo automatico
pdfjs-editor-alt-text-settings-create-model-button-label = Crea testo alternativo automaticamente
pdfjs-editor-alt-text-settings-create-model-description = Suggerisce una descrizione per le persone che non possono vedere l’immagine, o mostrata quando l’immagine non si carica.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Modello IA per il testo alternativo ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Viene eseguito localmente sul tuo dispositivo in modo che i tuoi dati rimangano riservati. È richiesto per la generazione automatica del testo alternativo.
pdfjs-editor-alt-text-settings-delete-model-button = Elimina
pdfjs-editor-alt-text-settings-download-model-button = Scarica
pdfjs-editor-alt-text-settings-downloading-model-button = Download…
pdfjs-editor-alt-text-settings-editor-title = Modifica testo alternativo
pdfjs-editor-alt-text-settings-show-dialog-button-label = Mostra l’editor del testo alternativo non appena si aggiunge un’immagine
pdfjs-editor-alt-text-settings-show-dialog-description = Ti aiuta ad assicurarti che tutte le tue immagini abbiano il testo alternativo.
pdfjs-editor-alt-text-settings-close-button = Chiudi

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Evidenziazione rimossa
pdfjs-editor-undo-bar-message-freetext = Testo rimosso
pdfjs-editor-undo-bar-message-ink = Disegno rimosso
pdfjs-editor-undo-bar-message-stamp = Immagine rimossa
pdfjs-editor-undo-bar-message-signature = Firma rimossa
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } annotazione rimossa
       *[other] { $count } annotazioni rimosse
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Annulla
pdfjs-editor-undo-bar-undo-button-label = Annulla
pdfjs-editor-undo-bar-close-button =
    .title = Chiudi
pdfjs-editor-undo-bar-close-button-label = Chiudi

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Questa finestra consente all’utente di creare una firma da aggiungere a un documento PDF. L’utente può modificare il nome (che verrà utilizzato anche come testo alternativo) e, se lo desidera, salvare la firma per riutilizzarla in futuro.
pdfjs-editor-add-signature-dialog-title = Aggiungi una firma

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Scrivi
    .title = Scrivi
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Disegna
    .title = Disegna
pdfjs-editor-add-signature-image-button = Immagine
    .title = Immagine

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Digita la tua firma
    .placeholder = Digita la tua firma
pdfjs-editor-add-signature-draw-placeholder = Disegna la tua firma
pdfjs-editor-add-signature-draw-thickness-range-label = Spessore
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Spessore del tratto: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Trascina un file qui per caricarlo
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Oppure scegli un file immagine
       *[other] Oppure sfoglia i file immagine
    }

## Controls

pdfjs-editor-add-signature-description-label = Descrizione (testo alternativo)
pdfjs-editor-add-signature-description-input =
    .title = Descrizione (testo alternativo)
pdfjs-editor-add-signature-description-default-when-drawing = Firma
pdfjs-editor-add-signature-clear-button-label = Cancella firma
pdfjs-editor-add-signature-clear-button =
    .title = Cancella firma
pdfjs-editor-add-signature-save-checkbox = Salva firma
pdfjs-editor-add-signature-save-warning-message = Hai raggiunto il limite di 5 firme salvate. Rimuovine una per salvarne altre.
pdfjs-editor-add-signature-image-upload-error-title = Impossibile caricare l’immagine
pdfjs-editor-add-signature-image-upload-error-description = Controlla la connessione di rete o prova con un’altra immagine.
pdfjs-editor-add-signature-error-close-button = Chiudi

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Annulla
pdfjs-editor-add-signature-add-button = Aggiungi
pdfjs-editor-edit-signature-update-button = Aggiorna

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Rimuovi firma salvata
pdfjs-editor-delete-signature-button-label1 = Rimuovi firma salvata

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Modifica descrizione

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Modifica descrizione
