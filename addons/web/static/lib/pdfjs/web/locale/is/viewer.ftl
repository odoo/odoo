# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Fyrri síða
pdfjs-previous-button-label = Fyrri
pdfjs-next-button =
    .title = Næsta síða
pdfjs-next-button-label = Næsti
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Síða
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = af { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } af { $pagesCount })
pdfjs-zoom-out-button =
    .title = Minnka aðdrátt
pdfjs-zoom-out-button-label = Minnka aðdrátt
pdfjs-zoom-in-button =
    .title = Auka aðdrátt
pdfjs-zoom-in-button-label = Auka aðdrátt
pdfjs-zoom-select =
    .title = Aðdráttur
pdfjs-presentation-mode-button =
    .title = Skipta yfir á kynningarham
pdfjs-presentation-mode-button-label = Kynningarhamur
pdfjs-open-file-button =
    .title = Opna skrá
pdfjs-open-file-button-label = Opna
pdfjs-print-button =
    .title = Prenta
pdfjs-print-button-label = Prenta
pdfjs-save-button =
    .title = Vista
pdfjs-save-button-label = Vista
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Sækja
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Sækja
pdfjs-bookmark-button =
    .title = Núverandi síða (Skoða vefslóð frá núverandi síðu)
pdfjs-bookmark-button-label = Núverandi síða

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Verkfæri
pdfjs-tools-button-label = Verkfæri
pdfjs-first-page-button =
    .title = Fara á fyrstu síðu
pdfjs-first-page-button-label = Fara á fyrstu síðu
pdfjs-last-page-button =
    .title = Fara á síðustu síðu
pdfjs-last-page-button-label = Fara á síðustu síðu
pdfjs-page-rotate-cw-button =
    .title = Snúa réttsælis
pdfjs-page-rotate-cw-button-label = Snúa réttsælis
pdfjs-page-rotate-ccw-button =
    .title = Snúa rangsælis
pdfjs-page-rotate-ccw-button-label = Snúa rangsælis
pdfjs-cursor-text-select-tool-button =
    .title = Virkja textavalsáhald
pdfjs-cursor-text-select-tool-button-label = Textavalsáhald
pdfjs-cursor-hand-tool-button =
    .title = Virkja handarverkfæri
pdfjs-cursor-hand-tool-button-label = Handarverkfæri
pdfjs-scroll-page-button =
    .title = Nota síðuskrun
pdfjs-scroll-page-button-label = Síðuskrun
pdfjs-scroll-vertical-button =
    .title = Nota lóðrétt skrun
pdfjs-scroll-vertical-button-label = Lóðrétt skrun
pdfjs-scroll-horizontal-button =
    .title = Nota lárétt skrun
pdfjs-scroll-horizontal-button-label = Lárétt skrun
pdfjs-scroll-wrapped-button =
    .title = Nota línuskipt síðuskrun
pdfjs-scroll-wrapped-button-label = Línuskipt síðuskrun
pdfjs-spread-none-button =
    .title = Ekki taka þátt í dreifingu síðna
pdfjs-spread-none-button-label = Engin dreifing
pdfjs-spread-odd-button =
    .title = Taka þátt í dreifingu síðna með oddatölum
pdfjs-spread-odd-button-label = Oddatöludreifing
pdfjs-spread-even-button =
    .title = Taktu þátt í dreifingu síðna með jöfnuntölum
pdfjs-spread-even-button-label = Jafnatöludreifing

## Document properties dialog

pdfjs-document-properties-button =
    .title = Eiginleikar skjals…
pdfjs-document-properties-button-label = Eiginleikar skjals…
pdfjs-document-properties-file-name = Skráarnafn:
pdfjs-document-properties-file-size = Skrárstærð:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bæti)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bæti)
pdfjs-document-properties-title = Titill:
pdfjs-document-properties-author = Hönnuður:
pdfjs-document-properties-subject = Efni:
pdfjs-document-properties-keywords = Stikkorð:
pdfjs-document-properties-creation-date = Búið til:
pdfjs-document-properties-modification-date = Dags breytingar:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Höfundur:
pdfjs-document-properties-producer = PDF framleiðandi:
pdfjs-document-properties-version = PDF útgáfa:
pdfjs-document-properties-page-count = Blaðsíðufjöldi:
pdfjs-document-properties-page-size = Stærð síðu:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = skammsnið
pdfjs-document-properties-page-size-orientation-landscape = langsnið
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
pdfjs-document-properties-linearized = Fljótleg vefskoðun:
pdfjs-document-properties-linearized-yes = Já
pdfjs-document-properties-linearized-no = Nei
pdfjs-document-properties-close-button = Loka

## Print

pdfjs-print-progress-message = Undirbý skjal fyrir prentun…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Hætta við
pdfjs-printing-not-supported = Aðvörun: Prentun er ekki með fyllilegan stuðning á þessum vafra.
pdfjs-printing-not-ready = Aðvörun: Ekki er búið að hlaða inn allri PDF skránni fyrir prentun.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Víxla hliðarstiku af/á
pdfjs-toggle-sidebar-notification-button =
    .title = Víxla hliðarstiku af/á (skjal inniheldur yfirlit/viðhengi/lög)
pdfjs-toggle-sidebar-button-label = Víxla hliðarstiku af/á
pdfjs-document-outline-button =
    .title = Sýna yfirlit skjals (tvísmelltu til að opna/loka öllum hlutum)
pdfjs-document-outline-button-label = Efnisskipan skjals
pdfjs-attachments-button =
    .title = Sýna viðhengi
pdfjs-attachments-button-label = Viðhengi
pdfjs-layers-button =
    .title = Birta lög (tvísmelltu til að endurstilla öll lög í sjálfgefna stöðu)
pdfjs-layers-button-label = Lög
pdfjs-thumbs-button =
    .title = Sýna smámyndir
pdfjs-thumbs-button-label = Smámyndir
pdfjs-current-outline-item-button =
    .title = Finna núverandi atriði efnisskipunar
pdfjs-current-outline-item-button-label = Núverandi atriði efnisskipunar
pdfjs-findbar-button =
    .title = Leita í skjali
pdfjs-findbar-button-label = Leita
pdfjs-additional-layers = Viðbótarlög

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Síða { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Smámynd af síðu { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Leita
    .placeholder = Leita í skjali…
pdfjs-find-previous-button =
    .title = Leita að fyrra tilfelli þessara orða
pdfjs-find-previous-button-label = Fyrri
pdfjs-find-next-button =
    .title = Leita að næsta tilfelli þessara orða
pdfjs-find-next-button-label = Næsti
pdfjs-find-highlight-checkbox = Lita allt
pdfjs-find-match-case-checkbox-label = Passa við stafstöðu
pdfjs-find-match-diacritics-checkbox-label = Passa við broddstafi
pdfjs-find-entire-word-checkbox-label = Heil orð
pdfjs-find-reached-top = Náði efst í skjal, held áfram neðst
pdfjs-find-reached-bottom = Náði enda skjals, held áfram efst
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } af { $total } passar við
       *[other] { $current } af { $total } passa við
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Fleiri en { $limit } passar við
       *[other] Fleiri en { $limit } passa við
    }
pdfjs-find-not-found = Fann ekki orðið

## Predefined zoom values

pdfjs-page-scale-width = Síðubreidd
pdfjs-page-scale-fit = Passa á síðu
pdfjs-page-scale-auto = Sjálfvirkur aðdráttur
pdfjs-page-scale-actual = Raunstærð
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Síða { $page }

## Loading indicator messages

pdfjs-loading-error = Villa kom upp við að hlaða inn PDF.
pdfjs-invalid-file-error = Ógild eða skemmd PDF skrá.
pdfjs-missing-file-error = Vantar PDF skrá.
pdfjs-unexpected-response-error = Óvænt svar frá netþjóni.
pdfjs-rendering-error = Upp kom villa við að birta síðuna.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } Skýring]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Settu inn lykilorð til að opna þessa PDF-skrá.
pdfjs-password-invalid = Ógilt lykilorð. Reyndu aftur.
pdfjs-password-ok-button = Í lagi
pdfjs-password-cancel-button = Hætta við
pdfjs-web-fonts-disabled = Vef leturgerðir eru óvirkar: get ekki notað innbyggðar PDF leturgerðir.

## Editing

pdfjs-editor-free-text-button =
    .title = Texti
pdfjs-editor-free-text-button-label = Texti
pdfjs-editor-ink-button =
    .title = Teikna
pdfjs-editor-ink-button-label = Teikna
pdfjs-editor-stamp-button =
    .title = Bæta við eða breyta myndum
pdfjs-editor-stamp-button-label = Bæta við eða breyta myndum
pdfjs-editor-highlight-button =
    .title = Áherslulita
pdfjs-editor-highlight-button-label = Áherslulita
pdfjs-highlight-floating-button1 =
    .title = Áherslulita
    .aria-label = Áherslulita
pdfjs-highlight-floating-button-label = Áherslulita
pdfjs-editor-signature-button =
    .title = Bæta við undirritun
pdfjs-editor-signature-button-label = Bæta við undirritun

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Fjarlægja teikningu
pdfjs-editor-remove-freetext-button =
    .title = Fjarlægja texta
pdfjs-editor-remove-stamp-button =
    .title = Fjarlægja mynd
pdfjs-editor-remove-highlight-button =
    .title = Fjarlægja áherslulit
pdfjs-editor-remove-signature-button =
    .title = Fjarlægja undirskrift

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Litur
pdfjs-editor-free-text-size-input = Stærð
pdfjs-editor-ink-color-input = Litur
pdfjs-editor-ink-thickness-input = Þykkt
pdfjs-editor-ink-opacity-input = Ógegnsæi
pdfjs-editor-stamp-add-image-button =
    .title = Bæta við mynd
pdfjs-editor-stamp-add-image-button-label = Bæta við mynd
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Þykkt
pdfjs-editor-free-highlight-thickness-title =
    .title = Breyta þykkt við áherslulitun annarra atriða en texta
pdfjs-editor-signature-add-signature-button =
    .title = Bæta við nýrri undirritun
pdfjs-editor-signature-add-signature-button-label = Bæta við nýrri undirritun
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Vistuð undirskrift: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Textaritill
    .default-content = Byrjaðu að skrifa…

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Alt-varatexti
pdfjs-editor-alt-text-edit-button =
    .aria-label = Breyta alt-myndatexta
pdfjs-editor-alt-text-dialog-label = Veldu valkost
pdfjs-editor-alt-text-dialog-description = Alt-varatexti (auka-myndatexti) hjálpar þegar fólk getur ekki séð myndina eða þegar hún hleðst ekki inn.
pdfjs-editor-alt-text-add-description-label = Bættu við lýsingu
pdfjs-editor-alt-text-add-description-description = Reyndu að takmarka þetta við 1-2 setningar sem lýsa efninu, umhverfi eða aðgerðum.
pdfjs-editor-alt-text-mark-decorative-label = Merkja sem skraut
pdfjs-editor-alt-text-mark-decorative-description = Þetta er notað fyrir skrautmyndir, eins og borða eða vatnsmerki.
pdfjs-editor-alt-text-cancel-button = Hætta við
pdfjs-editor-alt-text-save-button = Vista
pdfjs-editor-alt-text-decorative-tooltip = Merkt sem skraut
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Til dæmis: „Ungur maður sest við borð til að snæða máltíð“
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Alt-myndatexti

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Efst í vinstra horni - breyta stærð
pdfjs-editor-resizer-top-middle =
    .aria-label = Efst á miðju - breyta stærð
pdfjs-editor-resizer-top-right =
    .aria-label = Efst í hægra horni - breyta stærð
pdfjs-editor-resizer-middle-right =
    .aria-label = Miðja til hægri - breyta stærð
pdfjs-editor-resizer-bottom-right =
    .aria-label = Neðst í hægra horni - breyta stærð
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Neðst á miðju - breyta stærð
pdfjs-editor-resizer-bottom-left =
    .aria-label = Neðst í vinstra horni - breyta stærð
pdfjs-editor-resizer-middle-left =
    .aria-label = Miðja til vinstri - breyta stærð

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Áherslulitur
pdfjs-editor-colorpicker-button =
    .title = Skipta um lit
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Val lita
pdfjs-editor-colorpicker-yellow =
    .title = Gult
pdfjs-editor-colorpicker-green =
    .title = Grænt
pdfjs-editor-colorpicker-blue =
    .title = Blátt
pdfjs-editor-colorpicker-pink =
    .title = Bleikt
pdfjs-editor-colorpicker-red =
    .title = Rautt

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Birta allt
pdfjs-editor-highlight-show-all-button =
    .title = Birta allt

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Breyta alt-myndatexta (lýsingu á mynd)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Bæta við alt-myndatexta (lýsingu á mynd)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Skrifaðu lýsinguna þína hér…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Stutt lýsing fyrir fólk sem getur ekki séð myndina eða þegar myndin hleðst ekki inn.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Þessi alt-myndatexti var búinn til sjálfvirkt og gæti verið ónákvæmur.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Kanna nánar
pdfjs-editor-new-alt-text-create-automatically-button-label = Útbúa alt-myndatexta sjálfvirkt
pdfjs-editor-new-alt-text-not-now-button = Ekki núna
pdfjs-editor-new-alt-text-error-title = Gat ekki búið til alt-myndatexta sjálfkrafa
pdfjs-editor-new-alt-text-error-description = Skrifaðu þinn eiginn alt-myndatexta eða reyndu aftur síðar.
pdfjs-editor-new-alt-text-error-close-button = Loka
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Sækir gervigreindarlíkan með alt-myndatextum ({ $downloadedSize } af { $totalSize } MB)
    .aria-valuetext = Sækir gervigreindarlíkan með alt-myndatextum ({ $downloadedSize } af { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Alt-myndatexta bætt við
pdfjs-editor-new-alt-text-added-button-label = Alt-myndatexta bætt við
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Vantar alt-myndatexta
pdfjs-editor-new-alt-text-missing-button-label = Vantar alt-myndatexta
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Yfirfara alt-myndatexta
pdfjs-editor-new-alt-text-to-review-button-label = Yfirfara myndatexta
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Útbúið sjálfvirkt: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Stillingar fyrir alt-texta myndar
pdfjs-image-alt-text-settings-button-label = Stillingar fyrir alt-texta myndar
pdfjs-editor-alt-text-settings-dialog-label = Stillingar fyrir alt-texta myndar
pdfjs-editor-alt-text-settings-automatic-title = Sjálfvirkur alt-myndatexti
pdfjs-editor-alt-text-settings-create-model-button-label = Útbúa alt-myndatexta sjálfvirkt
pdfjs-editor-alt-text-settings-create-model-description = Stingur upp á lýsingum til að hjálpa fólki sem getur ekki séð myndina eða þegar myndin hleðst ekki inn.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Gervigreindarlíkan alt-myndatexta ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Keyrir staðbundið á tækinu þínu svo gögnin þín haldast undir þinni stjórn. Nauðsynlegt fyrir sjálfvirka alt-myndatexta.
pdfjs-editor-alt-text-settings-delete-model-button = Eyða
pdfjs-editor-alt-text-settings-download-model-button = Sækja
pdfjs-editor-alt-text-settings-downloading-model-button = Sæki…
pdfjs-editor-alt-text-settings-editor-title = Ritill fyrir alt-myndatexta
pdfjs-editor-alt-text-settings-show-dialog-button-label = Sýna alt-myndatextaritil strax þegar mynd er bætt við
pdfjs-editor-alt-text-settings-show-dialog-description = Hjálpar þér að tryggja að allar myndirnar þínar séu með alt-myndatexta.
pdfjs-editor-alt-text-settings-close-button = Loka

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-stamp-added-alert = Mynd bætt við
pdfjs-editor-signature-added-alert = Undirritun bætt við

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Áherslulitun fjarlægð
pdfjs-editor-undo-bar-message-freetext = Texti fjarlægður
pdfjs-editor-undo-bar-message-ink = Teikning fjarlægð
pdfjs-editor-undo-bar-message-stamp = Mynd fjarlægð
pdfjs-editor-undo-bar-message-signature = Undirskrift fjarlægð
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } glósa fjarlægð
       *[other] { $count } glósur fjarlægðar
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Afturkalla
pdfjs-editor-undo-bar-undo-button-label = Afturkalla
pdfjs-editor-undo-bar-close-button =
    .title = Loka
pdfjs-editor-undo-bar-close-button-label = Loka

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Þessi gluggi gerir notandanum kleift að búa til undirskrift til að bæta við PDF-skjal. Notandinn getur breytt nafninu (sem einnig þjónar sem alt-texti), og valið að vista undirskriftina til endurtekinnar notkunar.
pdfjs-editor-add-signature-dialog-title = Bæta við undirskrift

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Tegund
    .title = Tegund
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Teikna
    .title = Teikna
pdfjs-editor-add-signature-image-button = Mynd
    .title = Mynd

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Skrifaðu inn undirskriftina þína
    .placeholder = Skrifaðu inn undirskriftina þína
pdfjs-editor-add-signature-draw-placeholder = Teiknaðu undirskriftina þína
pdfjs-editor-add-signature-draw-thickness-range-label = Þykkt
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Sverleiki teikningar: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Dragðu skrá hingað til að senda inn
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Eða skoðaðu myndskrár
       *[other] Eða skoðaðu myndskrár
    }

## Controls

pdfjs-editor-add-signature-description-label = Lýsing (alt-hjálpartexti)
pdfjs-editor-add-signature-description-input =
    .title = Lýsing (alt-hjálpartexti)
pdfjs-editor-add-signature-description-default-when-drawing = Undirskrift
pdfjs-editor-add-signature-clear-button-label = Hreinsa undirskrift
pdfjs-editor-add-signature-clear-button =
    .title = Hreinsa undirskrift
pdfjs-editor-add-signature-save-checkbox = Vista undirskrift
pdfjs-editor-add-signature-save-warning-message = Þú hefur náð hámarki 5 vistaðra undirskrifta. Fjarlægðu eina til að geta vistað fleiri.
pdfjs-editor-add-signature-image-upload-error-title = Ekki tókst að senda inn mynd
pdfjs-editor-add-signature-image-upload-error-description = Athugaðu nettenginguna þína eða prófaðu aðra mynd.
pdfjs-editor-add-signature-image-no-data-error-title = Get ekki breytt þessari mynd í undirskrift
pdfjs-editor-add-signature-image-no-data-error-description = Reyndu að senda inn aðra mynd.
pdfjs-editor-add-signature-error-close-button = Loka

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Hætta við
pdfjs-editor-add-signature-add-button = Bæta við
pdfjs-editor-edit-signature-update-button = Uppfæra

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Aðgerðir
pdfjs-editor-edit-comment-actions-button =
    .title = Aðgerðir
pdfjs-editor-edit-comment-close-button-label = Loka
pdfjs-editor-edit-comment-close-button =
    .title = Loka
pdfjs-editor-edit-comment-actions-edit-button-label = Breyta
pdfjs-editor-edit-comment-actions-delete-button-label = Eyða
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Settu inn athugasemdina þína
pdfjs-editor-edit-comment-manager-cancel-button = Hætta við
pdfjs-editor-edit-comment-manager-save-button = Vista

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Breyta athugasemd

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Fjarlægja vistaða undirskrift
pdfjs-editor-delete-signature-button-label1 = Fjarlægja vistaða undirskrift

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Breyta lýsingu

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Breyta lýsingu
