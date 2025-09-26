# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Pagina precedentă
pdfjs-previous-button-label = Înapoi
pdfjs-next-button =
    .title = Pagina următoare
pdfjs-next-button-label = Înainte
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Pagina
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = din { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } din { $pagesCount })
pdfjs-zoom-out-button =
    .title = Micșorează
pdfjs-zoom-out-button-label = Micșorează
pdfjs-zoom-in-button =
    .title = Mărește
pdfjs-zoom-in-button-label = Mărește
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Comută la modul de prezentare
pdfjs-presentation-mode-button-label = Mod de prezentare
pdfjs-open-file-button =
    .title = Deschide un fișier
pdfjs-open-file-button-label = Deschide
pdfjs-print-button =
    .title = Tipărește
pdfjs-print-button-label = Tipărește
pdfjs-save-button =
    .title = Salvează
pdfjs-save-button-label = Salvează
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Descarcă
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Descarcă
pdfjs-bookmark-button =
    .title = Pagina curentă (Vezi URL din pagina curentă)
pdfjs-bookmark-button-label = Pagină curentă

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Instrumente
pdfjs-tools-button-label = Instrumente
pdfjs-first-page-button =
    .title = Mergi la prima pagină
pdfjs-first-page-button-label = Mergi la prima pagină
pdfjs-last-page-button =
    .title = Mergi la ultima pagină
pdfjs-last-page-button-label = Mergi la ultima pagină
pdfjs-page-rotate-cw-button =
    .title = Rotește în sensul acelor de ceas
pdfjs-page-rotate-cw-button-label = Rotește în sensul acelor de ceas
pdfjs-page-rotate-ccw-button =
    .title = Rotește în sens invers al acelor de ceas
pdfjs-page-rotate-ccw-button-label = Rotește în sens invers al acelor de ceas
pdfjs-cursor-text-select-tool-button =
    .title = Activează instrumentul de selecție a textului
pdfjs-cursor-text-select-tool-button-label = Instrumentul de selecție a textului
pdfjs-cursor-hand-tool-button =
    .title = Activează instrumentul mână
pdfjs-cursor-hand-tool-button-label = Unealta mână
pdfjs-scroll-page-button =
    .title = Folosește derularea paginilor
pdfjs-scroll-page-button-label = Derulare pagini
pdfjs-scroll-vertical-button =
    .title = Folosește derularea verticală
pdfjs-scroll-vertical-button-label = Derulare verticală
pdfjs-scroll-horizontal-button =
    .title = Folosește derularea orizontală
pdfjs-scroll-horizontal-button-label = Derulare orizontală
pdfjs-scroll-wrapped-button =
    .title = Folosește derularea încadrată
pdfjs-scroll-wrapped-button-label = Derulare încadrată
pdfjs-spread-none-button =
    .title = Nu uni paginile broșate
pdfjs-spread-none-button-label = Fără pagini broșate
pdfjs-spread-odd-button =
    .title = Unește paginile broșate începând cu cele impare
pdfjs-spread-odd-button-label = Broșare pagini impare
pdfjs-spread-even-button =
    .title = Unește paginile broșate începând cu cele pare
pdfjs-spread-even-button-label = Broșare pagini pare

## Document properties dialog

pdfjs-document-properties-button =
    .title = Proprietățile documentului…
pdfjs-document-properties-button-label = Proprietățile documentului…
pdfjs-document-properties-file-name = Numele fișierului:
pdfjs-document-properties-file-size = Mărimea fișierului:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } octeți)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } octeți)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } byți)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } byți)
pdfjs-document-properties-title = Titlu:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Subiect:
pdfjs-document-properties-keywords = Cuvinte cheie:
pdfjs-document-properties-creation-date = Data creării:
pdfjs-document-properties-modification-date = Data modificării:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Autor:
pdfjs-document-properties-producer = Producător PDF:
pdfjs-document-properties-version = Versiune PDF:
pdfjs-document-properties-page-count = Număr de pagini:
pdfjs-document-properties-page-size = Mărimea paginii:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = verticală
pdfjs-document-properties-page-size-orientation-landscape = orizontală
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Literă
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
pdfjs-document-properties-linearized = Vizualizare web rapidă:
pdfjs-document-properties-linearized-yes = Da
pdfjs-document-properties-linearized-no = Nu
pdfjs-document-properties-close-button = Închide

## Print

pdfjs-print-progress-message = Se pregătește documentul pentru tipărire…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Anulează
pdfjs-printing-not-supported = Avertisment: Tipărirea nu este suportată în totalitate de acest browser.
pdfjs-printing-not-ready = Avertisment: PDF-ul nu este încărcat complet pentru tipărire.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Comută bara laterală
pdfjs-toggle-sidebar-notification-button =
    .title = Comută bara laterală (documentul conține schițe/atașamente/straturi)
pdfjs-toggle-sidebar-button-label = Comută bara laterală
pdfjs-document-outline-button =
    .title = Afișează schița documentului (dublu-clic pentru a extinde/restrânge toate elementele)
pdfjs-document-outline-button-label = Schiță a documentului
pdfjs-attachments-button =
    .title = Afișează atașamentele
pdfjs-attachments-button-label = Atașamente
pdfjs-layers-button =
    .title = Afișează straturile (dă dublu clic pentru resetarea tuturor straturilor la starea implicită)
pdfjs-layers-button-label = Straturi
pdfjs-thumbs-button =
    .title = Afișează miniaturi
pdfjs-thumbs-button-label = Miniaturi
pdfjs-current-outline-item-button =
    .title = Găsește elementul pe schița actuală
pdfjs-current-outline-item-button-label = Element al schiței actuale
pdfjs-findbar-button =
    .title = Caută în document
pdfjs-findbar-button-label = Caută
pdfjs-additional-layers = Straturi suplimentare

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Pagina { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura paginii { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Caută
    .placeholder = Caută în document…
pdfjs-find-previous-button =
    .title = Mergi la apariția anterioară a textului
pdfjs-find-previous-button-label = Înapoi
pdfjs-find-next-button =
    .title = Mergi la apariția următoare a textului
pdfjs-find-next-button-label = Înainte
pdfjs-find-highlight-checkbox = Evidențiază toate aparițiile
pdfjs-find-match-case-checkbox-label = Ține cont de majuscule și minuscule
pdfjs-find-match-diacritics-checkbox-label = Respectă diacriticele
pdfjs-find-entire-word-checkbox-label = Cuvinte întregi
pdfjs-find-reached-top = Am ajuns la începutul documentului, continuă de la sfârșit
pdfjs-find-reached-bottom = Am ajuns la sfârșitul documentului, continuă de la început
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } din { $total } rezultat
        [few] { $current } din { $total } rezultate
       *[other] { $current } din { $total } de rezultate
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mai mult de { $limit } rezultat
        [few] Mai mult de { $limit } rezultate
       *[other] Mai mult de { $limit } de rezultate
    }
pdfjs-find-not-found = Nu s-a găsit textul

## Predefined zoom values

pdfjs-page-scale-width = Lățime pagină
pdfjs-page-scale-fit = Potrivire la pagină
pdfjs-page-scale-auto = Zoom automat
pdfjs-page-scale-actual = Mărime reală
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Pagina { $page }

## Loading indicator messages

pdfjs-loading-error = A intervenit o eroare la încărcarea PDF-ului.
pdfjs-invalid-file-error = Fișier PDF nevalid sau corupt.
pdfjs-missing-file-error = Fișier PDF lipsă.
pdfjs-unexpected-response-error = Răspuns neașteptat de la server.
pdfjs-rendering-error = A intervenit o eroare la randarea paginii.

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
    .alt = [Adnotare { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Introdu parola pentru a deschide acest fișier PDF.
pdfjs-password-invalid = Parolă nevalidă. Te rugăm să încerci din nou.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Anulează
pdfjs-web-fonts-disabled = Fonturile web sunt dezactivate: nu se pot folosi fonturile PDF încorporate.

## Editing

pdfjs-editor-free-text-button =
    .title = Text
pdfjs-editor-color-picker-free-text-input =
    .title = Schimbă culoarea textului
pdfjs-editor-free-text-button-label = Text
pdfjs-editor-ink-button =
    .title = Desenează
pdfjs-editor-color-picker-ink-input =
    .title = Schimbă culoarea de desen
pdfjs-editor-ink-button-label = Desenează
pdfjs-editor-stamp-button =
    .title = Adaugă sau editează imagini
pdfjs-editor-stamp-button-label = Adaugă sau editează imagini
pdfjs-editor-highlight-button =
    .title = Evidențiere
pdfjs-editor-highlight-button-label = Evidențiere
pdfjs-highlight-floating-button1 =
    .title = Evidențiază
    .aria-label = Evidențiere
pdfjs-highlight-floating-button-label = Evidențiază
pdfjs-comment-floating-button =
    .title = Comentează
    .aria-label = Comentariu
pdfjs-comment-floating-button-label = Comentează
pdfjs-editor-signature-button =
    .title = Adaugă semnătură
pdfjs-editor-signature-button-label = Adaugă semnătură

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor de evidențiere
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editor de desen
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor de semnătură: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editor de imagini

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Elimină desenul
pdfjs-editor-remove-freetext-button =
    .title = Elimină textul
pdfjs-editor-remove-stamp-button =
    .title = Elimină imaginea
pdfjs-editor-remove-highlight-button =
    .title = Elimină evidențierea
pdfjs-editor-remove-signature-button =
    .title = Elimină semnătura

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Culoare
pdfjs-editor-free-text-size-input = Mărime
pdfjs-editor-ink-color-input = Culoare
pdfjs-editor-ink-thickness-input = Grosime
pdfjs-editor-ink-opacity-input = Opacitate
pdfjs-editor-stamp-add-image-button =
    .title = Adaugă imagine
pdfjs-editor-stamp-add-image-button-label = Adaugă imagine
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Grosime
pdfjs-editor-free-highlight-thickness-title =
    .title = Schimbă grosimea când evidențiezi alte elemente decât text
pdfjs-editor-add-signature-container =
    .aria-label = Controale de semnături și semnături salvate
pdfjs-editor-signature-add-signature-button =
    .title = Adaugă o semnătură nouă
pdfjs-editor-signature-add-signature-button-label = Adaugă o semnătură nouă
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Semnătură salvată: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor de text
    .default-content = Începe să tastezi...
pdfjs-free-text =
    .aria-label = Editor de text
pdfjs-free-text-default-content = Începe să tastezi…
pdfjs-ink =
    .aria-label = Editor de desene
pdfjs-ink-canvas =
    .aria-label = Imagine creată de utilizator

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Text alternativ
pdfjs-editor-alt-text-edit-button =
    .aria-label = Editează textul alternativ
pdfjs-editor-alt-text-edit-button-label = Editează textul alternativ
pdfjs-editor-alt-text-dialog-label = Alege o opțiune
pdfjs-editor-alt-text-dialog-description = Textul alternativ (alt text) ajută când oamenii nu pot vedea imaginea sau când nu se încarcă.
pdfjs-editor-alt-text-add-description-label = Adaugă o descriere
pdfjs-editor-alt-text-add-description-description = Încearcă să scrii 1-2 propoziții care să descrie subiectul, cadrul sau acțiunile.
pdfjs-editor-alt-text-mark-decorative-label = Marchează ca decorativ
pdfjs-editor-alt-text-mark-decorative-description = Este pentru imagini ornamentale, cum ar fi chenare sau filigrane.
pdfjs-editor-alt-text-cancel-button = Anulează
pdfjs-editor-alt-text-save-button = Salvează
pdfjs-editor-alt-text-decorative-tooltip = Marcat ca decorativ
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = De exemplu, „Un tânăr se așează la o masă să mănânce”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Text alternativ

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Colțul din stânga sus — redimensionează
pdfjs-editor-resizer-label-top-middle = Mijloc de sus — redimensionează
pdfjs-editor-resizer-label-top-right = Colțul din dreapta sus — redimensionează
pdfjs-editor-resizer-label-middle-right = Mijloc dreapta — redimensionează
pdfjs-editor-resizer-label-bottom-right = Colțul din dreapta jos — redimensionează
pdfjs-editor-resizer-label-bottom-middle = Mijloc de jos - redimensionează
pdfjs-editor-resizer-label-bottom-left = Colțul din stânga jos — redimensionează
pdfjs-editor-resizer-label-middle-left = Mijloc stânga — redimensionează
pdfjs-editor-resizer-top-left =
    .aria-label = Colțul din stânga sus — redimensionează
pdfjs-editor-resizer-top-middle =
    .aria-label = Mijloc de sus — redimensionează
pdfjs-editor-resizer-top-right =
    .aria-label = Colțul din dreapta sus — redimensionează
pdfjs-editor-resizer-middle-right =
    .aria-label = Mijloc dreapta — redimensionează
pdfjs-editor-resizer-bottom-right =
    .aria-label = Colțul din dreapta jos — redimensionează
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Mijloc de jos - redimensionează
pdfjs-editor-resizer-bottom-left =
    .aria-label = Colțul din stânga jos — redimensionează
pdfjs-editor-resizer-middle-left =
    .aria-label = Mijloc stânga — redimensionează

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Culoare de evidențiere
pdfjs-editor-colorpicker-button =
    .title = Schimbă culoarea
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Opțiuni de culoare
pdfjs-editor-colorpicker-yellow =
    .title = Galben
pdfjs-editor-colorpicker-green =
    .title = Verde
pdfjs-editor-colorpicker-blue =
    .title = Albastru
pdfjs-editor-colorpicker-pink =
    .title = Roz
pdfjs-editor-colorpicker-red =
    .title = Roșu

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Afișează tot
pdfjs-editor-highlight-show-all-button =
    .title = Afișează tot

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Editează textul alternativ (descrierea imaginii)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Adaugă text alternativ (descrierea imaginii)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Scrie descrierea aici...
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Scurtă descriere pentru cei care nu pot vedea imaginea sau pentru când nu se încarcă imaginea.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Acest text alternativ a fost creat automat și este posibil să nu fie exact.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Află mai multe
pdfjs-editor-new-alt-text-create-automatically-button-label = Creează automat texte alternative
pdfjs-editor-new-alt-text-not-now-button = Nu acum
pdfjs-editor-new-alt-text-error-title = Nu s-a putut crea automat textul alternativ
pdfjs-editor-new-alt-text-error-description = Te rugăm să scrii propriul text alternativ sau să încerci din nou mai târziu.
pdfjs-editor-new-alt-text-error-close-button = Închide
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Se descarcă modelul IA de text alternativ ({ $downloadedSize } de { $totalSize } MB)
    .aria-valuetext = Se descarcă modelul IA de text alternativ ({ $downloadedSize } de { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Text alternativ adăugat
pdfjs-editor-new-alt-text-added-button-label = Text alternativ adăugat
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Text alternativ lipsă
pdfjs-editor-new-alt-text-missing-button-label = Text alternativ lipsă
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Revizuiește textul alternativ
pdfjs-editor-new-alt-text-to-review-button-label = Revizuiește textul alternativ
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Creat automat: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Setări text alternativ imagini
pdfjs-image-alt-text-settings-button-label = Setări text alternativ imagini
pdfjs-editor-alt-text-settings-dialog-label = Setări text alternativ imagini
pdfjs-editor-alt-text-settings-automatic-title = Text alternativ automat
pdfjs-editor-alt-text-settings-create-model-button-label = Creează automat texte alternative
pdfjs-editor-alt-text-settings-create-model-description = Sugerează descrieri ca să îi ajuți pe cei care nu pot vedea imaginea sau pentru când nu se încarcă imaginea.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Model IA de text alternativ ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Rulează local pe dispozitiv, deci datele tale rămân private. Necesar pentru text alternativ automat.
pdfjs-editor-alt-text-settings-delete-model-button = Șterge
pdfjs-editor-alt-text-settings-download-model-button = Descarcă
pdfjs-editor-alt-text-settings-downloading-model-button = Se descarcă…
pdfjs-editor-alt-text-settings-editor-title = Editor de text alternativ
pdfjs-editor-alt-text-settings-show-dialog-button-label = Afișează editorul de text alternativ imediat când adaugi o imagine
pdfjs-editor-alt-text-settings-show-dialog-description = Te ajută să te asiguri că toate imaginile au text alternativ.
pdfjs-editor-alt-text-settings-close-button = Închide

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Evidențiere adăugată
pdfjs-editor-freetext-added-alert = Text adăugat
pdfjs-editor-ink-added-alert = Desen adăugat
pdfjs-editor-stamp-added-alert = Imagine adăugată
pdfjs-editor-signature-added-alert = Semnătură adăugată

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Evidențiere eliminată
pdfjs-editor-undo-bar-message-freetext = Text eliminat
pdfjs-editor-undo-bar-message-ink = Desen eliminat
pdfjs-editor-undo-bar-message-stamp = Imagine eliminată
pdfjs-editor-undo-bar-message-signature = Semnătură eliminată
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } adnotare eliminată
        [few] { $count } adnotări eliminate
       *[other] { $count } de adnotări eliminate
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Anulează
pdfjs-editor-undo-bar-undo-button-label = Anulează
pdfjs-editor-undo-bar-close-button =
    .title = Închide
pdfjs-editor-undo-bar-close-button-label = Închide

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Această fereastră permite utilizatorului să creeze o semnătură de adăugat la un document PDF. Utilizatorul poate edita numele (care servește și ca text alternativ) și, opțional, poate salva semnătura pentru utilizare repetată.
pdfjs-editor-add-signature-dialog-title = Adaugă o semnătură

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Tip
    .title = Tip
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Desenează
    .title = Desenează
pdfjs-editor-add-signature-image-button = Imagine
    .title = Imagine

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Tastează semnătura
    .placeholder = Tastează semnătura
pdfjs-editor-add-signature-draw-placeholder = Desenează semnătura
pdfjs-editor-add-signature-draw-thickness-range-label = Grosime
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Grosimea desenului: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Trage aici un fișier pentru încărcare
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Sau alege fișiere de imagini
       *[other] Sau răsfoiește prin fișiere de imagini
    }

## Controls

pdfjs-editor-add-signature-description-label = Descriere (text alternativ)
pdfjs-editor-add-signature-description-input =
    .title = Descriere (text alternativ)
pdfjs-editor-add-signature-description-default-when-drawing = Semnătură
pdfjs-editor-add-signature-clear-button-label = Șterge semnătura
pdfjs-editor-add-signature-clear-button =
    .title = Șterge semnătura
pdfjs-editor-add-signature-save-checkbox = Salvează semnătura
pdfjs-editor-add-signature-save-warning-message = Ai atins limita de 5 semnături salvate. Elimină una dacă vrei să salvezi alta.
pdfjs-editor-add-signature-image-upload-error-title = Imaginea nu a putut fi încărcată
pdfjs-editor-add-signature-image-upload-error-description = Verifică-ți conexiunea la rețea sau încearcă cu o altă imagine.
pdfjs-editor-add-signature-image-no-data-error-title = Imaginea nu poate fi convertită în semnătură
pdfjs-editor-add-signature-image-no-data-error-description = Încearcă să încarci altă imagine.
pdfjs-editor-add-signature-error-close-button = Închide

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Anulează
pdfjs-editor-add-signature-add-button = Adaugă
pdfjs-editor-edit-signature-update-button = Actualizează

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Acțiuni
pdfjs-editor-edit-comment-actions-button =
    .title = Acțiuni
pdfjs-editor-edit-comment-close-button-label = Închide
pdfjs-editor-edit-comment-close-button =
    .title = Închide
pdfjs-editor-edit-comment-actions-edit-button-label = Editează
pdfjs-editor-edit-comment-actions-delete-button-label = Șterge
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Introdu comentariul
pdfjs-editor-edit-comment-manager-cancel-button = Anulează
pdfjs-editor-edit-comment-manager-save-button = Salvează

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Editează comentariul

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Elimină semnătura salvată
pdfjs-editor-delete-signature-button-label1 = Elimină semnătura salvată

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Editează descrierea

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Editează descrierea
