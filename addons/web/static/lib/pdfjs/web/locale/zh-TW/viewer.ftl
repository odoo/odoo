# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = 上一頁
pdfjs-previous-button-label = 上一頁
pdfjs-next-button =
    .title = 下一頁
pdfjs-next-button-label = 下一頁
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = 第
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = 頁，共 { $pagesCount } 頁
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = （第 { $pageNumber } 頁，共 { $pagesCount } 頁）
pdfjs-zoom-out-button =
    .title = 縮小
pdfjs-zoom-out-button-label = 縮小
pdfjs-zoom-in-button =
    .title = 放大
pdfjs-zoom-in-button-label = 放大
pdfjs-zoom-select =
    .title = 縮放
pdfjs-presentation-mode-button =
    .title = 切換至簡報模式
pdfjs-presentation-mode-button-label = 簡報模式
pdfjs-open-file-button =
    .title = 開啟檔案
pdfjs-open-file-button-label = 開啟
pdfjs-print-button =
    .title = 列印
pdfjs-print-button-label = 列印
pdfjs-save-button =
    .title = 儲存
pdfjs-save-button-label = 儲存
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = 下載
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = 下載
pdfjs-bookmark-button =
    .title = 目前頁面（含目前檢視頁面的網址）
pdfjs-bookmark-button-label = 目前頁面

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = 工具
pdfjs-tools-button-label = 工具
pdfjs-first-page-button =
    .title = 跳到第一頁
pdfjs-first-page-button-label = 跳到第一頁
pdfjs-last-page-button =
    .title = 跳到最後一頁
pdfjs-last-page-button-label = 跳到最後一頁
pdfjs-page-rotate-cw-button =
    .title = 順時針旋轉
pdfjs-page-rotate-cw-button-label = 順時針旋轉
pdfjs-page-rotate-ccw-button =
    .title = 逆時針旋轉
pdfjs-page-rotate-ccw-button-label = 逆時針旋轉
pdfjs-cursor-text-select-tool-button =
    .title = 開啟文字選擇工具
pdfjs-cursor-text-select-tool-button-label = 文字選擇工具
pdfjs-cursor-hand-tool-button =
    .title = 開啟頁面移動工具
pdfjs-cursor-hand-tool-button-label = 頁面移動工具
pdfjs-scroll-page-button =
    .title = 使用單頁捲動版面
pdfjs-scroll-page-button-label = 單頁捲動
pdfjs-scroll-vertical-button =
    .title = 使用垂直捲動版面
pdfjs-scroll-vertical-button-label = 垂直捲動
pdfjs-scroll-horizontal-button =
    .title = 使用水平捲動版面
pdfjs-scroll-horizontal-button-label = 水平捲動
pdfjs-scroll-wrapped-button =
    .title = 使用多頁捲動版面
pdfjs-scroll-wrapped-button-label = 多頁捲動
pdfjs-spread-none-button =
    .title = 不要進行跨頁顯示
pdfjs-spread-none-button-label = 不跨頁
pdfjs-spread-odd-button =
    .title = 從奇數頁開始跨頁
pdfjs-spread-odd-button-label = 奇數跨頁
pdfjs-spread-even-button =
    .title = 從偶數頁開始跨頁
pdfjs-spread-even-button-label = 偶數跨頁

## Document properties dialog

pdfjs-document-properties-button =
    .title = 文件內容…
pdfjs-document-properties-button-label = 文件內容…
pdfjs-document-properties-file-name = 檔案名稱：
pdfjs-document-properties-file-size = 檔案大小：
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB（{ $b } 位元組）
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB（{ $b } 位元組）
pdfjs-document-properties-title = 標題：
pdfjs-document-properties-author = 作者：
pdfjs-document-properties-subject = 主旨：
pdfjs-document-properties-keywords = 關鍵字：
pdfjs-document-properties-creation-date = 建立日期：
pdfjs-document-properties-modification-date = 修改日期：
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = 建立者：
pdfjs-document-properties-producer = PDF 產生器：
pdfjs-document-properties-version = PDF 版本：
pdfjs-document-properties-page-count = 頁數：
pdfjs-document-properties-page-size = 頁面大小：
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = 垂直
pdfjs-document-properties-page-size-orientation-landscape = 水平
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

pdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit }（{ $orientation }）
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit }（{ $name }，{ $orientation }）

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = 快速 Web 檢視：
pdfjs-document-properties-linearized-yes = 是
pdfjs-document-properties-linearized-no = 否
pdfjs-document-properties-close-button = 關閉

## Print

pdfjs-print-progress-message = 正在準備列印文件…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = 取消
pdfjs-printing-not-supported = 警告：此瀏覽器未完整支援列印功能。
pdfjs-printing-not-ready = 警告：此 PDF 未完成下載以供列印。

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = 切換側邊欄
pdfjs-toggle-sidebar-notification-button =
    .title = 切換側邊欄（包含大綱、附件、圖層的文件）
pdfjs-toggle-sidebar-button-label = 切換側邊欄
pdfjs-document-outline-button =
    .title = 顯示文件大綱（雙擊展開/摺疊所有項目）
pdfjs-document-outline-button-label = 文件大綱
pdfjs-attachments-button =
    .title = 顯示附件
pdfjs-attachments-button-label = 附件
pdfjs-layers-button =
    .title = 顯示圖層（滑鼠雙擊即可將所有圖層重設為預設狀態）
pdfjs-layers-button-label = 圖層
pdfjs-thumbs-button =
    .title = 顯示縮圖
pdfjs-thumbs-button-label = 縮圖
pdfjs-current-outline-item-button =
    .title = 尋找目前的大綱項目
pdfjs-current-outline-item-button-label = 目前的大綱項目
pdfjs-findbar-button =
    .title = 在文件中尋找
pdfjs-findbar-button-label = 尋找
pdfjs-additional-layers = 其他圖層

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = 第 { $page } 頁
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = 第 { $page } 頁的縮圖

## Find panel button title and messages

pdfjs-find-input =
    .title = 尋找
    .placeholder = 在文件中搜尋…
pdfjs-find-previous-button =
    .title = 尋找文字前次出現的位置
pdfjs-find-previous-button-label = 上一個
pdfjs-find-next-button =
    .title = 尋找文字下次出現的位置
pdfjs-find-next-button-label = 下一個
pdfjs-find-highlight-checkbox = 強調全部
pdfjs-find-match-case-checkbox-label = 區分大小寫
pdfjs-find-match-diacritics-checkbox-label = 符合變音符號
pdfjs-find-entire-word-checkbox-label = 符合整個字
pdfjs-find-reached-top = 已搜尋至文件頂端，自底端繼續搜尋
pdfjs-find-reached-bottom = 已搜尋至文件底端，自頂端繼續搜尋
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count = 第 { $current } 筆符合，共符合 { $total } 筆
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit = 符合超過 { $limit } 項
pdfjs-find-not-found = 找不到指定文字

## Predefined zoom values

pdfjs-page-scale-width = 頁面寬度
pdfjs-page-scale-fit = 縮放至頁面大小
pdfjs-page-scale-auto = 自動縮放
pdfjs-page-scale-actual = 實際大小
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = 第 { $page } 頁

## Loading indicator messages

pdfjs-loading-error = 載入 PDF 時發生錯誤。
pdfjs-invalid-file-error = 無效或毀損的 PDF 檔案。
pdfjs-missing-file-error = 找不到 PDF 檔案。
pdfjs-unexpected-response-error = 伺服器回應未預期的內容。
pdfjs-rendering-error = 描繪頁面時發生錯誤。

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } 註解]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = 請輸入用來開啟此 PDF 檔案的密碼。
pdfjs-password-invalid = 密碼不正確，請再試一次。
pdfjs-password-ok-button = 確定
pdfjs-password-cancel-button = 取消
pdfjs-web-fonts-disabled = 已停用網路字型 (Web fonts): 無法使用 PDF 內嵌字型。

## Editing

pdfjs-editor-free-text-button =
    .title = 文字
pdfjs-editor-color-picker-free-text-input =
    .title = 更改文字色彩
pdfjs-editor-free-text-button-label = 文字
pdfjs-editor-ink-button =
    .title = 繪圖
pdfjs-editor-color-picker-ink-input =
    .title = 更改繪圖色彩
pdfjs-editor-ink-button-label = 繪圖
pdfjs-editor-stamp-button =
    .title = 新增或編輯圖片
pdfjs-editor-stamp-button-label = 新增或編輯圖片
pdfjs-editor-highlight-button =
    .title = 強調
pdfjs-editor-highlight-button-label = 強調
pdfjs-highlight-floating-button1 =
    .title = 強調
    .aria-label = 強調
pdfjs-highlight-floating-button-label = 強調
pdfjs-comment-floating-button =
    .title = 註解
    .aria-label = 註解
pdfjs-comment-floating-button-label = 註解
pdfjs-editor-comment-button =
    .title = 註解
    .aria-label = 註解
pdfjs-editor-comment-button-label = 註解
pdfjs-editor-signature-button =
    .title = 加入簽章
pdfjs-editor-signature-button-label = 加入簽章

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = 強調樣式編輯器
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = 繪圖編輯器
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = 簽章編輯器：{ $description }
pdfjs-editor-stamp-editor =
    .aria-label = 圖片編輯器

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = 移除繪圖
pdfjs-editor-remove-freetext-button =
    .title = 移除文字
pdfjs-editor-remove-stamp-button =
    .title = 移除圖片
pdfjs-editor-remove-highlight-button =
    .title = 移除選擇範圍的強調效果
pdfjs-editor-remove-signature-button =
    .title = 移除簽章

##

# Editor Parameters
pdfjs-editor-free-text-color-input = 色彩
pdfjs-editor-free-text-size-input = 大小
pdfjs-editor-ink-color-input = 色彩
pdfjs-editor-ink-thickness-input = 線條粗細
pdfjs-editor-ink-opacity-input = 透​明度
pdfjs-editor-stamp-add-image-button =
    .title = 新增圖片
pdfjs-editor-stamp-add-image-button-label = 新增圖片
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = 線條粗細
pdfjs-editor-free-highlight-thickness-title =
    .title = 更改強調文字以外的項目時的線條粗細
pdfjs-editor-add-signature-container =
    .aria-label = 簽章控制元件與儲存的簽章
pdfjs-editor-signature-add-signature-button =
    .title = 新增簽章
pdfjs-editor-signature-add-signature-button-label = 新增簽章
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = 已儲存簽章：{ $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = 文字編輯器
    .default-content = 請打字…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title = 註解
pdfjs-editor-comments-sidebar-close-button =
    .title = 關閉側邊欄
    .aria-label = 關閉側邊欄
pdfjs-editor-comments-sidebar-close-button-label = 關閉側邊欄
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = 想把哪個部分記下來？可以畫螢光強調，並且留下註解。
pdfjs-editor-comments-sidebar-no-comments-link = 更多資訊

## Alt-text dialog

pdfjs-editor-alt-text-button-label = 替代文字
pdfjs-editor-alt-text-edit-button =
    .aria-label = 編輯替代文字
pdfjs-editor-alt-text-dialog-label = 挑選一種
pdfjs-editor-alt-text-dialog-description = 替代文字可協助盲人，或於圖片無法載入時提供說明。
pdfjs-editor-alt-text-add-description-label = 新增描述
pdfjs-editor-alt-text-add-description-description = 用 1-2 句文字描述主題、背景或動作。
pdfjs-editor-alt-text-mark-decorative-label = 標示為裝飾性內容
pdfjs-editor-alt-text-mark-decorative-description = 這是裝飾性圖片，例如邊框或浮水印。
pdfjs-editor-alt-text-cancel-button = 取消
pdfjs-editor-alt-text-save-button = 儲存
pdfjs-editor-alt-text-decorative-tooltip = 已標示為裝飾性內容
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = 例如：「有一位年輕男人坐在桌子前面吃飯」
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = 替代文字

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = 左上角 — 調整大小
pdfjs-editor-resizer-top-middle =
    .aria-label = 頂部中間 — 調整大小
pdfjs-editor-resizer-top-right =
    .aria-label = 右上角 — 調整大小
pdfjs-editor-resizer-middle-right =
    .aria-label = 中間右方 — 調整大小
pdfjs-editor-resizer-bottom-right =
    .aria-label = 右下角 — 調整大小
pdfjs-editor-resizer-bottom-middle =
    .aria-label = 底部中間 — 調整大小
pdfjs-editor-resizer-bottom-left =
    .aria-label = 左下角 — 調整大小
pdfjs-editor-resizer-middle-left =
    .aria-label = 中間左方 — 調整大小

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = 強調色彩
pdfjs-editor-colorpicker-button =
    .title = 更改色彩
pdfjs-editor-colorpicker-dropdown =
    .aria-label = 色彩選項
pdfjs-editor-colorpicker-yellow =
    .title = 黃色
pdfjs-editor-colorpicker-green =
    .title = 綠色
pdfjs-editor-colorpicker-blue =
    .title = 藍色
pdfjs-editor-colorpicker-pink =
    .title = 粉紅色
pdfjs-editor-colorpicker-red =
    .title = 紅色

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = 顯示全部
pdfjs-editor-highlight-show-all-button =
    .title = 顯示全部

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = 編輯替代文字（圖片描述）
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = 新增替代文字（圖片描述）
pdfjs-editor-new-alt-text-textarea =
    .placeholder = 在此寫下您的描述文字…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = 為看不到圖片的讀者，或圖片無法載入時顯示的簡短描述。
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = 此替代文字是自動產生的，可能不夠精確。
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = 更多資訊
pdfjs-editor-new-alt-text-create-automatically-button-label = 自動產生替代文字
pdfjs-editor-new-alt-text-not-now-button = 暫時不要
pdfjs-editor-new-alt-text-error-title = 無法自動產生替代文字
pdfjs-editor-new-alt-text-error-description = 請自行填寫替代文字，或稍後再試一次。
pdfjs-editor-new-alt-text-error-close-button = 關閉
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = 正在下載替代文字 AI 模型（{ $downloadedSize } / { $totalSize } MB）
    .aria-valuetext = 正在下載替代文字 AI 模型（{ $downloadedSize } / { $totalSize } MB）
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = 已新增替代文字
pdfjs-editor-new-alt-text-added-button-label = 已新增替代文字
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = 缺少替代文字
pdfjs-editor-new-alt-text-missing-button-label = 缺少替代文字
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = 確認替代文字
pdfjs-editor-new-alt-text-to-review-button-label = 確認替代文字
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = 自動產生：{ $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = 圖片替代文字設定
pdfjs-image-alt-text-settings-button-label = 圖片替代文字設定
pdfjs-editor-alt-text-settings-dialog-label = 圖片替代文字設定
pdfjs-editor-alt-text-settings-automatic-title = 自動化替代文字
pdfjs-editor-alt-text-settings-create-model-button-label = 自動產生替代文字
pdfjs-editor-alt-text-settings-create-model-description = 為您建議圖片描述，幫助看不到圖片的讀者，或於圖片無法載入時顯示。
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = 替代文字 AI 模型（{ $totalSize } MB）
pdfjs-editor-alt-text-settings-ai-model-description = 在您的本機裝置上運作，以確保您的資料隱私。必須下載此模型才可以自動產生替代文字。
pdfjs-editor-alt-text-settings-delete-model-button = 刪除
pdfjs-editor-alt-text-settings-download-model-button = 下載
pdfjs-editor-alt-text-settings-downloading-model-button = 下載中…
pdfjs-editor-alt-text-settings-editor-title = 替代文字編輯器
pdfjs-editor-alt-text-settings-show-dialog-button-label = 新增圖片後立即顯示替代文字編輯器
pdfjs-editor-alt-text-settings-show-dialog-description = 幫助您確保所有圖片都有替代文字。
pdfjs-editor-alt-text-settings-close-button = 關閉

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = 已加入強調範圍
pdfjs-editor-freetext-added-alert = 已加入文字
pdfjs-editor-ink-added-alert = 已新增繪圖
pdfjs-editor-stamp-added-alert = 已新增圖片
pdfjs-editor-signature-added-alert = 已新增簽章

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = 已移除強調
pdfjs-editor-undo-bar-message-freetext = 已移除文字
pdfjs-editor-undo-bar-message-ink = 已移除繪圖
pdfjs-editor-undo-bar-message-stamp = 已移除圖片
pdfjs-editor-undo-bar-message-signature = 已移除簽章
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple = 已移除 { $count } 筆註解
pdfjs-editor-undo-bar-undo-button =
    .title = 還原
pdfjs-editor-undo-bar-undo-button-label = 還原
pdfjs-editor-undo-bar-close-button =
    .title = 關閉
pdfjs-editor-undo-bar-close-button-label = 關閉

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = 此對話框讓使用者能夠建立簽章以加入 PDF 文件。使用者可以編輯他們的姓名（同時也是替代文字），並選擇性儲存簽章，以供未來重複使用。
pdfjs-editor-add-signature-dialog-title = 加入簽章

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = 打字
    .title = 打字
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = 手繪
    .title = 手繪
pdfjs-editor-add-signature-image-button = 圖片
    .title = 圖片

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = 輸入簽章
    .placeholder = 輸入簽章
pdfjs-editor-add-signature-draw-placeholder = 手繪簽章
pdfjs-editor-add-signature-draw-thickness-range-label = 線條粗細
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = 繪製時的線條粗細：{ $thickness }
pdfjs-editor-add-signature-image-placeholder = 將檔案拖曳到此處即可上傳
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] 或選擇圖片檔案
       *[other] 或瀏覽圖片檔案
    }

## Controls

pdfjs-editor-add-signature-description-label = 描述（替代文字）
pdfjs-editor-add-signature-description-input =
    .title = 描述（替代文字）
pdfjs-editor-add-signature-description-default-when-drawing = 簽章
pdfjs-editor-add-signature-clear-button-label = 清除簽章
pdfjs-editor-add-signature-clear-button =
    .title = 清除簽章
pdfjs-editor-add-signature-save-checkbox = 儲存簽章
pdfjs-editor-add-signature-save-warning-message = 您已經儲存 5 式簽章，請移除任一式才能再新增。
pdfjs-editor-add-signature-image-upload-error-title = 無法上傳圖片
pdfjs-editor-add-signature-image-upload-error-description = 請檢查您的網路連線，或改用其他圖片。
pdfjs-editor-add-signature-image-no-data-error-title = 無法將此圖片轉換成簽章
pdfjs-editor-add-signature-image-no-data-error-description = 請試著上傳另一張圖片。
pdfjs-editor-add-signature-error-close-button = 關閉

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = 取消
pdfjs-editor-add-signature-add-button = 新增
pdfjs-editor-edit-signature-update-button = 更新

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = 編輯註解
pdfjs-editor-edit-comment-popup-button =
    .title = 編輯註解
pdfjs-editor-delete-comment-popup-button-label = 移除註解
pdfjs-editor-delete-comment-popup-button =
    .title = 移除註解
pdfjs-show-comment-button =
    .title = 顯示註解

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = 動作
pdfjs-editor-edit-comment-actions-button =
    .title = 動作
pdfjs-editor-edit-comment-close-button-label = 關閉
pdfjs-editor-edit-comment-close-button =
    .title = 關閉
pdfjs-editor-edit-comment-actions-edit-button-label = 編輯
pdfjs-editor-edit-comment-actions-delete-button-label = 刪除
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = 輸入您的註解
pdfjs-editor-edit-comment-manager-cancel-button = 取消
pdfjs-editor-edit-comment-manager-save-button = 儲存
# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = 編輯註解
pdfjs-editor-edit-comment-dialog-save-button-when-editing = 更新
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = 新增註解
pdfjs-editor-edit-comment-dialog-save-button-when-adding = 新增
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = 在此打字…
pdfjs-editor-edit-comment-dialog-cancel-button = 取消

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = 編輯註解
pdfjs-editor-add-comment-button =
    .title = 新增註解

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = 移除儲存的簽章
pdfjs-editor-delete-signature-button-label1 = 移除儲存的簽章

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = 編輯描述

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = 編輯描述
