# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Προηγούμενη σελίδα
pdfjs-previous-button-label = Προηγούμενη
pdfjs-next-button =
    .title = Επόμενη σελίδα
pdfjs-next-button-label = Επόμενη
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Σελίδα
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = από { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } από { $pagesCount })
pdfjs-zoom-out-button =
    .title = Σμίκρυνση
pdfjs-zoom-out-button-label = Σμίκρυνση
pdfjs-zoom-in-button =
    .title = Μεγέθυνση
pdfjs-zoom-in-button-label = Μεγέθυνση
pdfjs-zoom-select =
    .title = Ζουμ
pdfjs-presentation-mode-button =
    .title = Εναλλαγή σε λειτουργία παρουσίασης
pdfjs-presentation-mode-button-label = Λειτουργία παρουσίασης
pdfjs-open-file-button =
    .title = Άνοιγμα αρχείου
pdfjs-open-file-button-label = Άνοιγμα
pdfjs-print-button =
    .title = Εκτύπωση
pdfjs-print-button-label = Εκτύπωση
pdfjs-save-button =
    .title = Αποθήκευση
pdfjs-save-button-label = Αποθήκευση
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Λήψη
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Λήψη
pdfjs-bookmark-button =
    .title = Τρέχουσα σελίδα (Προβολή URL από τρέχουσα σελίδα)
pdfjs-bookmark-button-label = Τρέχουσα σελίδα

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Εργαλεία
pdfjs-tools-button-label = Εργαλεία
pdfjs-first-page-button =
    .title = Μετάβαση στην πρώτη σελίδα
pdfjs-first-page-button-label = Μετάβαση στην πρώτη σελίδα
pdfjs-last-page-button =
    .title = Μετάβαση στην τελευταία σελίδα
pdfjs-last-page-button-label = Μετάβαση στην τελευταία σελίδα
pdfjs-page-rotate-cw-button =
    .title = Δεξιόστροφη περιστροφή
pdfjs-page-rotate-cw-button-label = Δεξιόστροφη περιστροφή
pdfjs-page-rotate-ccw-button =
    .title = Αριστερόστροφη περιστροφή
pdfjs-page-rotate-ccw-button-label = Αριστερόστροφη περιστροφή
pdfjs-cursor-text-select-tool-button =
    .title = Ενεργοποίηση εργαλείου επιλογής κειμένου
pdfjs-cursor-text-select-tool-button-label = Εργαλείο επιλογής κειμένου
pdfjs-cursor-hand-tool-button =
    .title = Ενεργοποίηση εργαλείου χεριού
pdfjs-cursor-hand-tool-button-label = Εργαλείο χεριού
pdfjs-scroll-page-button =
    .title = Χρήση κύλισης σελίδας
pdfjs-scroll-page-button-label = Κύλιση σελίδας
pdfjs-scroll-vertical-button =
    .title = Χρήση κάθετης κύλισης
pdfjs-scroll-vertical-button-label = Κάθετη κύλιση
pdfjs-scroll-horizontal-button =
    .title = Χρήση οριζόντιας κύλισης
pdfjs-scroll-horizontal-button-label = Οριζόντια κύλιση
pdfjs-scroll-wrapped-button =
    .title = Χρήση κυκλικής κύλισης
pdfjs-scroll-wrapped-button-label = Κυκλική κύλιση
pdfjs-spread-none-button =
    .title = Να μην γίνει σύνδεση των επεκτάσεων σελίδων
pdfjs-spread-none-button-label = Χωρίς επεκτάσεις
pdfjs-spread-odd-button =
    .title = Σύνδεση επεκτάσεων σελίδων ξεκινώντας από τις μονές σελίδες
pdfjs-spread-odd-button-label = Μονές επεκτάσεις
pdfjs-spread-even-button =
    .title = Σύνδεση επεκτάσεων σελίδων ξεκινώντας από τις ζυγές σελίδες
pdfjs-spread-even-button-label = Ζυγές επεκτάσεις

## Document properties dialog

pdfjs-document-properties-button =
    .title = Ιδιότητες εγγράφου…
pdfjs-document-properties-button-label = Ιδιότητες εγγράφου…
pdfjs-document-properties-file-name = Όνομα αρχείου:
pdfjs-document-properties-file-size = Μέγεθος αρχείου:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)
pdfjs-document-properties-title = Τίτλος:
pdfjs-document-properties-author = Συγγραφέας:
pdfjs-document-properties-subject = Θέμα:
pdfjs-document-properties-keywords = Λέξεις-κλειδιά:
pdfjs-document-properties-creation-date = Ημερομηνία δημιουργίας:
pdfjs-document-properties-modification-date = Ημερομηνία τροποποίησης:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Δημιουργός:
pdfjs-document-properties-producer = Παραγωγός PDF:
pdfjs-document-properties-version = Έκδοση PDF:
pdfjs-document-properties-page-count = Αριθμός σελίδων:
pdfjs-document-properties-page-size = Μέγεθος σελίδας:
pdfjs-document-properties-page-size-unit-inches = ίντσες
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = κατακόρυφα
pdfjs-document-properties-page-size-orientation-landscape = οριζόντια
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Επιστολή
pdfjs-document-properties-page-size-name-legal = Τύπου Legal

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
pdfjs-document-properties-linearized = Ταχεία προβολή ιστού:
pdfjs-document-properties-linearized-yes = Ναι
pdfjs-document-properties-linearized-no = Όχι
pdfjs-document-properties-close-button = Κλείσιμο
pdfjs-digital-signature-properties-view-certificate = Προβολή πιστοποιητικού
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Αιτία: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Χρονοσήμανση: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Δευτερεύουσα υπογραφή ({ $count })
       *[other] Δευτερεύουσες υπογραφές ({ $count })
    }

## Print

pdfjs-print-progress-message = Προετοιμασία του εγγράφου για εκτύπωση…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Ακύρωση
pdfjs-printing-not-supported = Προειδοποίηση: Η εκτύπωση δεν υποστηρίζεται πλήρως από το πρόγραμμα περιήγησης.
pdfjs-printing-not-ready = Προειδοποίηση: Το PDF δεν φορτώθηκε πλήρως για εκτύπωση.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Εύρεση τρέχοντος στοιχείου διάρθρωσης
pdfjs-current-outline-item-button-label = Τρέχον στοιχείο διάρθρωσης
pdfjs-findbar-button =
    .title = Εύρεση στο έγγραφο
pdfjs-findbar-button-label = Εύρεση
pdfjs-additional-layers = Επιπρόσθετα επίπεδα

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Μικρογραφία σελίδας { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Επιλογή σελίδας { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Σελίδα { $page } από { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Εύρεση στο έγγραφο…
    .title = Εύρεση
pdfjs-find-previous-button =
    .title = Εύρεση της προηγούμενης εμφάνισης της φράσης
pdfjs-find-previous-button-label = Προηγούμενο
pdfjs-find-next-button =
    .title = Εύρεση της επόμενης εμφάνισης της φράσης
pdfjs-find-next-button-label = Επόμενο
pdfjs-find-highlight-checkbox = Επισήμανση όλων
pdfjs-find-match-case-checkbox-label = Συμφωνία πεζών/κεφαλαίων
pdfjs-find-match-diacritics-checkbox-label = Αντιστοίχιση διακριτικών
pdfjs-find-entire-word-checkbox-label = Ολόκληρες λέξεις
pdfjs-find-reached-top = Φτάσατε στην αρχή του εγγράφου, συνέχεια από το τέλος
pdfjs-find-reached-bottom = Φτάσατε στο τέλος του εγγράφου, συνέχεια από την αρχή
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } από { $total } αντιστοιχία
       *[other] { $current } από { $total } αντιστοιχίες
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Περισσότερες από { $limit } αντιστοιχία
       *[other] Περισσότερες από { $limit } αντιστοιχίες
    }
pdfjs-find-not-found = Η φράση δεν βρέθηκε

## Predefined zoom values

pdfjs-page-scale-width = Πλάτος σελίδας
pdfjs-page-scale-fit = Μέγεθος σελίδας
pdfjs-page-scale-auto = Αυτόματο ζουμ
pdfjs-page-scale-actual = Πραγματικό μέγεθος
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Σελίδα { $page }

## Loading indicator messages

pdfjs-loading-error = Προέκυψε σφάλμα κατά τη φόρτωση του PDF.
pdfjs-invalid-file-error = Μη έγκυρο ή κατεστραμμένο αρχείο PDF.
pdfjs-missing-file-error = Λείπει αρχείο PDF.
pdfjs-unexpected-response-error = Απρόσμενη απάντηση διακομιστή.
pdfjs-rendering-error = Προέκυψε σφάλμα κατά την εμφάνιση της σελίδας.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Σχόλιο «{ $type }»]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Εισαγάγετε τον κωδικό πρόσβασης για να ανοίξετε αυτό το αρχείο PDF.
pdfjs-password-invalid = Μη έγκυρος κωδικός πρόσβασης. Δοκιμάστε ξανά.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Ακύρωση
pdfjs-web-fonts-disabled = Οι γραμματοσειρές ιστού είναι ανενεργές: δεν είναι δυνατή η χρήση των ενσωματωμένων γραμματοσειρών PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Κείμενο
pdfjs-editor-color-picker-free-text-input =
    .title = Αλλαγή χρώματος κειμένου
pdfjs-editor-free-text-button-label = Κείμενο
pdfjs-editor-ink-button =
    .title = Σχέδιο
pdfjs-editor-color-picker-ink-input =
    .title = Αλλαγή χρώματος σχεδίου
pdfjs-editor-ink-button-label = Σχέδιο
pdfjs-editor-stamp-button =
    .title = Προσθήκη ή επεξεργασία εικόνων
pdfjs-editor-stamp-button-label = Προσθήκη ή επεξεργασία εικόνων
pdfjs-editor-highlight-button =
    .title = Επισήμανση
pdfjs-editor-highlight-button-label = Επισήμανση
pdfjs-highlight-floating-button1 =
    .aria-label = Επισήμανση
    .title = Επισήμανση
pdfjs-highlight-floating-button-label = Επισήμανση
pdfjs-comment-floating-button =
    .aria-label = Σχόλιο
    .title = Σχόλιο
pdfjs-comment-floating-button-label = Σχόλιο
pdfjs-editor-comment-button =
    .aria-label = Σχόλιο
    .title = Σχόλιο
pdfjs-editor-comment-button-label = Σχόλιο
pdfjs-editor-signature-button =
    .title = Προσθήκη υπογραφής
pdfjs-editor-signature-button-label = Προσθήκη υπογραφής

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Επεξεργασία επισήμανσης
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Επεξεργασία σχεδίου
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Επεξεργασία υπογραφής: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Επεξεργασία εικόνας

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Αφαίρεση σχεδίου
pdfjs-editor-remove-freetext-button =
    .title = Αφαίρεση κειμένου
pdfjs-editor-remove-stamp-button =
    .title = Αφαίρεση εικόνας
pdfjs-editor-remove-highlight-button =
    .title = Αφαίρεση επισήμανσης
pdfjs-editor-remove-signature-button =
    .title = Αφαίρεση υπογραφής

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Χρώμα
pdfjs-editor-free-text-size-input = Μέγεθος
pdfjs-editor-ink-color-input = Χρώμα
pdfjs-editor-ink-thickness-input = Πάχος
pdfjs-editor-ink-opacity-input = Αδιαφάνεια
pdfjs-editor-stamp-add-image-button =
    .title = Προσθήκη εικόνας
pdfjs-editor-stamp-add-image-button-label = Προσθήκη εικόνας
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Πάχος
pdfjs-editor-free-highlight-thickness-title =
    .title = Αλλαγή πάχους κατά την επισήμανση στοιχείων εκτός κειμένου
pdfjs-editor-add-signature-container =
    .aria-label = Στοιχεία ελέγχου υπογραφής και αποθηκευμένες υπογραφές
pdfjs-editor-signature-add-signature-button =
    .title = Προσθήκη νέας υπογραφής
pdfjs-editor-signature-add-signature-button-label = Προσθήκη νέας υπογραφής
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Αποθηκευμένη υπογραφή: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Επεξεργασία κειμένου
    .default-content = Ξεκινήστε να πληκτρολογείτε…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Σχόλια
       *[other] Σχόλια
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Κλείσιμο πλευρικής στήλης
    .title = Κλείσιμο πλευρικής στήλης
pdfjs-editor-comments-sidebar-close-button-label = Κλείσιμο πλευρικής στήλης
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Βλέπετε κάτι αξιοσημείωτο; Επισημάνετε το και αφήστε ένα σχόλιο.
pdfjs-editor-comments-sidebar-no-comments-link = Μάθετε περισσότερα

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Εναλλακτικό κείμενο
pdfjs-editor-alt-text-edit-button =
    .aria-label = Επεξεργασία εναλλακτικού κειμένου
pdfjs-editor-alt-text-dialog-label = Διαλέξτε μια επιλογή
pdfjs-editor-alt-text-dialog-description = Το εναλλακτικό κείμενο είναι χρήσιμο όταν οι άνθρωποι δεν μπορούν να δουν την εικόνα ή όταν αυτή δεν φορτώνεται.
pdfjs-editor-alt-text-add-description-label = Προσθήκη περιγραφής
pdfjs-editor-alt-text-add-description-description = Στοχεύστε σε μία ή δύο προτάσεις που περιγράφουν το θέμα, τη ρύθμιση ή τις ενέργειες.
pdfjs-editor-alt-text-mark-decorative-label = Επισήμανση ως διακοσμητικό
pdfjs-editor-alt-text-mark-decorative-description = Χρησιμοποιείται για διακοσμητικές εικόνες, όπως περιγράμματα ή υδατογραφήματα.
pdfjs-editor-alt-text-cancel-button = Ακύρωση
pdfjs-editor-alt-text-save-button = Αποθήκευση
pdfjs-editor-alt-text-decorative-tooltip = Επισημασμένο ως διακοσμητικό
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Για παράδειγμα, «Ένας νεαρός άνδρας κάθεται σε ένα τραπέζι για να φάει ένα γεύμα»
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Εναλλακτικό κείμενο

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Επάνω αριστερή γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-top-middle =
    .aria-label = Μέσο επάνω πλευράς — αλλαγή μεγέθους
pdfjs-editor-resizer-top-right =
    .aria-label = Επάνω δεξιά γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-middle-right =
    .aria-label = Μέσο δεξιάς πλευράς — αλλαγή μεγέθους
pdfjs-editor-resizer-bottom-right =
    .aria-label = Κάτω δεξιά γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Μέσο κάτω πλευράς — αλλαγή μεγέθους
pdfjs-editor-resizer-bottom-left =
    .aria-label = Κάτω αριστερή γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-middle-left =
    .aria-label = Μέσο αριστερής πλευράς — αλλαγή μεγέθους

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Χρώμα επισήμανσης
pdfjs-editor-colorpicker-button =
    .title = Αλλαγή χρώματος
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Επιλογές χρωμάτων
pdfjs-editor-colorpicker-yellow =
    .title = Κίτρινο
pdfjs-editor-colorpicker-green =
    .title = Πράσινο
pdfjs-editor-colorpicker-blue =
    .title = Μπλε
pdfjs-editor-colorpicker-pink =
    .title = Ροζ
pdfjs-editor-colorpicker-red =
    .title = Κόκκινο

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Εμφάνιση όλων
pdfjs-editor-highlight-show-all-button =
    .title = Εμφάνιση όλων

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Επεξεργασία εναλλακτικού κειμένου (περιγραφή εικόνας)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Προσθήκη εναλλακτικού κειμένου (περιγραφή εικόνας)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Γράψτε την περιγραφή σας εδώ…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Σύντομη περιγραφή για άτομα που δεν μπορούν να δουν την εικόνα ή όταν η εικόνα δεν φορτώνεται.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Αυτό το εναλλακτικό κείμενο δημιουργήθηκε αυτόματα και ενδέχεται να είναι ανακριβές.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Μάθετε περισσότερα
pdfjs-editor-new-alt-text-create-automatically-button-label = Αυτόματη δημιουργία εναλλακτικού κειμένου
pdfjs-editor-new-alt-text-not-now-button = Όχι τώρα
pdfjs-editor-new-alt-text-error-title = Δεν ήταν δυνατή η αυτόματη δημιουργία εναλλακτικού κειμένου
pdfjs-editor-new-alt-text-error-description = Γράψτε το δικό σας εναλλακτικό κείμενο ή δοκιμάστε ξανά αργότερα.
pdfjs-editor-new-alt-text-error-close-button = Κλείσιμο
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Λήψη μοντέλου ΤΝ εναλλακτικού κειμένου ({ $downloadedSize } από { $totalSize } MB)
    .aria-valuetext = Λήψη μοντέλου ΤΝ εναλλακτικού κειμένου ({ $downloadedSize } από { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Προστέθηκε εναλλακτικό κείμενο
pdfjs-editor-new-alt-text-added-button-label = Προστέθηκε εναλλακτικό κείμενο
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Απουσία εναλλακτικού κειμένου
pdfjs-editor-new-alt-text-missing-button-label = Απουσία εναλλακτικού κειμένου
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Έλεγχος εναλλακτικού κειμένου
pdfjs-editor-new-alt-text-to-review-button-label = Έλεγχος εναλλακτικού κειμένου
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Αυτόματη δημιουργία: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Ρυθμίσεις εναλλακτικού κειμένου εικόνας
pdfjs-image-alt-text-settings-button-label = Ρυθμίσεις εναλλακτικού κειμένου εικόνας
pdfjs-editor-alt-text-settings-dialog-label = Ρυθμίσεις εναλλακτικού κειμένου εικόνας
pdfjs-editor-alt-text-settings-automatic-title = Αυτόματο εναλλακτικό κείμενο
pdfjs-editor-alt-text-settings-create-model-button-label = Αυτόματη δημιουργία εναλλακτικού κειμένου
pdfjs-editor-alt-text-settings-create-model-description = Προτείνει περιγραφές για άτομα που δεν μπορούν να δουν την εικόνα ή όταν η εικόνα δεν φορτώνεται.
pdfjs-editor-alt-text-settings-editor-title = Επεξεργασία εναλλακτικού κειμένου
pdfjs-editor-alt-text-settings-show-dialog-button-label = Άμεση εμφάνιση της επεξεργασίας εναλλακτικού κειμένου κατά την προσθήκη εικόνας
pdfjs-editor-alt-text-settings-show-dialog-description = Σας βοηθά να βεβαιωθείτε ότι όλες οι εικόνες σας έχουν εναλλακτικό κείμενο.
pdfjs-editor-alt-text-settings-close-button = Κλείσιμο

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Προστέθηκε επισήμανση
pdfjs-editor-freetext-added-alert = Προστέθηκε κείμενο
pdfjs-editor-ink-added-alert = Προστέθηκε σχέδιο
pdfjs-editor-stamp-added-alert = Προστέθηκε εικόνα
pdfjs-editor-signature-added-alert = Προστέθηκε υπογραφή

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Η επισήμανση αφαιρέθηκε
pdfjs-editor-undo-bar-message-freetext = Το κείμενο αφαιρέθηκε
pdfjs-editor-undo-bar-message-ink = Το σχέδιο αφαιρέθηκε
pdfjs-editor-undo-bar-message-stamp = Η εικόνα αφαιρέθηκε
pdfjs-editor-undo-bar-message-signature = Η υπογραφή αφαιρέθηκε
pdfjs-editor-undo-bar-message-comment = Το σχόλιο αφαιρέθηκε
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] Αφαιρέθηκε { $count } σχολιασμός
       *[other] Αφαιρέθηκαν { $count } σχολιασμοί
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Αναίρεση
pdfjs-editor-undo-bar-undo-button-label = Αναίρεση
pdfjs-editor-undo-bar-close-button =
    .title = Κλείσιμο
pdfjs-editor-undo-bar-close-button-label = Κλείσιμο

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Αυτό το παράθυρο διαλόγου επιτρέπει στον χρήστη να δημιουργήσει μια υπογραφή για να την προσθέσει σε ένα έγγραφο PDF. Ο χρήστης μπορεί να επεξεργαστεί το όνομα (το οποίο χρησιμεύει και ως εναλλακτικό κείμενο) και, προαιρετικά, να αποθηκεύσει την υπογραφή για επαναλαμβανόμενη χρήση.
pdfjs-editor-add-signature-dialog-title = Προσθήκη υπογραφής

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Πληκτρολόγηση
    .title = Πληκτρολόγηση
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Σχέδιο
    .title = Σχέδιο
pdfjs-editor-add-signature-image-button = Εικόνα
    .title = Εικόνα

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Πληκτρολογήστε την υπογραφή σας
    .placeholder = Πληκτρολογήστε την υπογραφή σας
pdfjs-editor-add-signature-draw-placeholder = Σχεδιάστε την υπογραφή σας
pdfjs-editor-add-signature-draw-thickness-range-label = Πάχος
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Πάχος σχεδίου: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Σύρετε ένα αρχείο εδώ για μεταφόρτωση
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ή επιλέξτε αρχεία εικόνας
       *[other] Ή περιηγηθείτε σε αρχεία εικόνας
    }

## Controls

pdfjs-editor-add-signature-description-label = Περιγραφή (εναλλακτικό κείμενο)
pdfjs-editor-add-signature-description-input =
    .title = Περιγραφή (εναλλακτικό κείμενο)
pdfjs-editor-add-signature-description-default-when-drawing = Υπογραφή
pdfjs-editor-add-signature-clear-button-label = Απαλοιφή υπογραφής
pdfjs-editor-add-signature-clear-button =
    .title = Απαλοιφή υπογραφής
pdfjs-editor-add-signature-save-checkbox = Αποθήκευση υπογραφής
pdfjs-editor-add-signature-save-warning-message = Έχετε φτάσει το όριο των 5 αποθηκευμένων υπογραφών. Αφαιρέστε μία για να αποθηκεύσετε περισσότερες.
pdfjs-editor-add-signature-image-upload-error-title = Δεν ήταν δυνατή η μεταφόρτωση της εικόνας
pdfjs-editor-add-signature-image-upload-error-description = Ελέγξτε τη σύνδεση δικτύου σας ή δοκιμάστε μια άλλη εικόνα.
pdfjs-editor-add-signature-image-no-data-error-title = Δεν είναι δυνατή η μετατροπή αυτής της εικόνας σε υπογραφή
pdfjs-editor-add-signature-image-no-data-error-description = Δοκιμάστε να μεταφορτώσετε μια άλλη εικόνα.
pdfjs-editor-add-signature-error-close-button = Κλείσιμο

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Ακύρωση
pdfjs-editor-add-signature-add-button = Προσθήκη
pdfjs-editor-edit-signature-update-button = Ενημέρωση

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Επεξεργασία σχολίου
pdfjs-editor-edit-comment-popup-button =
    .title = Επεξεργασία σχολίου
pdfjs-editor-delete-comment-popup-button-label = Αφαίρεση σχολίου
pdfjs-editor-delete-comment-popup-button =
    .title = Αφαίρεση σχολίου
pdfjs-show-comment-button =
    .title = Εμφάνιση σχολίου

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Επεξεργασία σχολίου
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Ενημέρωση
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Προσθήκη σχολίου
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Προσθήκη
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Ξεκινήστε να πληκτρολογείτε…
pdfjs-editor-edit-comment-dialog-cancel-button = Ακύρωση

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Προσθήκη σχολίου

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = (Απ)ενεργοποίηση πλαϊνής γραμμής (το έγγραφο περιέχει μικρογραφίες/περίγραμμα/συνημμένα/επίπεδα)
pdfjs-toggle-views-manager-button1-label = Διαχείριση σελίδων
pdfjs-views-manager-sidebar =
    .aria-label = Πλαϊνή γραμμή
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Αλλαγή μεγέθους πλαϊνής γραμμής
pdfjs-views-manager-view-selector-button =
    .title = Προβολές
pdfjs-views-manager-view-selector-button-label = Προβολές
pdfjs-views-manager-pages-title = Σελίδες
pdfjs-views-manager-outlines-title1 = Διάρθρωση εγγράφου
    .title = Διάρθρωση εγγράφου (διπλό κλικ για ανάπτυξη/σύμπτυξη όλων των στοιχείων)
pdfjs-views-manager-attachments-title = Συνημμένα
pdfjs-views-manager-layers-title1 = Επίπεδα
    .title = Επίπεδα (διπλό κλικ για επαναφορά όλων των επιπέδων στην προεπιλεγμένη κατάσταση)
pdfjs-views-manager-pages-option-label = Σελίδες
pdfjs-views-manager-outlines-option-label = Διάρθρωση εγγράφου
pdfjs-views-manager-attachments-option-label = Συνημμένα
pdfjs-views-manager-layers-option-label = Επίπεδα
pdfjs-views-manager-add-file-button =
    .title = Προσθήκη αρχείου
pdfjs-views-manager-add-file-button-label = Προσθήκη αρχείου
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } επιλεγμένη
       *[other] { $count } επιλεγμένες
    }
pdfjs-views-manager-pages-status-none-action-label = Επιλογή σελίδων
pdfjs-views-manager-pages-status-action-button-label = Διαχείριση
pdfjs-views-manager-pages-status-copy-button-label = Αντιγραφή
pdfjs-views-manager-pages-status-cut-button-label = Αποκοπή
pdfjs-views-manager-pages-status-delete-button-label = Διαγραφή
pdfjs-views-manager-pages-status-export-selected-button-label = Εξαγωγή επιλεγμένων…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] Αποκόπηκε 1 σελίδα
       *[other] Αποκόπηκαν { $count } σελίδες
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] Αντιγράφηκε 1 σελίδα
       *[other] Αντιγράφηκαν { $count } σελίδες
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] Διαγράφηκε 1 σελίδα
       *[other] Διαγράφηκαν { $count } σελίδες
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Προετοιμασία αρχείου…
pdfjs-views-manager-pages-status-waiting-uploading-label = Μεταφόρτωση αρχείου…
pdfjs-views-manager-status-warning-cut-label = Δεν ήταν δυνατή η αποκοπή. Ανανεώστε τη σελίδα και δοκιμάστε ξανά.
pdfjs-views-manager-status-warning-copy-label = Δεν ήταν δυνατή η αντιγραφή. Ανανεώστε τη σελίδα και δοκιμάστε ξανά.
pdfjs-views-manager-status-warning-delete-label = Δεν ήταν δυνατή η διαγραφή. Ανανεώστε τη σελίδα και δοκιμάστε ξανά.
pdfjs-views-manager-status-warning-save-label = Δεν ήταν δυνατή η αποθήκευση. Ανανεώστε τη σελίδα και δοκιμάστε ξανά.
pdfjs-views-manager-status-undo-button-label = Αναίρεση
pdfjs-views-manager-status-done-button-label = Τέλος
pdfjs-views-manager-status-close-button =
    .title = Κλείσιμο
pdfjs-views-manager-status-close-button-label = Κλείσιμο
pdfjs-views-manager-paste-button-label = Επικόλληση
pdfjs-views-manager-paste-button-before =
    .title = Επικόλληση πριν από την πρώτη σελίδα
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Επικόλληση μετά τη σελίδα { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = ΝΕΟ
pdfjs-views-manager-waiting-for-file = Μεταφόρτωση αρχείου…
pdfjs-toggle-views-manager-button1 =
    .title = Διαχείριση σελίδων

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Ιδιότητες ψηφιακής υπογραφής
    .title = Ιδιότητες ψηφιακής υπογραφής
pdfjs-digital-signature-properties-button-label = Ιδιότητες ψηφιακής υπογραφής

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Το έγγραφο έχει υπογραφεί με έγκυρη ψηφιακή υπογραφή
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Το έγγραφο έχει υπογραφεί, αλλά δεν ήταν δυνατή η επαλήθευση { $count } ψηφιακής υπογραφής
       *[other] Το έγγραφο έχει υπογραφεί, αλλά δεν ήταν δυνατή η επαλήθευση { $count } ψηφιακών υπογραφών
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Το έγγραφο έχει υπογραφεί με { $count } πιστοποιητικό που δεν είναι αξιόπιστο
       *[other] Το έγγραφο έχει υπογραφεί με { $count } πιστοποιητικά που δεν είναι αξιόπιστα
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Το έγγραφο έχει υπογραφεί με { $count } ληγμένο πιστοποιητικό
       *[other] Το έγγραφο έχει υπογραφεί με { $count } ληγμένα πιστοποιητικά
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] Το έγγραφο διαθέτει { $count } μη έγκυρη ψηφιακή υπογραφή
       *[other] Το έγγραφο διαθέτει { $count } μη έγκυρες ψηφιακές υπογραφές
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Το έγγραφο έχει υπογραφεί με { $count } ανακληθέν πιστοποιητικό
       *[other] Το έγγραφο έχει υπογραφεί με { $count } ανακληθέντα πιστοποιητικά
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Κατάσταση: Επαληθευμένη υπογραφή
pdfjs-digital-signature-properties-status-invalid = Κατάσταση: Μη έγκυρη υπογραφή
pdfjs-digital-signature-properties-status-unknown = Κατάσταση: Αδυναμία επαλήθευσης (δεν υποστηρίζεται)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Πιστοποιητικό: Έμπιστο ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Πιστοποιητικό: Μη διαθέσιμο
pdfjs-digital-signature-properties-certificate-untrusted = Πιστοποιητικό: Μη αξιόπιστο
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Πιστοποιητικό: Άγνωστος εκδότης ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Πιστοποιητικό: Αυτοϋπογεγραμμένο ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Πιστοποιητικό: Μη αξιόπιστος εκδότης ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Πιστοποιητικό: Έχει λήξει
pdfjs-digital-signature-properties-certificate-expired-with-date = Πιστοποιητικό: Έχει λήξει ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Πιστοποιητικό: Έχει ανακληθεί

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Αφαίρεση αποθηκευμένης υπογραφής
pdfjs-editor-delete-signature-button-label1 = Αφαίρεση αποθηκευμένης υπογραφής

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Επεξεργασία περιγραφής

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Επεξεργασία περιγραφής
