import { Builder } from "@html_builder/builder";
import { BuilderOptionsPlugin } from "@html_builder/core/builder_options_plugin_translate";
import { CORE_PLUGINS as CORE_BUILDER_PLUGINS } from "@html_builder/core/core_plugins";
import { DisableSnippetsPlugin } from "@html_builder/core/disable_snippets_plugin_translation";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { VisibilityPlugin } from "@html_builder/core/visibility_plugin";
import { removePlugins } from "@html_builder/utils/utils";
import { MAIN_PLUGINS as MAIN_EDITOR_PLUGINS } from "@html_editor/plugin_sets";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { HighlightPlugin } from "./plugins/highlight/highlight_plugin";
import { PopupVisibilityPlugin } from "./plugins/popup_visibility_plugin";
import { SaveTranslationPlugin } from "./plugins/save_translation_plugin";
import { TranslationPlugin } from "./plugins/translation_plugin";
import { WebsiteVisibilityPlugin } from "./plugins/website_visibility_plugin";

const TRANSLATION_PLUGINS = [
    BuilderOptionsPlugin,
    DisableSnippetsPlugin,
    SavePlugin,
    SetupEditorPlugin,
    VisibilityPlugin,
    PopupVisibilityPlugin,
    SaveTranslationPlugin,
    TranslationPlugin,
    WebsiteVisibilityPlugin,
    HighlightPlugin,
];

export class WebsiteBuilder extends Component {
    static template = "website.WebsiteBuilder";
    static components = { Builder };
    static props = {
        translation: { type: Boolean },
        builderProps: { type: Object },
    };

    get builderProps() {
        const builderProps = Object.assign({}, this.props.builderProps);
        const websitePlugins = this.props.translation
            ? TRANSLATION_PLUGINS
            : registry.category("website-plugins").getAll();
        const mainEditorPlugins = removePlugins(
            [...MAIN_EDITOR_PLUGINS],
            [
                "PowerButtonsPlugin",
                "DoubleClickImagePreviewPlugin",
                "SeparatorPlugin",
                "StarPlugin",
                "BannerPlugin",
                "MoveNodePlugin",
            ]
        );
        const coreBuilderPlugins = this.props.translation ? [] : CORE_BUILDER_PLUGINS;
        const Plugins = [...mainEditorPlugins, ...coreBuilderPlugins, ...(websitePlugins || [])];
        builderProps.Plugins = Plugins;
        return builderProps;
    }
}

registry.category("lazy_components").add("website.WebsiteBuilder", WebsiteBuilder);
