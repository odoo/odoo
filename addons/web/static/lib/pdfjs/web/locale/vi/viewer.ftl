# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Trang trước
pdfjs-previous-button-label = Trước
pdfjs-next-button =
    .title = Trang Sau
pdfjs-next-button-label = Tiếp
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Trang
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = trên { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } trên { $pagesCount })
pdfjs-zoom-out-button =
    .title = Thu nhỏ
pdfjs-zoom-out-button-label = Thu nhỏ
pdfjs-zoom-in-button =
    .title = Phóng to
pdfjs-zoom-in-button-label = Phóng to
pdfjs-zoom-select =
    .title = Thu phóng
pdfjs-presentation-mode-button =
    .title = Chuyển sang chế độ trình chiếu
pdfjs-presentation-mode-button-label = Chế độ trình chiếu
pdfjs-open-file-button =
    .title = Mở tập tin
pdfjs-open-file-button-label = Mở tập tin
pdfjs-print-button =
    .title = In
pdfjs-print-button-label = In
pdfjs-save-button =
    .title = Lưu
pdfjs-save-button-label = Lưu
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Tải xuống
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Tải xuống
pdfjs-bookmark-button =
    .title = Trang hiện tại (xem URL từ trang hiện tại)
pdfjs-bookmark-button-label = Trang hiện tại

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Công cụ
pdfjs-tools-button-label = Công cụ
pdfjs-first-page-button =
    .title = Về trang đầu
pdfjs-first-page-button-label = Về trang đầu
pdfjs-last-page-button =
    .title = Đến trang cuối
pdfjs-last-page-button-label = Đến trang cuối
pdfjs-page-rotate-cw-button =
    .title = Xoay theo chiều kim đồng hồ
pdfjs-page-rotate-cw-button-label = Xoay theo chiều kim đồng hồ
pdfjs-page-rotate-ccw-button =
    .title = Xoay ngược chiều kim đồng hồ
pdfjs-page-rotate-ccw-button-label = Xoay ngược chiều kim đồng hồ
pdfjs-cursor-text-select-tool-button =
    .title = Kích hoạt công cụ chọn vùng văn bản
pdfjs-cursor-text-select-tool-button-label = Công cụ chọn vùng văn bản
pdfjs-cursor-hand-tool-button =
    .title = Kích hoạt công cụ con trỏ
pdfjs-cursor-hand-tool-button-label = Công cụ con trỏ
pdfjs-scroll-page-button =
    .title = Sử dụng cuộn trang hiện tại
pdfjs-scroll-page-button-label = Cuộn trang hiện tại
pdfjs-scroll-vertical-button =
    .title = Sử dụng cuộn dọc
pdfjs-scroll-vertical-button-label = Cuộn dọc
pdfjs-scroll-horizontal-button =
    .title = Sử dụng cuộn ngang
pdfjs-scroll-horizontal-button-label = Cuộn ngang
pdfjs-scroll-wrapped-button =
    .title = Sử dụng cuộn ngắt dòng
pdfjs-scroll-wrapped-button-label = Cuộn ngắt dòng
pdfjs-spread-none-button =
    .title = Không nối rộng trang
pdfjs-spread-none-button-label = Không có phân cách
pdfjs-spread-odd-button =
    .title = Nối trang bài bắt đầu với các trang được đánh số lẻ
pdfjs-spread-odd-button-label = Phân cách theo số lẻ
pdfjs-spread-even-button =
    .title = Nối trang bài bắt đầu với các trang được đánh số chẵn
pdfjs-spread-even-button-label = Phân cách theo số chẵn

## Document properties dialog

pdfjs-document-properties-button =
    .title = Thuộc tính của tài liệu…
pdfjs-document-properties-button-label = Thuộc tính của tài liệu…
pdfjs-document-properties-file-name = Tên tập tin:
pdfjs-document-properties-file-size = Kích thước:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)
pdfjs-document-properties-title = Tiêu đề:
pdfjs-document-properties-author = Tác giả:
pdfjs-document-properties-subject = Chủ đề:
pdfjs-document-properties-keywords = Từ khóa:
pdfjs-document-properties-creation-date = Ngày tạo:
pdfjs-document-properties-modification-date = Ngày sửa đổi:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Người tạo:
pdfjs-document-properties-producer = Phần mềm tạo PDF:
pdfjs-document-properties-version = Phiên bản PDF:
pdfjs-document-properties-page-count = Tổng số trang:
pdfjs-document-properties-page-size = Kích thước trang:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = khổ dọc
pdfjs-document-properties-page-size-orientation-landscape = khổ ngang
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Thư
pdfjs-document-properties-page-size-name-legal = Pháp lý

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
pdfjs-document-properties-linearized = Xem nhanh trên web:
pdfjs-document-properties-linearized-yes = Có
pdfjs-document-properties-linearized-no = Không
pdfjs-document-properties-close-button = Ðóng
pdfjs-digital-signature-properties-view-certificate = Xem chứng chỉ
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Nguyên nhân: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Timestamp: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures = Chữ ký thành phần ({ $count })

## Print

pdfjs-print-progress-message = Chuẩn bị trang để in…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Hủy bỏ
pdfjs-printing-not-supported = Cảnh báo: In ấn không được hỗ trợ đầy đủ ở trình duyệt này.
pdfjs-printing-not-ready = Cảnh báo: PDF chưa được tải hết để in.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Tìm mục phác thảo hiện tại
pdfjs-current-outline-item-button-label = Mục phác thảo hiện tại
pdfjs-findbar-button =
    .title = Tìm trong tài liệu
pdfjs-findbar-button-label = Tìm
pdfjs-additional-layers = Các lớp bổ sung

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Ảnh thu nhỏ của trang { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Chọn trang { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Trang { $page } / { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Tìm trong tài liệu…
    .title = Tìm
pdfjs-find-previous-button =
    .title = Tìm cụm từ ở phần trước
pdfjs-find-previous-button-label = Trước
pdfjs-find-next-button =
    .title = Tìm cụm từ ở phần sau
pdfjs-find-next-button-label = Tiếp
pdfjs-find-highlight-checkbox = Đánh dấu tất cả
pdfjs-find-match-case-checkbox-label = Phân biệt hoa, thường
pdfjs-find-match-diacritics-checkbox-label = Khớp dấu phụ
pdfjs-find-entire-word-checkbox-label = Toàn bộ từ
pdfjs-find-reached-top = Đã đến phần đầu tài liệu, quay trở lại từ cuối
pdfjs-find-reached-bottom = Đã đến phần cuối của tài liệu, quay trở lại từ đầu
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count = { $current } trên { $total } kết quả
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit = Tìm thấy hơn { $limit } kết quả
pdfjs-find-not-found = Không tìm thấy cụm từ này

## Predefined zoom values

pdfjs-page-scale-width = Vừa chiều rộng
pdfjs-page-scale-fit = Vừa chiều cao
pdfjs-page-scale-auto = Tự động chọn kích thước
pdfjs-page-scale-actual = Kích thước thực
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Trang { $page }

## Loading indicator messages

pdfjs-loading-error = Lỗi khi tải tài liệu PDF.
pdfjs-invalid-file-error = Tập tin PDF hỏng hoặc không hợp lệ.
pdfjs-missing-file-error = Thiếu tập tin PDF.
pdfjs-unexpected-response-error = Máy chủ có phản hồi lạ.
pdfjs-rendering-error = Lỗi khi hiển thị trang.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } Chú thích]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Nhập mật khẩu để mở tập tin PDF này.
pdfjs-password-invalid = Mật khẩu không đúng. Vui lòng thử lại.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Hủy bỏ
pdfjs-web-fonts-disabled = Phông chữ Web bị vô hiệu hóa: không thể sử dụng các phông chữ PDF được nhúng.

## Editing

pdfjs-editor-free-text-button =
    .title = Văn bản
pdfjs-editor-color-picker-free-text-input =
    .title = Thay đổi màu chữ
pdfjs-editor-free-text-button-label = Văn bản
pdfjs-editor-ink-button =
    .title = Vẽ
pdfjs-editor-color-picker-ink-input =
    .title = Thay đổi màu vẽ
pdfjs-editor-ink-button-label = Vẽ
pdfjs-editor-stamp-button =
    .title = Thêm hoặc chỉnh sửa hình ảnh
pdfjs-editor-stamp-button-label = Thêm hoặc chỉnh sửa hình ảnh
pdfjs-editor-highlight-button =
    .title = Đánh dấu
pdfjs-editor-highlight-button-label = Đánh dấu
pdfjs-highlight-floating-button1 =
    .aria-label = Đánh dấu
    .title = Đánh dấu
pdfjs-highlight-floating-button-label = Đánh dấu
pdfjs-comment-floating-button =
    .aria-label = Chú thích
    .title = Chú thích
pdfjs-comment-floating-button-label = Chú thích
pdfjs-editor-comment-button =
    .aria-label = Chú thích
    .title = Chú thích
pdfjs-editor-comment-button-label = Chú thích
pdfjs-editor-signature-button =
    .title = Thêm chữ ký
pdfjs-editor-signature-button-label = Thêm chữ ký

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Trình chỉnh sửa đánh dấu
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Trình chỉnh sửa bản vẽ
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Trình chỉnh sửa chữ ký: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Trình chỉnh sửa hình ảnh

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Xóa bản vẽ
pdfjs-editor-remove-freetext-button =
    .title = Xóa văn bản
pdfjs-editor-remove-stamp-button =
    .title = Xóa ảnh
pdfjs-editor-remove-highlight-button =
    .title = Xóa phần đánh dấu
pdfjs-editor-remove-signature-button =
    .title = Xoá chữ ký

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Màu
pdfjs-editor-free-text-size-input = Kích cỡ
pdfjs-editor-ink-color-input = Màu
pdfjs-editor-ink-thickness-input = Độ dày
pdfjs-editor-ink-opacity-input = Độ mờ
pdfjs-editor-stamp-add-image-button =
    .title = Thêm hình ảnh
pdfjs-editor-stamp-add-image-button-label = Thêm hình ảnh
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Độ dày
pdfjs-editor-free-highlight-thickness-title =
    .title = Thay đổi độ dày khi đánh dấu các mục không phải là văn bản
pdfjs-editor-add-signature-container =
    .aria-label = Kiểm soát chữ ký và chữ ký đã lưu
pdfjs-editor-signature-add-signature-button =
    .title = Thêm chữ ký mới
pdfjs-editor-signature-add-signature-button-label = Thêm chữ ký mới
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Đã lưu chữ ký: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Trình chỉnh sửa văn bản
    .default-content = Bắt đầu nhập…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title = Chú thích
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Đóng thanh lề
    .title = Đóng thanh lề
pdfjs-editor-comments-sidebar-close-button-label = Đóng thanh lề
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Bạn thấy điều gì đáng chú ý? Hãy đánh dấu và để lại chú thích.
pdfjs-editor-comments-sidebar-no-comments-link = Tìm hiểu thêm

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Văn bản thay thế
pdfjs-editor-alt-text-edit-button =
    .aria-label = Chỉnh sửa văn bản thay thế
pdfjs-editor-alt-text-dialog-label = Chọn một lựa chọn
pdfjs-editor-alt-text-dialog-description = Văn bản thay thế sẽ hữu ích khi mọi người không thể thấy hình ảnh hoặc khi hình ảnh không tải.
pdfjs-editor-alt-text-add-description-label = Thêm một mô tả
pdfjs-editor-alt-text-add-description-description = Hãy nhắm tới 1-2 câu mô tả chủ đề, bối cảnh hoặc hành động.
pdfjs-editor-alt-text-mark-decorative-label = Đánh dấu là trang trí
pdfjs-editor-alt-text-mark-decorative-description = Điều này được sử dụng cho các hình ảnh trang trí, như đường viền hoặc watermark.
pdfjs-editor-alt-text-cancel-button = Hủy bỏ
pdfjs-editor-alt-text-save-button = Lưu
pdfjs-editor-alt-text-decorative-tooltip = Đã đánh dấu là trang trí
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Ví dụ: “Một thanh niên ngồi xuống bàn để thưởng thức một bữa ăn”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Văn bản thay thế

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Trên cùng bên trái — thay đổi kích thước
pdfjs-editor-resizer-top-middle =
    .aria-label = Trên cùng ở giữa — thay đổi kích thước
pdfjs-editor-resizer-top-right =
    .aria-label = Trên cùng bên phải — thay đổi kích thước
pdfjs-editor-resizer-middle-right =
    .aria-label = Ở giữa bên phải — thay đổi kích thước
pdfjs-editor-resizer-bottom-right =
    .aria-label = Dưới cùng bên phải — thay đổi kích thước
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Ở giữa dưới cùng — thay đổi kích thước
pdfjs-editor-resizer-bottom-left =
    .aria-label = Góc dưới bên trái — thay đổi kích thước
pdfjs-editor-resizer-middle-left =
    .aria-label = Ở giữa bên trái — thay đổi kích thước

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Màu đánh dấu
pdfjs-editor-colorpicker-button =
    .title = Thay đổi màu
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Lựa chọn màu sắc
pdfjs-editor-colorpicker-yellow =
    .title = Vàng
pdfjs-editor-colorpicker-green =
    .title = Xanh lục
pdfjs-editor-colorpicker-blue =
    .title = Xanh dương
pdfjs-editor-colorpicker-pink =
    .title = Hồng
pdfjs-editor-colorpicker-red =
    .title = Đỏ

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Hiện tất cả
pdfjs-editor-highlight-show-all-button =
    .title = Hiện tất cả

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Chỉnh sửa văn bản thay thế (mô tả hình ảnh)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Thêm văn bản thay thế (mô tả hình ảnh)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Viết mô tả của bạn ở đây…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Mô tả ngắn gọn dành cho người không xem được ảnh hoặc khi không thể tải ảnh.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Văn bản thay thế này được tạo tự động và có thể không chính xác.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Tìm hiểu thêm
pdfjs-editor-new-alt-text-create-automatically-button-label = Tạo văn bản thay thế tự động
pdfjs-editor-new-alt-text-not-now-button = Để sau
pdfjs-editor-new-alt-text-error-title = Không thể tạo tự động văn bản thay thế
pdfjs-editor-new-alt-text-error-description = Vui lòng viết văn bản thay thế của riêng bạn hoặc thử lại sau.
pdfjs-editor-new-alt-text-error-close-button = Đóng
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Đang tải xuống mô hình AI văn bản thay thế ({ $downloadedSize } / { $totalSize } MB)
    .aria-valuetext = Đang tải xuống mô hình AI văn bản thay thế ({ $downloadedSize } / { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Đã thêm văn bản thay thế
pdfjs-editor-new-alt-text-added-button-label = Đã thêm văn bản thay thế
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Thiếu văn bản thay thế
pdfjs-editor-new-alt-text-missing-button-label = Thiếu văn bản thay thế
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Xem lại văn bản thay thế
pdfjs-editor-new-alt-text-to-review-button-label = Xem lại văn bản thay thế
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Được tạo tự động: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Cài đặt văn bản thay thế của hình ảnh
pdfjs-image-alt-text-settings-button-label = Cài đặt văn bản thay thế của hình ảnh
pdfjs-editor-alt-text-settings-dialog-label = Cài đặt văn bản thay thế của hình ảnh
pdfjs-editor-alt-text-settings-automatic-title = Văn bản thay thế tự động
pdfjs-editor-alt-text-settings-create-model-button-label = Tạo văn bản thay thế tự động
pdfjs-editor-alt-text-settings-create-model-description = Đề xuất mô tả giúp ích cho những người không xem được ảnh hoặc khi không thể tải ảnh.
pdfjs-editor-alt-text-settings-editor-title = Trình soạn thảo văn bản thay thế
pdfjs-editor-alt-text-settings-show-dialog-button-label = Hiển thị ngay trình soạn thảo văn bản thay thế khi thêm hình ảnh
pdfjs-editor-alt-text-settings-show-dialog-description = Giúp bạn đảm bảo tất cả hình ảnh của bạn đều có văn bản thay thế.
pdfjs-editor-alt-text-settings-close-button = Đóng

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Đã thêm tô sáng
pdfjs-editor-freetext-added-alert = Đã thêm chữ
pdfjs-editor-ink-added-alert = Đã thêm bản vẽ
pdfjs-editor-stamp-added-alert = Đã thêm ảnh
pdfjs-editor-signature-added-alert = Đã thêm chữ ký

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Đã xóa đánh dấu
pdfjs-editor-undo-bar-message-freetext = Đã xóa văn bản
pdfjs-editor-undo-bar-message-ink = Đã xóa bản vẽ
pdfjs-editor-undo-bar-message-stamp = Đã xóa hình ảnh
pdfjs-editor-undo-bar-message-signature = Chữ ký đã bị xoá
pdfjs-editor-undo-bar-message-comment = Đã xoá chú thích
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple = { $count } chú thích đã bị xóa
pdfjs-editor-undo-bar-undo-button =
    .title = Hoàn tác
pdfjs-editor-undo-bar-undo-button-label = Hoàn tác
pdfjs-editor-undo-bar-close-button =
    .title = Đóng
pdfjs-editor-undo-bar-close-button-label = Đóng

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Phương thức này cho phép người dùng tạo một chữ ký để thêm vào tài liệu PDF. Người dùng có thể chỉnh sửa tên (cũng đóng vai trò là văn bản thay thế) và tùy chọn lưu chữ ký để sử dụng nhiều lần.
pdfjs-editor-add-signature-dialog-title = Thêm chữ ký

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Đánh văn bản
    .title = Đánh văn bản
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Vẽ
    .title = Vẽ
pdfjs-editor-add-signature-image-button = Hình ảnh
    .title = Hình ảnh

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Nhập chữ ký của bạn
    .placeholder = Nhập chữ ký của bạn
pdfjs-editor-add-signature-draw-placeholder = Vẽ chữ ký của bạn
pdfjs-editor-add-signature-draw-thickness-range-label = Độ dày
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Độ dày bút vẽ: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Kéo một tập tin tại đây để tải lên
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Hoặc chọn hình ảnh
       *[other] Hoặc chọn hình ảnh
    }

## Controls

pdfjs-editor-add-signature-description-label = Mô tả (văn bản thay thế)
pdfjs-editor-add-signature-description-input =
    .title = Mô tả (văn bản thay thế)
pdfjs-editor-add-signature-description-default-when-drawing = Chữ ký
pdfjs-editor-add-signature-clear-button-label = Xoá chữ ký
pdfjs-editor-add-signature-clear-button =
    .title = Xoá chữ ký
pdfjs-editor-add-signature-save-checkbox = Lưu chữ ký
pdfjs-editor-add-signature-save-warning-message = Bạn đã đạt đến giới hạn 5 chữ ký đã lưu. Hãy xóa một cái để lưu thêm.
pdfjs-editor-add-signature-image-upload-error-title = Không thể tải lên hình ảnh
pdfjs-editor-add-signature-image-upload-error-description = Kiểm tra kết nối mạng của bạn hoặc thử hình ảnh khác.
pdfjs-editor-add-signature-image-no-data-error-title = Không thể chuyển đổi hình ảnh này thành chữ ký
pdfjs-editor-add-signature-image-no-data-error-description = Vui lòng thử tải lên một hình ảnh khác.
pdfjs-editor-add-signature-error-close-button = Đóng

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Hủy bỏ
pdfjs-editor-add-signature-add-button = Thêm
pdfjs-editor-edit-signature-update-button = Cập nhật

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Chỉnh sửa chú thích
pdfjs-editor-edit-comment-popup-button =
    .title = Chỉnh sửa chú thích
pdfjs-editor-delete-comment-popup-button-label = Xoá chú thích
pdfjs-editor-delete-comment-popup-button =
    .title = Xoá chú thích
pdfjs-show-comment-button =
    .title = Hiển thị chú thích

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Chỉnh sửa chú thích
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Cập nhật
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Thêm chú thích
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Thêm
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Bắt đầu nhập…
pdfjs-editor-edit-comment-dialog-cancel-button = Hủy bỏ

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Thêm chú thích

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Bật tắt thanh lề (tài liệu bao gồm hình thu nhỏ/phác thảo/tập tin đính kèm/lớp)
pdfjs-toggle-views-manager-button1-label = Quản lý trang
pdfjs-views-manager-sidebar =
    .aria-label = Thanh lề
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Công cụ điều chỉnh kích thước thanh lề
pdfjs-views-manager-view-selector-button =
    .title = Chế độ hiển thị
pdfjs-views-manager-view-selector-button-label = Chế độ hiển thị
pdfjs-views-manager-pages-title = Trang
pdfjs-views-manager-outlines-title1 = Bản phác thảo tài liệu
    .title = Bản phác thảo tài liệu (nhấp đúp chuột để mở rộng/thu gọn tất cả các mục)
pdfjs-views-manager-attachments-title = Đính kèm
pdfjs-views-manager-layers-title1 = Lớp
    .title = Lớp (nhấp đúp chuột để đặt lại tất cả các lớp về trạng thái mặc định.)
pdfjs-views-manager-pages-option-label = Trang
pdfjs-views-manager-outlines-option-label = Bản phác thảo tài liệu
pdfjs-views-manager-attachments-option-label = Đính kèm
pdfjs-views-manager-layers-option-label = Lớp
pdfjs-views-manager-add-file-button =
    .title = Thêm tập tin
pdfjs-views-manager-add-file-button-label = Thêm tập tin
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label = { $count } đã chọn
pdfjs-views-manager-pages-status-none-action-label = Chọn trang
pdfjs-views-manager-pages-status-action-button-label = Quản lý
pdfjs-views-manager-pages-status-copy-button-label = Sao chép
pdfjs-views-manager-pages-status-cut-button-label = Cắt
pdfjs-views-manager-pages-status-delete-button-label = Dán
pdfjs-views-manager-pages-status-export-selected-button-label = Xuất các mục đã chọn…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label = Đã cắt { $count } trang
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label = Đã sao chép { $count } trang
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label = Đã xoá { $count } trang
pdfjs-views-manager-pages-status-waiting-ready-label = Đang chuẩn bị tập tin của bạn…
pdfjs-views-manager-pages-status-waiting-uploading-label = Đang tải lên tập tin…
pdfjs-views-manager-status-warning-cut-label = Không thể cắt. Vui lòng làm mới trang và thử lại.
pdfjs-views-manager-status-warning-copy-label = Không thể sao chép. Vui lòng làm mới trang và thử lại.
pdfjs-views-manager-status-warning-delete-label = Không thể xoá. Vui lòng làm mới trang và thử lại.
pdfjs-views-manager-status-warning-save-label = Không thể lưu. Vui lòng làm mới trang và thử lại.
pdfjs-views-manager-status-undo-button-label = Hoàn tác
pdfjs-views-manager-status-done-button-label = Xong
pdfjs-views-manager-status-close-button =
    .title = Đóng
pdfjs-views-manager-status-close-button-label = Đóng
pdfjs-views-manager-paste-button-label = Dán
pdfjs-views-manager-paste-button-before =
    .title = Dán trước trang đầu
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Dán sau trang { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = MỚI
pdfjs-views-manager-waiting-for-file = Đang tải lên tập tin…
pdfjs-toggle-views-manager-button1 =
    .title = Quản lý trang

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Thuộc tính chữ ký điện tử
    .title = Thuộc tính chữ ký điện tử
pdfjs-digital-signature-properties-button-label = Thuộc tính chữ ký điện tử

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Tài liệu đã được ký bằng chữ ký điện tử hợp lệ
pdfjs-digital-signature-properties-banner-unknown = Tài liệu đã được ký nhưng không thể xác minh { $count } chữ ký điện tử
pdfjs-digital-signature-properties-banner-untrusted = Tài liệu được ký bằng { $count } chứng chỉ không đáng tin cậy
pdfjs-digital-signature-properties-banner-expired = Tài liệu được ký bằng { $count } chứng chỉ đã hết hạn
pdfjs-digital-signature-properties-banner-invalid = Tài liệu có { $count } chữ ký điện tử không hợp lệ
pdfjs-digital-signature-properties-banner-revoked = Tài liệu được ký bằng { $count } chứng chỉ đã bị thu hồi

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Trạng thái: Chữ ký đã được xác minh
pdfjs-digital-signature-properties-status-invalid = Trạng thái: Chữ ký không hợp lệ
pdfjs-digital-signature-properties-status-unknown = Trạng thái: Không thể xác minh (không được hỗ trợ)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Chứng chỉ: Đáng tin cậy ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Chứng chỉ: Không khả dụng
pdfjs-digital-signature-properties-certificate-untrusted = Chứng chỉ: Không đáng tin cậy
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Chứng chỉ: Người cấp không xác định ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Chứng chỉ: Tự ký ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Chứng chỉ: Người cấp không đáng tin cậy ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Chứng chỉ: Đã hết hạn
pdfjs-digital-signature-properties-certificate-expired-with-date = Chứng chỉ: Đã hết hạn ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Chứng chỉ: Đã bị thu hồi

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Xoá chữ ký đã lưu
pdfjs-editor-delete-signature-button-label1 = Xoá chữ ký đã lưu

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Chỉnh sửa mô tả

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Chỉnh sửa mô tả
