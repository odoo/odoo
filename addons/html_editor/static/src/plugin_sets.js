import { ClipboardPlugin } from "./core/clipboard_plugin";
import { CommentPlugin } from "./core/comment_plugin";
import { DeletePlugin } from "./core/delete_plugin";
import { DialogPlugin } from "./core/dialog_plugin";
import { DomPlugin } from "./core/dom_plugin";
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
import { AlignPlugin } from "./main/align_plugin";
import { BannerPlugin } from "./main/banner_plugin";
import { ChatGPTPlugin } from "./main/chatgpt/chatgpt_plugin";
import { ColumnPlugin } from "./main/column_plugin";
import { EmojiPlugin } from "./main/emoji_plugin";
import { ColorPlugin } from "./main/font/color_plugin";
import { FontPlugin } from "./main/font/font_plugin";
import { HintPlugin } from "./main/hint_plugin";
import { InlineCodePlugin } from "./main/inline_code";
import { LinkPastePlugin } from "./main/link/link_paste_plugin";
import { LinkPlugin } from "./main/link/link_plugin";
import { OdooLinkSelectionPlugin } from "./main/link/link_selection_odoo_plugin";
import { LinkSelectionPlugin } from "./main/link/link_selection_plugin";
import { ListPlugin } from "./main/list/list_plugin";
import { LocalOverlayPlugin } from "./main/local_overlay_plugin";
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
import { TablePlugin } from "./main/table/table_plugin";
import { TableResizePlugin } from "./main/table/table_resize_plugin";
import { TableUIPlugin } from "./main/table/table_ui_plugin";
import { TabulationPlugin } from "./main/tabulation_plugin";
import { TextDirectionPlugin } from "./main/text_direction_plugin";
import { ToolbarPlugin } from "./main/toolbar/toolbar_plugin";
import { YoutubePlugin } from "./main/youtube_plugin";
import { CollaborationOdooPlugin } from "./others/collaboration/collaboration_odoo_plugin";
import { CollaborationPlugin } from "./others/collaboration/collaboration_plugin";
import { CollaborationSelectionAvatarPlugin } from "./others/collaboration/collaboration_selection_avatar_plugin";
import { CollaborationSelectionPlugin } from "./others/collaboration/collaboration_selection_plugin";
import { DynamicPlaceholderPlugin } from "./others/dynamic_placeholder_plugin";
import { EmbeddedComponentPlugin } from "./others/embedded_component_plugin";
import { ExcalidrawPlugin } from "@html_editor/others/embedded_components/plugins/excalidraw_plugin/excalidraw_plugin";
import { FilePlugin } from "@html_editor/others/embedded_components/plugins/file_plugin/file_plugin";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { VideoPlugin } from "@html_editor/others/embedded_components/plugins/video_plugin/video_plugin";
import { QWebPlugin } from "./others/qweb_plugin";

/**
 * @typedef { Object } SharedMethods
 *
 * Core
 * @property { import("./core/clipboard_plugin").ClipboardShared } clipboard
 * @property { import("./core/delete_plugin").DeleteShared } delete
 * @property { import("./core/dialog_plugin").DialogShared } dialog
 * @property { import("./core/dom_plugin").DomShared } dom
 * @property { import("./core/format_plugin").FormatShared } format
 * @property { import("./core/history_plugin").HistoryShared } history
 * @property { import("./core/line_break_plugin").LineBreakShared } lineBreak
 * @property { import("./core/overlay_plugin").OverlayShared } overlay
 * @property { import("./core/protected_node_plugin").ProtectedNodeShared } protectedNode
 * @property { import("./core/sanitize_plugin").SanitizeShared } sanitize
 * @property { import("./core/selection_plugin").SelectionShared } selection
 * @property { import("./core/split_plugin").SplitShared } split
 * @property { import("./core/user_command_plugin").UserCommandShared } userCommand
 *
 * Main
 * @property { import("./main/font/color_plugin").ColorShared } color
 * @property { import("./main/link/link_plugin").LinkShared } link
 * @property { import ("./main/link/link_selection_plugin").LinkSelectionShared } linkSelection
 * @property { import ("./main/media/media_plugin").MediaShared } media
 * @property { import("./main/powerbox/powerbox_plugin").PowerboxShared } powerbox
 * @property { import ("./main/table/table_plugin").TableShared } table
 * @property { import ("./main/toolbar/toolbar_plugin").ToolbarShared } toolbar
 * @property { import ("./main/emoji_plugin").EmojiShared } emoji
 * @property { import ("./main/local_overlay_plugin").LocalOverlayShared } localOverlay
 * @property { import ("./main/tabulation_plugin").TabulationShared } tabulation
 *
 * Others
 * @property { import("./others/collaboration/collaboration_odoo_plugin").CollaborationOdooShared } collaborationOdoo
 * @property { import("./others/collaboration/collaboration_plugin").CollaborationShared } collaboration
 * @property { import("./others/dynamic_placeholder_plugin").DynamicPlaceholderShared } dynamicPlaceholder
 */

export const CORE_PLUGINS = [
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
];

export const MAIN_PLUGINS = [
    ...CORE_PLUGINS,
    BannerPlugin,
    ChatGPTPlugin,
    ColorPlugin,
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
    TableUIPlugin,
    TabulationPlugin,
    ToolbarPlugin,
    FontPlugin, // note: if before ListPlugin, there are a few split tests that fails
    YoutubePlugin,
    IconPlugin,
    ImagePlugin,
    ImageCropPlugin,
    LinkPlugin,
    LinkPastePlugin,
    LinkSelectionPlugin,
    OdooLinkSelectionPlugin,
    PowerButtonsPlugin,
    MoveNodePlugin,
    LocalOverlayPlugin,
    PositionPlugin,
    TextDirectionPlugin,
    InlineCodePlugin,
    TableResizePlugin,
];

export const COLLABORATION_PLUGINS = [
    CollaborationPlugin,
    CollaborationOdooPlugin,
    CollaborationSelectionPlugin,
    CollaborationSelectionAvatarPlugin,
];

export const EMBEDDED_COMPONENT_PLUGINS = [
    EmbeddedComponentPlugin,
    ExcalidrawPlugin,
    FilePlugin,
    TableOfContentPlugin,
    VideoPlugin,
];

export const DYNAMIC_PLACEHOLDER_PLUGINS = [DynamicPlaceholderPlugin, QWebPlugin];

export const EXTRA_PLUGINS = [
    ...COLLABORATION_PLUGINS,
    ...MAIN_PLUGINS,
    ...EMBEDDED_COMPONENT_PLUGINS,
    QWebPlugin,
];
