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
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
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
import { TranslateTableOfContentOptionPlugin } from "./plugins/options/table_of_content_option_plugin_translate";
import { BuilderContentEditablePlugin } from "@html_builder/core/builder_content_editable_plugin";
import { ImageFieldPlugin } from "@html_builder/plugins/image_field_plugin";
import { MonetaryFieldPlugin } from "@html_builder/plugins/monetary_field_plugin";
import { Many2OneOptionPlugin } from "@html_builder/plugins/many2one_option_plugin";

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
    TranslateTableOfContentOptionPlugin,
    BuilderContentEditablePlugin,
    CarouselOptionTranslationPlugin,
    ImageFieldPlugin,
    MonetaryFieldPlugin,
    Many2OneOptionPlugin,
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
        this.dialog = useService("dialog");
        useSetupAction({
            beforeUnload: (ev) => this.onBeforeUnload(ev),
            beforeLeave: () => this.onBeforeLeave(),
        });
    }

    discard() {
        if (this.editor.shared.history.canUndo()) {
            this.dialog.add(ConfirmationDialog, {
                body: _t(
                    "If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."
                ),
                confirm: () => this.props.builderProps.closeEditor(),
                cancel: () => {},
            });
        } else {
            this.props.builderProps.closeEditor();
        }
    }

    onBeforeUnload(event) {
        if (!this.editor) {
            return;
        }
        if (!this.isSaving && this.editor.shared.history.canUndo()) {
            event.preventDefault();
            event.returnValue = "Unsaved changes";
        }
    }

    async onBeforeLeave() {
        if (!this.editor) {
            return true;
        }
        if (this.editor.shared.history.canUndo()) {
            let continueProcess = true;
            await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    body: _t("If you proceed, your changes will be lost"),
                    confirmLabel: _t("Continue"),
                    confirm: () => resolve(),
                    cancel: () => {
                        continueProcess = false;
                        resolve();
                    },
                });
            });
            return continueProcess;
        }
        return true;
    }

    async save() {
        this.editor.shared.operation.next(this._save.bind(this), { withLoadingEffect: false });
    }

    async _save() {
        this.isSaving = true;
        // TODO: handle the urgent save and the fail of the save operation
        await this.editor.shared.savePlugin.save({ alwaysSkipAfterSaveHandlers: false });
        this.props.builderProps.closeEditor();
        this.isSaving = false;
    }

    get builderProps() {
        const builderProps = Object.assign({}, this.props.builderProps);
        const websitePlugins = this.props.translation
            ? TRANSLATION_PLUGINS
            : [
                  ...registry.category("builder-plugins").getAll(),
                  ...registry.category("website-plugins").getAll(),
              ];
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
        const installSnippetModule = builderProps.installSnippetModule;
        builderProps.installSnippetModule = (snippet) =>
            installSnippetModule(snippet, this.save.bind(this));
        return builderProps;
    }
}

registry.category("lazy_components").add("website.WebsiteBuilder", WebsiteBuilder);
