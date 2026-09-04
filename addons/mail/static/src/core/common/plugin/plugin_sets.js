import { ColorPlugin } from "@html_editor/main/font/color_plugin";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { EmbeddedComponentPlugin } from "@html_editor/others/embedded_component_plugin";
import { EmojiPlugin } from "@html_editor/main/emoji_plugin";
import { FeffPlugin } from "@html_editor/main/feff_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { InlineCodePlugin } from "@html_editor/main/inline_code";
import { LinkPastePlugin } from "@html_editor/main/link/link_paste_plugin";
import { LinkPlugin } from "@html_editor/main/link/link_plugin";
import { ProtectedNodePlugin } from "@html_editor/core/protected_node_plugin";
import { SelectionPlaceholderPlugin } from "@html_editor/main/selection_placeholder_plugin";
import { LinkSelectionPlugin } from "@html_editor/main/link/link_selection_plugin";
import { OdooLinkSelectionPlugin } from "@html_editor/main/link/link_selection_odoo_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";
import { SyntaxHighlightingPlugin } from "@html_editor/others/embedded_components/plugins/syntax_highlighting_plugin/syntax_highlighting_plugin";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { TranslatePlugin } from "@html_editor/main/translate/translate_plugin";

import { DisableImplicitFormatShortcutsPlugin } from "@mail/core/common/plugin/disable_implicit_format_shortcuts_plugin";
import { MailCodeBlockPlugin } from "@mail/core/common/plugin/mail_code_block_plugin";
import { MailComposerPlugin } from "@mail/core/common/plugin/mail_composer_plugin";
import { MentionPlugin } from "@mail/core/common/plugin/mention_plugin";
import { ClipboardPlugin } from "@html_editor/core/clipboard_plugin";
import { BaseContainerPlugin } from "@html_editor/core/base_container_plugin";
import { DeletePlugin } from "@html_editor/core/delete_plugin";
import { DomPlugin } from "@html_editor/core/dom_plugin";
import { HistoryPlugin } from "@html_editor/core/history_plugin";
import { DomReferenceMapPlugin } from "@html_editor/core/dom_reference_map_plugin";
import { DomObserverPlugin } from "@html_editor/core/dom_observer_plugin";
import { InputPlugin } from "@html_editor/core/input_plugin";
import { LineBreakPlugin } from "@html_editor/core/line_break_plugin";
import { OverlayPlugin } from "@html_editor/core/overlay_plugin";
import { SanitizePlugin } from "@html_editor/core/sanitize_plugin";
import { SelectionPlugin } from "@html_editor/core/selection_plugin";
import { SplitPlugin } from "@html_editor/core/split_plugin";
import { UserCommandPlugin } from "@html_editor/core/user_command_plugin";

export const MAIL_TEXT_PLUGINS = [
    BaseContainerPlugin,
    ClipboardPlugin,
    DeletePlugin,
    DisableImplicitFormatShortcutsPlugin,
    DomObserverPlugin,
    DomReferenceMapPlugin,
    DomPlugin,
    EmojiPlugin,
    FeffPlugin,
    HintPlugin,
    HistoryPlugin,
    InputPlugin,
    LineBreakPlugin,
    MailComposerPlugin,
    MentionPlugin,
    OverlayPlugin,
    SanitizePlugin,
    SelectionPlugin,
    SplitPlugin,
    UserCommandPlugin,
];

export const MAIL_CORE_PLUGINS = [
    ...CORE_PLUGINS,
    ColorPlugin,
    EmojiPlugin,
    FeffPlugin,
    HintPlugin,
    InlineCodePlugin,
    LinkPastePlugin,
    LinkPlugin,
    LinkSelectionPlugin,
    MailComposerPlugin,
    MentionPlugin,
    OdooLinkSelectionPlugin,
    ProtectedNodePlugin,
    SelectionPlaceholderPlugin,
    ShortCutPlugin,
    TabulationPlugin,
    TranslatePlugin,
];

export const MAIL_HTML_PLUGINS = [
    ...MAIL_CORE_PLUGINS,
    EmbeddedComponentPlugin,
    MailCodeBlockPlugin,
    SyntaxHighlightingPlugin,
    ToolbarPlugin,
];
export const MAIL_HTML_PLUGINS_SMALL_UI = MAIL_CORE_PLUGINS;
