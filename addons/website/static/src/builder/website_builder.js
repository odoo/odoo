import { Builder } from "@html_builder/builder";
import { CORE_PLUGINS, MAIN_PLUGINS } from "@html_builder/core/core_plugins";
import { removePlugins } from "@html_builder/utils/utils";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Component, onMounted, onWillStart } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSetupAction } from "@web/search/action_hook";
import { ThemeTab } from "./plugins/theme/theme_tab";
import { Plugin } from "@html_editor/plugin";
import { revertPreview } from "@html_builder/core/utils";
import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";
import {
    localStorageNoDialogKey,
    TranslatorInfoDialog,
} from "./translation_components/translatorInfoDialog";

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
        useSetupAction({
            beforeUnload: (ev) => this.onBeforeUnload(ev),
            beforeLeave: () => this.onBeforeLeave(),
        });
        onWillStart(async () => {
            this.translatedElements = this.props.translation
                ? await rpc("/website/get_translated_elements")
                : [];
        });
        onMounted(() => {
            if (this.props.translation && !browser.localStorage.getItem(localStorageNoDialogKey)) {
                this.dialog.add(TranslatorInfoDialog);
            }
        });
    }

    async discard() {
        await revertPreview(this.editor);
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
        this.reloadAfterTimeout();
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

    reloadAfterTimeout() {
        if (this.editor.shared.operation.hasTimedOut()) {
            const currentUrl = new URL(window.location.href);
            // A timed-out operation might still be running; reload the page to avoid side effects
            redirect(`/@${currentUrl.pathname}`);
        }
    }

    async save() {
        if (this.editor.shared.operation.hasTimedOut()) {
            const shouldContinue = await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Corrupted content"),
                    body: _t(
                        "This page may be corrupted if you save these changes. Are you sure you want to continue?"
                    ),
                    confirmLabel: _t("Save anyway"),
                    confirmClass: "btn-danger",
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                    dismiss: () => resolve(false),
                });
            });
            if (!shouldContinue) {
                return;
            }
        }

        // TODO: handle the urgent save and the fail of the save operation
        await this.editor.shared.operation.next(
            async () => {
                await this.editor.shared.savePlugin.save();
                this.props.builderProps.closeEditor();
            },
            { withLoadingEffect: false, canTimeout: false }
        );
        this.reloadAfterTimeout();
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
        builderProps.config.translatedElements = this.translatedElements;
        builderProps.getThemeTab = () => this.websiteService.isDesigner && ThemeTab;
        const installSnippetModule = builderProps.installSnippetModule;
        builderProps.installSnippetModule = (snippet) =>
            installSnippetModule(snippet, this.save.bind(this));
        builderProps.config.builderOptionsTemplate = "website.BuilderOptions";
        builderProps.config.builderOptionsRegistry = "website-options";
        return builderProps;
    }
}

registry.category("lazy_components").add("website.WebsiteBuilder", WebsiteBuilder);
