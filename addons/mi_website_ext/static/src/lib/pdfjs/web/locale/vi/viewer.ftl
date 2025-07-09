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
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } byte)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } byte)
pdfjs-document-properties-title = Tiêu đề:
pdfjs-document-properties-author = Tác giả:
pdfjs-document-properties-subject = Chủ đề:
pdfjs-document-properties-keywords = Từ khóa:
pdfjs-document-properties-creation-date = Ngày tạo:
pdfjs-document-properties-modification-date = Ngày sửa đổi:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
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

## Print

pdfjs-print-progress-message = Chuẩn bị trang để in…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Hủy bỏ
pdfjs-printing-not-supported = Cảnh báo: In ấn không được hỗ trợ đầy đủ ở trình duyệt này.
pdfjs-printing-not-ready = Cảnh báo: PDF chưa được tải hết để in.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Bật/Tắt thanh lề
pdfjs-toggle-sidebar-notification-button =
    .title = Bật tắt thanh lề (tài liệu bao gồm bản phác thảo/tập tin đính kèm/lớp)
pdfjs-toggle-sidebar-button-label = Bật/Tắt thanh lề
pdfjs-document-outline-button =
    .title = Hiển thị tài liệu phác thảo (nhấp đúp vào để mở rộng/thu gọn tất cả các mục)
pdfjs-document-outline-button-label = Bản phác tài liệu
pdfjs-attachments-button =
    .title = Hiện nội dung đính kèm
pdfjs-attachments-button-label = Nội dung đính kèm
pdfjs-layers-button =
    .title = Hiển thị các lớp (nhấp đúp để đặt lại tất cả các lớp về trạng thái mặc định)
pdfjs-layers-button-label = Lớp
pdfjs-thumbs-button =
    .title = Hiển thị ảnh thu nhỏ
pdfjs-thumbs-button-label = Ảnh thu nhỏ
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
pdfjs-thumb-page-title =
    .title = Trang { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Ảnh thu nhỏ của trang { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Tìm
    .placeholder = Tìm trong tài liệu…
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
pdfjs-editor-free-text-button-label = Văn bản
pdfjs-editor-ink-button =
    .title = Vẽ
pdfjs-editor-ink-button-label = Vẽ
pdfjs-editor-stamp-button =
    .title = Thêm hoặc chỉnh sửa hình ảnh
pdfjs-editor-stamp-button-label = Thêm hoặc chỉnh sửa hình ảnh
pdfjs-editor-highlight-button =
    .title = Đánh dấu
pdfjs-editor-highlight-button-label = Đánh dấu
pdfjs-highlight-floating-button1 =
    .title = Đánh dấu
    .aria-label = Đánh dấu
pdfjs-highlight-floating-button-label = Đánh dấu
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
pdfjs-free-text =
    .aria-label = Trình sửa văn bản
pdfjs-free-text-default-content = Bắt đầu nhập…
pdfjs-ink =
    .aria-label = Trình sửa nét vẽ
pdfjs-ink-canvas =
    .aria-label = Hình ảnh do người dùng tạo

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Văn bản thay thế
pdfjs-editor-alt-text-edit-button =
    .aria-label = Chỉnh sửa văn bản thay thế
pdfjs-editor-alt-text-edit-button-label = Chỉnh sửa văn bản thay thế
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

pdfjs-editor-resizer-label-top-left = Trên cùng bên trái — thay đổi kích thước
pdfjs-editor-resizer-label-top-middle = Trên cùng ở giữa — thay đổi kích thước
pdfjs-editor-resizer-label-top-right = Trên cùng bên phải — thay đổi kích thước
pdfjs-editor-resizer-label-middle-right = Ở giữa bên phải — thay đổi kích thước
pdfjs-editor-resizer-label-bottom-right = Dưới cùng bên phải — thay đổi kích thước
pdfjs-editor-resizer-label-bottom-middle = Ở giữa dưới cùng — thay đổi kích thước
pdfjs-editor-resizer-label-bottom-left = Góc dưới bên trái — thay đổi kích thước
pdfjs-editor-resizer-label-middle-left = Ở giữa bên trái — thay đổi kích thước
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
pdfjs-editor-new-alt-text-not-now-button = Không phải bây giờ
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
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Mô hình AI văn bản khác ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = Chạy cục bộ trên thiết bị của bạn để dữ liệu của bạn luôn ở chế độ riêng tư. Bắt buộc đối với văn bản thay thế tự động.
pdfjs-editor-alt-text-settings-delete-model-button = Xóa
pdfjs-editor-alt-text-settings-download-model-button = Tải xuống
pdfjs-editor-alt-text-settings-downloading-model-button = Đang tải xuống…
pdfjs-editor-alt-text-settings-editor-title = Trình soạn thảo văn bản thay thế
pdfjs-editor-alt-text-settings-show-dialog-button-label = Hiển thị ngay trình soạn thảo văn bản thay thế khi thêm hình ảnh
pdfjs-editor-alt-text-settings-show-dialog-description = Giúp bạn đảm bảo tất cả hình ảnh của bạn đều có văn bản thay thế.
pdfjs-editor-alt-text-settings-close-button = Đóng

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Đã xóa đánh dấu
pdfjs-editor-undo-bar-message-freetext = Đã xóa văn bản
pdfjs-editor-undo-bar-message-ink = Đã xóa bản vẽ
pdfjs-editor-undo-bar-message-stamp = Đã xóa hình ảnh
pdfjs-editor-undo-bar-message-signature = Chữ ký đã bị xoá
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
pdfjs-editor-add-signature-error-close-button = Đóng

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Hủy bỏ
pdfjs-editor-add-signature-add-button = Thêm
pdfjs-editor-edit-signature-update-button = Cập nhật

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Xoá chữ ký đã lưu
pdfjs-editor-delete-signature-button-label1 = Xoá chữ ký đã lưu

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Chỉnh sửa mô tả

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Chỉnh sửa mô tả
