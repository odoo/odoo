# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = മുമ്പുള്ള താള്‍
pdfjs-previous-button-label = മുമ്പു്
pdfjs-next-button =
    .title = അടുത്ത താള്‍
pdfjs-next-button-label = അടുത്തതു്
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = താള്‍
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = { $pagesCount } ലെ
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pagesCount } ലെ { $pageNumber })
pdfjs-zoom-out-button =
    .title = ചെറുതാക്കുക
pdfjs-zoom-out-button-label = ചെറുതാക്കുക
pdfjs-zoom-in-button =
    .title = വലുതാക്കുക
pdfjs-zoom-in-button-label = വലുതാക്കുക
pdfjs-zoom-select =
    .title = വ്യാപ്തി മാറ്റുക
pdfjs-presentation-mode-button =
    .title = പ്രസന്റേഷന്‍ രീതിയിലേക്കു് മാറ്റുക
pdfjs-presentation-mode-button-label = പ്രസന്റേഷന്‍ രീതി
pdfjs-open-file-button =
    .title = ഫയല്‍ തുറക്കുക
pdfjs-open-file-button-label = തുറക്കുക
pdfjs-print-button =
    .title = അച്ചടിക്കുക
pdfjs-print-button-label = അച്ചടിക്കുക
pdfjs-save-button =
    .title = കരുതിവയ്ക്കുക
pdfjs-save-button-label = കരുതിവയ്ക്കുക
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = ഇറക്കിവയ്ക്കുക
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = ഇറക്കിവയ്ക്കുക
pdfjs-bookmark-button =
    .title = നിലവിലെ താൾ (നിലവിലെ താളിൽ നിന്നു് യൂ.ആർ.എൽ കാണുക)
pdfjs-bookmark-button-label = നിലവിലുള്ള താൾ

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = ഉപകരണങ്ങള്‍
pdfjs-tools-button-label = ഉപകരണങ്ങള്‍
pdfjs-first-page-button =
    .title = ആദ്യത്തെ താളിലേയ്ക്കു് പോകുക
pdfjs-first-page-button-label = ആദ്യത്തെ താളിലേയ്ക്കു് പോകുക
pdfjs-last-page-button =
    .title = അവസാന താളിലേയ്ക്കു് പോകുക
pdfjs-last-page-button-label = അവസാന താളിലേയ്ക്കു് പോകുക
pdfjs-page-rotate-cw-button =
    .title = ഘടികാരദിശയില്‍ കറക്കുക
pdfjs-page-rotate-cw-button-label = ഘടികാരദിശയില്‍ കറക്കുക
pdfjs-page-rotate-ccw-button =
    .title = ഘടികാര ദിശയ്ക്കു് വിപരീതമായി കറക്കുക
pdfjs-page-rotate-ccw-button-label = ഘടികാര ദിശയ്ക്കു് വിപരീതമായി കറക്കുക
pdfjs-cursor-text-select-tool-button =
    .title = ടെക്സ്റ്റ് തിരഞ്ഞെടുക്കൽ ടൂള്‍ പ്രാപ്തമാക്കുക
pdfjs-cursor-text-select-tool-button-label = എഴുത്തു് തിരഞ്ഞെടുക്കൽ കരു
pdfjs-cursor-hand-tool-button =
    .title = കൈക്കരു പ്രാപ്തമാക്കുക
pdfjs-cursor-hand-tool-button-label = കൈക്കരു

## Document properties dialog

pdfjs-document-properties-button =
    .title = രേഖയുടെ വിശേഷതകള്‍...
pdfjs-document-properties-button-label = രേഖയുടെ വിശേഷതകള്‍...
pdfjs-document-properties-file-name = ഫയലിന്റെ പേര്‌:
pdfjs-document-properties-file-size = ഫയലിന്റെ വലിപ്പം:‌‌
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } ബൈറ്റുകൾ)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } ബൈറ്റുകൾ)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } കെബി ({ $size_b } ബൈറ്റുകള്‍)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } എംബി ({ $size_b } ബൈറ്റുകള്‍)
pdfjs-document-properties-title = തലക്കെട്ട്‌
pdfjs-document-properties-author = രചയിതാവ്:
pdfjs-document-properties-subject = വിഷയം:
pdfjs-document-properties-keywords = പെരുമുരികൾ:
pdfjs-document-properties-creation-date = പൂര്‍ത്തിയാകുന്ന തീയതി:
pdfjs-document-properties-modification-date = മാറ്റം വരുത്തിയ തീയതി:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = സൃഷ്ടികര്‍ത്താവ്:
pdfjs-document-properties-producer = പിഡിഎഫ് പ്രൊഡ്യൂസര്‍:
pdfjs-document-properties-version = പിഡിഎഫ് പതിപ്പ്:
pdfjs-document-properties-page-count = താളിന്റെ എണ്ണം:
pdfjs-document-properties-page-size = താൾ വലുപ്പം
pdfjs-document-properties-page-size-unit-inches = ഇഞ്ചു്
pdfjs-document-properties-page-size-unit-millimeters = മില്ലീമീറ്റർ
pdfjs-document-properties-page-size-orientation-portrait = ഛായപടം രീതിയില്‍
pdfjs-document-properties-page-size-orientation-landscape = ഭൂദൃശ്യത്തിന്റെ ആകൃതിയില്‍
pdfjs-document-properties-page-size-name-a-three = ആ 3
pdfjs-document-properties-page-size-name-a-four = ആ 4
pdfjs-document-properties-page-size-name-letter = കത്തു്
pdfjs-document-properties-page-size-name-legal = നിയമപരം

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit } ({ $orientation })
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name },{ $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = വിരവോള ഗോളാന്തരക്കാഴ്ച :
pdfjs-document-properties-linearized-yes = അതെ
pdfjs-document-properties-linearized-no = ഇല്ല
pdfjs-document-properties-close-button = അടയ്ക്കുക

## Print

pdfjs-print-progress-message = അച്ചടിപ്പിനു് പ്രമാണം ഒരുക്കുന്നു...
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = റദ്ദാക്കുക
pdfjs-printing-not-supported = മുന്നറിയിപ്പു്: ഈ അന്വേഷിയന്ത്രമിൽ അച്ചടിപ്പു് മുഴുവനായി പിന്തുണയ്ക്കാരില്ല.
pdfjs-printing-not-ready = മുന്നറിയിപ്പു്: അച്ചടിക്കാനായി ഈ പിഡിഎഫ മൊത്തം ലഭ്യമാക്കിയിട്ടില്ല

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = അണിവക്കം ടോഗിൾ ചെയ്യുക
pdfjs-toggle-sidebar-button-label = അണിവക്കം ടോഗിൾ ചെയ്യുക
pdfjs-document-outline-button =
    .title = ഡോക്യുമെന്റിന്റെ ബാഹ്യരേഖ കാണിക്കുക (എല്ലാ ഇനങ്ങളും വിപുലീകരിക്കാനും ചുരുക്കാനും ഇരട്ട ക്ലിക്കുചെയ്യുക)
pdfjs-document-outline-button-label = രേഖയുടെ ഔട്ട്ലൈന്‍
pdfjs-attachments-button =
    .title = അറ്റാച്മെന്റുകള്‍ കാണിയ്ക്കുക
pdfjs-attachments-button-label = അറ്റാച്മെന്റുകള്‍
pdfjs-layers-button-label = പാളികൾ
pdfjs-thumbs-button =
    .title = തംബ്നെയിലുകള്‍ കാണിയ്ക്കുക
pdfjs-thumbs-button-label = തംബ്നെയിലുകള്‍
pdfjs-findbar-button =
    .title = രേഖയില്‍ കണ്ടുപിടിയ്ക്കുക
pdfjs-findbar-button-label = കണ്ടെത്തുക
pdfjs-additional-layers = കൂടാത്ത പാളികൾ

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = താള്‍ { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = { $page } താളിനുള്ള തംബ്നെയില്‍

## Find panel button title and messages

pdfjs-find-input =
    .title = കണ്ടെത്തുക
    .placeholder = ഡോക്യുമെന്റില്‍ കണ്ടെത്തുക…
pdfjs-find-previous-button =
    .title = വാചകം ഇതിനു മുന്‍പ്‌ ആവര്‍ത്തിച്ചത്‌ കണ്ടെത്തുക
pdfjs-find-previous-button-label = മുമ്പു്
pdfjs-find-next-button =
    .title = വാചകം വീണ്ടും ആവര്‍ത്തിക്കുന്നത്‌ കണ്ടെത്തുക
pdfjs-find-next-button-label = അടുത്തതു്
pdfjs-find-highlight-checkbox = എല്ലാം എടുത്തുകാണിയ്ക്കുക
pdfjs-find-match-case-checkbox-label = അക്ഷരങ്ങള്‍ ഒത്തുനോക്കുക
pdfjs-find-entire-word-checkbox-label = മുഴുവൻ വാക്കുകൾ
pdfjs-find-reached-top = രേഖയുടെ മുകളില്‍ എത്തിയിരിക്കുന്നു, താഴെ നിന്നും തുടരുന്നു
pdfjs-find-reached-bottom = രേഖയുടെ അവസാനം വരെ എത്തിയിരിക്കുന്നു, മുകളില്‍ നിന്നും തുടരുന്നു
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } / { $total } പൊരുത്തങ്ങള്‍
       *[other] { $current } / { $total } പൊരുത്തങ്ങള്‍
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] { $limit } പൊരുത്തങ്ങളില്‍ കൂടുതല്‍
       *[other] { $limit } പൊരുത്തങ്ങളില്‍ കൂടുതല്‍
    }
pdfjs-find-not-found = വാചകം കണ്ടെത്താനായില്ല

## Predefined zoom values

pdfjs-page-scale-width = താളിന്റെ വീതി
pdfjs-page-scale-fit = താള്‍ പാകത്തിനാക്കുക
pdfjs-page-scale-auto = സ്വയമായി വലുതാക്കുക
pdfjs-page-scale-actual = യഥാര്‍ത്ഥ വ്യാപ്തി
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = താള്‍ { $page }

## Loading indicator messages

pdfjs-loading-error = പിഡിഎഫ് ലഭ്യമാക്കുമ്പോള്‍ പിശക് ഉണ്ടായിരിയ്ക്കുന്നു.
pdfjs-invalid-file-error = തെറ്റായ അല്ലെങ്കില്‍ തകരാറുള്ള പിഡിഎഫ് ഫയല്‍.
pdfjs-missing-file-error = പിഡിഎഫ് ഫയല്‍ ലഭ്യമല്ല.
pdfjs-unexpected-response-error = പ്രതീക്ഷിക്കാത്ത സെര്‍വര്‍ മറുപടി.
pdfjs-rendering-error = താള്‍ റെണ്ടര്‍ ചെയ്യുമ്പോള്‍‌ പിശകുണ്ടായിരിയ്ക്കുന്നു.

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
    .alt = [{ $type } Annotation]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = ഈ പിഡിഎഫ് ഫയല്‍ തുറക്കുന്നതിനു് ഒളിവാക്ക് നല്‍കുക.
pdfjs-password-invalid = തെറ്റായ ഒളിവാക്ക്, ദയവായി വീണ്ടും ശ്രമിയ്ക്കുക.
pdfjs-password-ok-button = ശരി
pdfjs-password-cancel-button = റദ്ദാക്കുക
pdfjs-web-fonts-disabled = വെബിനുള്ള അക്ഷരസഞ്ചയങ്ങള്‍ പ്രവര്‍ത്തന രഹിതം: എംബഡ്ഡ് ചെയ്ത പിഡിഎഫ് അക്ഷരസഞ്ചയങ്ങള്‍ ഉപയോഗിയ്ക്കുവാന്‍ സാധ്യമല്ല.

## Editing

pdfjs-editor-free-text-button =
    .title = എഴുത്തു്
pdfjs-editor-free-text-button-label = എഴുത്തു്
pdfjs-editor-ink-button =
    .title = വരയ്ക്കുക
pdfjs-editor-ink-button-label = വരയ്ക്കുക
pdfjs-editor-stamp-button =
    .title = ചിത്രങ്ങളെ ചേർക്കുക അല്ലെങ്കിൽ തിരുത്തുക
pdfjs-editor-stamp-button-label = ചിത്രങ്ങളെ ചേർക്കുക അല്ലെങ്കിൽ തിരുത്തുക
pdfjs-editor-highlight-button =
    .title = അടയാളപ്പെടുക
pdfjs-editor-highlight-button-label = അടയാളപ്പെടുക
pdfjs-highlight-floating-button1 =
    .title = അടയാളപ്പെടുക
    .aria-label = അടയാളപ്പെടുക
pdfjs-highlight-floating-button-label = അടയാളപ്പെടുക
pdfjs-editor-signature-button =
    .title = പുതിയ ഒപ്പു് ചേൎക്കുക
pdfjs-editor-signature-button-label = പുതിയ ഒപ്പു് ചേൎക്കുക

## Default editor aria labels


## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = ആലേഖ്യം മാറ്റുക
pdfjs-editor-remove-freetext-button =
    .title = എഴുത്തു് മാറ്റുക
pdfjs-editor-remove-stamp-button =
    .title = ചിത്രം മാറ്റുക
pdfjs-editor-remove-highlight-button =
    .title = അടയാളപ്പെട്ടുതു് മാറ്റുക
pdfjs-editor-remove-signature-button =
    .title = ഒപ്പു് മാറ്റുക

##

# Editor Parameters
pdfjs-editor-free-text-color-input = നിറം
pdfjs-editor-free-text-size-input = വലുപ്പം
pdfjs-editor-ink-color-input = നിറം
pdfjs-editor-ink-thickness-input = കനം
pdfjs-editor-ink-opacity-input = അതാര്യത
pdfjs-editor-stamp-add-image-button =
    .title = ചിത്രം ചേർക്കുക
pdfjs-editor-stamp-add-image-button-label = ചിത്രം ചേർക്കുക
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = കനം
pdfjs-editor-signature-add-signature-button =
    .title = പുതിയ ഒപ്പു് ചേൎക്കുക
pdfjs-editor-signature-add-signature-button-label = പുതിയ ഒപ്പു് ചേൎക്കുക
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = കരുതിവച്ച ഒപ്പു് : { $description }
pdfjs-free-text-default-content = എഴുതാൻ തുടങ്ങുക…
pdfjs-ink-canvas =
    .aria-label = ഉപയോക്താവ് ഉണ്ടാക്കിയ ചിത്രം

## Alt-text dialog

pdfjs-editor-alt-text-button-label = മറുയെഴുത്തു്
pdfjs-editor-alt-text-edit-button =
    .aria-label = മറുയെഴുത്തു് തിരുത്തുക
pdfjs-editor-alt-text-edit-button-label = മറുയെഴുത്തു് തിരുത്തുക
pdfjs-editor-alt-text-dialog-label = സാധ്യത തിരഞ്ഞെടുക്കൂ
pdfjs-editor-alt-text-add-description-label = ഒരു വിവരണം ചേർക്കുക
pdfjs-editor-alt-text-cancel-button = റദ്ദാക്കുക
pdfjs-editor-alt-text-save-button = കരുതിവയ്ക്കുക
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = ഉദാഹരണം, “ഒരു ചെറുപ്പക്കാരൻ ഭക്ഷണം കഴിക്കാൻ മേശയിലിരുന്നു”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = മറുയെഴുത്തു്

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = ഇടതു മീത്ത മുക്ക് — വലുപ്പം മാറ്റുക
pdfjs-editor-resizer-label-top-middle = നടുവിൽ മീത്ത മുക്ക് - വലുപ്പം മാറ്റുക
pdfjs-editor-resizer-label-top-right = വലതു മീത്ത മുക്ക് — വലുപ്പം മാറ്റുക
pdfjs-editor-resizer-label-middle-right = വലതു നടുവിലുള്ള മുക്ക് — വലുപ്പം മാറ്റുക
pdfjs-editor-resizer-label-bottom-right = വലതു കീഴിലുള്ള മുക്ക് — വലുപ്പം മാറ്റുക
pdfjs-editor-resizer-label-bottom-middle = നടുവെ കീഴിലുള്ള മുക്ക് — വലുപ്പം മാറ്റുക
pdfjs-editor-resizer-label-bottom-left = ഇടതു കീഴിലുള്ള മുക്ക് — വലുപ്പം മാറ്റുക

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = അടയാളന്നിറം
pdfjs-editor-colorpicker-button =
    .title = നിറം മാറ്റുക
pdfjs-editor-colorpicker-dropdown =
    .aria-label = നിറസാധ്യതകൾ
pdfjs-editor-colorpicker-yellow =
    .title = മഞ്ഞ
pdfjs-editor-colorpicker-green =
    .title = പച്ച
pdfjs-editor-colorpicker-blue =
    .title = നീല
pdfjs-editor-colorpicker-pink =
    .title = പാടല
pdfjs-editor-colorpicker-red =
    .title = ചുമന്ന

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = എല്ലാം കാണിക്കുക
pdfjs-editor-highlight-show-all-button =
    .title = എല്ലാം കാണിക്കുക

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = മറുയെഴുത്തു് തിരുത്തുക (ചിത്ര വിവരണം)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = മറുയെഴുത്തു് ചേൎക്കുക (ചിത്ര വിവരണം)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = താങ്ങളുടെ വിവരണം ഇവിടെ എഴുതുക...
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = ഈ മറുയെഴുത്തു് തന്നെതാനെയുണ്ടാക്കിയതുകൊണ്ടു് തെറ്റായതാവാം.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = കൂടുതല്‍ അറിയുക
pdfjs-editor-new-alt-text-create-automatically-button-label = തന്നെതാനെ മറുയെഴുത്തു് ഉണ്ടാക്കുക
pdfjs-editor-new-alt-text-not-now-button = ഇപ്പോഴല്ല
pdfjs-editor-new-alt-text-error-title = തന്നെതാനെ മറുയെഴുത്തു് ഉണ്ടാക്കാൻ പറ്റിയില്ല
pdfjs-editor-new-alt-text-error-description = തനതായ മറുയെഴുത്തു് ഇടുക അല്ലെങ്കിൽ പിന്നീടു് ശ്രമിയ്ക്കുക.
pdfjs-editor-new-alt-text-error-close-button = അടയ്ക്കുക
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = മറുയെഴുത്തു് ചേൎത്തു
pdfjs-editor-new-alt-text-added-button-label = മറുയെഴുത്തു് ചേൎത്തു
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = മറുയെഴുത്തു് കാണാന്നില്ല
pdfjs-editor-new-alt-text-missing-button-label = മറുയെഴുത്തു് കാണാന്നില്ല
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = മറുയെഴുത്തു് അവലോകിക്കുക
pdfjs-editor-new-alt-text-to-review-button-label = മറുയെഴുത്തു് അവലോകിക്കുക
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = തന്നെതാനെ ഉണ്ടാക്കി : { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = ചിത്ര മറുയെഴുത്തു് ക്രമീകരണങ്ങൾ
pdfjs-image-alt-text-settings-button-label = ചിത്ര മറുയെഴുത്തു് ക്രമീകരണങ്ങൾ
pdfjs-editor-alt-text-settings-dialog-label = ചിത്ര മറുയെഴുത്തു് ക്രമീകരണങ്ങൾ
pdfjs-editor-alt-text-settings-automatic-title = യാന്ത്രിക മറുയെഴുത്തു്
pdfjs-editor-alt-text-settings-create-model-button-label = തന്നെതാനെ മറുയെഴുത്തു് ഉണ്ടാക്കുക
pdfjs-editor-alt-text-settings-delete-model-button = മായ്ക്കുക
pdfjs-editor-alt-text-settings-download-model-button = ഇറക്കിവയ്ക്കുക
pdfjs-editor-alt-text-settings-downloading-model-button = ഇറക്കിവയ്ക്കുന്നു
pdfjs-editor-alt-text-settings-show-dialog-description = താങ്ങളുടെ എല്ലാ പടങ്ങളിലും മറുയെഴുത്തുണ്ടെന്നു് തീൎച്ചപ്പെടുത്താൻ തുണയ്ക്കുന്നു.
pdfjs-editor-alt-text-settings-close-button = അടയ്ക്കുക

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = അടയാളം മാറ്റി
pdfjs-editor-undo-bar-message-freetext = എഴുത്തു് മാറ്റി
pdfjs-editor-undo-bar-message-ink = ആലേഖ്യം മാറ്റി
pdfjs-editor-undo-bar-message-stamp = ചിത്രം മാറ്റി
pdfjs-editor-undo-bar-message-signature = ഒപ്പു് മാറ്റി
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } കുറിപ്പെഴുതലുകൾ മാറ്റി
       *[other] { $count } കുറിപ്പെഴുതലുകൾ മാറ്റി
    }
pdfjs-editor-undo-bar-undo-button =
    .title = പഴയപോലെയാക്കുക
pdfjs-editor-undo-bar-undo-button-label = പഴയപോലെയാക്കുക
pdfjs-editor-undo-bar-close-button =
    .title = അടയ്ക്കുക
pdfjs-editor-undo-bar-close-button-label = അടയ്ക്കുക

## Add a signature dialog

pdfjs-editor-add-signature-dialog-title = ഒപ്പു് ചേൎക്കുക

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = തരം
    .title = തരം
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = വരയ്ക്കുക
    .title = വരയ്ക്കുക
pdfjs-editor-add-signature-image-button = ചിത്രം
    .title = ചിത്രം

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = താങ്ങളുടെ ഒപ്പു് ഇവിടെ എഴുതുക
    .placeholder = താങ്ങളുടെ ഒപ്പു് ഇവിടെ എഴുതുക
pdfjs-editor-add-signature-draw-placeholder = താങ്ങളുടെ ഒപ്പു് വരയ്ക്കുക
pdfjs-editor-add-signature-draw-thickness-range-label = കനം
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = വരപ്പുകനം: { $thickness }
pdfjs-editor-add-signature-image-placeholder = കയറ്റുവയ്ക്കാൻ വേണ്ടി ഫയലിനു് ഇവിടോട്ടു് വലിച്ചിടുക
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] അല്ലെങ്കിൽ ചിത്രം ഫയലുകൾ തപ്പുക
       *[other] അല്ലെങ്കിൽ ചിത്രം ഫയലുകൾ തപ്പുക
    }

## Controls

pdfjs-editor-add-signature-description-label = വിവരണം (ഇതരയെഴുതു്)
pdfjs-editor-add-signature-description-input =
    .title = വിവരണം (ഇതരയെഴുതു്)
pdfjs-editor-add-signature-description-default-when-drawing = ഒപ്പു്
pdfjs-editor-add-signature-clear-button-label = ഒപ്പു് മായ്ക്കുക
pdfjs-editor-add-signature-clear-button =
    .title = ഒപ്പു് മായ്ക്കുക
pdfjs-editor-add-signature-save-checkbox = ഒപ്പു് കരുതിവയ്ക്കുക
pdfjs-editor-add-signature-save-warning-message = താങ്ങളുടെ ഒപ്പുകളുടെ എണ്ണം 5 ആയി. കൂടുതൽ കരുതിവയ്ക്കാൻ വേണ്ടി ഒരെണ്ണം മാറ്റണ്ടിവരും.
pdfjs-editor-add-signature-image-upload-error-title = ചിത്രം കയറ്റുവയ്ക്കാൻ പറ്റിയില്ല
pdfjs-editor-add-signature-image-upload-error-description = താങ്ങളുടെ ശൃംഖല സമ്പൎക്കം പരിശോധിക്കുക അല്ലെങ്കിൽ വേറെയൊരു ചിത്രം ഇട്ടുനോക്കുക
pdfjs-editor-add-signature-error-close-button = അടയ്ക്കുക

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = റദ്ദാക്കുക
pdfjs-editor-add-signature-add-button = ചേൎക്കുക
pdfjs-editor-edit-signature-update-button = പുതുക്കുക

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = കരുതിവച്ച ഒപ്പു് മാറ്റുക
pdfjs-editor-delete-signature-button-label1 = കരുതിവച്ച ഒപ്പു് മാറ്റുക

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = വിവരണം തിരുത്തുക

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = വിവരണം തിരുത്തുക
