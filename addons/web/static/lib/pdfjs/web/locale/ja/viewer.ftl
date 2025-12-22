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
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } バイト)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } バイト)
pdfjs-document-properties-title = タイトル:
pdfjs-document-properties-author = 作成者:
pdfjs-document-properties-subject = 件名:
pdfjs-document-properties-keywords = キーワード:
pdfjs-document-properties-creation-date = 作成日:
pdfjs-document-properties-modification-date = 更新日:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
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

## Print

pdfjs-print-progress-message = 文書の印刷を準備しています...
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = キャンセル
pdfjs-printing-not-supported = 警告: このブラウザーでは印刷が完全にサポートされていません。
pdfjs-printing-not-ready = 警告: PDF を印刷するための読み込みが終了していません。

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = サイドバー表示を切り替えます
pdfjs-toggle-sidebar-notification-button =
    .title = サイドバー表示を切り替えます (文書に含まれるアウトライン / 添付 / レイヤー)
pdfjs-toggle-sidebar-button-label = サイドバーの切り替え
pdfjs-document-outline-button =
    .title = 文書の目次を表示します (ダブルクリックで項目を開閉します)
pdfjs-document-outline-button-label = 文書の目次
pdfjs-attachments-button =
    .title = 添付ファイルを表示します
pdfjs-attachments-button-label = 添付ファイル
pdfjs-layers-button =
    .title = レイヤーを表示します (ダブルクリックですべてのレイヤーが初期状態に戻ります)
pdfjs-layers-button-label = レイヤー
pdfjs-thumbs-button =
    .title = 縮小版を表示します
pdfjs-thumbs-button-label = 縮小版
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
pdfjs-thumb-page-title =
    .title = { $page } ページ
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = { $page } ページの縮小版

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
pdfjs-editor-free-text-button-label = フリーテキスト注釈
pdfjs-editor-ink-button =
    .title = インク注釈を追加します
pdfjs-editor-ink-button-label = インク注釈
pdfjs-editor-stamp-button =
    .title = 画像を追加または編集します
pdfjs-editor-stamp-button-label = 画像を追加または編集
pdfjs-editor-highlight-button =
    .title = 強調します
pdfjs-editor-highlight-button-label = 強調
pdfjs-highlight-floating-button1 =
    .title = 強調
    .aria-label = 強調します
pdfjs-highlight-floating-button-label = 強調

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = インク注釈を削除します
pdfjs-editor-remove-freetext-button =
    .title = テキストを削除します
pdfjs-editor-remove-stamp-button =
    .title = 画像を削除します
pdfjs-editor-remove-highlight-button =
    .title = 強調を削除します

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
pdfjs-free-text =
    .aria-label = フリーテキスト注釈エディター
pdfjs-free-text-default-content = テキストを入力してください...
pdfjs-ink =
    .aria-label = インク注釈エディター
pdfjs-ink-canvas =
    .aria-label = ユーザー作成画像

## Alt-text dialog

# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button-label = 代替テキスト
pdfjs-editor-alt-text-edit-button-label = 代替テキストを編集
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

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = 左上隅 — サイズ変更
pdfjs-editor-resizer-label-top-middle = 上中央 — サイズ変更
pdfjs-editor-resizer-label-top-right = 右上隅 — サイズ変更
pdfjs-editor-resizer-label-middle-right = 右中央 — サイズ変更
pdfjs-editor-resizer-label-bottom-right = 右下隅 — サイズ変更
pdfjs-editor-resizer-label-bottom-middle = 下中央 — サイズ変更
pdfjs-editor-resizer-label-bottom-left = 左下隅 — サイズ変更
pdfjs-editor-resizer-label-middle-left = 左中央 — サイズ変更
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
#   $percent (Number) - the percentage of the downloaded size.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = 代替テキスト AI モデルをダウンロードしています ({ $downloadedSize } / { $totalSize } MB)
    .aria-valuetext = 代替テキスト AI モデルをダウンロードしています ({ $downloadedSize } / { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button-label = 代替テキストを追加しました
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button-label = 代替テキストがありません
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
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
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = 代替テキスト AI モデル ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = ローカルの端末上で実行されるためデータは非公開になります。代替テキストの自動生成に必要です。
pdfjs-editor-alt-text-settings-delete-model-button = 削除
pdfjs-editor-alt-text-settings-download-model-button = ダウンロード
pdfjs-editor-alt-text-settings-downloading-model-button = ダウンロード中...
pdfjs-editor-alt-text-settings-editor-title = 代替テキストエディター
pdfjs-editor-alt-text-settings-show-dialog-button-label = 画像の追加時に代替テキストエディターを表示する
pdfjs-editor-alt-text-settings-show-dialog-description = すべての画像に代替テキストを追加する助けになります。
pdfjs-editor-alt-text-settings-close-button = 閉じる
