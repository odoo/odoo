import { Builder } from "@html_builder/builder";
import { BuilderOptionsPlugin } from "@html_builder/core/builder_options_plugin_translate";
import { CORE_PLUGINS, MAIN_PLUGINS } from "@html_builder/core/core_plugins";
import { DisableSnippetsPlugin } from "@html_builder/core/disable_snippets_plugin_translation";
import { OperationPlugin } from "@html_builder/core/operation_plugin";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { VisibilityPlugin } from "@html_builder/core/visibility_plugin";
import { removePlugins } from "@html_builder/utils/utils";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { HighlightPlugin } from "./plugins/highlight/highlight_plugin";
import { PopupVisibilityPlugin } from "./plugins/popup_visibility_plugin";
import { SaveTranslationPlugin } from "./plugins/save_translation_plugin";
import { TranslationPlugin } from "./plugins/translation_plugin";
import { WebsiteVisibilityPlugin } from "./plugins/website_visibility_plugin";
import { EditInteractionPlugin } from "./plugins/edit_interaction_plugin";
import { AnimateOptionPlugin } from "./plugins/options/animate_option_plugin";
import { BuilderComponentPlugin } from "@html_builder/core/builder_component_plugin";
import { BuilderActionsPlugin } from "@html_builder/core/builder_actions_plugin";
import { CoreBuilderActionPlugin } from "@html_builder/core/core_builder_action_plugin";

const TRANSLATION_PLUGINS = [
    BuilderOptionsPlugin,
    BuilderActionsPlugin,
    BuilderComponentPlugin,
    CoreBuilderActionPlugin,
    DisableSnippetsPlugin,
    SavePlugin,
    SetupEditorPlugin,
    VisibilityPlugin,
    PopupVisibilityPlugin,
    SaveTranslationPlugin,
    TranslationPlugin,
    WebsiteVisibilityPlugin,
    AnimateOptionPlugin,
    HighlightPlugin,
    OperationPlugin,
    EditInteractionPlugin,
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
        const builderPluginsToRemove = [
            // Currently empty.
        ];
        const pluginsBlockedInTranslationMode = [
            "PowerboxPlugin",
            "SearchPowerboxPlugin",
            "YoutubePlugin",
            "ImagePlugin",
        ];
        const pluginsToRemove = this.props.translation
            ? [...builderPluginsToRemove, ...pluginsBlockedInTranslationMode]
            : builderPluginsToRemove;
        const coreBuilderPlugins = removePlugins(
            this.props.translation ? MAIN_PLUGINS : CORE_PLUGINS,
            pluginsToRemove
        );
        const Plugins = [...coreBuilderPlugins, ...(websitePlugins || [])];
        builderProps.Plugins = Plugins;
        builderProps.onEditorLoad = (editor) => {
            this.editor = editor;
        };
        builderProps.config.getRecordInfo = (editableEl) => {
            if (this.editor && !editableEl) {
                editableEl = closestElement(
                    this.editor.shared.selection.getEditableSelection().anchorNode,
                    "[data-oe-model]"
                );
            }
            if (!editableEl) {
                return {};
            }
            return {
                resModel: editableEl.dataset["oeModel"],
                resId: editableEl.dataset["oeId"],
                field: editableEl.dataset["oeField"],
                type: editableEl.dataset["oeType"],
            };
        };
        return builderProps;
    }
}

registry.category("lazy_components").add("website.WebsiteBuilder", WebsiteBuilder);
