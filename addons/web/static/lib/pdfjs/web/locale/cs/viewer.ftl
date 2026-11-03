# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Přejde na předchozí stránku
pdfjs-previous-button-label = Předchozí
pdfjs-next-button =
    .title = Přejde na následující stránku
pdfjs-next-button-label = Další
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Stránka
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = z { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } z { $pagesCount })
pdfjs-zoom-out-button =
    .title = Zmenší velikost
pdfjs-zoom-out-button-label = Zmenšit
pdfjs-zoom-in-button =
    .title = Zvětší velikost
pdfjs-zoom-in-button-label = Zvětšit
pdfjs-zoom-select =
    .title = Nastaví velikost
pdfjs-presentation-mode-button =
    .title = Přepne do režimu prezentace
pdfjs-presentation-mode-button-label = Režim prezentace
pdfjs-open-file-button =
    .title = Otevře soubor
pdfjs-open-file-button-label = Otevřít
pdfjs-print-button =
    .title = Vytiskne dokument
pdfjs-print-button-label = Vytisknout
pdfjs-save-button =
    .title = Uložit
pdfjs-save-button-label = Uložit
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Stáhnout
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Stáhnout
pdfjs-bookmark-button =
    .title = Aktuální stránka (zobrazit URL od aktuální stránky)
pdfjs-bookmark-button-label = Aktuální stránka

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Nástroje
pdfjs-tools-button-label = Nástroje
pdfjs-first-page-button =
    .title = Přejde na první stránku
pdfjs-first-page-button-label = Přejít na první stránku
pdfjs-last-page-button =
    .title = Přejde na poslední stránku
pdfjs-last-page-button-label = Přejít na poslední stránku
pdfjs-page-rotate-cw-button =
    .title = Otočí po směru hodin
pdfjs-page-rotate-cw-button-label = Otočit po směru hodin
pdfjs-page-rotate-ccw-button =
    .title = Otočí proti směru hodin
pdfjs-page-rotate-ccw-button-label = Otočit proti směru hodin
pdfjs-cursor-text-select-tool-button =
    .title = Povolí výběr textu
pdfjs-cursor-text-select-tool-button-label = Výběr textu
pdfjs-cursor-hand-tool-button =
    .title = Povolí nástroj ručička
pdfjs-cursor-hand-tool-button-label = Nástroj ručička
pdfjs-scroll-page-button =
    .title = Posouvat po stránkách
pdfjs-scroll-page-button-label = Posouvání po stránkách
pdfjs-scroll-vertical-button =
    .title = Použít svislé posouvání
pdfjs-scroll-vertical-button-label = Svislé posouvání
pdfjs-scroll-horizontal-button =
    .title = Použít vodorovné posouvání
pdfjs-scroll-horizontal-button-label = Vodorovné posouvání
pdfjs-scroll-wrapped-button =
    .title = Použít postupné posouvání
pdfjs-scroll-wrapped-button-label = Postupné posouvání
pdfjs-spread-none-button =
    .title = Nesdružovat stránky
pdfjs-spread-none-button-label = Žádné sdružení
pdfjs-spread-odd-button =
    .title = Sdruží stránky s umístěním lichých vlevo
pdfjs-spread-odd-button-label = Sdružení stránek (liché vlevo)
pdfjs-spread-even-button =
    .title = Sdruží stránky s umístěním sudých vlevo
pdfjs-spread-even-button-label = Sdružení stránek (sudé vlevo)

## Document properties dialog

pdfjs-document-properties-button =
    .title = Vlastnosti dokumentu…
pdfjs-document-properties-button-label = Vlastnosti dokumentu…
pdfjs-document-properties-file-name = Název souboru:
pdfjs-document-properties-file-size = Velikost souboru:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } kB ({ $b } bajtů)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bajtů)
pdfjs-document-properties-title = Název stránky:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Předmět:
pdfjs-document-properties-keywords = Klíčová slova:
pdfjs-document-properties-creation-date = Datum vytvoření:
pdfjs-document-properties-modification-date = Datum úpravy:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Vytvořil:
pdfjs-document-properties-producer = Tvůrce PDF:
pdfjs-document-properties-version = Verze PDF:
pdfjs-document-properties-page-count = Počet stránek:
pdfjs-document-properties-page-size = Velikost stránky:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = na výšku
pdfjs-document-properties-page-size-orientation-landscape = na šířku
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Dopis
pdfjs-document-properties-page-size-name-legal = Právní dokument

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
pdfjs-document-properties-linearized = Rychlé zobrazování z webu:
pdfjs-document-properties-linearized-yes = Ano
pdfjs-document-properties-linearized-no = Ne
pdfjs-document-properties-close-button = Zavřít
pdfjs-digital-signature-properties-view-certificate = Zobrazit certifikát
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Důvod: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Časové razítko: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Podpis ({ $count })
        [few] Podpisy ({ $count })
        [many] Podpisy ({ $count })
       *[other] Podpisy ({ $count })
    }

## Print

pdfjs-print-progress-message = Příprava dokumentu pro tisk…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Zrušit
pdfjs-printing-not-supported = Upozornění: Tisk není v tomto prohlížeči plně podporován.
pdfjs-printing-not-ready = Upozornění: Dokument PDF není kompletně načten.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Najít aktuální položku v osnově
pdfjs-current-outline-item-button-label = Aktuální položka v osnově
pdfjs-findbar-button =
    .title = Najde v dokumentu
pdfjs-findbar-button-label = Najít
pdfjs-additional-layers = Další vrstvy

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Náhled strany { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Vybrat stranu { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Strana { $page } z { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Najít v dokumentu…
    .title = Najít
pdfjs-find-previous-button =
    .title = Najde předchozí výskyt hledaného textu
pdfjs-find-previous-button-label = Předchozí
pdfjs-find-next-button =
    .title = Najde další výskyt hledaného textu
pdfjs-find-next-button-label = Další
pdfjs-find-highlight-checkbox = Zvýraznit
pdfjs-find-match-case-checkbox-label = Rozlišovat velikost
pdfjs-find-match-diacritics-checkbox-label = Rozlišovat diakritiku
pdfjs-find-entire-word-checkbox-label = Celá slova
pdfjs-find-reached-top = Dosažen začátek dokumentu, pokračuje se od konce
pdfjs-find-reached-bottom = Dosažen konec dokumentu, pokračuje se od začátku
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current }. z { $total } výskytu
        [few] { $current }. z { $total } výskytů
        [many] { $current }. z { $total } výskytů
       *[other] { $current }. z { $total } výskytů
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Více než { $limit } výskyt
        [few] Více než { $limit } výskyty
        [many] Více než { $limit } výskytů
       *[other] Více než { $limit } výskytů
    }
pdfjs-find-not-found = Hledaný text nenalezen

## Predefined zoom values

pdfjs-page-scale-width = Podle šířky
pdfjs-page-scale-fit = Podle stránky
pdfjs-page-scale-auto = Automatická velikost
pdfjs-page-scale-actual = Skutečná velikost
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Strana { $page }

## Loading indicator messages

pdfjs-loading-error = Při nahrávání PDF nastala chyba.
pdfjs-invalid-file-error = Neplatný nebo chybný soubor PDF.
pdfjs-missing-file-error = Chybí soubor PDF.
pdfjs-unexpected-response-error = Neočekávaná odpověď serveru.
pdfjs-rendering-error = Při vykreslování stránky nastala chyba.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Anotace typu { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Pro otevření PDF souboru vložte heslo.
pdfjs-password-invalid = Neplatné heslo. Zkuste to znovu.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Zrušit
pdfjs-web-fonts-disabled = Webová písma jsou zakázána, proto není možné použít vložená písma PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Text
pdfjs-editor-color-picker-free-text-input =
    .title = Změna barvy textu
pdfjs-editor-free-text-button-label = Text
pdfjs-editor-ink-button =
    .title = Kreslení
pdfjs-editor-color-picker-ink-input =
    .title = Změna barvy kresby
pdfjs-editor-ink-button-label = Kreslení
pdfjs-editor-stamp-button =
    .title = Přidání či úprava obrázků
pdfjs-editor-stamp-button-label = Přidání či úprava obrázků
pdfjs-editor-highlight-button =
    .title = Zvýraznění
pdfjs-editor-highlight-button-label = Zvýraznění
pdfjs-highlight-floating-button1 =
    .aria-label = Zvýraznit
    .title = Zvýraznit
pdfjs-highlight-floating-button-label = Zvýraznit
pdfjs-comment-floating-button =
    .aria-label = Komentář
    .title = Komentář
pdfjs-comment-floating-button-label = Komentář
pdfjs-editor-comment-button =
    .aria-label = Komentář
    .title = Komentář
pdfjs-editor-comment-button-label = Komentář
pdfjs-editor-signature-button =
    .title = Přidat podpis
pdfjs-editor-signature-button-label = Přidat podpis

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor zvýraznění
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editor kresby
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor podpisu: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editor obrázků

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Odebrat kresbu
pdfjs-editor-remove-freetext-button =
    .title = Odebrat text
pdfjs-editor-remove-stamp-button =
    .title = Odebrat obrázek
pdfjs-editor-remove-highlight-button =
    .title = Odebrat zvýraznění
pdfjs-editor-remove-signature-button =
    .title = Odebrat podpis

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Barva
pdfjs-editor-free-text-size-input = Velikost
pdfjs-editor-ink-color-input = Barva
pdfjs-editor-ink-thickness-input = Tloušťka
pdfjs-editor-ink-opacity-input = Průhlednost
pdfjs-editor-stamp-add-image-button =
    .title = Přidat obrázek
pdfjs-editor-stamp-add-image-button-label = Přidat obrázek
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Tloušťka
pdfjs-editor-free-highlight-thickness-title =
    .title = Změna tloušťky při zvýrazňování jiných položek než textu
pdfjs-editor-add-signature-container =
    .aria-label = Ovládací prvky pro podpisy a uložené podpisy
pdfjs-editor-signature-add-signature-button =
    .title = Přidat nový podpis
pdfjs-editor-signature-add-signature-button-label = Přidat nový podpis
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Uložený podpis: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Textový editor
    .default-content = Začněte psát...
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Komentář
        [few] Komentáře
        [many] Komentáře
       *[other] Komentáře
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Zavřít postranní lištu
    .title = Zavřít postranní lištu
pdfjs-editor-comments-sidebar-close-button-label = Zavřít postranní lištu
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Vidíte něco pozoruhodného? Zvýrazněte to a zanechte komentář.
pdfjs-editor-comments-sidebar-no-comments-link = Zjistit více

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Náhradní popis
pdfjs-editor-alt-text-edit-button =
    .aria-label = Upravit alternativní text
pdfjs-editor-alt-text-dialog-label = Vyberte možnost
pdfjs-editor-alt-text-dialog-description = Náhradní popis pomáhá, když lidé obrázek nevidí nebo když se nenačítá.
pdfjs-editor-alt-text-add-description-label = Přidat popis
pdfjs-editor-alt-text-add-description-description = Snažte se o 1-2 věty, které popisují předmět, prostředí nebo činnosti.
pdfjs-editor-alt-text-mark-decorative-label = Označit jako dekorativní
pdfjs-editor-alt-text-mark-decorative-description = Používá se pro okrasné obrázky, jako jsou rámečky nebo vodoznaky.
pdfjs-editor-alt-text-cancel-button = Zrušit
pdfjs-editor-alt-text-save-button = Uložit
pdfjs-editor-alt-text-decorative-tooltip = Označen jako dekorativní
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Například: “Mladý muž si sedá ke stolu, aby se najedl.”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alternativní text

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Levý horní roh — změna velikosti
pdfjs-editor-resizer-top-middle =
    .aria-label = Horní střed — změna velikosti
pdfjs-editor-resizer-top-right =
    .aria-label = Pravý horní roh — změna velikosti
pdfjs-editor-resizer-middle-right =
    .aria-label = Vpravo uprostřed — změna velikosti
pdfjs-editor-resizer-bottom-right =
    .aria-label = Pravý dolní roh — změna velikosti
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Střed dole — změna velikosti
pdfjs-editor-resizer-bottom-left =
    .aria-label = Levý dolní roh — změna velikosti
pdfjs-editor-resizer-middle-left =
    .aria-label = Vlevo uprostřed — změna velikosti

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Barva zvýraznění
pdfjs-editor-colorpicker-button =
    .title = Změna barvy
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Výběr barev
pdfjs-editor-colorpicker-yellow =
    .title = Žlutá
pdfjs-editor-colorpicker-green =
    .title = Zelená
pdfjs-editor-colorpicker-blue =
    .title = Modrá
pdfjs-editor-colorpicker-pink =
    .title = Růžová
pdfjs-editor-colorpicker-red =
    .title = Červená

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Zobrazit vše
pdfjs-editor-highlight-show-all-button =
    .title = Zobrazit vše

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Upravit alternativní text (popis obrázku)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Přidat alternativní text (popis obrázku)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Sem napište svůj popis…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Krátký popis pro lidi, kteří neuvidí obrázek nebo když se obrázek nenačítá.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Tento alternativní text byl vytvořen automaticky a může být nepřesný.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Více informací
pdfjs-editor-new-alt-text-create-automatically-button-label = Vytvořit alternativní text automaticky
pdfjs-editor-new-alt-text-not-now-button = Teď ne
pdfjs-editor-new-alt-text-error-title = Nepodařilo se automaticky vytvořit alternativní text
pdfjs-editor-new-alt-text-error-description = Napište prosím vlastní alternativní text nebo to zkuste znovu později.
pdfjs-editor-new-alt-text-error-close-button = Zavřít
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Stahuje se model AI pro alternativní texty ({ $downloadedSize } z { $totalSize } MB)
    .aria-valuetext = Stahuje se model AI pro alternativní texty ({ $downloadedSize } z { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alternativní text byl přidán
pdfjs-editor-new-alt-text-added-button-label = Alternativní text byl přidán
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Chybí alternativní text
pdfjs-editor-new-alt-text-missing-button-label = Chybí alternativní text
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Zkontrolovat alternativní text
pdfjs-editor-new-alt-text-to-review-button-label = Zkontrolovat alternativní text
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Vytvořeno automaticky: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Nastavení alternativního textu obrázku
pdfjs-image-alt-text-settings-button-label = Nastavení alternativního textu obrázku
pdfjs-editor-alt-text-settings-dialog-label = Nastavení alternativního textu obrázku
pdfjs-editor-alt-text-settings-automatic-title = Automatický alternativní text
pdfjs-editor-alt-text-settings-create-model-button-label = Vytvořit alternativní text automaticky
pdfjs-editor-alt-text-settings-create-model-description = Navrhuje popisy, které pomohou lidem, kteří nevidí obrázek nebo když se obrázek nenačte.
pdfjs-editor-alt-text-settings-editor-title = Editor alternativního textu
pdfjs-editor-alt-text-settings-show-dialog-button-label = Při přidávání obrázku hned zobrazit editor alternativního textu
pdfjs-editor-alt-text-settings-show-dialog-description = Pomůže vám zajistit, aby všechny vaše obrázky obsahovaly alternativní text.
pdfjs-editor-alt-text-settings-close-button = Zavřít

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Přidáno zvýraznění
pdfjs-editor-freetext-added-alert = Text přidán
pdfjs-editor-ink-added-alert = Kresba byla přidána
pdfjs-editor-stamp-added-alert = Obrázek byl přidán
pdfjs-editor-signature-added-alert = Byl přidán podpis

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Zvýraznění odebráno
pdfjs-editor-undo-bar-message-freetext = Text odstraněn
pdfjs-editor-undo-bar-message-ink = Kresba odstraněna
pdfjs-editor-undo-bar-message-stamp = Obrázek odebrán
pdfjs-editor-undo-bar-message-signature = Podpis odebrán
pdfjs-editor-undo-bar-message-comment = Komentář odebrán
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } anotace odebrána
        [few] { $count } anotace odebrány
        [many] { $count } anotací odebráno
       *[other] { $count } anotací odebráno
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Zpět
pdfjs-editor-undo-bar-undo-button-label = Zpět
pdfjs-editor-undo-bar-close-button =
    .title = Zavřít
pdfjs-editor-undo-bar-close-button-label = Zavřít

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Tento způsob umožňuje uživateli vytvořit podpis, který se přidá do dokumentu PDF. Uživatel může upravit jméno (které slouží zároveň jako alternativní text) a podpis uložit pro pozdější použití.
pdfjs-editor-add-signature-dialog-title = Přidat podpis

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Psát
    .title = Psát
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Kreslit
    .title = Kreslit
pdfjs-editor-add-signature-image-button = Obrázek
    .title = Obrázek

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Zadejte svůj podpis
    .placeholder = Zadejte svůj podpis
pdfjs-editor-add-signature-draw-placeholder = Nakreslete svůj podpis
pdfjs-editor-add-signature-draw-thickness-range-label = Tloušťka
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Tloušťka kresby: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Přetáhněte sem soubor, který chcete nahrát
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Nebo vyberte soubory obrazu
       *[other] Nebo vyberte soubory obrazu
    }

## Controls

pdfjs-editor-add-signature-description-label = Popis (alternativní text)
pdfjs-editor-add-signature-description-input =
    .title = Popis (alternativní text)
pdfjs-editor-add-signature-description-default-when-drawing = Podpis
pdfjs-editor-add-signature-clear-button-label = Vymazání podpisu
pdfjs-editor-add-signature-clear-button =
    .title = Vymazání podpisu
pdfjs-editor-add-signature-save-checkbox = Uložit podpis
pdfjs-editor-add-signature-save-warning-message = Dosáhli jste limitu 5 uložených podpisů. Chcete-li uložit další, jeden odstraňte.
pdfjs-editor-add-signature-image-upload-error-title = Obrázek se nepodařilo nahrát
pdfjs-editor-add-signature-image-upload-error-description = Zkontrolujte připojení k síti nebo zkuste jiný obrázek.
pdfjs-editor-add-signature-image-no-data-error-title = Nelze převést tento obrázek na podpis
pdfjs-editor-add-signature-image-no-data-error-description = Zkuste nahrát jiný obrázek.
pdfjs-editor-add-signature-error-close-button = Zavřít

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Zrušit
pdfjs-editor-add-signature-add-button = Přidat
pdfjs-editor-edit-signature-update-button = Aktualizovat

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Upravit komentář
pdfjs-editor-edit-comment-popup-button =
    .title = Upravit komentář
pdfjs-editor-delete-comment-popup-button-label = Odebrat komentář
pdfjs-editor-delete-comment-popup-button =
    .title = Odebrat komentář
pdfjs-show-comment-button =
    .title = Zobrazit komentář

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Upravit komentář
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Aktualizovat
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Přidání komentáře
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Přidat
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Začněte psát…
pdfjs-editor-edit-comment-dialog-cancel-button = Zrušit

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Přidání komentáře

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Přepnout postranní lištu (dokument obsahuje náhledy/osnovu/přílohy/vrstvy)
pdfjs-toggle-views-manager-button1-label = Spravovat strany
pdfjs-views-manager-sidebar =
    .aria-label = Postranní lišta
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Změna velikosti v postranní liště
pdfjs-views-manager-view-selector-button =
    .title = Zobrazení
pdfjs-views-manager-view-selector-button-label = Zobrazení
pdfjs-views-manager-pages-title = Stránky
pdfjs-views-manager-outlines-title1 = Osnova dokumentu
    .title = Osnova dokumentu (dvojité klepnutí rozbalí/sbalí všechny položky)
pdfjs-views-manager-attachments-title = Přílohy
pdfjs-views-manager-layers-title1 = Vrstvy
    .title = Vrstvy (dvojité klepnutí obnoví všechny vrstvy do výchozího stavu)
pdfjs-views-manager-pages-option-label = Stránky
pdfjs-views-manager-outlines-option-label = Osnova dokumentu
pdfjs-views-manager-attachments-option-label = Přílohy
pdfjs-views-manager-layers-option-label = Vrstvy
pdfjs-views-manager-add-file-button =
    .title = Přidat soubor
pdfjs-views-manager-add-file-button-label = Přidat soubor
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } vybrána
        [few] { $count } vybrány
        [many] { $count } vybráno
       *[other] { $count } vybráno
    }
pdfjs-views-manager-pages-status-none-action-label = Výběr stránek
pdfjs-views-manager-pages-status-action-button-label = Správa
pdfjs-views-manager-pages-status-copy-button-label = Kopírovat
pdfjs-views-manager-pages-status-cut-button-label = Vyjmout
pdfjs-views-manager-pages-status-delete-button-label = Smazat
pdfjs-views-manager-pages-status-export-selected-button-label = Exportovat vybrané…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 stránka vyjmuta
        [few] { $count } stránky vyjmuty
        [many] { $count } stránek vyjmuto
       *[other] { $count } stránek vyjmuto
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 stránka zkopírována
        [few] { $count } stránky zkopírovány
        [many] { $count } stránek zkopírováno
       *[other] { $count } stránek zkopírováno
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 stránka smazána
        [few] { $count } stránky smazány
        [many] { $count } stránek smazáno
       *[other] { $count } stránek smazáno
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Příprava vašeho souboru…
pdfjs-views-manager-pages-status-waiting-uploading-label = Nahrávání souboru…
pdfjs-views-manager-status-warning-cut-label = Nelze vyjmout. Obnovte stránku a zkuste to znovu.
pdfjs-views-manager-status-warning-copy-label = Kopírování se nezdařilo. Obnovte stránku a zkuste to znovu.
pdfjs-views-manager-status-warning-delete-label = Smazání se nezdařilo. Obnovte stránku a zkuste to znovu.
pdfjs-views-manager-status-warning-save-label = Nepodařilo se uložit. Obnovte stránku a zkuste to znovu.
pdfjs-views-manager-status-undo-button-label = Zpět
pdfjs-views-manager-status-done-button-label = Hotovo
pdfjs-views-manager-status-close-button =
    .title = Zavřít
pdfjs-views-manager-status-close-button-label = Zavřít
pdfjs-views-manager-paste-button-label = Vložit
pdfjs-views-manager-paste-button-before =
    .title = Vloží před první stránku
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Vložit za stránku { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NOVÉ
pdfjs-views-manager-waiting-for-file = Nahrávání souboru…
pdfjs-toggle-views-manager-button1 =
    .title = Spravovat strany

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Vlastnosti digitálního podpisu
    .title = Vlastnosti digitálního podpisu
pdfjs-digital-signature-properties-button-label = Vlastnosti digitálního podpisu

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Dokument byl podepsán platným digitálním podpisem
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Dokument je podepsán, ale { $count } elektronický podpis se nepodařilo ověřit
        [few] Dokument je podepsán, ale { $count } elektronické podpisy se nepodařilo ověřit
        [many] Dokument je podepsán, ale { $count } elektronických podpisů se nepodařilo ověřit
       *[other] Dokument je podepsán, ale { $count } elektronických podpisů se nepodařilo ověřit
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Dokument podepsaný { $count } certifikátem, který není důvěryhodný
        [few] Dokument podepsaný { $count } certifikáty, které nejsou důvěryhodné
        [many] Dokument podepsaný { $count } certifikáty, které nejsou důvěryhodné
       *[other] Dokument podepsaný { $count } certifikáty, které nejsou důvěryhodné
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Dokument je podepsaný { $count } prošlým certifikátem
        [few] Dokument je podepsaný { $count } prošlými certifikáty
        [many] Dokument je podepsaný { $count } prošlými certifikáty
       *[other] Dokument je podepsaný { $count } prošlými certifikáty
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] Dokument má { $count } neplatný elektronický podpis
        [few] Dokument má { $count } neplatné elektronické podpisy
        [many] Dokument má { $count } neplatných elektronických podpisů
       *[other] Dokument má { $count } neplatných elektronických podpisů
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Dokument je podepsaný { $count } zneplatněným certifikátem
        [few] Dokument je podepsaný { $count } zneplatněnými certifikáty
        [many] Dokument je podepsaný { $count } zneplatněnými certifikáty
       *[other] Dokument je podepsaný { $count } zneplatněnými certifikáty
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Stav: Podpis ověřen
pdfjs-digital-signature-properties-status-invalid = Stav: Podpis je neplatný
pdfjs-digital-signature-properties-status-unknown = Stav: Nelze ověřit (nepodporováno)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Certifikát: Důvěryhodný ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Certifikát: nedostupný
pdfjs-digital-signature-properties-certificate-untrusted = Certifikát: nedůvěryhodný
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Certifikát: Neznámý vydavatel ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Certifikát: Self-signed ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Certifikát: Nedůvěryhodný vydavatel ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Certifikát: vypršel
pdfjs-digital-signature-properties-certificate-expired-with-date = Certifikát: Vypršel ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Certifikát: zneplatněn

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Odebrat uložený podpis
pdfjs-editor-delete-signature-button-label1 = Odebrat uložený podpis

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Upravit popis

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Upravit popis
