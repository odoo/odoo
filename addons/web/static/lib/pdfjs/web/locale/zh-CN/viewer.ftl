# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = 上一页
pdfjs-previous-button-label = 上一页
pdfjs-next-button =
    .title = 下一页
pdfjs-next-button-label = 下一页
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = 页面
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = / { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } / { $pagesCount })
pdfjs-zoom-out-button =
    .title = 缩小
pdfjs-zoom-out-button-label = 缩小
pdfjs-zoom-in-button =
    .title = 放大
pdfjs-zoom-in-button-label = 放大
pdfjs-zoom-select =
    .title = 缩放
pdfjs-presentation-mode-button =
    .title = 切换到演示模式
pdfjs-presentation-mode-button-label = 演示模式
pdfjs-open-file-button =
    .title = 打开文件
pdfjs-open-file-button-label = 打开
pdfjs-print-button =
    .title = 打印
pdfjs-print-button-label = 打印
pdfjs-save-button =
    .title = 保存
pdfjs-save-button-label = 保存
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = 下载
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = 下载
pdfjs-bookmark-button =
    .title = 当前页面（在当前页面查看 URL）
pdfjs-bookmark-button-label = 当前页面

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = 工具
pdfjs-tools-button-label = 工具
pdfjs-first-page-button =
    .title = 转到第一页
pdfjs-first-page-button-label = 转到第一页
pdfjs-last-page-button =
    .title = 转到最后一页
pdfjs-last-page-button-label = 转到最后一页
pdfjs-page-rotate-cw-button =
    .title = 顺时针旋转
pdfjs-page-rotate-cw-button-label = 顺时针旋转
pdfjs-page-rotate-ccw-button =
    .title = 逆时针旋转
pdfjs-page-rotate-ccw-button-label = 逆时针旋转
pdfjs-cursor-text-select-tool-button =
    .title = 启用文本选择工具
pdfjs-cursor-text-select-tool-button-label = 文本选择工具
pdfjs-cursor-hand-tool-button =
    .title = 启用手形工具
pdfjs-cursor-hand-tool-button-label = 手形工具
pdfjs-scroll-page-button =
    .title = 使用页面滚动
pdfjs-scroll-page-button-label = 页面滚动
pdfjs-scroll-vertical-button =
    .title = 使用垂直滚动
pdfjs-scroll-vertical-button-label = 垂直滚动
pdfjs-scroll-horizontal-button =
    .title = 使用水平滚动
pdfjs-scroll-horizontal-button-label = 水平滚动
pdfjs-scroll-wrapped-button =
    .title = 使用平铺滚动
pdfjs-scroll-wrapped-button-label = 平铺滚动
pdfjs-spread-none-button =
    .title = 不加入衔接页
pdfjs-spread-none-button-label = 单页视图
pdfjs-spread-odd-button =
    .title = 加入衔接页使奇数页作为起始页
pdfjs-spread-odd-button-label = 双页视图
pdfjs-spread-even-button =
    .title = 加入衔接页使偶数页作为起始页
pdfjs-spread-even-button-label = 书籍视图

## Document properties dialog

pdfjs-document-properties-button =
    .title = 文档属性…
pdfjs-document-properties-button-label = 文档属性…
pdfjs-document-properties-file-name = 文件名:
pdfjs-document-properties-file-size = 文件大小:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB（{ $b } 字节）
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB（{ $b } 字节）
pdfjs-document-properties-title = 标题:
pdfjs-document-properties-author = 作者:
pdfjs-document-properties-subject = 主题:
pdfjs-document-properties-keywords = 关键词:
pdfjs-document-properties-creation-date = 创建日期:
pdfjs-document-properties-modification-date = 修改日期:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = 创建者:
pdfjs-document-properties-producer = PDF 生成器：
pdfjs-document-properties-version = PDF 版本:
pdfjs-document-properties-page-count = 页数:
pdfjs-document-properties-page-size = 页面大小：
pdfjs-document-properties-page-size-unit-inches = 英寸
pdfjs-document-properties-page-size-unit-millimeters = 毫米
pdfjs-document-properties-page-size-orientation-portrait = 纵向
pdfjs-document-properties-page-size-orientation-landscape = 横向
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
pdfjs-document-properties-linearized = 快速 Web 视图：
pdfjs-document-properties-linearized-yes = 是
pdfjs-document-properties-linearized-no = 否
pdfjs-document-properties-close-button = 关闭

## Print

pdfjs-print-progress-message = 正在准备打印文档…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = 取消
pdfjs-printing-not-supported = 警告：此浏览器尚未完整支持打印功能。
pdfjs-printing-not-ready = 警告：此 PDF 未完成加载，无法打印。

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = 切换侧栏
pdfjs-toggle-sidebar-notification-button =
    .title = 切换侧栏（文档所含的大纲/附件/图层）
pdfjs-toggle-sidebar-button-label = 切换侧栏
pdfjs-document-outline-button =
    .title = 显示文档大纲（双击展开/折叠所有项）
pdfjs-document-outline-button-label = 文档大纲
pdfjs-attachments-button =
    .title = 显示附件
pdfjs-attachments-button-label = 附件
pdfjs-layers-button =
    .title = 显示图层（双击即可将所有图层重置为默认状态）
pdfjs-layers-button-label = 图层
pdfjs-thumbs-button =
    .title = 显示缩略图
pdfjs-thumbs-button-label = 缩略图
pdfjs-current-outline-item-button =
    .title = 查找当前大纲项目
pdfjs-current-outline-item-button-label = 当前大纲项目
pdfjs-findbar-button =
    .title = 在文档中查找
pdfjs-findbar-button-label = 查找
pdfjs-additional-layers = 其他图层

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = 第 { $page } 页
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = 页面 { $page } 的缩略图

## Find panel button title and messages

pdfjs-find-input =
    .title = 查找
    .placeholder = 在文档中查找…
pdfjs-find-previous-button =
    .title = 查找词语上一次出现的位置
pdfjs-find-previous-button-label = 上一页
pdfjs-find-next-button =
    .title = 查找词语后一次出现的位置
pdfjs-find-next-button-label = 下一页
pdfjs-find-highlight-checkbox = 全部高亮显示
pdfjs-find-match-case-checkbox-label = 区分大小写
pdfjs-find-match-diacritics-checkbox-label = 匹配变音符号
pdfjs-find-entire-word-checkbox-label = 全词匹配
pdfjs-find-reached-top = 到达文档开头，从末尾继续
pdfjs-find-reached-bottom = 到达文档末尾，从开头继续
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count = 第 { $current } 项，共找到 { $total } 个匹配项
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit = 匹配超过 { $limit } 项
pdfjs-find-not-found = 找不到指定词语

## Predefined zoom values

pdfjs-page-scale-width = 适合页宽
pdfjs-page-scale-fit = 适合页面
pdfjs-page-scale-auto = 自动缩放
pdfjs-page-scale-actual = 实际大小
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = 第 { $page } 页

## Loading indicator messages

pdfjs-loading-error = 加载 PDF 时发生错误。
pdfjs-invalid-file-error = 无效或损坏的 PDF 文件。
pdfjs-missing-file-error = 缺少 PDF 文件。
pdfjs-unexpected-response-error = 意外的服务器响应。
pdfjs-rendering-error = 渲染页面时发生错误。

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [{ $type } 注释]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = 输入密码以打开此 PDF 文件。
pdfjs-password-invalid = 密码无效。请重试。
pdfjs-password-ok-button = 确定
pdfjs-password-cancel-button = 取消
pdfjs-web-fonts-disabled = Web 字体已被禁用：无法使用嵌入的 PDF 字体。

## Editing

pdfjs-editor-free-text-button =
    .title = 文本
pdfjs-editor-color-picker-free-text-input =
    .title = 更改文本颜色
pdfjs-editor-free-text-button-label = 文本
pdfjs-editor-ink-button =
    .title = 绘图
pdfjs-editor-color-picker-ink-input =
    .title = 更改绘图颜色
pdfjs-editor-ink-button-label = 绘图
pdfjs-editor-stamp-button =
    .title = 添加或编辑图像
pdfjs-editor-stamp-button-label = 添加或编辑图像
pdfjs-editor-highlight-button =
    .title = 高亮
pdfjs-editor-highlight-button-label = 高亮
pdfjs-highlight-floating-button1 =
    .title = 高亮
    .aria-label = 高亮
pdfjs-highlight-floating-button-label = 高亮
pdfjs-comment-floating-button =
    .title = 批注
    .aria-label = 批注
pdfjs-comment-floating-button-label = 批注
pdfjs-editor-comment-button =
    .title = 批注
    .aria-label = 批注
pdfjs-editor-comment-button-label = 批注
pdfjs-editor-signature-button =
    .title = 添加签名
pdfjs-editor-signature-button-label = 添加签名

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = 高亮编辑器
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = 绘图编辑器
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = 签名编辑器：{ $description }
pdfjs-editor-stamp-editor =
    .aria-label = 图像编辑器

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = 移除绘图
pdfjs-editor-remove-freetext-button =
    .title = 移除文本
pdfjs-editor-remove-stamp-button =
    .title = 移除图像
pdfjs-editor-remove-highlight-button =
    .title = 移除高亮
pdfjs-editor-remove-signature-button =
    .title = 移除签名

##

# Editor Parameters
pdfjs-editor-free-text-color-input = 颜色
pdfjs-editor-free-text-size-input = 字号
pdfjs-editor-ink-color-input = 颜色
pdfjs-editor-ink-thickness-input = 粗细
pdfjs-editor-ink-opacity-input = 不透明度
pdfjs-editor-stamp-add-image-button =
    .title = 添加图像
pdfjs-editor-stamp-add-image-button-label = 添加图像
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = 粗细
pdfjs-editor-free-highlight-thickness-title =
    .title = 更改高亮粗细（用于文本以外项目）
pdfjs-editor-add-signature-container =
    .aria-label = 签名管理和保存的签名
pdfjs-editor-signature-add-signature-button =
    .title = 添加新签名
pdfjs-editor-signature-add-signature-button-label = 添加新签名
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = 保存的签名：{ $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = 文本编辑器
    .default-content = 在此键入…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title = 批注
pdfjs-editor-comments-sidebar-close-button =
    .title = 关闭侧栏
    .aria-label = 关闭侧栏
pdfjs-editor-comments-sidebar-close-button-label = 关闭侧栏
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = 发现值得注意的地方？可为其添加高亮并批注。
pdfjs-editor-comments-sidebar-no-comments-link = 详细了解

## Alt-text dialog

pdfjs-editor-alt-text-button-label = 替换文字
pdfjs-editor-alt-text-edit-button =
    .aria-label = 编辑替换文字
pdfjs-editor-alt-text-dialog-label = 选择一项
pdfjs-editor-alt-text-dialog-description = 替换文字可在用户无法看到或加载图像时，描述其内容。
pdfjs-editor-alt-text-add-description-label = 添加描述
pdfjs-editor-alt-text-add-description-description = 用一两个句子，描述主题、背景或动作。
pdfjs-editor-alt-text-mark-decorative-label = 标记为装饰
pdfjs-editor-alt-text-mark-decorative-description = 用于装饰的图像，例如边框和水印。
pdfjs-editor-alt-text-cancel-button = 取消
pdfjs-editor-alt-text-save-button = 保存
pdfjs-editor-alt-text-decorative-tooltip = 已标记为装饰
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = 例如：一个少年坐到桌前，准备吃饭
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = 替换文字

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = 调整尺寸 - 左上角
pdfjs-editor-resizer-top-middle =
    .aria-label = 调整尺寸 - 顶部中间
pdfjs-editor-resizer-top-right =
    .aria-label = 调整尺寸 - 右上角
pdfjs-editor-resizer-middle-right =
    .aria-label = 调整尺寸 - 右侧中间
pdfjs-editor-resizer-bottom-right =
    .aria-label = 调整尺寸 - 右下角
pdfjs-editor-resizer-bottom-middle =
    .aria-label = 调整大小 - 底部中间
pdfjs-editor-resizer-bottom-left =
    .aria-label = 调整尺寸 - 左下角
pdfjs-editor-resizer-middle-left =
    .aria-label = 调整尺寸 - 左侧中间

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = 高亮色
pdfjs-editor-colorpicker-button =
    .title = 更改颜色
pdfjs-editor-colorpicker-dropdown =
    .aria-label = 颜色选择
pdfjs-editor-colorpicker-yellow =
    .title = 黄色
pdfjs-editor-colorpicker-green =
    .title = 绿色
pdfjs-editor-colorpicker-blue =
    .title = 蓝色
pdfjs-editor-colorpicker-pink =
    .title = 粉色
pdfjs-editor-colorpicker-red =
    .title = 红色

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = 显示全部
pdfjs-editor-highlight-show-all-button =
    .title = 显示全部

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = 编辑替换文字（图像描述）
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = 添加替换文字（图像描述）
pdfjs-editor-new-alt-text-textarea =
    .placeholder = 请在此处撰写描述…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = 向无法看到或加载图像的用户提供的简短描述。
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = 此段替换文字为自动创建，有可能不准确。
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = 详细了解
pdfjs-editor-new-alt-text-create-automatically-button-label = 自动创建替换文字
pdfjs-editor-new-alt-text-not-now-button = 暂时不要
pdfjs-editor-new-alt-text-error-title = 无法自动创建替换文字
pdfjs-editor-new-alt-text-error-description = 请自行撰写替换文字，或稍后再试。
pdfjs-editor-new-alt-text-error-close-button = 关闭
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = 正在下载提供替换文字的 AI 模型（{ $downloadedSize }/{ $totalSize } MB）
    .aria-valuetext = 正在下载提供替换文字的 AI 模型（{ $downloadedSize }/{ $totalSize } MB）
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = 已添加替换文字
pdfjs-editor-new-alt-text-added-button-label = 已添加替换文字
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = 缺少替换文字
pdfjs-editor-new-alt-text-missing-button-label = 缺少替换文字
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = 检查替换文字
pdfjs-editor-new-alt-text-to-review-button-label = 检查替换文字
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = [自动创建] { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = 图像替换文字设置
pdfjs-image-alt-text-settings-button-label = 图像替换文字设置
pdfjs-editor-alt-text-settings-dialog-label = 图像替换文字设置
pdfjs-editor-alt-text-settings-automatic-title = 自动创建替换文字
pdfjs-editor-alt-text-settings-create-model-button-label = 自动创建替换文字
pdfjs-editor-alt-text-settings-create-model-description = 向无法看到或加载图像的用户提供描述。
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = 提供替换文字的 AI 模型（{ $totalSize } MB）
pdfjs-editor-alt-text-settings-ai-model-description = 在您的设备本地运行，可使数据保持私密。自动创建替换文字需要使用此模型。
pdfjs-editor-alt-text-settings-delete-model-button = 删除
pdfjs-editor-alt-text-settings-download-model-button = 下载
pdfjs-editor-alt-text-settings-downloading-model-button = 正在下载…
pdfjs-editor-alt-text-settings-editor-title = 替换文字编辑器
pdfjs-editor-alt-text-settings-show-dialog-button-label = 添加图像后立即显示替换文字编辑器
pdfjs-editor-alt-text-settings-show-dialog-description = 帮助确保所有图像均拥有替换文字。
pdfjs-editor-alt-text-settings-close-button = 关闭

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = 已添加高亮
pdfjs-editor-freetext-added-alert = 已添加文本
pdfjs-editor-ink-added-alert = 已添加绘图
pdfjs-editor-stamp-added-alert = 已添加图像
pdfjs-editor-signature-added-alert = 已添加签名

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = 已移除高亮
pdfjs-editor-undo-bar-message-freetext = 已移除文本
pdfjs-editor-undo-bar-message-ink = 已移除绘图
pdfjs-editor-undo-bar-message-stamp = 已移除图像
pdfjs-editor-undo-bar-message-signature = 签名已移除
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple = 已移除 { $count } 条注释
pdfjs-editor-undo-bar-undo-button =
    .title = 撤销
pdfjs-editor-undo-bar-undo-button-label = 撤销
pdfjs-editor-undo-bar-close-button =
    .title = 关闭
pdfjs-editor-undo-bar-close-button-label = 关闭

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = 用户可通过此模态对话框创建要添加到 PDF 文档中的签名、编辑其名称（同时用作替换文字），并可保存签名以便重复使用。
pdfjs-editor-add-signature-dialog-title = 添加签名

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = 键入
    .title = 键入
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = 绘制
    .title = 绘制
pdfjs-editor-add-signature-image-button = 图像
    .title = 图像

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = 键入签名
    .placeholder = 键入签名
pdfjs-editor-add-signature-draw-placeholder = 绘制签名
pdfjs-editor-add-signature-draw-thickness-range-label = 粗细
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = 笔画粗细：{ $thickness }
pdfjs-editor-add-signature-image-placeholder = 拖放文件到此处以上传
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] 或选取图像文件
       *[other] 或浏览图像文件
    }

## Controls

pdfjs-editor-add-signature-description-label = 描述（替换文字）
pdfjs-editor-add-signature-description-input =
    .title = 描述（替换文字）
pdfjs-editor-add-signature-description-default-when-drawing = 签名
pdfjs-editor-add-signature-clear-button-label = 清除签名
pdfjs-editor-add-signature-clear-button =
    .title = 清除签名
pdfjs-editor-add-signature-save-checkbox = 保存签名
pdfjs-editor-add-signature-save-warning-message = 最多可保存 5 个签名，请移除一个以继续保存。
pdfjs-editor-add-signature-image-upload-error-title = 无法上传图像
pdfjs-editor-add-signature-image-upload-error-description = 请检查网络连接，或尝试上传其他图像。
pdfjs-editor-add-signature-image-no-data-error-title = 无法将此图像转换为签名
pdfjs-editor-add-signature-image-no-data-error-description = 请尝试上传其他图像。
pdfjs-editor-add-signature-error-close-button = 关闭

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = 取消
pdfjs-editor-add-signature-add-button = 添加
pdfjs-editor-edit-signature-update-button = 更新

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = 编辑批注
pdfjs-editor-edit-comment-popup-button =
    .title = 编辑批注
pdfjs-editor-delete-comment-popup-button-label = 移除批注
pdfjs-editor-delete-comment-popup-button =
    .title = 移除批注
pdfjs-show-comment-button =
    .title = 显示批注

##  Edit a comment dialog

pdfjs-editor-edit-comment-actions-button-label = 操作
pdfjs-editor-edit-comment-actions-button =
    .title = 操作
pdfjs-editor-edit-comment-close-button-label = 关闭
pdfjs-editor-edit-comment-close-button =
    .title = 关闭
pdfjs-editor-edit-comment-actions-edit-button-label = 编辑
pdfjs-editor-edit-comment-actions-delete-button-label = 删除
pdfjs-editor-edit-comment-manager-text-input =
    .placeholder = 输入批注
pdfjs-editor-edit-comment-manager-cancel-button = 取消
pdfjs-editor-edit-comment-manager-save-button = 保存
# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = 编辑批注
pdfjs-editor-edit-comment-dialog-save-button-when-editing = 更新
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = 添加批注
pdfjs-editor-edit-comment-dialog-save-button-when-adding = 添加
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = 开始键入…
pdfjs-editor-edit-comment-dialog-cancel-button = 取消

## Edit a comment button in the editor toolbar

pdfjs-editor-edit-comment-button =
    .title = 编辑批注

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = 移除已保存的签名
pdfjs-editor-delete-signature-button-label1 = 移除已保存的签名

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = 编辑描述

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = 编辑描述
