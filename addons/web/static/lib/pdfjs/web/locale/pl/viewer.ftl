# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Poprzednia strona
pdfjs-previous-button-label = Poprzednia
pdfjs-next-button =
    .title = Następna strona
pdfjs-next-button-label = Następna
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Strona
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = z { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } z { $pagesCount })
pdfjs-zoom-out-button =
    .title = Pomniejsz
pdfjs-zoom-out-button-label = Pomniejsz
pdfjs-zoom-in-button =
    .title = Powiększ
pdfjs-zoom-in-button-label = Powiększ
pdfjs-zoom-select =
    .title = Skala
pdfjs-presentation-mode-button =
    .title = Przełącz na tryb prezentacji
pdfjs-presentation-mode-button-label = Tryb prezentacji
pdfjs-open-file-button =
    .title = Otwórz plik
pdfjs-open-file-button-label = Otwórz
pdfjs-print-button =
    .title = Drukuj
pdfjs-print-button-label = Drukuj
pdfjs-save-button =
    .title = Zapisz
pdfjs-save-button-label = Zapisz
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Pobierz
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Pobierz
pdfjs-bookmark-button =
    .title = Bieżąca strona (adres do otwarcia na bieżącej stronie)
pdfjs-bookmark-button-label = Bieżąca strona

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Narzędzia
pdfjs-tools-button-label = Narzędzia
pdfjs-first-page-button =
    .title = Przejdź do pierwszej strony
pdfjs-first-page-button-label = Przejdź do pierwszej strony
pdfjs-last-page-button =
    .title = Przejdź do ostatniej strony
pdfjs-last-page-button-label = Przejdź do ostatniej strony
pdfjs-page-rotate-cw-button =
    .title = Obróć zgodnie z ruchem wskazówek zegara
pdfjs-page-rotate-cw-button-label = Obróć zgodnie z ruchem wskazówek zegara
pdfjs-page-rotate-ccw-button =
    .title = Obróć przeciwnie do ruchu wskazówek zegara
pdfjs-page-rotate-ccw-button-label = Obróć przeciwnie do ruchu wskazówek zegara
pdfjs-cursor-text-select-tool-button =
    .title = Włącz narzędzie zaznaczania tekstu
pdfjs-cursor-text-select-tool-button-label = Narzędzie zaznaczania tekstu
pdfjs-cursor-hand-tool-button =
    .title = Włącz narzędzie rączka
pdfjs-cursor-hand-tool-button-label = Narzędzie rączka
pdfjs-scroll-page-button =
    .title = Przewijaj strony
pdfjs-scroll-page-button-label = Przewijanie stron
pdfjs-scroll-vertical-button =
    .title = Przewijaj dokument w pionie
pdfjs-scroll-vertical-button-label = Przewijanie pionowe
pdfjs-scroll-horizontal-button =
    .title = Przewijaj dokument w poziomie
pdfjs-scroll-horizontal-button-label = Przewijanie poziome
pdfjs-scroll-wrapped-button =
    .title = Strony dokumentu wyświetlaj i przewijaj w kolumnach
pdfjs-scroll-wrapped-button-label = Widok dwóch stron
pdfjs-spread-none-button =
    .title = Nie ustawiaj stron obok siebie
pdfjs-spread-none-button-label = Brak kolumn
pdfjs-spread-odd-button =
    .title = Strony nieparzyste ustawiaj na lewo od parzystych
pdfjs-spread-odd-button-label = Nieparzyste po lewej
pdfjs-spread-even-button =
    .title = Strony parzyste ustawiaj na lewo od nieparzystych
pdfjs-spread-even-button-label = Parzyste po lewej

## Document properties dialog

pdfjs-document-properties-button =
    .title = Właściwości dokumentu…
pdfjs-document-properties-button-label = Właściwości dokumentu…
pdfjs-document-properties-file-name = Nazwa pliku:
pdfjs-document-properties-file-size = Rozmiar pliku:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } B)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } B)
pdfjs-document-properties-title = Tytuł:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Temat:
pdfjs-document-properties-keywords = Słowa kluczowe:
pdfjs-document-properties-creation-date = Data utworzenia:
pdfjs-document-properties-modification-date = Data modyfikacji:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Utworzony przez:
pdfjs-document-properties-producer = PDF wyprodukowany przez:
pdfjs-document-properties-version = Wersja PDF:
pdfjs-document-properties-page-count = Liczba stron:
pdfjs-document-properties-page-size = Wymiary strony:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = pionowa
pdfjs-document-properties-page-size-orientation-landscape = pozioma
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = US Letter
pdfjs-document-properties-page-size-name-legal = US Legal

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = { $width }×{ $height } { $unit } (orientacja { $orientation })
pdfjs-document-properties-page-size-dimension-name-string = { $width }×{ $height } { $unit } ({ $name }, orientacja { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = Szybki podgląd w Internecie:
pdfjs-document-properties-linearized-yes = tak
pdfjs-document-properties-linearized-no = nie
pdfjs-document-properties-close-button = Zamknij

## Print

pdfjs-print-progress-message = Przygotowywanie dokumentu do druku…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Anuluj
pdfjs-printing-not-supported = Ostrzeżenie: drukowanie nie jest w pełni obsługiwane przez tę przeglądarkę.
pdfjs-printing-not-ready = Ostrzeżenie: dokument PDF nie jest całkowicie wczytany, więc nie można go wydrukować.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Przełącz panel boczny
pdfjs-toggle-sidebar-notification-button =
    .title = Przełącz panel boczny (dokument zawiera konspekt/załączniki/warstwy)
pdfjs-toggle-sidebar-button-label = Przełącz panel boczny
pdfjs-document-outline-button =
    .title = Konspekt dokumentu (podwójne kliknięcie rozwija lub zwija wszystkie pozycje)
pdfjs-document-outline-button-label = Konspekt dokumentu
pdfjs-attachments-button =
    .title = Załączniki
pdfjs-attachments-button-label = Załączniki
pdfjs-layers-button =
    .title = Warstwy (podwójne kliknięcie przywraca wszystkie warstwy do stanu domyślnego)
pdfjs-layers-button-label = Warstwy
pdfjs-thumbs-button =
    .title = Miniatury
pdfjs-thumbs-button-label = Miniatury
pdfjs-current-outline-item-button =
    .title = Znajdź bieżący element konspektu
pdfjs-current-outline-item-button-label = Bieżący element konspektu
pdfjs-findbar-button =
    .title = Znajdź w dokumencie
pdfjs-findbar-button-label = Znajdź
pdfjs-additional-layers = Dodatkowe warstwy

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = { $page }. strona
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura { $page }. strony

## Find panel button title and messages

pdfjs-find-input =
    .title = Znajdź
    .placeholder = Znajdź w dokumencie…
pdfjs-find-previous-button =
    .title = Znajdź poprzednie wystąpienie tekstu
pdfjs-find-previous-button-label = Poprzednie
pdfjs-find-next-button =
    .title = Znajdź następne wystąpienie tekstu
pdfjs-find-next-button-label = Następne
pdfjs-find-highlight-checkbox = Wyróżnianie wszystkich
pdfjs-find-match-case-checkbox-label = Rozróżnianie wielkości liter
pdfjs-find-match-diacritics-checkbox-label = Rozróżnianie liter diakrytyzowanych
pdfjs-find-entire-word-checkbox-label = Całe słowa
pdfjs-find-reached-top = Początek dokumentu. Wyszukiwanie od końca.
pdfjs-find-reached-bottom = Koniec dokumentu. Wyszukiwanie od początku.
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current }. z { $total } trafienia
        [few] { $current }. z { $total } trafień
       *[many] { $current }. z { $total } trafień
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Więcej niż { $limit } trafienie
        [few] Więcej niż { $limit } trafienia
       *[many] Więcej niż { $limit } trafień
    }
pdfjs-find-not-found = Nie znaleziono tekstu

## Predefined zoom values

pdfjs-page-scale-width = Szerokość strony
pdfjs-page-scale-fit = Dopasowanie strony
pdfjs-page-scale-auto = Skala automatyczna
pdfjs-page-scale-actual = Rozmiar oryginalny
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = { $page }. strona

## Loading indicator messages

pdfjs-loading-error = Podczas wczytywania dokumentu PDF wystąpił błąd.
pdfjs-invalid-file-error = Nieprawidłowy lub uszkodzony plik PDF.
pdfjs-missing-file-error = Brak pliku PDF.
pdfjs-unexpected-response-error = Nieoczekiwana odpowiedź serwera.
pdfjs-rendering-error = Podczas renderowania strony wystąpił błąd.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Przypis: { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Wpisz hasło, aby otworzyć ten dokument PDF.
pdfjs-password-invalid = Nieprawidłowe hasło. Proszę spróbować ponownie.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Anuluj
pdfjs-web-fonts-disabled = Czcionki sieciowe są wyłączone: nie można użyć osadzonych czcionek PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Tekst
pdfjs-editor-color-picker-free-text-input =
    .title = Zmień kolor tekstu
pdfjs-editor-free-text-button-label = Tekst
pdfjs-editor-ink-button =
    .title = Rysunek
pdfjs-editor-color-picker-ink-input =
    .title = Zmień kolor rysunku
pdfjs-editor-ink-button-label = Rysunek
pdfjs-editor-stamp-button =
    .title = Dodaj lub edytuj obrazy
pdfjs-editor-stamp-button-label = Dodaj lub edytuj obrazy
pdfjs-editor-highlight-button =
    .title = Wyróżnij
pdfjs-editor-highlight-button-label = Wyróżnij
pdfjs-highlight-floating-button1 =
    .title = Wyróżnij
    .aria-label = Wyróżnij
pdfjs-highlight-floating-button-label = Wyróżnij
pdfjs-comment-floating-button =
    .title = Dodaj komentarz
    .aria-label = Dodaj komentarz
pdfjs-comment-floating-button-label = Dodaj komentarz
pdfjs-editor-comment-button =
    .title = Dodaj komentarz
    .aria-label = Dodaj komentarz
pdfjs-editor-comment-button-label = Dodaj komentarz
pdfjs-editor-signature-button =
    .title = Dodaj podpis
pdfjs-editor-signature-button-label = Dodaj podpis

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Edytor wyróżnienia
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Edytor rysunku
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Edytor podpisu: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Edytor obrazu

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Usuń rysunek
pdfjs-editor-remove-freetext-button =
    .title = Usuń tekst
pdfjs-editor-remove-stamp-button =
    .title = Usuń obraz
pdfjs-editor-remove-highlight-button =
    .title = Usuń wyróżnienie
pdfjs-editor-remove-signature-button =
    .title = Usuń podpis

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Kolor
pdfjs-editor-free-text-size-input = Rozmiar
pdfjs-editor-ink-color-input = Kolor
pdfjs-editor-ink-thickness-input = Grubość
pdfjs-editor-ink-opacity-input = Nieprzezroczystość
pdfjs-editor-stamp-add-image-button =
    .title = Dodaj obraz
pdfjs-editor-stamp-add-image-button-label = Dodaj obraz
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Grubość
pdfjs-editor-free-highlight-thickness-title =
    .title = Zmień grubość podczas wyróżniania elementów innych niż tekst
pdfjs-editor-add-signature-container =
    .aria-label = Sterowanie podpisami i zachowane podpisy
pdfjs-editor-signature-add-signature-button =
    .title = Dodaj nowy podpis
pdfjs-editor-signature-add-signature-button-label = Dodaj nowy podpis
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Zachowany podpis: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Edytor tekstu
    .default-content = Zacznij pisać…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Komentarz
       *[other] Komentarze
    }
pdfjs-editor-comments-sidebar-close-button =
    .title = Zamknij panel boczny
    .aria-label = Zamknij panel boczny
pdfjs-editor-comments-sidebar-close-button-label = Zamknij panel boczny
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Widzisz coś godnego uwagi? Wyróżnij to i zostaw komentarz.
pdfjs-editor-comments-sidebar-no-comments-link = Więcej informacji

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Tekst alternatywny
pdfjs-editor-alt-text-edit-button =
    .aria-label = Edytuj tekst alternatywny
pdfjs-editor-alt-text-dialog-label = Wybierz opcję
pdfjs-editor-alt-text-dialog-description = Tekst alternatywny pomaga, kiedy ktoś nie może zobaczyć obrazu lub gdy się nie wczytuje.
pdfjs-editor-alt-text-add-description-label = Dodaj opis
pdfjs-editor-alt-text-add-description-description = Staraj się napisać 1-2 zdania opisujące temat, miejsce lub działania.
pdfjs-editor-alt-text-mark-decorative-label = Oznacz jako dekoracyjne
pdfjs-editor-alt-text-mark-decorative-description = Używane w przypadku obrazów ozdobnych, takich jak obramowania lub znaki wodne.
pdfjs-editor-alt-text-cancel-button = Anuluj
pdfjs-editor-alt-text-save-button = Zapisz
pdfjs-editor-alt-text-decorative-tooltip = Oznaczone jako dekoracyjne
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Na przykład: „Młody człowiek siada przy stole, aby zjeść posiłek”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Tekst alternatywny

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Lewy górny róg — zmień rozmiar
pdfjs-editor-resizer-top-middle =
    .aria-label = Górny środkowy — zmień rozmiar
pdfjs-editor-resizer-top-right =
    .aria-label = Prawy górny róg — zmień rozmiar
pdfjs-editor-resizer-middle-right =
    .aria-label = Prawy środkowy — zmień rozmiar
pdfjs-editor-resizer-bottom-right =
    .aria-label = Prawy dolny róg — zmień rozmiar
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Dolny środkowy — zmień rozmiar
pdfjs-editor-resizer-bottom-left =
    .aria-label = Lewy dolny róg — zmień rozmiar
pdfjs-editor-resizer-middle-left =
    .aria-label = Lewy środkowy — zmień rozmiar

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Kolor wyróżnienia
pdfjs-editor-colorpicker-button =
    .title = Zmień kolor
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Wybór kolorów
pdfjs-editor-colorpicker-yellow =
    .title = Żółty
pdfjs-editor-colorpicker-green =
    .title = Zielony
pdfjs-editor-colorpicker-blue =
    .title = Niebieski
pdfjs-editor-colorpicker-pink =
    .title = Różowy
pdfjs-editor-colorpicker-red =
    .title = Czerwony

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Pokaż wszystkie
pdfjs-editor-highlight-show-all-button =
    .title = Pokaż wszystkie

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Edytuj tekst alternatywny (opis obrazu)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Dodaj tekst alternatywny (opis obrazu)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Napisz tutaj opis…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Krótki opis dla osób, które nie widzą obrazu lub kiedy obraz się nie wczytuje.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ten tekst alternatywny został utworzony automatycznie i może być niepoprawny.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Więcej informacji
pdfjs-editor-new-alt-text-create-automatically-button-label = Automatycznie utwórz tekst alternatywny
pdfjs-editor-new-alt-text-not-now-button = Nie teraz
pdfjs-editor-new-alt-text-error-title = Nie można automatycznie utworzyć tekstu alternatywnego
pdfjs-editor-new-alt-text-error-description = Proszę napisać własny tekst alternatywny lub spróbować ponownie później.
pdfjs-editor-new-alt-text-error-close-button = Zamknij
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Pobieranie modelu SI tekstu alternatywnego ({ $downloadedSize } z { $totalSize } MB)
    .aria-valuetext = Pobieranie modelu SI tekstu alternatywnego ({ $downloadedSize } z { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Dodano tekst alternatywny
pdfjs-editor-new-alt-text-added-button-label = Dodano tekst alternatywny
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Brak tekstu alternatywnego
pdfjs-editor-new-alt-text-missing-button-label = Brak tekstu alternatywnego
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Przejrzyj tekst alternatywny
pdfjs-editor-new-alt-text-to-review-button-label = Przejrzyj tekst alternatywny
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Utworzono automatycznie: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Ustawienia tekstu alternatywnego obrazów
pdfjs-image-alt-text-settings-button-label = Ustawienia tekstu alternatywnego obrazów
pdfjs-editor-alt-text-settings-dialog-label = Ustawienia tekstu alternatywnego obrazów
pdfjs-editor-alt-text-settings-automatic-title = Automatyczny tekst alternatywny
pdfjs-editor-alt-text-settings-create-model-button-label = Automatyczne tworzenie tekstu alternatywnego
pdfjs-editor-alt-text-settings-create-model-description = Podpowiada opisy, które mogą pomóc osobom, które nie widzą obrazu lub kiedy obraz się nie wczytuje.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Model SI tekstu alternatywnego ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Działa lokalnie na urządzeniu użytkownika, więc Twoje dane pozostają prywatne. Wymagane do funkcji automatycznego tekstu alternatywnego.
pdfjs-editor-alt-text-settings-delete-model-button = Usuń
pdfjs-editor-alt-text-settings-download-model-button = Pobierz
pdfjs-editor-alt-text-settings-downloading-model-button = Pobieranie…
pdfjs-editor-alt-text-settings-editor-title = Edytor tekstu alternatywnego
pdfjs-editor-alt-text-settings-show-dialog-button-label = Wyświetlanie edytora tekstu alternatywnego od razu po dodaniu obrazu
pdfjs-editor-alt-text-settings-show-dialog-description = Pomaga upewnić się, że wszystkie obrazy mają tekst alternatywny.
pdfjs-editor-alt-text-settings-close-button = Zamknij

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Dodano wyróżnione
pdfjs-editor-freetext-added-alert = Dodano tekst
pdfjs-editor-ink-added-alert = Dodano rysunek
pdfjs-editor-stamp-added-alert = Dodano obraz
pdfjs-editor-signature-added-alert = Dodano podpis

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Usunięto wyróżnienie
pdfjs-editor-undo-bar-message-freetext = Usunięto tekst
pdfjs-editor-undo-bar-message-ink = Usunięto rysunek
pdfjs-editor-undo-bar-message-stamp = Usunięto obraz
pdfjs-editor-undo-bar-message-signature = Usunięto podpis
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] Usunięto przypis
        [few] Usunięto { $count } przypisy
       *[many] Usunięto { $count } przypisów
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Cofnij
pdfjs-editor-undo-bar-undo-button-label = Cofnij
pdfjs-editor-undo-bar-close-button =
    .title = Zamknij
pdfjs-editor-undo-bar-close-button-label = Zamknij

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = To okno umożliwia utworzenie podpisu, który można dodać do dokumentu PDF. Można zmienić nazwę (która służy także jako tekst alternatywny) i opcjonalnie zachować podpis do ponownego użycia.
pdfjs-editor-add-signature-dialog-title = Dodanie podpisu

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Wpisz
    .title = Wpisz
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Narysuj
    .title = Narysuj
pdfjs-editor-add-signature-image-button = Obraz
    .title = Obraz

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Wpisz swój podpis
    .placeholder = Wpisz swój podpis
pdfjs-editor-add-signature-draw-placeholder = Narysuj swój podpis
pdfjs-editor-add-signature-draw-thickness-range-label = Grubość
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Grubość kreski: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Przeciągnij tutaj plik, aby go przesłać
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Lub wybierz plik obrazu
       *[other] Lub przeglądaj pliki obrazów
    }

## Controls

pdfjs-editor-add-signature-description-label = Opis (tekst alternatywny)
pdfjs-editor-add-signature-description-input =
    .title = Opis (tekst alternatywny)
pdfjs-editor-add-signature-description-default-when-drawing = Podpis
pdfjs-editor-add-signature-clear-button-label = Usuń podpis
pdfjs-editor-add-signature-clear-button =
    .title = Usuń podpis
pdfjs-editor-add-signature-save-checkbox = Zachowaj podpis
pdfjs-editor-add-signature-save-warning-message = Osiągnięto ograniczenie wynoszące pięć zachowanych podpisów. Usuń jeden, aby zachować więcej.
pdfjs-editor-add-signature-image-upload-error-title = Nie można przesłać obrazu
pdfjs-editor-add-signature-image-upload-error-description = Sprawdź połączenie sieciowe lub spróbuj przesłać inny obraz.
pdfjs-editor-add-signature-image-no-data-error-title = Nie można przekonwertować tego obrazu na podpis
pdfjs-editor-add-signature-image-no-data-error-description = Spróbuj przesłać inny obraz.
pdfjs-editor-add-signature-error-close-button = Zamknij

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Anuluj
pdfjs-editor-add-signature-add-button = Dodaj
pdfjs-editor-edit-signature-update-button = Aktualizuj

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Edytuj komentarz
pdfjs-editor-edit-comment-popup-button =
    .title = Edytuj komentarz
pdfjs-editor-delete-comment-popup-button-label = Usuń komentarz
pdfjs-editor-delete-comment-popup-button =
    .title = Usuń komentarz
pdfjs-show-comment-button =
    .title = Wyświetl komentarz

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Działania
pdfjs-editor-edit-comment-actions-button =
    .title = Działania
pdfjs-editor-edit-comment-close-button-label = Zamknij
pdfjs-editor-edit-comment-close-button =
    .title = Zamknij
pdfjs-editor-edit-comment-actions-edit-button-label = Edytuj
pdfjs-editor-edit-comment-actions-delete-button-label = Usuń
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Napisz komentarz
pdfjs-editor-edit-comment-manager-cancel-button = Anuluj
pdfjs-editor-edit-comment-manager-save-button = Zapisz
# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Edytuj komentarz
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Aktualizuj
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Dodaj komentarz
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Dodaj
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Zacznij pisać…
pdfjs-editor-edit-comment-dialog-cancel-button = Anuluj

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Edytuj komentarz

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Usuń zachowany podpis
pdfjs-editor-delete-signature-button-label1 = Usuń zachowany podpis

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Edytuj opis

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Edycja opisu
