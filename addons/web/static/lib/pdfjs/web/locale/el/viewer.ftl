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
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bytes)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bytes)
pdfjs-document-properties-title = Τίτλος:
pdfjs-document-properties-author = Συγγραφέας:
pdfjs-document-properties-subject = Θέμα:
pdfjs-document-properties-keywords = Λέξεις-κλειδιά:
pdfjs-document-properties-creation-date = Ημερομηνία δημιουργίας:
pdfjs-document-properties-modification-date = Ημερομηνία τροποποίησης:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
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

## Print

pdfjs-print-progress-message = Προετοιμασία του εγγράφου για εκτύπωση…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Ακύρωση
pdfjs-printing-not-supported = Προειδοποίηση: Η εκτύπωση δεν υποστηρίζεται πλήρως από το πρόγραμμα περιήγησης.
pdfjs-printing-not-ready = Προειδοποίηση: Το PDF δεν φορτώθηκε πλήρως για εκτύπωση.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = (Απ)ενεργοποίηση πλαϊνής γραμμής
pdfjs-toggle-sidebar-notification-button =
    .title = (Απ)ενεργοποίηση πλαϊνής γραμμής (το έγγραφο περιέχει περίγραμμα/συνημμένα/επίπεδα)
pdfjs-toggle-sidebar-button-label = (Απ)ενεργοποίηση πλαϊνής γραμμής
pdfjs-document-outline-button =
    .title = Εμφάνιση διάρθρωσης εγγράφου (διπλό κλικ για ανάπτυξη/σύμπτυξη όλων των στοιχείων)
pdfjs-document-outline-button-label = Διάρθρωση εγγράφου
pdfjs-attachments-button =
    .title = Εμφάνιση συνημμένων
pdfjs-attachments-button-label = Συνημμένα
pdfjs-layers-button =
    .title = Εμφάνιση επιπέδων (διπλό κλικ για επαναφορά όλων των επιπέδων στην προεπιλεγμένη κατάσταση)
pdfjs-layers-button-label = Επίπεδα
pdfjs-thumbs-button =
    .title = Εμφάνιση μικρογραφιών
pdfjs-thumbs-button-label = Μικρογραφίες
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
pdfjs-thumb-page-title =
    .title = Σελίδα { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Μικρογραφία σελίδας { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Εύρεση
    .placeholder = Εύρεση στο έγγραφο…
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
    .title = Επισήμανση
    .aria-label = Επισήμανση
pdfjs-highlight-floating-button-label = Επισήμανση
pdfjs-comment-floating-button =
    .title = Σχόλιο
    .aria-label = Σχόλιο
pdfjs-comment-floating-button-label = Σχόλιο
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
pdfjs-free-text =
    .aria-label = Επεξεργασία κειμένου
pdfjs-free-text-default-content = Ξεκινήστε να πληκτρολογείτε…
pdfjs-ink =
    .aria-label = Επεξεργασία σχεδίων
pdfjs-ink-canvas =
    .aria-label = Εικόνα από τον χρήστη

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Εναλλακτικό κείμενο
pdfjs-editor-alt-text-edit-button =
    .aria-label = Επεξεργασία εναλλακτικού κειμένου
pdfjs-editor-alt-text-edit-button-label = Επεξεργασία εναλλακτικού κειμένου
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

pdfjs-editor-resizer-label-top-left = Επάνω αριστερή γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-label-top-middle = Μέσο επάνω πλευράς — αλλαγή μεγέθους
pdfjs-editor-resizer-label-top-right = Επάνω δεξιά γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-label-middle-right = Μέσο δεξιάς πλευράς — αλλαγή μεγέθους
pdfjs-editor-resizer-label-bottom-right = Κάτω δεξιά γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-label-bottom-middle = Μέσο κάτω πλευράς — αλλαγή μεγέθους
pdfjs-editor-resizer-label-bottom-left = Κάτω αριστερή γωνία — αλλαγή μεγέθους
pdfjs-editor-resizer-label-middle-left = Μέσο αριστερής πλευράς — αλλαγή μεγέθους
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
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Μοντέλο ΤΝ εναλλακτικού κειμένου ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Εκτελείται τοπικά στη συσκευή σας, ώστε τα δεδομένα σας να παραμένουν ιδιωτικά. Απαιτείται για τη δημιουργία του αυτόματου εναλλακτικού κειμένου.
pdfjs-editor-alt-text-settings-delete-model-button = Διαγραφή
pdfjs-editor-alt-text-settings-download-model-button = Λήψη
pdfjs-editor-alt-text-settings-downloading-model-button = Λήψη…
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

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Ενέργειες
pdfjs-editor-edit-comment-actions-button =
    .title = Ενέργειες
pdfjs-editor-edit-comment-close-button-label = Κλείσιμο
pdfjs-editor-edit-comment-close-button =
    .title = Κλείσιμο
pdfjs-editor-edit-comment-actions-edit-button-label = Επεξεργασία
pdfjs-editor-edit-comment-actions-delete-button-label = Διαγραφή
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Εισαγάγετε το σχόλιό σας
pdfjs-editor-edit-comment-manager-cancel-button = Ακύρωση
pdfjs-editor-edit-comment-manager-save-button = Αποθήκευση

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Επεξεργασία σχολίου

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Αφαίρεση αποθηκευμένης υπογραφής
pdfjs-editor-delete-signature-button-label1 = Αφαίρεση αποθηκευμένης υπογραφής

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Επεξεργασία περιγραφής

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Επεξεργασία περιγραφής
