import { Builder } from "@html_builder/builder";
import { BuilderOptionsTranslationPlugin } from "@html_builder/core/builder_options_plugin_translate";
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
import { useService } from "@web/core/utils/hooks";
import { HighlightPlugin } from "./plugins/highlight/highlight_plugin";
import { PopupVisibilityPlugin } from "./plugins/popup_visibility_plugin";
import { SaveTranslationPlugin } from "./plugins/save_translation_plugin";
import { TranslateLinkInlinePlugin } from "./plugins/translate_link_inline_plugin";
import { TranslationPlugin } from "./plugins/translation_plugin";
import { WebsiteVisibilityPlugin } from "./plugins/website_visibility_plugin";
import { EditInteractionPlugin } from "./plugins/edit_interaction_plugin";
import { AnimateOptionPlugin } from "./plugins/options/animate_option_plugin";
import { BuilderComponentPlugin } from "@html_builder/core/builder_component_plugin";
import { BuilderActionsPlugin } from "@html_builder/core/builder_actions_plugin";
import { CoreBuilderActionPlugin } from "@html_builder/core/core_builder_action_plugin";
import { CarouselOptionTranslationPlugin } from "./plugins/carousel_option_translation_plugin";
import { ThemeTab } from "./plugins/theme/theme_tab";
import { BuilderContentEditablePlugin } from "@html_builder/core/builder_content_editable_plugin";
import { ImageFieldPlugin } from "@html_builder/plugins/image_field_plugin";
import { MonetaryFieldPlugin } from "@html_builder/plugins/monetary_field_plugin";

const TRANSLATION_PLUGINS = [
    BuilderOptionsTranslationPlugin,
    BuilderActionsPlugin,
    BuilderComponentPlugin,
    CoreBuilderActionPlugin,
    DisableSnippetsPlugin,
    SavePlugin,
    SetupEditorPlugin,
    VisibilityPlugin,
    PopupVisibilityPlugin,
    SaveTranslationPlugin,
    TranslateLinkInlinePlugin,
    TranslationPlugin,
    WebsiteVisibilityPlugin,
    AnimateOptionPlugin,
    HighlightPlugin,
    OperationPlugin,
    EditInteractionPlugin,
    CarouselOptionTranslationPlugin,
    BuilderContentEditablePlugin,
    ImageFieldPlugin,
    MonetaryFieldPlugin,
];

export class WebsiteBuilder extends Component {
    static template = "website.WebsiteBuilder";
    static components = { Builder };
    static props = {
        translation: { type: Boolean },
        builderProps: { type: Object },
    };

    setup() {
        this.websiteService = useService("website");
    }

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
        builderProps.getThemeTab = () => this.websiteService.isDesigner && ThemeTab;
        return builderProps;
    }
}

registry.category("lazy_components").add("website.WebsiteBuilder", WebsiteBuilder);
