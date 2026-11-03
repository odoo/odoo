# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = 前のページへ戻ります
pdfjs-previous-button-label = 前へ
pdfjs-next-button =
    .title = 次のページへ進みます
pdfjs-next-button-label = 次へ
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = ページ
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = / { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } / { $pagesCount })
pdfjs-zoom-out-button =
    .title = 表示を縮小します
pdfjs-zoom-out-button-label = 縮小
pdfjs-zoom-in-button =
    .title = 表示を拡大します
pdfjs-zoom-in-button-label = 拡大
pdfjs-zoom-select =
    .title = 拡大/縮小
pdfjs-presentation-mode-button =
    .title = プレゼンテーションモードに切り替えます
pdfjs-presentation-mode-button-label = プレゼンテーションモード
pdfjs-open-file-button =
    .title = ファイルを開きます
pdfjs-open-file-button-label = 開く
pdfjs-print-button =
    .title = 印刷します
pdfjs-print-button-label = 印刷
pdfjs-save-button =
    .title = 保存します
pdfjs-save-button-label = 保存
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = ダウンロードします
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = ダウンロード
pdfjs-bookmark-button =
    .title = 現在のページの URL です (現在のページを表示する URL)
pdfjs-bookmark-button-label = 現在のページ

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = ツール
pdfjs-tools-button-label = ツール
pdfjs-first-page-button =
    .title = 最初のページへ移動します
pdfjs-first-page-button-label = 最初のページへ移動
pdfjs-last-page-button =
    .title = 最後のページへ移動します
pdfjs-last-page-button-label = 最後のページへ移動
pdfjs-page-rotate-cw-button =
    .title = ページを右へ回転します
pdfjs-page-rotate-cw-button-label = 右回転
pdfjs-page-rotate-ccw-button =
    .title = ページを左へ回転します
pdfjs-page-rotate-ccw-button-label = 左回転
pdfjs-cursor-text-select-tool-button =
    .title = テキスト選択ツールを有効にします
pdfjs-cursor-text-select-tool-button-label = テキスト選択ツール
pdfjs-cursor-hand-tool-button =
    .title = 手のひらツールを有効にします
pdfjs-cursor-hand-tool-button-label = 手のひらツール
pdfjs-scroll-page-button =
    .title = ページ単位でスクロールします
pdfjs-scroll-page-button-label = ページ単位でスクロール
pdfjs-scroll-vertical-button =
    .title = 縦スクロールにします
pdfjs-scroll-vertical-button-label = 縦スクロール
pdfjs-scroll-horizontal-button =
    .title = 横スクロールにします
pdfjs-scroll-horizontal-button-label = 横スクロール
pdfjs-scroll-wrapped-button =
    .title = 折り返しスクロールにします
pdfjs-scroll-wrapped-button-label = 折り返しスクロール
pdfjs-spread-none-button =
    .title = 見開きにしません
pdfjs-spread-none-button-label = 見開きにしない
pdfjs-spread-odd-button =
    .title = 奇数ページ開始で見開きにします
pdfjs-spread-odd-button-label = 奇数ページ見開き
pdfjs-spread-even-button =
    .title = 偶数ページ開始で見開きにします
pdfjs-spread-even-button-label = 偶数ページ見開き

## Document properties dialog

pdfjs-document-properties-button =
    .title = 文書のプロパティ...
pdfjs-document-properties-button-label = 文書のプロパティ...
pdfjs-document-properties-file-name = ファイル名:
pdfjs-document-properties-file-size = ファイルサイズ:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } バイト)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } バイト)
pdfjs-document-properties-title = タイトル:
pdfjs-document-properties-author = 作成者:
pdfjs-document-properties-subject = 件名:
pdfjs-document-properties-keywords = キーワード:
pdfjs-document-properties-creation-date = 作成日:
pdfjs-document-properties-modification-date = 更新日:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = アプリケーション:
pdfjs-document-properties-producer = PDF 作成:
pdfjs-document-properties-version = PDF のバージョン:
pdfjs-document-properties-page-count = ページ数:
pdfjs-document-properties-page-size = ページサイズ:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = 縦
pdfjs-document-properties-page-size-orientation-landscape = 横
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = レター
pdfjs-document-properties-page-size-name-legal = リーガル

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
pdfjs-document-properties-linearized = ウェブ表示用に最適化:
pdfjs-document-properties-linearized-yes = はい
pdfjs-document-properties-linearized-no = いいえ
pdfjs-document-properties-close-button = 閉じる
pdfjs-digital-signature-properties-view-certificate = 証明書を表示
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = 理由: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = タイムスタンプ: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures = サブ署名 ({ $count } 筆)

## Print

pdfjs-print-progress-message = 文書の印刷を準備しています...
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = キャンセル
pdfjs-printing-not-supported = 警告: このブラウザーでは印刷が完全にサポートされていません。
pdfjs-printing-not-ready = 警告: PDF を印刷するための読み込みが終了していません。

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = 現在のアウトライン項目を検索
pdfjs-current-outline-item-button-label = 現在のアウトライン項目
pdfjs-findbar-button =
    .title = 文書内を検索します
pdfjs-findbar-button-label = 検索
pdfjs-additional-layers = 追加レイヤー

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = { $page } ページの縮小版
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = { $page } ページを選択します
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = { $page } / { $total } ページ

## Find panel button title and messages

pdfjs-find-input =
    .title = 検索
    .placeholder = 文書内を検索...
pdfjs-find-previous-button =
    .title = 現在より前の位置で指定文字列が現れる部分を検索します
pdfjs-find-previous-button-label = 前へ
pdfjs-find-next-button =
    .title = 現在より後の位置で指定文字列が現れる部分を検索します
pdfjs-find-next-button-label = 次へ
pdfjs-find-highlight-checkbox = すべて強調表示
pdfjs-find-match-case-checkbox-label = 大文字/小文字を区別
pdfjs-find-match-diacritics-checkbox-label = 発音区別符号を区別
pdfjs-find-entire-word-checkbox-label = 単語一致
pdfjs-find-reached-top = 文書先頭に到達したので末尾から続けて検索します
pdfjs-find-reached-bottom = 文書末尾に到達したので先頭から続けて検索します
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count = { $total } 件中 { $current } 件目
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit = { $limit } 件以上一致
pdfjs-find-not-found = 見つかりませんでした

## Predefined zoom values

pdfjs-page-scale-width = 幅に合わせる
pdfjs-page-scale-fit = ページのサイズに合わせる
pdfjs-page-scale-auto = 自動ズーム
pdfjs-page-scale-actual = 実際のサイズ
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = { $page } ページ

## Loading indicator messages

pdfjs-loading-error = PDF の読み込み中にエラーが発生しました。
pdfjs-invalid-file-error = 無効または破損した PDF ファイル。
pdfjs-missing-file-error = PDF ファイルが見つかりません。
pdfjs-unexpected-response-error = サーバーから予期せぬ応答がありました。
pdfjs-rendering-error = ページのレンダリング中にエラーが発生しました。

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } 注釈]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = この PDF ファイルを開くためのパスワードを入力してください。
pdfjs-password-invalid = パスワードが正しくありません。もう一度試してください。
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = キャンセル
pdfjs-web-fonts-disabled = ウェブフォントが無効になっています: 埋め込まれた PDF のフォントを使用できません。

## Editing

pdfjs-editor-free-text-button =
    .title = フリーテキスト注釈を追加します
pdfjs-editor-color-picker-free-text-input =
    .title = テキスト色を変更します
pdfjs-editor-free-text-button-label = フリーテキスト注釈
pdfjs-editor-ink-button =
    .title = インク注釈を追加します
pdfjs-editor-color-picker-ink-input =
    .title = インク色を変更します
pdfjs-editor-ink-button-label = インク注釈
pdfjs-editor-stamp-button =
    .title = 画像を追加または編集します
pdfjs-editor-stamp-button-label = 画像を追加または編集
pdfjs-editor-highlight-button =
    .title = 強調します
pdfjs-editor-highlight-button-label = 強調
pdfjs-highlight-floating-button1 =
    .title = 強調します
    .aria-label = 強調します
pdfjs-highlight-floating-button-label = 強調
pdfjs-comment-floating-button =
    .title = コメントを追加します
    .aria-label = コメントを追加します
pdfjs-comment-floating-button-label = コメント
pdfjs-editor-comment-button =
    .title = コメントを編集します
    .aria-label = コメントを編集します
pdfjs-editor-comment-button-label = コメント
pdfjs-editor-signature-button =
    .title = 署名を追加します
pdfjs-editor-signature-button-label = 署名を追加

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = 強調エディター
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = 描画エディター
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = 署名エディター: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = 画像エディター

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = インク注釈を削除します
pdfjs-editor-remove-freetext-button =
    .title = テキストを削除します
pdfjs-editor-remove-stamp-button =
    .title = 画像を削除します
pdfjs-editor-remove-highlight-button =
    .title = 強調を削除します
pdfjs-editor-remove-signature-button =
    .title = 署名を削除します

##

# Editor Parameters
pdfjs-editor-free-text-color-input = 色
pdfjs-editor-free-text-size-input = サイズ
pdfjs-editor-ink-color-input = 色
pdfjs-editor-ink-thickness-input = 太さ
pdfjs-editor-ink-opacity-input = 不透明度
pdfjs-editor-stamp-add-image-button =
    .title = 画像を追加します
pdfjs-editor-stamp-add-image-button-label = 画像を追加
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = 太さ
pdfjs-editor-free-highlight-thickness-title =
    .title = テキスト以外のアイテムを強調する時の太さを変更します
pdfjs-editor-add-signature-container =
    .aria-label = 署名コントロールと保存された署名
pdfjs-editor-signature-add-signature-button =
    .title = 新しい署名を追加します
pdfjs-editor-signature-add-signature-button-label = 新しい署名を追加
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = 保存された署名: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = フリーテキスト注釈エディター
    .default-content = テキストを入力してください...
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title = コメント
pdfjs-editor-comments-sidebar-close-button =
    .title = サイドバーを閉じます
    .aria-label = サイドバーを閉じる
pdfjs-editor-comments-sidebar-close-button-label = サイドバーを閉じる
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = 気になることがあれば、選択してコメントを残してください。
pdfjs-editor-comments-sidebar-no-comments-link = 詳細情報

## Alt-text dialog

pdfjs-editor-alt-text-button-label = 代替テキスト
pdfjs-editor-alt-text-edit-button =
    .aria-label = 代替テキストを編集
pdfjs-editor-alt-text-dialog-label = オプションの選択
pdfjs-editor-alt-text-dialog-description = 代替テキストは画像が表示されない場合や読み込まれない場合にユーザーの助けになります。
pdfjs-editor-alt-text-add-description-label = 説明を追加
pdfjs-editor-alt-text-add-description-description = 対象や設定、動作を説明する短い文章を記入してください。
pdfjs-editor-alt-text-mark-decorative-label = 装飾マークを付ける
pdfjs-editor-alt-text-mark-decorative-description = これは区切り線やウォーターマークなどの装飾画像に使用されます。
pdfjs-editor-alt-text-cancel-button = キャンセル
pdfjs-editor-alt-text-save-button = 保存
pdfjs-editor-alt-text-decorative-tooltip = 装飾マークが付いています
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = 例:「若い人がテーブルの席について食事をしています」
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = 代替テキスト

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = 左上隅 — サイズ変更
pdfjs-editor-resizer-top-middle =
    .aria-label = 上中央 — サイズ変更
pdfjs-editor-resizer-top-right =
    .aria-label = 右上隅 — サイズ変更
pdfjs-editor-resizer-middle-right =
    .aria-label = 右中央 — サイズ変更
pdfjs-editor-resizer-bottom-right =
    .aria-label = 右下隅 — サイズ変更
pdfjs-editor-resizer-bottom-middle =
    .aria-label = 下中央 — サイズ変更
pdfjs-editor-resizer-bottom-left =
    .aria-label = 左下隅 — サイズ変更
pdfjs-editor-resizer-middle-left =
    .aria-label = 左中央 — サイズ変更

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = 強調色
pdfjs-editor-colorpicker-button =
    .title = 色を変更します
pdfjs-editor-colorpicker-dropdown =
    .aria-label = 色の選択
pdfjs-editor-colorpicker-yellow =
    .title = 黄色
pdfjs-editor-colorpicker-green =
    .title = 緑色
pdfjs-editor-colorpicker-blue =
    .title = 青色
pdfjs-editor-colorpicker-pink =
    .title = ピンク色
pdfjs-editor-colorpicker-red =
    .title = 赤色

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = すべて表示
# (^m^) en-US: .title = Show all
pdfjs-editor-highlight-show-all-button =
    .title = 強調の表示を切り替えます

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = 代替テキストを編集 (画像の説明)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = 代替テキストを追加 (画像の説明)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = ここに説明を記入してください...
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = 画像が読み込まれない場合や見えない人のための短い説明です。
pdfjs-editor-new-alt-text-disclaimer1 = この代替テキストは自動的に生成されたため正確でない可能性があります。
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = 詳細情報
pdfjs-editor-new-alt-text-create-automatically-button-label = 代替テキストを自動生成
pdfjs-editor-new-alt-text-not-now-button = 後で
pdfjs-editor-new-alt-text-error-title = 代替テキストを自動生成できませんでした
pdfjs-editor-new-alt-text-error-description = ご自分で代替テキストを書くか後でもう一度試してください。
pdfjs-editor-new-alt-text-error-close-button = 閉じる
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = 代替テキスト AI モデルをダウンロードしています ({ $downloadedSize } / { $totalSize } MB)
    .aria-valuetext = 代替テキスト AI モデルをダウンロードしています ({ $downloadedSize } / { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = 代替テキストを追加しました
pdfjs-editor-new-alt-text-added-button-label = 代替テキストを追加しました
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = 代替テキストがありません
pdfjs-editor-new-alt-text-missing-button-label = 代替テキストがありません
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = 代替テキストをレビュー
pdfjs-editor-new-alt-text-to-review-button-label = 代替テキストをレビュー
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = 自動生成されました: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = 画像の代替テキスト設定
pdfjs-image-alt-text-settings-button-label = 画像の代替テキスト設定
pdfjs-editor-alt-text-settings-dialog-label = 画像の代替テキスト設定
pdfjs-editor-alt-text-settings-automatic-title = 自動代替テキスト
pdfjs-editor-alt-text-settings-create-model-button-label = 代替テキストを自動生成
pdfjs-editor-alt-text-settings-create-model-description = 画像が読み込まれない場合や見えない人のために説明を提案します。
pdfjs-editor-alt-text-settings-editor-title = 代替テキストエディター
pdfjs-editor-alt-text-settings-show-dialog-button-label = 画像の追加時に代替テキストエディターを表示する
pdfjs-editor-alt-text-settings-show-dialog-description = すべての画像に代替テキストを追加する助けになります。
pdfjs-editor-alt-text-settings-close-button = 閉じる

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = 強調表示を追加しました
pdfjs-editor-freetext-added-alert = フリーテキスト注釈を追加しました
pdfjs-editor-ink-added-alert = インク注釈を追加しました
pdfjs-editor-stamp-added-alert = 画像を追加しました
pdfjs-editor-signature-added-alert = 署名を追加しました

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = 強調表示が削除されました
pdfjs-editor-undo-bar-message-freetext = フリーテキスト注釈が削除されました
pdfjs-editor-undo-bar-message-ink = インク注釈が削除されました
pdfjs-editor-undo-bar-message-stamp = 画像が削除されました
pdfjs-editor-undo-bar-message-signature = 署名が削除されました
pdfjs-editor-undo-bar-message-comment = コメントが削除されました
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple = { $count } 個の注釈が削除されました
pdfjs-editor-undo-bar-undo-button =
    .title = 元に戻す
pdfjs-editor-undo-bar-undo-button-label = 元に戻す
pdfjs-editor-undo-bar-close-button =
    .title = 閉じる
pdfjs-editor-undo-bar-close-button-label = 閉じる

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = このダイアログではユーザーが署名を作成して PDF 文書に追加できます。
pdfjs-editor-add-signature-dialog-title = 署名を追加

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = タイプ
    .title = キーボード入力します
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = 手書き
    .title = 手書き入力します
pdfjs-editor-add-signature-image-button = 画像
    .title = 画像を指定します

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = 署名をキーボード入力
    .placeholder = 署名をキーボード入力
pdfjs-editor-add-signature-draw-placeholder = 署名を手書き入力
pdfjs-editor-add-signature-draw-thickness-range-label = 線の太さ
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = 線の太さ: { $thickness }
pdfjs-editor-add-signature-image-placeholder = ファイルをここにドラッグしてアップロード
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] または画像ファイルを選択
       *[other] または画像ファイルを参照
    }

## Controls

pdfjs-editor-add-signature-description-label = 説明 (代替テキスト)
pdfjs-editor-add-signature-description-input =
    .title = 説明 (代替テキスト) を追加します
pdfjs-editor-add-signature-description-default-when-drawing = 署名
pdfjs-editor-add-signature-clear-button-label = 署名を消去
pdfjs-editor-add-signature-clear-button =
    .title = 署名を消去します
pdfjs-editor-add-signature-save-checkbox = 署名を保存
pdfjs-editor-add-signature-save-warning-message = 保存された署名が上限の 5 個に達しました。さらに保存するにはいずれかを削除してください。
pdfjs-editor-add-signature-image-upload-error-title = 画像をアップロードできません
pdfjs-editor-add-signature-image-upload-error-description = ネットワーク接続を確認するか別の画像を試してください。
pdfjs-editor-add-signature-image-no-data-error-title = この画像は署名に変換できません
pdfjs-editor-add-signature-image-no-data-error-description = 別の画像をアップロードしてください。
pdfjs-editor-add-signature-error-close-button = 閉じる

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = キャンセル
pdfjs-editor-add-signature-add-button = 追加
pdfjs-editor-edit-signature-update-button = 更新

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = コメントを編集
pdfjs-editor-edit-comment-popup-button =
    .title = コメントを編集します
pdfjs-editor-delete-comment-popup-button-label = コメントを削除
pdfjs-editor-delete-comment-popup-button =
    .title = コメントを削除します
pdfjs-show-comment-button =
    .title = コメントを表示します

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = コメントを編集
pdfjs-editor-edit-comment-dialog-save-button-when-editing = 更新
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = コメントを追加
pdfjs-editor-edit-comment-dialog-save-button-when-adding = 追加
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = コメントを入力してください...
pdfjs-editor-edit-comment-dialog-cancel-button = キャンセル

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = コメントを追加します

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = サイドバーを切り替えます (文書に含まれるサムネイル、アウトライン、添付データ、レイヤー)
pdfjs-toggle-views-manager-button1-label = ページを管理
pdfjs-views-manager-sidebar =
    .aria-label = サイドバー
pdfjs-views-manager-sidebar-resizer =
    .aria-label = サイドバーの幅変更
pdfjs-views-manager-view-selector-button =
    .title = ビュー
pdfjs-views-manager-view-selector-button-label = ビュー
pdfjs-views-manager-pages-title = ページ
pdfjs-views-manager-outlines-title1 = 文書のアウトライン
    .title = 文書のアウトライン (ダブルクリックですべての項目を展開/折りたたみ)
pdfjs-views-manager-attachments-title = 添付データ
pdfjs-views-manager-layers-title1 = レイヤー
    .title = レイヤー (ダブルクリックですべてのレイヤーを既定状態にリセット)
pdfjs-views-manager-pages-option-label = ページ
pdfjs-views-manager-outlines-option-label = 文書のアウトライン
pdfjs-views-manager-attachments-option-label = 添付データ
pdfjs-views-manager-layers-option-label = レイヤー
pdfjs-views-manager-add-file-button =
    .title = ファイルを追加します
pdfjs-views-manager-add-file-button-label = ファイルを追加
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label = { $count } ページ選択中
pdfjs-views-manager-pages-status-none-action-label = ページを選択
pdfjs-views-manager-pages-status-action-button-label = 管理
pdfjs-views-manager-pages-status-copy-button-label = コピー
pdfjs-views-manager-pages-status-cut-button-label = 切り取り
pdfjs-views-manager-pages-status-delete-button-label = 削除
pdfjs-views-manager-pages-status-export-selected-button-label = 選択したページをエクスポート...
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label = { $count } ページを切り取りました
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label = { $count } ページをコピーしました
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label = { $count } ページを削除しました
pdfjs-views-manager-pages-status-waiting-ready-label = ファイルを準備しています...
pdfjs-views-manager-pages-status-waiting-uploading-label = ファイルをアップロードしています...
pdfjs-views-manager-status-warning-cut-label = 切り取りできませんでした。ページを更新してもう一度試してください。
pdfjs-views-manager-status-warning-copy-label = コピーできませんでした。ページを更新してもう一度試してください。
pdfjs-views-manager-status-warning-delete-label = 削除できませんでした。ページを更新してもう一度試してください。
pdfjs-views-manager-status-warning-save-label = 保存できませんでした。ページを更新してもう一度試してください。
pdfjs-views-manager-status-undo-button-label = 元に戻す
pdfjs-views-manager-status-done-button-label = 完了
pdfjs-views-manager-status-close-button =
    .title = 閉じる
pdfjs-views-manager-status-close-button-label = 閉じる
pdfjs-views-manager-paste-button-label = 貼り付け
pdfjs-views-manager-paste-button-before =
    .title = 最初のページの前に貼り付けます
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = { $page } ページの後に貼り付けます
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = 新機能
pdfjs-views-manager-waiting-for-file = ファイルをアップロードしています...
pdfjs-toggle-views-manager-button1 =
    .title = ページを管理

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .title = デジタル署名のプロパティ
    .aria-label = デジタル署名のプロパティ
pdfjs-digital-signature-properties-button-label = デジタル署名のプロパティ

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = 文書は検証されたデジタル署名で署名されています
pdfjs-digital-signature-properties-banner-unknown = 文書は署名されていますが、{ $count } 筆のデジタル署名が検証できません
pdfjs-digital-signature-properties-banner-untrusted = 文書は { $count } 筆の信頼できないデジタル署名で署名されています
pdfjs-digital-signature-properties-banner-expired = 文書は { $count } 枚の有効期限が切れた証明書で署名されています
pdfjs-digital-signature-properties-banner-invalid = 文書には { $count } 筆の不正なデジタル署名があります
pdfjs-digital-signature-properties-banner-revoked = 文書は { $count } 枚の破棄された証明書で署名されています

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = 状態: 検証された証明書
pdfjs-digital-signature-properties-status-invalid = 状態: 不正な証明書
pdfjs-digital-signature-properties-status-unknown = 状態: 検証不可 (未サポート)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = 証明書: 信頼されている ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = 証明書: 利用不可
pdfjs-digital-signature-properties-certificate-untrusted = 証明書: 信頼できない
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = 証明書: 発行者不明 ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = 証明書: 自己署名 ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = 証明書: 信頼できない発行者 ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = 証明書: 有効期限切れ
pdfjs-digital-signature-properties-certificate-expired-with-date = 証明書: 有効期限切れ ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = 証明書: 破棄

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = 保存された署名を削除します
pdfjs-editor-delete-signature-button-label1 = 保存された署名を削除

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = 説明を編集

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = 説明の編集
