# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Kuatiarogue mboyvegua
pdfjs-previous-button-label = Mboyvegua
pdfjs-next-button =
    .title = Kuatiarogue upeigua
pdfjs-next-button-label = Upeigua
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Kuatiarogue
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = { $pagesCount } gui
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } of { $pagesCount })
pdfjs-zoom-out-button =
    .title = Momichĩ
pdfjs-zoom-out-button-label = Momichĩ
pdfjs-zoom-in-button =
    .title = Mbotuicha
pdfjs-zoom-in-button-label = Mbotuicha
pdfjs-zoom-select =
    .title = Tuichakue
pdfjs-presentation-mode-button =
    .title = Jehechauka reko moambue
pdfjs-presentation-mode-button-label = Jehechauka reko
pdfjs-open-file-button =
    .title = Marandurendápe jeike
pdfjs-open-file-button-label = Jeike
pdfjs-print-button =
    .title = Monguatia
pdfjs-print-button-label = Monguatia
pdfjs-save-button =
    .title = Ñongatu
pdfjs-save-button-label = Ñongatu
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Mboguejy
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Mboguejy
pdfjs-bookmark-button =
    .title = Kuatiarogue ag̃agua (Ehecha URL kuatiarogue ag̃agua)
pdfjs-bookmark-button-label = Kuatiarogue Ag̃agua

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Tembiporu
pdfjs-tools-button-label = Tembiporu
pdfjs-first-page-button =
    .title = Kuatiarogue ñepyrũme jeho
pdfjs-first-page-button-label = Kuatiarogue ñepyrũme jeho
pdfjs-last-page-button =
    .title = Kuatiarogue pahápe jeho
pdfjs-last-page-button-label = Kuatiarogue pahápe jeho
pdfjs-page-rotate-cw-button =
    .title = Aravóicha mbojere
pdfjs-page-rotate-cw-button-label = Aravóicha mbojere
pdfjs-page-rotate-ccw-button =
    .title = Aravo rapykue gotyo mbojere
pdfjs-page-rotate-ccw-button-label = Aravo rapykue gotyo mbojere
pdfjs-cursor-text-select-tool-button =
    .title = Emyandy moñe’ẽrã jeporavo rembiporu
pdfjs-cursor-text-select-tool-button-label = Moñe’ẽrã jeporavo rembiporu
pdfjs-cursor-hand-tool-button =
    .title = Tembiporu po pegua myandy
pdfjs-cursor-hand-tool-button-label = Tembiporu po pegua
pdfjs-scroll-page-button =
    .title = Eiporu kuatiarogue jeku’e
pdfjs-scroll-page-button-label = Kuatiarogue jeku’e
pdfjs-scroll-vertical-button =
    .title = Eiporu jeku’e ykeguáva
pdfjs-scroll-vertical-button-label = Jeku’e ykeguáva
pdfjs-scroll-horizontal-button =
    .title = Eiporu jeku’e yvate gotyo
pdfjs-scroll-horizontal-button-label = Jeku’e yvate gotyo
pdfjs-scroll-wrapped-button =
    .title = Eiporu jeku’e mbohyrupyre
pdfjs-scroll-wrapped-button-label = Jeku’e mbohyrupyre
pdfjs-spread-none-button =
    .title = Ani ejuaju spreads kuatiarogue ndive
pdfjs-spread-none-button-label = Spreads ỹre
pdfjs-spread-odd-button =
    .title = Embojuaju kuatiarogue jepysokue eñepyrũvo kuatiarogue impar-vagui
pdfjs-spread-odd-button-label = Spreads impar
pdfjs-spread-even-button =
    .title = Embojuaju kuatiarogue jepysokue eñepyrũvo kuatiarogue par-vagui
pdfjs-spread-even-button-label = Ipukuve uvei

## Document properties dialog

pdfjs-document-properties-button =
    .title = Kuatia mba’etee…
pdfjs-document-properties-button-label = Kuatia mba’etee…
pdfjs-document-properties-file-name = Marandurenda réra:
pdfjs-document-properties-file-size = Marandurenda tuichakue:
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
pdfjs-document-properties-title = Teratee:
pdfjs-document-properties-author = Apohára:
pdfjs-document-properties-subject = Mba’egua:
pdfjs-document-properties-keywords = Jehero:
pdfjs-document-properties-creation-date = Teñoihague arange:
pdfjs-document-properties-modification-date = Iñambue hague arange:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Apo’ypyha:
pdfjs-document-properties-producer = PDF mbosako’iha:
pdfjs-document-properties-version = PDF mbojuehegua:
pdfjs-document-properties-page-count = Kuatiarogue papapy:
pdfjs-document-properties-page-size = Kuatiarogue tuichakue:
pdfjs-document-properties-page-size-unit-inches = Amo
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = Oĩháicha
pdfjs-document-properties-page-size-orientation-landscape = apaisado
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Kuatiañe’ẽ
pdfjs-document-properties-page-size-name-legal = Tee

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
pdfjs-document-properties-linearized = Ñanduti jahecha pya’e:
pdfjs-document-properties-linearized-yes = Añete
pdfjs-document-properties-linearized-no = Ahániri
pdfjs-document-properties-close-button = Mboty

## Print

pdfjs-print-progress-message = Embosako’i kuatia emonguatia hag̃ua…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Heja
pdfjs-printing-not-supported = Kyhyjerã: Ñembokuatia ndojokupytypái ko kundahára ndive.
pdfjs-printing-not-ready = Kyhyjerã: Ko PDF nahenyhẽmbái oñembokuatia hag̃uáicha.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Tenda yke moambue
pdfjs-toggle-sidebar-notification-button =
    .title = Embojopyru tenda ykegua (kuatia oguereko kuaakaha/moirũha/ñuãha)
pdfjs-toggle-sidebar-button-label = Tenda yke moambue
pdfjs-document-outline-button =
    .title = Ehechauka kuatia rape (eikutu mokõi jey embotuicha/emomichĩ hag̃ua opavavete mba’eporu)
pdfjs-document-outline-button-label = Kuatia apopyre
pdfjs-attachments-button =
    .title = Moirũha jehechauka
pdfjs-attachments-button-label = Moirũha
pdfjs-layers-button =
    .title = Ehechauka ñuãha (eikutu jo’a emomba’apo hag̃ua opaite ñuãha tekoypýpe)
pdfjs-layers-button-label = Ñuãha
pdfjs-thumbs-button =
    .title = Mba’emirĩ jehechauka
pdfjs-thumbs-button-label = Mba’emirĩ
pdfjs-current-outline-item-button =
    .title = Eheka mba’eporu ag̃aguaitéva
pdfjs-current-outline-item-button-label = Mba’eporu ag̃aguaitéva
pdfjs-findbar-button =
    .title = Kuatiápe jeheka
pdfjs-findbar-button-label = Juhu
pdfjs-additional-layers = Ñuãha moirũguáva

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Kuatiarogue { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Kuatiarogue mba’emirĩ { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Juhu
    .placeholder = Kuatiápe jejuhu…
pdfjs-find-previous-button =
    .title = Ejuhu ñe’ẽrysýi osẽ’ypy hague
pdfjs-find-previous-button-label = Mboyvegua
pdfjs-find-next-button =
    .title = Eho ñe’ẽ juhupyre upeiguávape
pdfjs-find-next-button-label = Upeigua
pdfjs-find-highlight-checkbox = Embojekuaavepa
pdfjs-find-match-case-checkbox-label = Ejesareko taiguasu/taimichĩre
pdfjs-find-match-diacritics-checkbox-label = Diacrítico moñondive
pdfjs-find-entire-word-checkbox-label = Ñe’ẽ oĩmbáva
pdfjs-find-reached-top = Ojehupyty kuatia ñepyrũ, oku’ejeýta kuatia paha guive
pdfjs-find-reached-bottom = Ojehupyty kuatia paha, oku’ejeýta kuatia ñepyrũ guive
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } ha { $total } ojueheguáva
       *[other] { $current } ha { $total } ojueheguáva
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Hetave { $limit } ojueheguáva
       *[other] Hetave { $limit } ojueheguáva
    }
pdfjs-find-not-found = Ñe’ẽrysýi ojejuhu’ỹva

## Predefined zoom values

pdfjs-page-scale-width = Kuatiarogue pekue
pdfjs-page-scale-fit = Kuatiarogue ñemoĩporã
pdfjs-page-scale-auto = Tuichakue ijeheguíva
pdfjs-page-scale-actual = Tuichakue ag̃agua
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Kuatiarogue { $page }

## Loading indicator messages

pdfjs-loading-error = Oiko jejavy PDF oñemyeñyhẽnguévo.
pdfjs-invalid-file-error = PDF marandurenda ndoikóiva térã ivaipyréva.
pdfjs-missing-file-error = Ndaipóri PDF marandurenda
pdfjs-unexpected-response-error = Mohendahavusu mbohovái eha’ãrõ’ỹva.
pdfjs-rendering-error = Oiko jejavy ehechaukasévo kuatiarogue.

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
    .alt = [Jehaipy { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Emoinge ñe’ẽñemi eipe’a hag̃ua ko marandurenda PDF.
pdfjs-password-invalid = Ñe’ẽñemi ndoikóiva. Eha’ã jey.
pdfjs-password-ok-button = MONEĨ
pdfjs-password-cancel-button = Heja
pdfjs-web-fonts-disabled = Ñanduti taity oñemongéma: ndaikatumo’ãi eiporu PDF jehai’íva taity.

## Editing

pdfjs-editor-free-text-button =
    .title = Moñe’ẽrã
pdfjs-editor-color-picker-free-text-input =
    .title = Emoambue moñe’ẽrã sa’y
pdfjs-editor-free-text-button-label = Moñe’ẽrã
pdfjs-editor-ink-button =
    .title = Moha’ãnga
pdfjs-editor-color-picker-ink-input =
    .title = Emoambue ta’ãnga sa’y
pdfjs-editor-ink-button-label = Moha’ãnga
pdfjs-editor-stamp-button =
    .title = Embojuaju térã embosako’i ta’ãnga
pdfjs-editor-stamp-button-label = Embojuaju térã embosako’i ta’ãnga
pdfjs-editor-highlight-button =
    .title = Mbosa’y
pdfjs-editor-highlight-button-label = Mbosa’y
pdfjs-highlight-floating-button1 =
    .title = Mbosa’y
    .aria-label = Mbosa’y
pdfjs-highlight-floating-button-label = Mbosa’y
pdfjs-comment-floating-button =
    .title = Je’erei
    .aria-label = Je’erei
pdfjs-comment-floating-button-label = Je’erei
pdfjs-editor-signature-button =
    .title = Embojuaju teraguapy
pdfjs-editor-signature-button-label = Embojuaju teraguapy

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Jehechaukarã mbosako’iha
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Ta’ãnga’apo moheñoiha
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Teraguapy mbosako’iha: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Ta’ãnga mbosako’iha

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Emboguete ta’ãnga
pdfjs-editor-remove-freetext-button =
    .title = Emboguete moñe’ẽrã
pdfjs-editor-remove-stamp-button =
    .title = Emboguete ta’ãnga
pdfjs-editor-remove-highlight-button =
    .title = Eipe’a jehechaveha
pdfjs-editor-remove-signature-button =
    .title = Embogue teraguapy

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Sa’y
pdfjs-editor-free-text-size-input = Tuichakue
pdfjs-editor-ink-color-input = Sa’y
pdfjs-editor-ink-thickness-input = Anambusu
pdfjs-editor-ink-opacity-input = Pytũngy
pdfjs-editor-stamp-add-image-button =
    .title = Embojuaju ta’ãnga
pdfjs-editor-stamp-add-image-button-label = Embojuaju ta’ãnga
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Anambusu
pdfjs-editor-free-highlight-thickness-title =
    .title = Emoambue anambusukue embosa’ývo mba’eporu ha’e’ỹva moñe’ẽrã
pdfjs-editor-add-signature-container =
    .aria-label = Teraguapy ñemaña ha teraguapy ñongatupyre
pdfjs-editor-signature-add-signature-button =
    .title = Embojuaju teraguapy pyahu
pdfjs-editor-signature-add-signature-button-label = Embojuaju teraguapy pyahu
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Teraguapy ñongatupyre: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Moñe’ẽrã moheñoiha
    .default-content = Eñepyrũ ehai…
pdfjs-free-text =
    .aria-label = Moñe’ẽrã moheñoiha
pdfjs-free-text-default-content = Ehai ñepyrũ…
pdfjs-ink =
    .aria-label = Ta’ãnga moheñoiha
pdfjs-ink-canvas =
    .aria-label = Ta’ãnga omoheñóiva poruhára

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Moñe’ẽrã mokõiháva
pdfjs-editor-alt-text-edit-button =
    .aria-label = Embojuruja moñe’ẽrã mokõiháva
pdfjs-editor-alt-text-edit-button-label = Embojuruja moñe’ẽrã mokõiháva
pdfjs-editor-alt-text-dialog-label = Eiporavo poravorã
pdfjs-editor-alt-text-dialog-description = Moñe’ẽrã ykepegua (moñe’ẽrã ykepegua) nepytyvõ nderehecháiramo ta’ãnga térã nahenyhẽiramo.
pdfjs-editor-alt-text-add-description-label = Embojuaju ñemoha’ãnga
pdfjs-editor-alt-text-add-description-description = Ehaimi 1 térã 2 ñe’ẽjuaju oñe’ẽva pe téma rehe, ijere térã mba’eapóre.
pdfjs-editor-alt-text-mark-decorative-label = Emongurusu jeguakárõ
pdfjs-editor-alt-text-mark-decorative-description = Ojeporu ta’ãnga jeguakarã, tembe’y térã ta’ãnga ruguarãramo.
pdfjs-editor-alt-text-cancel-button = Heja
pdfjs-editor-alt-text-save-button = Ñongatu
pdfjs-editor-alt-text-decorative-tooltip = Jeguakárõ mongurusupyre
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Techapyrã: “Peteĩ mitãrusu oguapy mesápe okaru hag̃ua”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Moñe’ẽrã mokõiháva

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Yvate asu gotyo — emoambue tuichakue
pdfjs-editor-resizer-label-top-middle = Yvate mbytépe — emoambue tuichakue
pdfjs-editor-resizer-label-top-right = Yvate akatúape — emoambue tuichakue
pdfjs-editor-resizer-label-middle-right = Mbyte akatúape — emoambue tuichakue
pdfjs-editor-resizer-label-bottom-right = Yvy gotyo akatúape — emoambue tuichakue
pdfjs-editor-resizer-label-bottom-middle = Yvy gotyo mbytépe — emoambue tuichakue
pdfjs-editor-resizer-label-bottom-left = Iguýpe asu gotyo — emoambue tuichakue
pdfjs-editor-resizer-label-middle-left = Mbyte asu gotyo — emoambue tuichakue
pdfjs-editor-resizer-top-left =
    .aria-label = Yvate asu gotyo — emoambue tuichakue
pdfjs-editor-resizer-top-middle =
    .aria-label = Yvate mbytépe — emoambue tuichakue
pdfjs-editor-resizer-top-right =
    .aria-label = Yvate akatúape — emoambue tuichakue
pdfjs-editor-resizer-middle-right =
    .aria-label = Mbyte akatúape — emoambue tuichakue
pdfjs-editor-resizer-bottom-right =
    .aria-label = Yvy gotyo akatúape — emoambue tuichakue
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Yvy gotyo mbytépe — emoambue tuichakue
pdfjs-editor-resizer-bottom-left =
    .aria-label = Iguýpe asu gotyo — emoambue tuichakue
pdfjs-editor-resizer-middle-left =
    .aria-label = Mbyte asu gotyo — emoambue tuichakue

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Jehechaveha sa’y
pdfjs-editor-colorpicker-button =
    .title = Emoambue sa’y
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Sa’y poravopyrã
pdfjs-editor-colorpicker-yellow =
    .title = Sa’yju
pdfjs-editor-colorpicker-green =
    .title = Hovyũ
pdfjs-editor-colorpicker-blue =
    .title = Hovy
pdfjs-editor-colorpicker-pink =
    .title = Pytãngy
pdfjs-editor-colorpicker-red =
    .title = Pyha

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Techaukapa
pdfjs-editor-highlight-show-all-button =
    .title = Techaukapa

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Embosako’i moñe’ẽrã mokõiha (ta’ãngáre ñeñe’ẽ)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Embojuaju moñe’ẽrã mokõiha (ta’ãngáre ñeñe’ẽ)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Edescribi ko’ápe…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Ñemyesakã mbykymi opavave ohecha’ỹva upe ta’ãnga térã pe ta’ãnga nahenyhẽiramo.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ko moñe’ẽrã mokõiha oñemoheñói ijehegui ha ikatu ndoikoporãi.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Eikuaave
pdfjs-editor-new-alt-text-create-automatically-button-label = Emoheñói moñe’ẽrã mokõiha ijeheguíva
pdfjs-editor-new-alt-text-not-now-button = Ani ko’ág̃a
pdfjs-editor-new-alt-text-error-title = Noñemoheñói moñe’ẽrã mokõiha ijeheguíva
pdfjs-editor-new-alt-text-error-description = Ehai ne moñe’ẽrã mokõiha térã eha’ã jey ag̃amieve.
pdfjs-editor-new-alt-text-error-close-button = Mboty
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Emboguejyhína IA moñe’ẽrã mokõiháva ({ $downloadedSize } { $totalSize } MB) mba’e
    .aria-valuetext = Emboguejyhína IA moñe’ẽrã mokõiháva ({ $downloadedSize } { $totalSize } MB) mba’e
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Moñe’ẽrã mokõiha mbojuajupyre
pdfjs-editor-new-alt-text-added-button-label = Oñembojuaju moñe’ẽrã mokõiha
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Ndaipóri moñe’ẽrã mokõiha
pdfjs-editor-new-alt-text-missing-button-label = Ndaipóri moñe’ẽrã mokõiha
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Ehechajey moñe’ẽrã mokõiha
pdfjs-editor-new-alt-text-to-review-button-label = Ehechajey moñe’ẽrã mokõiha
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Heñóiva ijeheguiete: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Ta’ãnga moñe’ẽrã mokõiha ñemboheko
pdfjs-image-alt-text-settings-button-label = Ta’ãnga moñe’ẽrã mokõiha ñemboheko
pdfjs-editor-alt-text-settings-dialog-label = Ta’ãnga moñe’ẽrã mokõiha ñemboheko
pdfjs-editor-alt-text-settings-automatic-title = Moñe’ẽrã mokõiha ijeheguíva
pdfjs-editor-alt-text-settings-create-model-button-label = Emoheñói moñe’ẽrã mokõiha ijeheguíva
pdfjs-editor-alt-text-settings-create-model-description = Ñemyesakã mbykymi opavave tapicha ohecha’ỹva upe ta’ãnga térã pe ta’ãnga nahenyhẽiramo.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Peteĩva IA moñe’ẽrã mokõiha ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Oku’e mba’e’okaitépe umi mba’ekuaarã hekoñemi hag̃ua. Tekotevẽva moñe’ẽrã ykegua ijeheguívape.
pdfjs-editor-alt-text-settings-delete-model-button = Mboguete
pdfjs-editor-alt-text-settings-download-model-button = Mboguejy
pdfjs-editor-alt-text-settings-downloading-model-button = Emboguejyhína…
pdfjs-editor-alt-text-settings-editor-title = Moñe’ẽrã mokõiha mbosako’iha
pdfjs-editor-alt-text-settings-show-dialog-button-label = Ehechauka moñe’ẽrã mokõiha mbosako’iha embojuajúvo ta’ãnga
pdfjs-editor-alt-text-settings-show-dialog-description = Nepytyvõta ta’ãngakuéra orekotaha moñe’ẽrã mokõiha.
pdfjs-editor-alt-text-settings-close-button = Mboty

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Techaukarã juajupyre
pdfjs-editor-freetext-added-alert = Moñe’ẽrã juajupyre
pdfjs-editor-ink-added-alert = Ta’ãnga juajupyre
pdfjs-editor-stamp-added-alert = Ta’ãnga juajupyre
pdfjs-editor-signature-added-alert = Teraguapy juajupyre

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Mbosa’ýva mboguete
pdfjs-editor-undo-bar-message-freetext = Moñe’ẽrã mboguepyre
pdfjs-editor-undo-bar-message-ink = Ta’ãnga mboguepyre
pdfjs-editor-undo-bar-message-stamp = Ta’ãnga mboguepyre
pdfjs-editor-undo-bar-message-signature = Teraguapy mboguepyre
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } jehaikue mboguepyre
       *[other] { $count } jehaikue mboguepyre
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Mboguevi
pdfjs-editor-undo-bar-undo-button-label = Mboguevi
pdfjs-editor-undo-bar-close-button =
    .title = Mboty
pdfjs-editor-undo-bar-close-button-label = Mboty

## Add a signature dialog

pdfjs-editor-add-signature-dialog-title = Embojuaju teraguapy

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Jehai
    .title = Jehai
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Moha’ãnga
    .title = Moha’ãnga
pdfjs-editor-add-signature-image-button = Ta’ãnga
    .title = Ta’ãnga

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Ehai nde reraguapy
    .placeholder = Ehai nde reraguapy
pdfjs-editor-add-signature-draw-placeholder = Emoha’ãnga nde reraguapy
pdfjs-editor-add-signature-draw-thickness-range-label = Anambusu
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Ta’ãnga anambusukue: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Egueru marandurenda ápe ehupi hag̃ua
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Eiporavo ta’ãnga marandurenda
       *[other] Eiporavo ta’ãnga marandurenda
    }

## Controls

pdfjs-editor-add-signature-description-label = Moha’ãnga (moñe’ẽrã ykepegua)
pdfjs-editor-add-signature-description-input =
    .title = Moha’ãnga (moñe’ẽrã ykepegua)
pdfjs-editor-add-signature-description-default-when-drawing = Teraguapy
pdfjs-editor-add-signature-clear-button-label = Emboguete teraguapy
pdfjs-editor-add-signature-clear-button =
    .title = Emboguete teraguapy
pdfjs-editor-add-signature-save-checkbox = Eñongatu teraguapy
pdfjs-editor-add-signature-save-warning-message = Ehupytýma 5 mboheraguapy ñongatupyre. Embogue peteĩ eñongatukuaa jey hag̃ua.
pdfjs-editor-add-signature-image-upload-error-title = Ndaikatúi ojehupi pe ta’ãnga
pdfjs-editor-add-signature-image-upload-error-description = Ehechajey ne ñanduti oikópa térã aha’ã ambue ta’ãnga ndive.
pdfjs-editor-add-signature-image-no-data-error-title = Ndaikatúi ejapo ko ta’ãngágui teraguapy
pdfjs-editor-add-signature-image-no-data-error-description = Eñeha’ãkena ehupi ambuéva ta’ãnga.
pdfjs-editor-add-signature-error-close-button = Mboty

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Heja
pdfjs-editor-add-signature-add-button = Mbojuaju
pdfjs-editor-edit-signature-update-button = Mbohekopyahu

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Ñemongu’e
pdfjs-editor-edit-comment-actions-button =
    .title = Ñemongu’e
pdfjs-editor-edit-comment-close-button-label = Mboty
pdfjs-editor-edit-comment-close-button =
    .title = Mboty
pdfjs-editor-edit-comment-actions-edit-button-label = Mbosako’i
pdfjs-editor-edit-comment-actions-delete-button-label = Mboguete
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Ehai peteĩ je’erei
pdfjs-editor-edit-comment-manager-cancel-button = Heja
pdfjs-editor-edit-comment-manager-save-button = Ñongatu

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Je’erei mbosako’i

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Embogue teraguapy ñongatupyre
pdfjs-editor-delete-signature-button-label1 = Embogue teraguapy ñongatupyre

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Embosako’i moha’ãnga

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Embosako’i moha’ãnga
