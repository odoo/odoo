# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = წინა გვერდი
pdfjs-previous-button-label = წინა
pdfjs-next-button =
    .title = შემდეგი გვერდი
pdfjs-next-button-label = შემდეგი
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = გვერდი
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = { $pagesCount }-დან
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } { $pagesCount }-დან)
pdfjs-zoom-out-button =
    .title = ზომის შემცირება
pdfjs-zoom-out-button-label = დაშორება
pdfjs-zoom-in-button =
    .title = ზომის გაზრდა
pdfjs-zoom-in-button-label = მოახლოება
pdfjs-zoom-select =
    .title = ზომა
pdfjs-presentation-mode-button =
    .title = წარდგენის რეჟიმზე გადართვა
pdfjs-presentation-mode-button-label = წარდგენის რეჟიმი
pdfjs-open-file-button =
    .title = ფაილის გახსნა
pdfjs-open-file-button-label = გახსნა
pdfjs-print-button =
    .title = ამობეჭდვა
pdfjs-print-button-label = ამობეჭდვა
pdfjs-save-button =
    .title = შენახვა
pdfjs-save-button-label = შენახვა
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = ჩამოტვირთვა
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = ჩამოტვირთვა
pdfjs-bookmark-button =
    .title = მიმდინარე გვერდი (ბმული ამ გვერდისთვის)
pdfjs-bookmark-button-label = მიმდინარე გვერდი

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = ხელსაწყოები
pdfjs-tools-button-label = ხელსაწყოები
pdfjs-first-page-button =
    .title = პირველ გვერდზე გადასვლა
pdfjs-first-page-button-label = პირველ გვერდზე გადასვლა
pdfjs-last-page-button =
    .title = ბოლო გვერდზე გადასვლა
pdfjs-last-page-button-label = ბოლო გვერდზე გადასვლა
pdfjs-page-rotate-cw-button =
    .title = საათის ისრის მიმართულებით შებრუნება
pdfjs-page-rotate-cw-button-label = მარჯვნივ გადაბრუნება
pdfjs-page-rotate-ccw-button =
    .title = საათის ისრის საპირისპიროდ შებრუნება
pdfjs-page-rotate-ccw-button-label = მარცხნივ გადაბრუნება
pdfjs-cursor-text-select-tool-button =
    .title = მოსანიშნი მაჩვენებლის გამოყენება
pdfjs-cursor-text-select-tool-button-label = მოსანიშნი მაჩვენებელი
pdfjs-cursor-hand-tool-button =
    .title = გადასაადგილებელი მაჩვენებლის გამოყენება
pdfjs-cursor-hand-tool-button-label = გადასაადგილებელი
pdfjs-scroll-page-button =
    .title = გვერდზე გადაადგილების გამოყენება
pdfjs-scroll-page-button-label = გვერდშივე გადაადგილება
pdfjs-scroll-vertical-button =
    .title = გვერდების შვეულად ჩვენება
pdfjs-scroll-vertical-button-label = შვეული გადაადგილება
pdfjs-scroll-horizontal-button =
    .title = გვერდების თარაზულად ჩვენება
pdfjs-scroll-horizontal-button-label = განივი გადაადგილება
pdfjs-scroll-wrapped-button =
    .title = გვერდების ცხრილურად ჩვენება
pdfjs-scroll-wrapped-button-label = ცხრილური გადაადგილება
pdfjs-spread-none-button =
    .title = ორ გვერდზე გაშლის გარეშე
pdfjs-spread-none-button-label = ცალგვერდიანი ჩვენება
pdfjs-spread-odd-button =
    .title = ორ გვერდზე გაშლა კენტი გვერდიდან
pdfjs-spread-odd-button-label = ორ გვერდზე კენტიდან
pdfjs-spread-even-button =
    .title = ორ გვერდზე გაშლა ლუწი გვერდიდან
pdfjs-spread-even-button-label = ორ გვერდზე ლუწიდან

## Document properties dialog

pdfjs-document-properties-button =
    .title = დოკუმენტის შესახებ…
pdfjs-document-properties-button-label = დოკუმენტის შესახებ…
pdfjs-document-properties-file-name = ფაილის სახელი:
pdfjs-document-properties-file-size = ფაილის მოცულობა:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } კბაიტი ({ $b } ბაიტი)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } მბაიტი ({ $b } ბაიტი)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } კბ ({ $size_b } ბაიტი)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } მბ ({ $size_b } ბაიტი)
pdfjs-document-properties-title = სათაური:
pdfjs-document-properties-author = შემქმნელი:
pdfjs-document-properties-subject = თემა:
pdfjs-document-properties-keywords = საკვანძო სიტყვები:
pdfjs-document-properties-creation-date = შექმნის დრო:
pdfjs-document-properties-modification-date = ჩასწორების დრო:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = შემდგენელი:
pdfjs-document-properties-producer = PDF-შემდგენელი:
pdfjs-document-properties-version = PDF-ვერსია:
pdfjs-document-properties-page-count = გვერდები:
pdfjs-document-properties-page-size = გვერდის ზომა:
pdfjs-document-properties-page-size-unit-inches = დუიმი
pdfjs-document-properties-page-size-unit-millimeters = მმ
pdfjs-document-properties-page-size-orientation-portrait = შვეულად
pdfjs-document-properties-page-size-orientation-landscape = თარაზულად
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
pdfjs-document-properties-linearized = მსუბუქი ვებჩვენება:
pdfjs-document-properties-linearized-yes = დიახ
pdfjs-document-properties-linearized-no = არა
pdfjs-document-properties-close-button = დახურვა

## Print

pdfjs-print-progress-message = დოკუმენტი მზადდება ამოსაბეჭდად…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = გაუქმება
pdfjs-printing-not-supported = გაფრთხილება: ამობეჭდვა ამ ბრაუზერში არაა სრულად მხარდაჭერილი.
pdfjs-printing-not-ready = გაფრთხილება: PDF სრულად ჩატვირთული არაა, ამობეჭდვის დასაწყებად.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = გვერდითა ზოლის გამოჩენა/დამალვა
pdfjs-toggle-sidebar-notification-button =
    .title = გვერდითი ზოლის გამოჩენა (შეიცავს სარჩევს/დანართს/შრეებს)
pdfjs-toggle-sidebar-button-label = გვერდითა ზოლის გამოჩენა/დამალვა
pdfjs-document-outline-button =
    .title = დოკუმენტის სარჩევის ჩვენება (ორმაგი წკაპით თითოეულის ჩამოშლა/აკეცვა)
pdfjs-document-outline-button-label = დოკუმენტის სარჩევი
pdfjs-attachments-button =
    .title = დანართების ჩვენება
pdfjs-attachments-button-label = დანართები
pdfjs-layers-button =
    .title = შრეების გამოჩენა (ორმაგი წკაპით ყველა შრის ნაგულისხმევზე დაბრუნება)
pdfjs-layers-button-label = შრეები
pdfjs-thumbs-button =
    .title = შეთვალიერება
pdfjs-thumbs-button-label = ესკიზები
pdfjs-current-outline-item-button =
    .title = მიმდინარე გვერდის მონახვა სარჩევში
pdfjs-current-outline-item-button-label = მიმდინარე გვერდი სარჩევში
pdfjs-findbar-button =
    .title = პოვნა დოკუმენტში
pdfjs-findbar-button-label = ძიება
pdfjs-additional-layers = დამატებითი შრეები

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = გვერდი { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = გვერდის შეთვალიერება { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = ძიება
    .placeholder = პოვნა დოკუმენტში…
pdfjs-find-previous-button =
    .title = წინა დამთხვევის პოვნა
pdfjs-find-previous-button-label = წინა
pdfjs-find-next-button =
    .title = მომდევნო დამთხვევის პოვნა
pdfjs-find-next-button-label = შემდეგი
pdfjs-find-highlight-checkbox = ყველაფრის მონიშვნა
pdfjs-find-match-case-checkbox-label = მთავრულით
pdfjs-find-match-diacritics-checkbox-label = ნიშნებით
pdfjs-find-entire-word-checkbox-label = მთლიანი სიტყვები
pdfjs-find-reached-top = მიღწეულია დოკუმენტის დასაწყისი, გრძელდება ბოლოდან
pdfjs-find-reached-bottom = მიღწეულია დოკუმენტის ბოლო, გრძელდება დასაწყისიდან
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] თანხვედრა { $current }, სულ { $total }
       *[other] თანხვედრა { $current }, სულ { $total }
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] არანაკლებ { $limit } თანხვედრა
       *[other] არანაკლებ { $limit } თანხვედრა
    }
pdfjs-find-not-found = ფრაზა ვერ მოიძებნა

## Predefined zoom values

pdfjs-page-scale-width = გვერდის სიგანეზე
pdfjs-page-scale-fit = მთლიანი გვერდი
pdfjs-page-scale-auto = ავტომატური
pdfjs-page-scale-actual = საწყისი ზომა
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = გვერდი { $page }

## Loading indicator messages

pdfjs-loading-error = შეცდომა, PDF-ფაილის ჩატვირთვისას.
pdfjs-invalid-file-error = არამართებული ან დაზიანებული PDF-ფაილი.
pdfjs-missing-file-error = ნაკლული PDF-ფაილი.
pdfjs-unexpected-response-error = სერვერის მოულოდნელი პასუხი.
pdfjs-rendering-error = შეცდომა, გვერდის ჩვენებისას.

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
    .alt = [{ $type } შენიშვნა]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = შეიყვანეთ პაროლი PDF-ფაილის გასახსნელად.
pdfjs-password-invalid = არასწორი პაროლი. გთხოვთ, სცადოთ ხელახლა.
pdfjs-password-ok-button = კარგი
pdfjs-password-cancel-button = გაუქმება
pdfjs-web-fonts-disabled = ვებშრიფტები გამორთულია: ჩაშენებული PDF-შრიფტების გამოყენება ვერ ხერხდება.

## Editing

pdfjs-editor-free-text-button =
    .title = წარწერა
pdfjs-editor-free-text-button-label = წარწერა
pdfjs-editor-ink-button =
    .title = ხაზვა
pdfjs-editor-ink-button-label = ხაზვა
pdfjs-editor-stamp-button =
    .title = სურათების დართვა ან ჩასწორება
pdfjs-editor-stamp-button-label = სურათების დართვა ან ჩასწორება
pdfjs-editor-highlight-button =
    .title = მონიშვნა
pdfjs-editor-highlight-button-label = მონიშვნა
pdfjs-highlight-floating-button1 =
    .title = მონიშვნა
    .aria-label = მონიშვნა
pdfjs-highlight-floating-button-label = მონიშვნა
pdfjs-editor-signature-button =
    .title = ხელმოწერის დამატება
pdfjs-editor-signature-button-label = ხელმოწერის დამატება

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = მონიშვნის ჩასწორება
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = ნახაზის ჩასწორება
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = ხელმოწერის ჩასწორება: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = სურათის ჩასწორება

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = დახაზულის მოცილება
pdfjs-editor-remove-freetext-button =
    .title = წარწერის მოცილება
pdfjs-editor-remove-stamp-button =
    .title = სურათის მოცილება
pdfjs-editor-remove-highlight-button =
    .title = მონიშვნის მოცილება
pdfjs-editor-remove-signature-button =
    .title = ხელმოწერის მოცილება

##

# Editor Parameters
pdfjs-editor-free-text-color-input = ფერი
pdfjs-editor-free-text-size-input = ზომა
pdfjs-editor-ink-color-input = ფერი
pdfjs-editor-ink-thickness-input = სისქე
pdfjs-editor-ink-opacity-input = გაუმჭვირვალობა
pdfjs-editor-stamp-add-image-button =
    .title = სურათის დამატება
pdfjs-editor-stamp-add-image-button-label = სურათის დამატება
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = სისქე
pdfjs-editor-free-highlight-thickness-title =
    .title = სისქის შეცვლა წარწერის გარდა სხვა ნაწილების მონიშვნისას
pdfjs-editor-add-signature-container =
    .aria-label = ხელმოწერის მართვა და შენახული ხელმოწერები
pdfjs-editor-signature-add-signature-button =
    .title = ახალი ხელმოწერის დამატება
pdfjs-editor-signature-add-signature-button-label = ახალი ხელმოწერის დამატება
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = შენახული ხელმოწერა: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = ნაწერის ჩასწორება
    .default-content = დაიწყეთ აკრეფა…
pdfjs-free-text =
    .aria-label = ნაწერის ჩასწორება
pdfjs-free-text-default-content = აკრიფეთ…
pdfjs-ink =
    .aria-label = დახაზულის შესწორება
pdfjs-ink-canvas =
    .aria-label = მომხმარებლის შექმნილი სურათი

## Alt-text dialog

pdfjs-editor-alt-text-button-label = თანდართული წარწერა
pdfjs-editor-alt-text-edit-button =
    .aria-label = დართული წარწერის ჩასწორება
pdfjs-editor-alt-text-edit-button-label = თანდართული წარწერის ჩასწორება
pdfjs-editor-alt-text-dialog-label = არჩევა
pdfjs-editor-alt-text-dialog-description = თანდართული (შემნაცვლებელი) წარწერა გამოსადეგია მათთვის, ვინც ვერ ხედავს სურათებს ან გამოისახება მაშინ, როცა სურათი ვერ ჩაიტვირთება.
pdfjs-editor-alt-text-add-description-label = აღწერილობის მითითება
pdfjs-editor-alt-text-add-description-description = განკუთვნილია 1-2 წინადადებით საგნის, მახასიათებლის ან მოქმედების აღსაწერად.
pdfjs-editor-alt-text-mark-decorative-label = მოინიშნოს მორთულობად
pdfjs-editor-alt-text-mark-decorative-description = განკუთვნილია შესამკობი სურათებისთვის, გარსშემოსავლები ჩარჩოებისა და ჭვირნიშნებისთვის.
pdfjs-editor-alt-text-cancel-button = გაუქმება
pdfjs-editor-alt-text-save-button = შენახვა
pdfjs-editor-alt-text-decorative-tooltip = მოინიშნოს მორთულობად
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = მაგალითად, „ახალგაზრდა მამაკაცი მაგიდასთან ზის და სადილობს“
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = დართული წარწერა

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = ზევით მარცხნივ — ზომაცვლა
pdfjs-editor-resizer-label-top-middle = ზევით შუაში — ზომაცვლა
pdfjs-editor-resizer-label-top-right = ზევით მარჯვნივ — ზომაცვლა
pdfjs-editor-resizer-label-middle-right = შუაში მარჯვნივ — ზომაცვლა
pdfjs-editor-resizer-label-bottom-right = ქვევით მარჯვნივ — ზომაცვლა
pdfjs-editor-resizer-label-bottom-middle = ქვევით შუაში — ზომაცვლა
pdfjs-editor-resizer-label-bottom-left = ზვევით მარცხნივ — ზომაცვლა
pdfjs-editor-resizer-label-middle-left = შუაში მარცხნივ — ზომაცვლა
pdfjs-editor-resizer-top-left =
    .aria-label = ზევით მარცხნივ — ზომაცვლა
pdfjs-editor-resizer-top-middle =
    .aria-label = ზევით შუაში — ზომაცვლა
pdfjs-editor-resizer-top-right =
    .aria-label = ზევით მარჯვნივ — ზომაცვლა
pdfjs-editor-resizer-middle-right =
    .aria-label = შუაში მარჯვნივ — ზომაცვლა
pdfjs-editor-resizer-bottom-right =
    .aria-label = ქვევით მარჯვნივ — ზომაცვლა
pdfjs-editor-resizer-bottom-middle =
    .aria-label = ქვევით შუაში — ზომაცვლა
pdfjs-editor-resizer-bottom-left =
    .aria-label = ზვევით მარცხნივ — ზომაცვლა
pdfjs-editor-resizer-middle-left =
    .aria-label = შუაში მარცხნივ — ზომაცვლა

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = მოსანიშნი ფერი
pdfjs-editor-colorpicker-button =
    .title = ფერის შეცვლა
pdfjs-editor-colorpicker-dropdown =
    .aria-label = ფერის არჩევა
pdfjs-editor-colorpicker-yellow =
    .title = ყვითელი
pdfjs-editor-colorpicker-green =
    .title = მწვანე
pdfjs-editor-colorpicker-blue =
    .title = ლურჯი
pdfjs-editor-colorpicker-pink =
    .title = ვარდისფერი
pdfjs-editor-colorpicker-red =
    .title = წითელი

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = ყველას ჩვენება
pdfjs-editor-highlight-show-all-button =
    .title = ყველას ჩვენება

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = დართული წარწერის ჩასწორება (სურათის აღწერის)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = დართული წარწერის დამატება (სურათის აღწერის)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = დაწერეთ თქვენი აღწერა აქ…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = მოკლე აღწერა მათთვის, ვინც ვერ ხედავს სურათს ან ვისთანაც ვერ ჩაიტვირთება სურათი.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = ეს დართული წარწერა ავტომატურადაა შედგენილი და შესაძლოა, უმართებულო იყოს.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = ვრცლად
pdfjs-editor-new-alt-text-create-automatically-button-label = დართული წარწერის ავტომატური შედგენა
pdfjs-editor-new-alt-text-not-now-button = ახლა არა
pdfjs-editor-new-alt-text-error-title = დართული წარწერის შედგენა ვერ მოხერხდა
pdfjs-editor-new-alt-text-error-description = გთხოვთ დაწეროთ საკუთარი დანართი და კვლავ სცადოთ მოგვიანებით.
pdfjs-editor-new-alt-text-error-close-button = დახურვა
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = ჩამოიტვირთება დართული წარწერის შესადეგი AI-მოდელი ({ $downloadedSize } ზომით { $totalSize } მბაიტი)
    .aria-valuetext = ჩამოიტვირთება დართული წარწერის შესადეგი AI-მოდელი ({ $downloadedSize } ზომით { $totalSize } მბაიტი)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = დართული წარწერა დამატებულია
pdfjs-editor-new-alt-text-added-button-label = დართული წარწერა დამატებულია
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = აკლია დართული წარწერა
pdfjs-editor-new-alt-text-missing-button-label = აკლია დართული წარწერა
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = დართული წარწერის გადახედვა
pdfjs-editor-new-alt-text-to-review-button-label = დართული წარწერის გადახედვა
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = შედგენილია ავტომატურად: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = სურათის დართული წარწერის პარამეტრები
pdfjs-image-alt-text-settings-button-label = სურათის დართული წარწერის პარამეტრები
pdfjs-editor-alt-text-settings-dialog-label = სურათის დართული წარწერის პარამეტრები
pdfjs-editor-alt-text-settings-automatic-title = ავტომატურად დართული წარწერა
pdfjs-editor-alt-text-settings-create-model-button-label = დართული წარწერის ავტომატური შედგენა
pdfjs-editor-alt-text-settings-create-model-description = აღწერს სურათს მათთვის, ვინც ვერ ხედავს ან ვისთანაც ვერ ჩაიტვირთება.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = დართული წარწერის შესადგენი AI-მოდელი ({ $totalSize } მბაიტი)
pdfjs-editor-alt-text-settings-ai-model-description = ეშვება ადგილობრივად თქვენს მოწყობილობასა, ასე რომ მონაცემები დარჩება პირადი. საჭიროა წარწერის ავტომატურად დართვისთვის.
pdfjs-editor-alt-text-settings-delete-model-button = წაშლა
pdfjs-editor-alt-text-settings-download-model-button = ჩამოტვირთვა
pdfjs-editor-alt-text-settings-downloading-model-button = ჩამოიტვრითება...
pdfjs-editor-alt-text-settings-editor-title = დართული წარწერის ჩამსწორებელი
pdfjs-editor-alt-text-settings-show-dialog-button-label = გამოჩნდეს დართული წარწერის ჩამსწორებელი სურათის დამატებისთანავე
pdfjs-editor-alt-text-settings-show-dialog-description = უზრუნველყოფს, რომ თქვენს ყველა სურათს ახლდეს დართული წარწერა.
pdfjs-editor-alt-text-settings-close-button = დახურვა

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = მონიშვნა მოცილებულია
pdfjs-editor-undo-bar-message-freetext = წარწერა მოცილებულია
pdfjs-editor-undo-bar-message-ink = ნახატი მოცილებულია
pdfjs-editor-undo-bar-message-stamp = სურათი მოცილებულია
pdfjs-editor-undo-bar-message-signature = ხელმოწერა მოცილებულია
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } შენიშვნა მოცილებულია
       *[other] { $count } შენიშვნა მოცილებულია
    }
pdfjs-editor-undo-bar-undo-button =
    .title = დაბრუნება
pdfjs-editor-undo-bar-undo-button-label = დაბრუნება
pdfjs-editor-undo-bar-close-button =
    .title = დახურვა
pdfjs-editor-undo-bar-close-button-label = დახურვა

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = ეს არე საშუალებას აძლევს მომხმარებელს, შექმნას საკუთარი ხელმოწერა PDF-დოკუმენტისთვის. მომხმარებელს შეეძლება ჩაასწოროს სახელი (რომელიც დართული ტექსტის მოვალეობასაც ასრულებს) და სურვილისამებრ შეინახოს ხელმოწერა განმეორებით გამოსაყენებლად.
pdfjs-editor-add-signature-dialog-title = ხელმოწერის დამატება

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = აკრეფა
    .title = აკრეფა
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = მოხაზვა
    .title = მოხაზვა
pdfjs-editor-add-signature-image-button = სურათი
    .title = სურათი

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = აკრიფეთ ხელმოწერა
    .placeholder = აკრიფეთ ხელმოწერა
pdfjs-editor-add-signature-draw-placeholder = მოხაზეთ ხელმოწერა
pdfjs-editor-add-signature-draw-thickness-range-label = სისქე
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = მოხაზულის სისქე: { $thickness }
pdfjs-editor-add-signature-image-placeholder = ჩავლებით გადმოიტანეთ ასატვირთად
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] ან ამოარჩიეთ სურათებიდან
       *[other] ან ამოარჩიეთ სურათებიდან
    }

## Controls

pdfjs-editor-add-signature-description-label = აღწერილობა (დართული ტექსტი)
pdfjs-editor-add-signature-description-input =
    .title = აღწერილობა (დართული ტექსტი)
pdfjs-editor-add-signature-description-default-when-drawing = ხელმოწერა
pdfjs-editor-add-signature-clear-button-label = ხელმოწერის წაშლა
pdfjs-editor-add-signature-clear-button =
    .title = ხელმოწერის წაშლა
pdfjs-editor-add-signature-save-checkbox = ხელმოწერის შენახვა
pdfjs-editor-add-signature-save-warning-message = მიღწეულია 5 ხელმოწერის შენახვის ზღვარი. მოაცილეთ რომელიმე ახლის შესანახად.
pdfjs-editor-add-signature-image-upload-error-title = ვერ აიტვირთა სურათი
pdfjs-editor-add-signature-image-upload-error-description = შეამოწმეთ ქსელთან კავშირი ან მოსინჯეთ სხვა სურათი.
pdfjs-editor-add-signature-error-close-button = დახურვა

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = გაუქმება
pdfjs-editor-add-signature-add-button = დამატება
pdfjs-editor-edit-signature-update-button = განახლება

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = შენახული ხელმოწერის მოცილება
pdfjs-editor-delete-signature-button-label1 = შენახული ხელმოწერის მოცილება

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = აღწერილობის ჩასწორება

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = აღწერილობის ჩასწორება
