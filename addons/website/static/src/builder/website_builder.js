import { Builder } from "@html_builder/builder";
import { BuilderOptionsPlugin } from "@html_builder/core/builder_options_plugin_translate";
import { CORE_PLUGINS as CORE_BUILDER_PLUGINS } from "@html_builder/core/core_plugins";
import { DisableSnippetsPlugin } from "@html_builder/core/disable_snippets_plugin_translation";
import { OperationPlugin } from "@html_builder/core/operation_plugin";
import { SavePlugin } from "@html_builder/core/save_plugin";
import { SetupEditorPlugin } from "@html_builder/core/setup_editor_plugin";
import { OverlayButtonsPlugin } from "@html_builder/core/overlay_buttons/overlay_buttons_plugin";
import { BuilderActionsPlugin } from "@html_builder/core/builder_actions_plugin";
import { BuilderComponentPlugin } from "@html_builder/core/builder_component_plugin";
import { DropZonePlugin } from "@html_builder/core/drop_zone_plugin";
import { DropZoneSelectorPlugin } from "@html_builder/core/dropzone_selector_plugin";
import { CustomizeTabPlugin } from "@html_builder/core/customize_tab_plugin";
import { VersionControlPlugin } from "@html_builder/core/version_control_plugin";
import { CoreBuilderActionPlugin } from "@html_builder/core/core_builder_action_plugin";
import { BuilderOverlayPlugin } from "@html_builder/core/builder_overlay/builder_overlay_plugin";
import { VisibilityPlugin } from "@html_builder/core/visibility_plugin";
import { removePlugins } from "@html_builder/utils/utils";
import { MAIN_PLUGINS as MAIN_EDITOR_PLUGINS } from "@html_editor/plugin_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { HighlightPlugin } from "./plugins/highlight/highlight_plugin";
import { PopupVisibilityPlugin } from "./plugins/popup_visibility_plugin";
import { SaveTranslationPlugin } from "./plugins/save_translation_plugin";
import { TranslationPlugin } from "./plugins/translation_plugin";
import { WebsiteVisibilityPlugin } from "./plugins/website_visibility_plugin";
import { EditInteractionPlugin } from "./plugins/edit_interaction_plugin";
import { CustomizeTranslationTabPlugin } from "./translation_components/customize_translation_tab_plugin";

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
    OperationPlugin,
    EditInteractionPlugin,
    CustomizeTranslationTabPlugin,
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
        const mainEditorPluginsToRemove = [
            "PowerButtonsPlugin",
            "DoubleClickImagePreviewPlugin",
            "SeparatorPlugin",
            "StarPlugin",
            "BannerPlugin",
            "MoveNodePlugin",
        ];
        const pluginsBlockedInTranslationMode = [
            "PowerboxPlugin",
            "SearchPowerboxPlugin",
            "YoutubePlugin",
            "ImagePlugin",
            "AlignPlugin",
            "ListPlugin",
            "FontPlugin",
            "FontFamilyPlugin",
        ];
        const pluginsToRemove = this.props.translation
            ? [...mainEditorPluginsToRemove, ...pluginsBlockedInTranslationMode]
            : mainEditorPluginsToRemove;
        const mainEditorPlugins = removePlugins([...MAIN_EDITOR_PLUGINS], pluginsToRemove);
        const coreBuilderPlugins = this.props.translation
            ? [
                  BuilderActionsPlugin,
                  BuilderComponentPlugin,
                  BuilderOverlayPlugin,
                  OverlayButtonsPlugin,
                  DropZonePlugin,
                  DropZoneSelectorPlugin,
                  CoreBuilderActionPlugin,
                  CustomizeTabPlugin,
                  VersionControlPlugin,
              ]
            : CORE_BUILDER_PLUGINS;
        const Plugins = [...mainEditorPlugins, ...coreBuilderPlugins, ...(websitePlugins || [])];
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
