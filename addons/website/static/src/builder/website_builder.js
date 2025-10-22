import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS, MAIN_PLUGINS } from "@html_builder/core/core_plugins";
import { removePlugins } from "@html_builder/utils/utils";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { ThemeTab } from "./plugins/theme/theme_tab";
import { Plugin } from "@html_editor/plugin";
import { websiteSnippetModelPatch } from "./snippet_model";

// Other Plugins depend on those 2 plugins, but they are not used in translation
// mode.
// Todo: find a better way to handle that.
class FakeClonePlugin extends Plugin {
    static id = "clone";
}
class FakeRemovePlugin extends Plugin {
    static id = "remove";
}

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
        this.snippetsService = useService("html_builder.snippets");
        this.snippetsService.patchSnippetModel(
            this.props.builderProps.snippetsName,
            websiteSnippetModelPatch
        );
        useSetupAction({
            beforeUnload: (ev) => this.onBeforeUnload(ev),
            beforeLeave: () => this.onBeforeLeave(),
        });
    }

    discard() {
        if (this.editor.shared.history.canUndo()) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Discard all changes?"),
                body: _t(
                    "Are you sure you want to discard all your changes? Once you do, they're gone for good."
                ),
                confirmLabel: _t("Discard changes"),
                cancelLabel: _t("Keep editing"),
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
        if (this.editor.shared.history.canUndo()) {
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
        // TODO: handle the urgent save and the fail of the save operation
        await this.editor.shared.operation.next(
            async () => {
                await this.editor.shared.savePlugin.save();
                this.props.builderProps.closeEditor();
            },
            { withLoadingEffect: false }
        );
    }

    get builderProps() {
        const builderProps = Object.assign({}, this.props.builderProps);
        const websitePlugins = this.props.translation
            ? [
                  FakeClonePlugin,
                  FakeRemovePlugin,
                  ...registry.category("translation-plugins").getAll(),
              ]
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
            "MediaUrlPastePlugin",
            "YoutubePlugin",
            "ImagePlugin",
            "AlignPlugin",
            "ListPlugin",
            "FontPlugin",
            "FontFamilyPlugin",
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
