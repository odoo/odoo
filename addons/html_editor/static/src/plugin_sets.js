/** @odoo-module native */
import { CaptionPlugin } from "@html_editor/others/embedded_components/plugins/caption_plugin/caption_plugin";
import { SyntaxHighlightingPlugin } from "@html_editor/others/embedded_components/plugins/syntax_highlighting_plugin/syntax_highlighting_plugin";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { DatePlugin } from "./others/embedded_components/plugins/date_plugin/date_plugin.js";
import { ToggleBlockPlugin } from "@html_editor/others/embedded_components/plugins/toggle_block_plugin/toggle_block_plugin";
import { EmbeddedVideoPlugin } from "@html_editor/others/embedded_components/plugins/video_plugin/embedded_video_plugin";

import { BaseContainerPlugin } from "./core/base_container_plugin.js";
import { ClipboardPlugin } from "./core/clipboard_plugin.js";
import { CommentPlugin } from "./core/comment_plugin.js";
import { ContentEditablePlugin } from "./core/content_editable_plugin.js";
import { DeletePlugin } from "./core/delete_plugin.js";
import { DialogPlugin } from "./core/dialog_plugin.js";
import { DomPlugin } from "./core/dom_plugin.js";
import { EditorVersionPlugin } from "./core/editor_version_plugin.js";
import { FormatPlugin } from "./core/format_plugin.js";
import { HistoryPlugin } from "./core/history_plugin.js";
import { InputPlugin } from "./core/input_plugin.js";
import { LineBreakPlugin } from "./core/line_break_plugin.js";
import { NoInlineRootPlugin } from "./core/no_inline_root_plugin.js";
import { OverlayPlugin } from "./core/overlay_plugin.js";
import { ProtectedNodePlugin } from "./core/protected_node_plugin.js";
import { SanitizePlugin } from "./core/sanitize_plugin.js";
import { SelectionPlugin } from "./core/selection_plugin.js";
import { ShortCutPlugin } from "./core/shortcut_plugin.js";
import { SplitPlugin } from "./core/split_plugin.js";
import { StylePlugin } from "./core/style_plugin.js";
import { UserCommandPlugin } from "./core/user_command_plugin.js";
import { AlignPlugin } from "./main/align/align_plugin.js";
import { BannerPlugin } from "./main/banner_plugin.js";
import { ChatGPTTranslatePlugin } from "./main/chatgpt/chatgpt_translate_plugin.js";
import { ColumnPlugin } from "./main/column_plugin.js";
import { EmojiPlugin } from "./main/emoji_plugin.js";
import { FeffPlugin } from "./main/feff_plugin.js";
import { ColorPlugin } from "./main/font/color_plugin.js";
import { ColorUIPlugin } from "./main/font/color_ui_plugin.js";
import { ContrastPlugin } from "./main/font/contrast_plugin.js";
import { FontFamilyPlugin } from "./main/font/font_family_plugin.js";
import { FontPlugin } from "./main/font/font_plugin.js";
import { HintPlugin } from "./main/hint_plugin.js";
import { InlineCodePlugin } from "./main/inline_code.js";
import { LinkPastePlugin } from "./main/link/link_paste_plugin.js";
import { LinkPlugin } from "./main/link/link_plugin.js";
import { OdooLinkSelectionPlugin } from "./main/link/link_selection_odoo_plugin.js";
import { LinkSelectionPlugin } from "./main/link/link_selection_plugin.js";
import { MediaUrlPastePlugin } from "./main/link/powerbox_url_paste_plugin.js";
import { ListPlugin } from "./main/list/list_plugin.js";
import { LocalOverlayPlugin } from "./main/local_overlay_plugin.js";
import { DoubleClickImagePreviewPlugin } from "./main/media/dblclick_image_preview_plugin.js";
import { FilePlugin } from "./main/media/file_plugin.js";
import { IconColorPlugin } from "./main/media/icon_color_plugin.js";
import { IconPlugin } from "./main/media/icon_plugin.js";
import { ImageCropPlugin } from "./main/media/image_crop_plugin.js";
import { ImagePlugin } from "./main/media/image_plugin.js";
import { ImagePostProcessPlugin } from "./main/media/image_post_process_plugin.js";
import { ImageSavePlugin } from "./main/media/image_save_plugin.js";
import { MediaPlugin } from "./main/media/media_plugin.js";
import { VideoPlugin } from "./main/media/video_plugin.js";
import { MoveNodePlugin } from "./main/movenode_plugin.js";
import { PlaceholderPlugin } from "./main/placeholder_plugin.js";
import { PositionPlugin } from "./main/position_plugin.js";
import { PowerButtonsPlugin } from "./main/power_buttons_plugin.js";
import { PowerboxPlugin } from "./main/powerbox/powerbox_plugin.js";
import { SearchPowerboxPlugin } from "./main/powerbox/search_powerbox_plugin.js";
import { SelectionPlaceholderPlugin } from "./main/selection_placeholder_plugin.js";
import { SeparatorPlugin } from "./main/separator_plugin.js";
import { StarPlugin } from "./main/star_plugin.js";
import { TableAlignPlugin } from "./main/table/table_align_plugin.js";
import { TableBorderPlugin } from "./main/table/table_border_plugin.js";
import { TablePlugin } from "./main/table/table_plugin.js";
import { TableResizePlugin } from "./main/table/table_resize_plugin.js";
import { TableUIPlugin } from "./main/table/table_ui_plugin.js";
import { TabulationPlugin } from "./main/tabulation_plugin.js";
import { TextDirectionPlugin } from "./main/text_direction_plugin.js";
import { ToolbarPlugin } from "./main/toolbar/toolbar_plugin.js";
import { YoutubePlugin } from "./main/youtube_plugin.js";
import { CollaborationOdooPlugin } from "./others/collaboration/collaboration_odoo_plugin.js";
import { CollaborationPlugin } from "./others/collaboration/collaboration_plugin.js";
import { CollaborationSelectionAvatarPlugin } from "./others/collaboration/collaboration_selection_avatar_plugin.js";
import { CollaborationSelectionPlugin } from "./others/collaboration/collaboration_selection_plugin.js";
import { EmbeddedComponentPlugin } from "./others/embedded_component_plugin.js";
import { EmbeddedYoutubePlugin } from "./others/embedded_components/plugins/video_plugin/embedded_youtube_plugin.js";
import { QWebPlugin } from "./others/qweb_plugin.js";

export const CORE_PLUGINS = [
    BaseContainerPlugin,
    ClipboardPlugin,
    CommentPlugin,
    DeletePlugin,
    DialogPlugin,
    DomPlugin,
    FormatPlugin,
    HistoryPlugin,
    InputPlugin,
    LineBreakPlugin,
    NoInlineRootPlugin,
    OverlayPlugin,
    ProtectedNodePlugin,
    SanitizePlugin,
    SelectionPlugin,
    SplitPlugin,
    UserCommandPlugin,
    StylePlugin,
    ContentEditablePlugin,
];

export const MAIN_PLUGINS = [
    ...CORE_PLUGINS,
    BannerPlugin,
    ChatGPTTranslatePlugin,
    ColorPlugin,
    ColorUIPlugin,
    ContrastPlugin,
    SeparatorPlugin,
    ColumnPlugin,
    EmojiPlugin,
    HintPlugin,
    AlignPlugin,
    ListPlugin,
    MediaPlugin,
    ImageSavePlugin,
    ShortCutPlugin,
    PowerboxPlugin,
    SearchPowerboxPlugin,
    MediaUrlPastePlugin,
    StarPlugin,
    TablePlugin,
    TableAlignPlugin,
    TableBorderPlugin,
    TableUIPlugin,
    TabulationPlugin,
    ToolbarPlugin,
    FontPlugin,
    FontFamilyPlugin,
    IconPlugin,
    IconColorPlugin,
    ImagePlugin,
    ImagePostProcessPlugin,
    ImageCropPlugin,
    DoubleClickImagePreviewPlugin,
    LinkPlugin,
    LinkPastePlugin,
    FeffPlugin,
    LinkSelectionPlugin,
    OdooLinkSelectionPlugin,
    PowerButtonsPlugin,
    MoveNodePlugin,
    LocalOverlayPlugin,
    PositionPlugin,
    TextDirectionPlugin,
    InlineCodePlugin,
    TableResizePlugin,
    FilePlugin,
    PlaceholderPlugin,
    SelectionPlaceholderPlugin,
];

export const COLLABORATION_PLUGINS = [
    CollaborationPlugin,
    CollaborationOdooPlugin,
    CollaborationSelectionPlugin,
    CollaborationSelectionAvatarPlugin,
];

export const EMBEDDED_COMPONENT_PLUGINS = [
    EmbeddedComponentPlugin,
    DatePlugin,
    TableOfContentPlugin,
    ToggleBlockPlugin,
    EmbeddedVideoPlugin,
    EmbeddedYoutubePlugin,
    CaptionPlugin,
    SyntaxHighlightingPlugin,
];

export const NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS = [VideoPlugin, YoutubePlugin];

export const EXTRA_PLUGINS = [
    ...COLLABORATION_PLUGINS,
    ...MAIN_PLUGINS,
    ...EMBEDDED_COMPONENT_PLUGINS,
    EditorVersionPlugin,
    QWebPlugin,
];
