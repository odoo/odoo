# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Laman Sebelumnya
pdfjs-previous-button-label = Sebelumnya
pdfjs-next-button =
    .title = Laman Selanjutnya
pdfjs-next-button-label = Selanjutnya
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Halaman
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = dari { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } dari { $pagesCount })
pdfjs-zoom-out-button =
    .title = Perkecil
pdfjs-zoom-out-button-label = Perkecil
pdfjs-zoom-in-button =
    .title = Perbesar
pdfjs-zoom-in-button-label = Perbesar
pdfjs-zoom-select =
    .title = Perbesaran
pdfjs-presentation-mode-button =
    .title = Ganti ke Mode Presentasi
pdfjs-presentation-mode-button-label = Mode Presentasi
pdfjs-open-file-button =
    .title = Buka Berkas
pdfjs-open-file-button-label = Buka
pdfjs-print-button =
    .title = Cetak
pdfjs-print-button-label = Cetak
pdfjs-save-button =
    .title = Simpan
pdfjs-save-button-label = Simpan
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Unduh
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Unduh
pdfjs-bookmark-button =
    .title = Laman Saat Ini (Lihat URL dari Laman Sekarang)
pdfjs-bookmark-button-label = Laman Saat Ini

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Alat
pdfjs-tools-button-label = Alat
pdfjs-first-page-button =
    .title = Buka Halaman Pertama
pdfjs-first-page-button-label = Buka Halaman Pertama
pdfjs-last-page-button =
    .title = Buka Halaman Terakhir
pdfjs-last-page-button-label = Buka Halaman Terakhir
pdfjs-page-rotate-cw-button =
    .title = Putar Searah Jarum Jam
pdfjs-page-rotate-cw-button-label = Putar Searah Jarum Jam
pdfjs-page-rotate-ccw-button =
    .title = Putar Berlawanan Arah Jarum Jam
pdfjs-page-rotate-ccw-button-label = Putar Berlawanan Arah Jarum Jam
pdfjs-cursor-text-select-tool-button =
    .title = Aktifkan Alat Seleksi Teks
pdfjs-cursor-text-select-tool-button-label = Alat Seleksi Teks
pdfjs-cursor-hand-tool-button =
    .title = Aktifkan Alat Tangan
pdfjs-cursor-hand-tool-button-label = Alat Tangan
pdfjs-scroll-page-button =
    .title = Gunakan Pengguliran Laman
pdfjs-scroll-page-button-label = Pengguliran Laman
pdfjs-scroll-vertical-button =
    .title = Gunakan Penggeseran Vertikal
pdfjs-scroll-vertical-button-label = Penggeseran Vertikal
pdfjs-scroll-horizontal-button =
    .title = Gunakan Penggeseran Horizontal
pdfjs-scroll-horizontal-button-label = Penggeseran Horizontal
pdfjs-scroll-wrapped-button =
    .title = Gunakan Penggeseran Terapit
pdfjs-scroll-wrapped-button-label = Penggeseran Terapit
pdfjs-spread-none-button =
    .title = Jangan gabungkan lembar halaman
pdfjs-spread-none-button-label = Tidak Ada Lembaran
pdfjs-spread-odd-button =
    .title = Gabungkan lembar lamanan mulai dengan halaman ganjil
pdfjs-spread-odd-button-label = Lembaran Ganjil
pdfjs-spread-even-button =
    .title = Gabungkan lembar halaman dimulai dengan halaman genap
pdfjs-spread-even-button-label = Lembaran Genap

## Document properties dialog

pdfjs-document-properties-button =
    .title = Properti Dokumen…
pdfjs-document-properties-button-label = Properti Dokumen…
pdfjs-document-properties-file-name = Nama berkas:
pdfjs-document-properties-file-size = Ukuran berkas:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } byte)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } byte)
pdfjs-document-properties-title = Judul:
pdfjs-document-properties-author = Penyusun:
pdfjs-document-properties-subject = Subjek:
pdfjs-document-properties-keywords = Kata Kunci:
pdfjs-document-properties-creation-date = Tanggal Dibuat:
pdfjs-document-properties-modification-date = Tanggal Dimodifikasi:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Pembuat:
pdfjs-document-properties-producer = Pemroduksi PDF:
pdfjs-document-properties-version = Versi PDF:
pdfjs-document-properties-page-count = Jumlah Halaman:
pdfjs-document-properties-page-size = Ukuran Laman:
pdfjs-document-properties-page-size-unit-inches = inci
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = tegak
pdfjs-document-properties-page-size-orientation-landscape = mendatar
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
pdfjs-document-properties-linearized = Tampilan Web Kilat:
pdfjs-document-properties-linearized-yes = Ya
pdfjs-document-properties-linearized-no = Tidak
pdfjs-document-properties-close-button = Tutup

## Print

pdfjs-print-progress-message = Menyiapkan dokumen untuk pencetakan…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Batalkan
pdfjs-printing-not-supported = Peringatan: Pencetakan tidak didukung secara lengkap pada peramban ini.
pdfjs-printing-not-ready = Peringatan: Berkas PDF masih belum dimuat secara lengkap untuk dapat dicetak.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Aktif/Nonaktifkan Bilah Samping
pdfjs-toggle-sidebar-notification-button =
    .title = Aktif/Nonaktifkan Bilah Samping (dokumen berisi kerangka/lampiran/lapisan)
pdfjs-toggle-sidebar-button-label = Aktif/Nonaktifkan Bilah Samping
pdfjs-document-outline-button =
    .title = Tampilkan Kerangka Dokumen (klik ganda untuk membentangkan/menciutkan semua item)
pdfjs-document-outline-button-label = Kerangka Dokumen
pdfjs-attachments-button =
    .title = Tampilkan Lampiran
pdfjs-attachments-button-label = Lampiran
pdfjs-layers-button =
    .title = Tampilkan Lapisan (klik ganda untuk mengatur ulang semua lapisan ke keadaan baku)
pdfjs-layers-button-label = Lapisan
pdfjs-thumbs-button =
    .title = Tampilkan Miniatur
pdfjs-thumbs-button-label = Miniatur
pdfjs-current-outline-item-button =
    .title = Cari Butir Ikhtisar Saat Ini
pdfjs-current-outline-item-button-label = Butir Ikhtisar Saat Ini
pdfjs-findbar-button =
    .title = Temukan di Dokumen
pdfjs-findbar-button-label = Temukan
pdfjs-additional-layers = Lapisan Tambahan

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Laman { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatur Laman { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Temukan
    .placeholder = Temukan di dokumen…
pdfjs-find-previous-button =
    .title = Temukan kata sebelumnya
pdfjs-find-previous-button-label = Sebelumnya
pdfjs-find-next-button =
    .title = Temukan lebih lanjut
pdfjs-find-next-button-label = Selanjutnya
pdfjs-find-highlight-checkbox = Sorot semuanya
pdfjs-find-match-case-checkbox-label = Cocokkan BESAR/kecil
pdfjs-find-match-diacritics-checkbox-label = Pencocokan Diakritik
pdfjs-find-entire-word-checkbox-label = Seluruh teks
pdfjs-find-reached-top = Sampai di awal dokumen, dilanjutkan dari bawah
pdfjs-find-reached-bottom = Sampai di akhir dokumen, dilanjutkan dari atas
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count = { $current } dari { $total } yang cocok
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit = Lebih dari { $limit } kecocokan
pdfjs-find-not-found = Frasa tidak ditemukan

## Predefined zoom values

pdfjs-page-scale-width = Lebar Laman
pdfjs-page-scale-fit = Muat Laman
pdfjs-page-scale-auto = Perbesaran Otomatis
pdfjs-page-scale-actual = Ukuran Asli
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Halaman { $page }

## Loading indicator messages

pdfjs-loading-error = Galat terjadi saat memuat PDF.
pdfjs-invalid-file-error = Berkas PDF tidak valid atau rusak.
pdfjs-missing-file-error = Berkas PDF tidak ada.
pdfjs-unexpected-response-error = Balasan server yang tidak diharapkan.
pdfjs-rendering-error = Galat terjadi saat merender laman.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Anotasi { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Masukkan sandi untuk membuka berkas PDF ini.
pdfjs-password-invalid = Sandi tidak valid. Silakan coba lagi.
pdfjs-password-ok-button = Oke
pdfjs-password-cancel-button = Batal
pdfjs-web-fonts-disabled = Font web dinonaktifkan: tidak dapat menggunakan font PDF yang tersemat.

## Editing

pdfjs-editor-free-text-button =
    .title = Teks
pdfjs-editor-color-picker-free-text-input =
    .title = Ubah warna teks
pdfjs-editor-free-text-button-label = Teks
pdfjs-editor-ink-button =
    .title = Gambar
pdfjs-editor-color-picker-ink-input =
    .title = Ubah warna gambar
pdfjs-editor-ink-button-label = Gambar
pdfjs-editor-stamp-button =
    .title = Tambah atau edit gambar
pdfjs-editor-stamp-button-label = Tambah atau edit gambar
pdfjs-editor-highlight-button =
    .title = Sorot
pdfjs-editor-highlight-button-label = Sorot
pdfjs-highlight-floating-button1 =
    .title = Sorot
    .aria-label = Sorot
pdfjs-highlight-floating-button-label = Sorot
pdfjs-comment-floating-button =
    .title = Komentar
    .aria-label = Komentar
pdfjs-comment-floating-button-label = Komentar
pdfjs-editor-signature-button =
    .title = Tambahkan tanda tangan
pdfjs-editor-signature-button-label = Tambahkan tanda tangan

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor sorot
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editor gambar
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor tanda tangan: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editor gambar

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Hapus gambar
pdfjs-editor-remove-freetext-button =
    .title = Hapus teks
pdfjs-editor-remove-stamp-button =
    .title = Hapus gambar
pdfjs-editor-remove-highlight-button =
    .title = Hapus sorotan
pdfjs-editor-remove-signature-button =
    .title = Hapus tanda tangan

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Warna
pdfjs-editor-free-text-size-input = Ukuran
pdfjs-editor-ink-color-input = Warna
pdfjs-editor-ink-thickness-input = Ketebalan
pdfjs-editor-ink-opacity-input = Opasitas
pdfjs-editor-stamp-add-image-button =
    .title = Tambahkan gambar
pdfjs-editor-stamp-add-image-button-label = Tambahkan gambar
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Ketebalan
pdfjs-editor-free-highlight-thickness-title =
    .title = Ubah ketebalan saat menyorot item selain teks
pdfjs-editor-add-signature-container =
    .aria-label = Kontrol tanda tangan dan tanda tangan tersimpan
pdfjs-editor-signature-add-signature-button =
    .title = Tambahkan tanda tangan baru
pdfjs-editor-signature-add-signature-button-label = Tambahkan tanda tangan baru
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Tanda tangan tersimpan: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor Teks
    .default-content = Mulai mengetik…

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Teks alternatif
pdfjs-editor-alt-text-edit-button =
    .aria-label = Edit teks alternatif
pdfjs-editor-alt-text-dialog-label = Pilih opsi
pdfjs-editor-alt-text-dialog-description = Teks alternatif membantu ketika orang tidak dapat melihat gambar atau ketika tidak termuat.
pdfjs-editor-alt-text-add-description-label = Tambahkan deskripsi
pdfjs-editor-alt-text-add-description-description = Upayakan 1-2 kalimat yang menggambarkan subjek, latar, atau tindakan.
pdfjs-editor-alt-text-mark-decorative-label = Tandai sebagai dekoratif
pdfjs-editor-alt-text-mark-decorative-description = Ini digunakan untuk gambar hias, seperti batas atau tanda air.
pdfjs-editor-alt-text-cancel-button = Batal
pdfjs-editor-alt-text-save-button = Simpan
pdfjs-editor-alt-text-decorative-tooltip = Ditandai sebagai dekoratif
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Misalnya, “Seorang pemuda duduk di meja untuk makan”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Teks alternatif

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Pojok kiri atas — ubah ukuran
pdfjs-editor-resizer-top-middle =
    .aria-label = Tengah atas — ubah ukuran
pdfjs-editor-resizer-top-right =
    .aria-label = Pojok kanan atas — ubah ukuran
pdfjs-editor-resizer-middle-right =
    .aria-label = Kanan tengah — ubah ukuran
pdfjs-editor-resizer-bottom-right =
    .aria-label = Pojok kanan bawah — ubah ukuran
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Tengah bawah — ubah ukuran
pdfjs-editor-resizer-bottom-left =
    .aria-label = Pojok kiri bawah — ubah ukuran
pdfjs-editor-resizer-middle-left =
    .aria-label = Kiri tengah — ubah ukuran

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Warna sorot
pdfjs-editor-colorpicker-button =
    .title = Ubah warna
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Pilihan warna
pdfjs-editor-colorpicker-yellow =
    .title = Kuning
pdfjs-editor-colorpicker-green =
    .title = Hijau
pdfjs-editor-colorpicker-blue =
    .title = Biru
pdfjs-editor-colorpicker-pink =
    .title = Merah Jambu
pdfjs-editor-colorpicker-red =
    .title = Merah

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Tampilkan semua
pdfjs-editor-highlight-show-all-button =
    .title = Tampilkan semua

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Edit teks alternatif (deskripsi gambar)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Tambahkan teks alternatif (deskripsi gambar)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Tulis deskripsi Anda di sini…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Deskripsi singkat untuk orang yang tidak dapat melihat gambar atau saat gambar tidak termuat.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Teks alternatif ini dibuat secara otomatis dan mungkin tidak akurat.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Pelajari lebih lanjut
pdfjs-editor-new-alt-text-create-automatically-button-label = Buat teks alternatif secara otomatis
pdfjs-editor-new-alt-text-not-now-button = Jangan sekarang
pdfjs-editor-new-alt-text-error-title = Tidak bisa membuat teks alternatif secara otomatis
pdfjs-editor-new-alt-text-error-description = Silakan tulis teks alternatif Anda sendiri atau coba lagi nanti.
pdfjs-editor-new-alt-text-error-close-button = Tutup
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Mengunduh model AI teks alternatif ({ $downloadedSize } dari { $totalSize } MB)
    .aria-valuetext = Mengunduh model AI teks alternatif ({ $downloadedSize } dari { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Teks alternatif ditambahkan
pdfjs-editor-new-alt-text-added-button-label = Teks alternatif ditambahkan
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Teks alternatif hilang
pdfjs-editor-new-alt-text-missing-button-label = Teks alternatif hilang
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Tinjau teks alternatif
pdfjs-editor-new-alt-text-to-review-button-label = Tinjau teks alternatif
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Dibuat secara otomatis: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Pengaturan teks alternatif gambar
pdfjs-image-alt-text-settings-button-label = Pengaturan teks alternatif gambar
pdfjs-editor-alt-text-settings-dialog-label = Pengaturan teks alternatif gambar
pdfjs-editor-alt-text-settings-automatic-title = Teks alternatif otomatis
pdfjs-editor-alt-text-settings-create-model-button-label = Buat teks alternatif secara otomatis
pdfjs-editor-alt-text-settings-create-model-description = Menyarankan deskripsi untuk membantu orang yang tidak dapat melihat gambar atau ketika gambar tidak termuat.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Model AI teks alternatif ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Berjalan secara lokal di perangkat Anda sehingga data Anda tetap pribadi. Diperlukan untuk teks alternatif otomatis.
pdfjs-editor-alt-text-settings-delete-model-button = Hapus
pdfjs-editor-alt-text-settings-download-model-button = Unduh
pdfjs-editor-alt-text-settings-downloading-model-button = Mengunduh…
pdfjs-editor-alt-text-settings-editor-title = Editor teks alternatif
pdfjs-editor-alt-text-settings-show-dialog-button-label = Tampilkan editor teks alternatif segera saat menambahkan gambar
pdfjs-editor-alt-text-settings-show-dialog-description = Membantu Anda memastikan semua gambar Anda memiliki teks alternatif.
pdfjs-editor-alt-text-settings-close-button = Tutup

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Sorotan ditambahkan
pdfjs-editor-freetext-added-alert = Teks ditambahkan
pdfjs-editor-ink-added-alert = Gambar ditambahkan
pdfjs-editor-stamp-added-alert = Citra ditambahkan
pdfjs-editor-signature-added-alert = Tanda tangan ditambahkan

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Sorotan dihapus
pdfjs-editor-undo-bar-message-freetext = Teks dihapus
pdfjs-editor-undo-bar-message-ink = Gambar dihapus
pdfjs-editor-undo-bar-message-stamp = Gambar dihapus
pdfjs-editor-undo-bar-message-signature = Tanda tangan dihapus
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple = { $count } anotasi dihapus
pdfjs-editor-undo-bar-undo-button =
    .title = Urungkan
pdfjs-editor-undo-bar-undo-button-label = Urungkan
pdfjs-editor-undo-bar-close-button =
    .title = Tutup
pdfjs-editor-undo-bar-close-button-label = Tutup

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Modal ini memungkinkan pengguna untuk membuat tanda tangan yang dapat ditambahkan ke dokumen PDF. Pengguna dapat mengedit nama (yang juga berfungsi sebagai teks alternatif), dan jika diinginkan, menyimpan tanda tangan untuk digunakan kembali.
pdfjs-editor-add-signature-dialog-title = Tambahkan tanda tangan

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Tipe
    .title = Tipe
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Gambarkan
    .title = Gambarkan
pdfjs-editor-add-signature-image-button = Gambar
    .title = Gambar

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Ketik tanda tangan Anda
    .placeholder = Ketik tanda tangan Anda
pdfjs-editor-add-signature-draw-placeholder = Buat tanda tangan Anda
pdfjs-editor-add-signature-draw-thickness-range-label = Ketebalan
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Ketebalan gambar: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Seret berkas ke sini untuk mengunggah
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Atau pilih berkas gambar
       *[other] Atau cari berkas gambar
    }

## Controls

pdfjs-editor-add-signature-description-label = Deskripsi (teks alternatif)
pdfjs-editor-add-signature-description-input =
    .title = Deskripsi (teks alternatif)
pdfjs-editor-add-signature-description-default-when-drawing = Tanda tangan
pdfjs-editor-add-signature-clear-button-label = Hapus tanda tangan
pdfjs-editor-add-signature-clear-button =
    .title = Hapus tanda tangan
pdfjs-editor-add-signature-save-checkbox = Simpan tanda tangan
pdfjs-editor-add-signature-save-warning-message = Anda telah mencapai batas 5 tanda tangan tersimpan. Hapus untuk menyimpan lebih banyak.
pdfjs-editor-add-signature-image-upload-error-title = Tidak dapat mengunggah gambar
pdfjs-editor-add-signature-image-upload-error-description = Periksa sambungan jaringan Anda atau coba gambar lain.
pdfjs-editor-add-signature-image-no-data-error-title = Tak bisa mengonversi citra ini menjadi tanda tangan
pdfjs-editor-add-signature-image-no-data-error-description = Coba unggah gambar lain.
pdfjs-editor-add-signature-error-close-button = Tutup

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Batal
pdfjs-editor-add-signature-add-button = Tambah
pdfjs-editor-edit-signature-update-button = Perbarui

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = Aksi
pdfjs-editor-edit-comment-actions-button =
    .title = Aksi
pdfjs-editor-edit-comment-close-button-label = Tutup
pdfjs-editor-edit-comment-close-button =
    .title = Tutup
pdfjs-editor-edit-comment-actions-edit-button-label = Sunting
pdfjs-editor-edit-comment-actions-delete-button-label = Hapus
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = Masukkan komentar Anda
pdfjs-editor-edit-comment-manager-cancel-button = Batal
pdfjs-editor-edit-comment-manager-save-button = Simpan

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = Sunting komentar

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Hapus tanda tangan tersimpan
pdfjs-editor-delete-signature-button-label1 = Hapus tanda tangan tersimpan

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Edit deskripsi

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Edit deskripsi
