# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = דף קודם
pdfjs-previous-button-label = קודם
pdfjs-next-button =
    .title = דף הבא
pdfjs-next-button-label = הבא
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = דף
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = מתוך { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } מתוך { $pagesCount })
pdfjs-zoom-out-button =
    .title = התרחקות
pdfjs-zoom-out-button-label = התרחקות
pdfjs-zoom-in-button =
    .title = התקרבות
pdfjs-zoom-in-button-label = התקרבות
pdfjs-zoom-select =
    .title = מרחק מתצוגה
pdfjs-presentation-mode-button =
    .title = מעבר למצב מצגת
pdfjs-presentation-mode-button-label = מצב מצגת
pdfjs-open-file-button =
    .title = פתיחת קובץ
pdfjs-open-file-button-label = פתיחה
pdfjs-print-button =
    .title = הדפסה
pdfjs-print-button-label = הדפסה
pdfjs-save-button =
    .title = שמירה
pdfjs-save-button-label = שמירה
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = הורדה
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = הורדה
pdfjs-bookmark-button =
    .title = עמוד נוכחי (הצגת כתובת האתר מהעמוד הנוכחי)
pdfjs-bookmark-button-label = עמוד נוכחי

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = כלים
pdfjs-tools-button-label = כלים
pdfjs-first-page-button =
    .title = מעבר לעמוד הראשון
pdfjs-first-page-button-label = מעבר לעמוד הראשון
pdfjs-last-page-button =
    .title = מעבר לעמוד האחרון
pdfjs-last-page-button-label = מעבר לעמוד האחרון
pdfjs-page-rotate-cw-button =
    .title = הטיה עם כיוון השעון
pdfjs-page-rotate-cw-button-label = הטיה עם כיוון השעון
pdfjs-page-rotate-ccw-button =
    .title = הטיה כנגד כיוון השעון
pdfjs-page-rotate-ccw-button-label = הטיה כנגד כיוון השעון
pdfjs-cursor-text-select-tool-button =
    .title = הפעלת כלי בחירת טקסט
pdfjs-cursor-text-select-tool-button-label = כלי בחירת טקסט
pdfjs-cursor-hand-tool-button =
    .title = הפעלת כלי היד
pdfjs-cursor-hand-tool-button-label = כלי יד
pdfjs-scroll-page-button =
    .title = שימוש בגלילת עמוד
pdfjs-scroll-page-button-label = גלילת עמוד
pdfjs-scroll-vertical-button =
    .title = שימוש בגלילה אנכית
pdfjs-scroll-vertical-button-label = גלילה אנכית
pdfjs-scroll-horizontal-button =
    .title = שימוש בגלילה אופקית
pdfjs-scroll-horizontal-button-label = גלילה אופקית
pdfjs-scroll-wrapped-button =
    .title = שימוש בגלילה רציפה
pdfjs-scroll-wrapped-button-label = גלילה רציפה
pdfjs-spread-none-button =
    .title = לא לצרף מפתחי עמודים
pdfjs-spread-none-button-label = ללא מפתחים
pdfjs-spread-odd-button =
    .title = צירוף מפתחי עמודים שמתחילים בדפים עם מספרים אי־זוגיים
pdfjs-spread-odd-button-label = מפתחים אי־זוגיים
pdfjs-spread-even-button =
    .title = צירוף מפתחי עמודים שמתחילים בדפים עם מספרים זוגיים
pdfjs-spread-even-button-label = מפתחים זוגיים

## Document properties dialog

pdfjs-document-properties-button =
    .title = מאפייני מסמך…
pdfjs-document-properties-button-label = מאפייני מסמך…
pdfjs-document-properties-file-name = שם קובץ:
pdfjs-document-properties-file-size = גודל הקובץ:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } ק״ב ({ $b } בתים)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } מ״ב ({ $b } בתים)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } ק״ב ({ $size_b } בתים)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } מ״ב ({ $size_b } בתים)
pdfjs-document-properties-title = כותרת:
pdfjs-document-properties-author = מחבר:
pdfjs-document-properties-subject = נושא:
pdfjs-document-properties-keywords = מילות מפתח:
pdfjs-document-properties-creation-date = תאריך יצירה:
pdfjs-document-properties-modification-date = תאריך שינוי:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = יוצר:
pdfjs-document-properties-producer = יצרן PDF:
pdfjs-document-properties-version = גרסת PDF:
pdfjs-document-properties-page-count = מספר דפים:
pdfjs-document-properties-page-size = גודל העמוד:
pdfjs-document-properties-page-size-unit-inches = אינ׳
pdfjs-document-properties-page-size-unit-millimeters = מ״מ
pdfjs-document-properties-page-size-orientation-portrait = לאורך
pdfjs-document-properties-page-size-orientation-landscape = לרוחב
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = מכתב
pdfjs-document-properties-page-size-name-legal = דף משפטי

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
pdfjs-document-properties-linearized = תצוגת דף מהירה:
pdfjs-document-properties-linearized-yes = כן
pdfjs-document-properties-linearized-no = לא
pdfjs-document-properties-close-button = סגירה

## Print

pdfjs-print-progress-message = מסמך בהכנה להדפסה…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = ביטול
pdfjs-printing-not-supported = אזהרה: הדפסה אינה נתמכת במלואה בדפדפן זה.
pdfjs-printing-not-ready = אזהרה: מסמך ה־PDF לא נטען לחלוטין עד מצב שמאפשר הדפסה.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = הצגה/הסתרה של סרגל הצד
pdfjs-toggle-sidebar-notification-button =
    .title = החלפת תצוגת סרגל צד (מסמך שמכיל תוכן עניינים/קבצים מצורפים/שכבות)
pdfjs-toggle-sidebar-button-label = הצגה/הסתרה של סרגל הצד
pdfjs-document-outline-button =
    .title = הצגת תוכן העניינים של המסמך (לחיצה כפולה כדי להרחיב או לצמצם את כל הפריטים)
pdfjs-document-outline-button-label = תוכן העניינים של המסמך
pdfjs-attachments-button =
    .title = הצגת צרופות
pdfjs-attachments-button-label = צרופות
pdfjs-layers-button =
    .title = הצגת שכבות (יש ללחוץ לחיצה כפולה כדי לאפס את כל השכבות למצב ברירת המחדל)
pdfjs-layers-button-label = שכבות
pdfjs-thumbs-button =
    .title = הצגת תצוגה מקדימה
pdfjs-thumbs-button-label = תצוגה מקדימה
pdfjs-current-outline-item-button =
    .title = מציאת פריט תוכן העניינים הנוכחי
pdfjs-current-outline-item-button-label = פריט תוכן העניינים הנוכחי
pdfjs-findbar-button =
    .title = חיפוש במסמך
pdfjs-findbar-button-label = חיפוש
pdfjs-additional-layers = שכבות נוספות

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = עמוד { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = תצוגה מקדימה של עמוד { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = חיפוש
    .placeholder = חיפוש במסמך…
pdfjs-find-previous-button =
    .title = מציאת המופע הקודם של הביטוי
pdfjs-find-previous-button-label = קודם
pdfjs-find-next-button =
    .title = מציאת המופע הבא של הביטוי
pdfjs-find-next-button-label = הבא
pdfjs-find-highlight-checkbox = הדגשת הכול
pdfjs-find-match-case-checkbox-label = התאמת אותיות
pdfjs-find-match-diacritics-checkbox-label = התאמה דיאקריטית
pdfjs-find-entire-word-checkbox-label = מילים שלמות
pdfjs-find-reached-top = הגיע לראש הדף, ממשיך מלמטה
pdfjs-find-reached-bottom = הגיע לסוף הדף, ממשיך מלמעלה
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } מתוך { $total } תוצאות
       *[other] { $current } מתוך { $total } תוצאות
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] יותר מתוצאה אחת
       *[other] יותר מ־{ $limit } תוצאות
    }
pdfjs-find-not-found = הביטוי לא נמצא

## Predefined zoom values

pdfjs-page-scale-width = רוחב העמוד
pdfjs-page-scale-fit = התאמה לעמוד
pdfjs-page-scale-auto = מרחק מתצוגה אוטומטי
pdfjs-page-scale-actual = גודל אמיתי
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = עמוד { $page }

## Loading indicator messages

pdfjs-loading-error = אירעה שגיאה בעת טעינת ה־PDF.
pdfjs-invalid-file-error = קובץ PDF פגום או לא תקין.
pdfjs-missing-file-error = קובץ PDF חסר.
pdfjs-unexpected-response-error = תגובת שרת לא צפויה.
pdfjs-rendering-error = אירעה שגיאה בעת עיבוד הדף.

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
    .alt = [הערת { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = נא להכניס את הססמה לפתיחת קובץ PDF זה.
pdfjs-password-invalid = ססמה שגויה. נא לנסות שוב.
pdfjs-password-ok-button = אישור
pdfjs-password-cancel-button = ביטול
pdfjs-web-fonts-disabled = גופני רשת מנוטרלים: לא ניתן להשתמש בגופני PDF מוטבעים.

## Editing

pdfjs-editor-free-text-button =
    .title = טקסט
pdfjs-editor-free-text-button-label = טקסט
pdfjs-editor-ink-button =
    .title = ציור
pdfjs-editor-ink-button-label = ציור
pdfjs-editor-stamp-button =
    .title = הוספה או עריכת תמונות
pdfjs-editor-stamp-button-label = הוספה או עריכת תמונות
pdfjs-editor-highlight-button =
    .title = סימון
pdfjs-editor-highlight-button-label = סימון
pdfjs-highlight-floating-button1 =
    .title = סימון
    .aria-label = סימון
pdfjs-highlight-floating-button-label = סימון
pdfjs-editor-signature-button =
    .title = הוספת חתימה
pdfjs-editor-signature-button-label = הוספת חתימה

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = עורך סימונים
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = עורך ציורים
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = עורך החתימות: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = עורך תמונות

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = הסרת ציור
pdfjs-editor-remove-freetext-button =
    .title = הסרת טקסט
pdfjs-editor-remove-stamp-button =
    .title = הסרת תמונה
pdfjs-editor-remove-highlight-button =
    .title = הסרת סימון
pdfjs-editor-remove-signature-button =
    .title = הסרת חתימה

##

# Editor Parameters
pdfjs-editor-free-text-color-input = צבע
pdfjs-editor-free-text-size-input = גודל
pdfjs-editor-ink-color-input = צבע
pdfjs-editor-ink-thickness-input = עובי
pdfjs-editor-ink-opacity-input = אטימות
pdfjs-editor-stamp-add-image-button =
    .title = הוספת תמונה
pdfjs-editor-stamp-add-image-button-label = הוספת תמונה
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = עובי
pdfjs-editor-free-highlight-thickness-title =
    .title = שינוי עובי בעת סימון פריטים שאינם טקסט
pdfjs-editor-add-signature-container =
    .aria-label = פקדי חתימה וחתימות שמורות
pdfjs-editor-signature-add-signature-button =
    .title = הוספת חתימה חדשה
pdfjs-editor-signature-add-signature-button-label = הוספת חתימה חדשה
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = חתימה שמורה: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = עורך טקסט
    .default-content = נא להתחיל להקליד…
pdfjs-free-text =
    .aria-label = עורך טקסט
pdfjs-free-text-default-content = להתחיל להקליד…
pdfjs-ink =
    .aria-label = עורך ציור
pdfjs-ink-canvas =
    .aria-label = תמונה שנוצרה על־ידי משתמש

## Alt-text dialog

pdfjs-editor-alt-text-button-label = טקסט חלופי
pdfjs-editor-alt-text-edit-button =
    .aria-label = עריכת טקסט חלופי
pdfjs-editor-alt-text-edit-button-label = עריכת טקסט חלופי
pdfjs-editor-alt-text-dialog-label = בחירת אפשרות
pdfjs-editor-alt-text-dialog-description = טקסט חלופי עוזר כשאנשים לא יכולים לראות את התמונה או כשהיא לא נטענת.
pdfjs-editor-alt-text-add-description-label = הוספת תיאור
pdfjs-editor-alt-text-add-description-description = כדאי לתאר במשפט אחד או שניים את הנושא, התפאורה או הפעולות.
pdfjs-editor-alt-text-mark-decorative-label = סימון כדקורטיבי
pdfjs-editor-alt-text-mark-decorative-description = זה משמש לתמונות נוי, כמו גבולות או סימני מים.
pdfjs-editor-alt-text-cancel-button = ביטול
pdfjs-editor-alt-text-save-button = שמירה
pdfjs-editor-alt-text-decorative-tooltip = מסומן כדקורטיבי
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = לדוגמה, ״גבר צעיר מתיישב ליד שולחן לאכול ארוחה״
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = טקסט חלופי

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = פינה שמאלית עליונה - שינוי גודל
pdfjs-editor-resizer-label-top-middle = למעלה באמצע - שינוי גודל
pdfjs-editor-resizer-label-top-right = פינה ימנית עליונה - שינוי גודל
pdfjs-editor-resizer-label-middle-right = ימינה באמצע - שינוי גודל
pdfjs-editor-resizer-label-bottom-right = פינה ימנית תחתונה - שינוי גודל
pdfjs-editor-resizer-label-bottom-middle = למטה באמצע - שינוי גודל
pdfjs-editor-resizer-label-bottom-left = פינה שמאלית תחתונה - שינוי גודל
pdfjs-editor-resizer-label-middle-left = שמאלה באמצע - שינוי גודל
pdfjs-editor-resizer-top-left =
    .aria-label = פינה שמאלית עליונה - שינוי גודל
pdfjs-editor-resizer-top-middle =
    .aria-label = למעלה באמצע - שינוי גודל
pdfjs-editor-resizer-top-right =
    .aria-label = פינה ימנית עליונה - שינוי גודל
pdfjs-editor-resizer-middle-right =
    .aria-label = ימינה באמצע - שינוי גודל
pdfjs-editor-resizer-bottom-right =
    .aria-label = פינה ימנית תחתונה - שינוי גודל
pdfjs-editor-resizer-bottom-middle =
    .aria-label = למטה באמצע - שינוי גודל
pdfjs-editor-resizer-bottom-left =
    .aria-label = פינה שמאלית תחתונה - שינוי גודל
pdfjs-editor-resizer-middle-left =
    .aria-label = שמאלה באמצע - שינוי גודל

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = צבע סימון
pdfjs-editor-colorpicker-button =
    .title = שינוי צבע
pdfjs-editor-colorpicker-dropdown =
    .aria-label = בחירת צבע
pdfjs-editor-colorpicker-yellow =
    .title = צהוב
pdfjs-editor-colorpicker-green =
    .title = ירוק
pdfjs-editor-colorpicker-blue =
    .title = כחול
pdfjs-editor-colorpicker-pink =
    .title = ורוד
pdfjs-editor-colorpicker-red =
    .title = אדום

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = הצגת הכול
pdfjs-editor-highlight-show-all-button =
    .title = הצגת הכול

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = עריכת טקסט חלופי (תיאור תמונה)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = הוספת טקסט חלופי (תיאור תמונה)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = נא לכתוב את התיאור שלך כאן…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = תיאור קצר לאנשים שאינם יכולים לראות את התמונה או כאשר התמונה אינה נטענת.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = טקסט חלופי זה נוצר באופן אוטומטי ועשוי להיות לא מדויק.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = מידע נוסף
pdfjs-editor-new-alt-text-create-automatically-button-label = יצירת טקסט חלופי באופן אוטומטי
pdfjs-editor-new-alt-text-not-now-button = לא כעת
pdfjs-editor-new-alt-text-error-title = לא ניתן היה ליצור טקסט חלופי באופן אוטומטי
pdfjs-editor-new-alt-text-error-description = נא לכתוב טקסט חלופי משלך או לנסות שוב מאוחר יותר.
pdfjs-editor-new-alt-text-error-close-button = סגירה
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = בתהליך הורדת מודל AI של טקסט חלופי ({ $downloadedSize } מתוך { $totalSize } מ״ב)
    .aria-valuetext = בתהליך הורדת מודל AI של טקסט חלופי ({ $downloadedSize } מתוך { $totalSize } מ״ב)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = נוסף טקסט חלופי
pdfjs-editor-new-alt-text-added-button-label = נוסף טקסט חלופי
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = חסר טקסט חלופי
pdfjs-editor-new-alt-text-missing-button-label = חסר טקסט חלופי
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = סקירת טקסט חלופי
pdfjs-editor-new-alt-text-to-review-button-label = סקירת טקסט חלופי
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = נוצר באופן אוטומטי: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = הגדרות טקסט חלופי של תמונה
pdfjs-image-alt-text-settings-button-label = הגדרות טקסט חלופי של תמונה
pdfjs-editor-alt-text-settings-dialog-label = הגדרות טקסט חלופי של תמונה
pdfjs-editor-alt-text-settings-automatic-title = טקסט חלופי אוטומטי
pdfjs-editor-alt-text-settings-create-model-button-label = יצירת טקסט חלופי באופן אוטומטי
pdfjs-editor-alt-text-settings-create-model-description = הצעת תיאורים כדי לסייע לאנשים שאינם יכולים לראות את התמונה או כאשר התמונה אינה נטענת.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = מודל AI לטקסט חלופי ({ $totalSize } מ״ב)
pdfjs-editor-alt-text-settings-ai-model-description = פועל באופן מקומי במכשיר שלך כך שהנתונים שלך נשארים פרטיים. נדרש עבור טקסט חלופי אוטומטי.
pdfjs-editor-alt-text-settings-delete-model-button = מחיקה
pdfjs-editor-alt-text-settings-download-model-button = הורדה
pdfjs-editor-alt-text-settings-downloading-model-button = בהורדה…
pdfjs-editor-alt-text-settings-editor-title = עורך טקסט חלופי
pdfjs-editor-alt-text-settings-show-dialog-button-label = הצגת עורך טקסט חלופי מיד בעת הוספת תמונה
pdfjs-editor-alt-text-settings-show-dialog-description = מסייע לך לוודא שלכל התמונות שלך יש טקסט חלופי.
pdfjs-editor-alt-text-settings-close-button = סגירה

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = הסימון הוסר
pdfjs-editor-undo-bar-message-freetext = הטקסט הוסר
pdfjs-editor-undo-bar-message-ink = הציור הוסר
pdfjs-editor-undo-bar-message-stamp = התמונה הוסרה
pdfjs-editor-undo-bar-message-signature = החתימה הוסרה
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] הערה אחת הוסרה
       *[other] { $count } הערות הוסרו
    }
pdfjs-editor-undo-bar-undo-button =
    .title = ביטול פעולה
pdfjs-editor-undo-bar-undo-button-label = ביטול פעלה
pdfjs-editor-undo-bar-close-button =
    .title = סגירה
pdfjs-editor-undo-bar-close-button-label = סגירה

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = מודל זה מאפשר למשתמש ליצור חתימה להוספה למסמך PDF. המשתמש יכול לערוך את השם (שמשמש גם כטקסט האלטרנטיבי), ובאופן אופציונלי לשמור את החתימה לשימוש חוזר.
pdfjs-editor-add-signature-dialog-title = הוספת חתימה

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = הקלדה
    .title = הקלדה
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = ציור
    .title = ציור
pdfjs-editor-add-signature-image-button = תמונה
    .title = תמונה

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = נא להקליד את החתימה שלך
    .placeholder = נא להקליד את החתימה שלך
pdfjs-editor-add-signature-draw-placeholder = נא לצייר את החתימה שלך
pdfjs-editor-add-signature-draw-thickness-range-label = עובי
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = עובי הציור: { $thickness }
pdfjs-editor-add-signature-image-placeholder = יש לגרור לכאן קובץ להעלאה
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] או לבחור בקובצי תמונה
       *[other] או לעיין בקובצי תמונה
    }

## Controls

pdfjs-editor-add-signature-description-label = תיאור (טקסט חלופי)
pdfjs-editor-add-signature-description-input =
    .title = תיאור (טקסט חלופי)
pdfjs-editor-add-signature-description-default-when-drawing = חתימה
pdfjs-editor-add-signature-clear-button-label = ניקוי חתימה
pdfjs-editor-add-signature-clear-button =
    .title = ניקוי חתימה
pdfjs-editor-add-signature-save-checkbox = שמירת החתימה
pdfjs-editor-add-signature-save-warning-message = הגעת למגבלה של 5 חתימות שמורות. יש להסיר אחד כדי לשמור עוד.
pdfjs-editor-add-signature-image-upload-error-title = לא ניתן להעלות את התמונה
pdfjs-editor-add-signature-image-upload-error-description = נא לבדוק את החיבור שלך לרשת או לנסות תמונה אחרת.
pdfjs-editor-add-signature-error-close-button = סגירה

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = ביטול
pdfjs-editor-add-signature-add-button = הוספה
pdfjs-editor-edit-signature-update-button = עדכון

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = הסרת חתימה שמורה
pdfjs-editor-delete-signature-button-label1 = הסרת חתימה שמורה

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = עריכת תיאור

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = עריכת תיאור
