import { BaseContainerPlugin } from "./core/base_container_plugin";
import { ClipboardPlugin } from "./core/clipboard_plugin";
import { CommentPlugin } from "./core/comment_plugin";
import { DeletePlugin } from "./core/delete_plugin";
import { DialogPlugin } from "./core/dialog_plugin";
import { DomPlugin } from "./core/dom_plugin";
import { SeparatorPlugin } from "./main/separator_plugin";
import { FormatPlugin } from "./core/format_plugin";
import { HistoryPlugin } from "./core/history_plugin";
import { InputPlugin } from "./core/input_plugin";
import { LineBreakPlugin } from "./core/line_break_plugin";
import { NoInlineRootPlugin } from "./core/no_inline_root_plugin";
import { OverlayPlugin } from "./core/overlay_plugin";
import { ProtectedNodePlugin } from "./core/protected_node_plugin";
import { SanitizePlugin } from "./core/sanitize_plugin";
import { SelectionPlugin } from "./core/selection_plugin";
import { ShortCutPlugin } from "./core/shortcut_plugin";
import { SplitPlugin } from "./core/split_plugin";
import { UserCommandPlugin } from "./core/user_command_plugin";
import { AlignPlugin } from "./main/align/align_plugin";
import { BannerPlugin } from "./main/banner_plugin";
import { ChatGPTTranslatePlugin } from "./main/chatgpt/chatgpt_translate_plugin";
import { ColumnPlugin } from "./main/column_plugin";
import { EmojiPlugin } from "./main/emoji_plugin";
import { ColorPlugin } from "./main/font/color_plugin";
import { FeffPlugin } from "./main/feff_plugin";
import { FontPlugin } from "./main/font/font_plugin";
import { FontFamilyPlugin } from "./main/font/font_family_plugin";
import { HintPlugin } from "./main/hint_plugin";
import { InlineCodePlugin } from "./main/inline_code";
import { LinkPastePlugin } from "./main/link/link_paste_plugin";
import { LinkPlugin } from "./main/link/link_plugin";
import { OdooLinkSelectionPlugin } from "./main/link/link_selection_odoo_plugin";
import { LinkSelectionPlugin } from "./main/link/link_selection_plugin";
import { ListPlugin } from "./main/list/list_plugin";
import { LocalOverlayPlugin } from "./main/local_overlay_plugin";
import { FilePlugin } from "./main/media/file_plugin";
import { IconPlugin } from "./main/media/icon_plugin";
import { ImageCropPlugin } from "./main/media/image_crop_plugin";
import { ImagePlugin } from "./main/media/image_plugin";
import { MediaPlugin } from "./main/media/media_plugin";
import { MoveNodePlugin } from "./main/movenode_plugin";
import { PowerButtonsPlugin } from "./main/power_buttons_plugin";
import { PositionPlugin } from "./main/position_plugin";
import { PowerboxPlugin } from "./main/powerbox/powerbox_plugin";
import { SearchPowerboxPlugin } from "./main/powerbox/search_powerbox_plugin";
import { SignaturePlugin } from "./main/signature_plugin";
import { StarPlugin } from "./main/star_plugin";
import { TableAlignPlugin } from "./main/table/table_align_plugin";
import { TablePlugin } from "./main/table/table_plugin";
import { TableResizePlugin } from "./main/table/table_resize_plugin";
import { TableUIPlugin } from "./main/table/table_ui_plugin";
import { TabulationPlugin } from "./main/tabulation_plugin";
import { TextDirectionPlugin } from "./main/text_direction_plugin";
import { ToolbarPlugin } from "./main/toolbar/toolbar_plugin";
import { YoutubePlugin } from "./main/youtube_plugin";
import { PlaceholderPlugin } from "./main/placeholder_plugin";
import { CollaborationOdooPlugin } from "./others/collaboration/collaboration_odoo_plugin";
import { CollaborationPlugin } from "./others/collaboration/collaboration_plugin";
import { CollaborationSelectionAvatarPlugin } from "./others/collaboration/collaboration_selection_avatar_plugin";
import { CollaborationSelectionPlugin } from "./others/collaboration/collaboration_selection_plugin";
import { EmbeddedComponentPlugin } from "./others/embedded_component_plugin";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { ToggleBlockPlugin } from "@html_editor/others/embedded_components/plugins/toggle_block_plugin/toggle_block_plugin";
import { VideoPlugin } from "@html_editor/others/embedded_components/plugins/video_plugin/video_plugin";
import { CaptionPlugin } from "@html_editor/others/embedded_components/plugins/caption_plugin/caption_plugin";
import { QWebPlugin } from "./others/qweb_plugin";
import { EditorVersionPlugin } from "./core/editor_version_plugin";
import { ImagePostProcessPlugin } from "./main/media/image_post_process_plugin";
import { DoubleClickImagePreviewPlugin } from "./main/media/dblclick_image_preview_plugin";
import { StylePlugin } from "./core/style_plugin";
import { ContentEditablePlugin } from "./core/content_editable_plugin";

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
    SeparatorPlugin,
    ColumnPlugin,
    EmojiPlugin,
    HintPlugin,
    AlignPlugin,
    ListPlugin,
    MediaPlugin,
    ShortCutPlugin,
    PowerboxPlugin,
    SearchPowerboxPlugin,
    SignaturePlugin,
    StarPlugin,
    TablePlugin,
    TableAlignPlugin,
    TableUIPlugin,
    TabulationPlugin,
    ToolbarPlugin,
    FontPlugin, // note: if before ListPlugin, there are a few split tests that fails
    FontFamilyPlugin,
    YoutubePlugin,
    IconPlugin,
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
];

export const COLLABORATION_PLUGINS = [
    CollaborationPlugin,
    CollaborationOdooPlugin,
    CollaborationSelectionPlugin,
    CollaborationSelectionAvatarPlugin,
];

export const EMBEDDED_COMPONENT_PLUGINS = [
    EmbeddedComponentPlugin,
    TableOfContentPlugin,
    ToggleBlockPlugin,
    VideoPlugin,
    CaptionPlugin,
];

export const EXTRA_PLUGINS = [
    ...COLLABORATION_PLUGINS,
    ...MAIN_PLUGINS,
    ...EMBEDDED_COMPONENT_PLUGINS,
    EditorVersionPlugin,
    QWebPlugin,
];
