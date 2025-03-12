import { CORE_PLUGINS } from "@html_builder/core/core_plugins";
import { BlockTab } from "@html_builder/sidebar/block_tab";
import { CustomizeTab } from "@html_builder/sidebar/customize_tab";
import { EDITOR_COLOR_CSS_VARIABLES, getCSSVariableValue } from "@html_builder/utils/utils_css";
import { Editor } from "@html_editor/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { withSequence } from "@html_editor/utils/resource";
import { DesignTab } from "@mass_mailing_egg/tabs/design_tab";
import {
    Component,
    EventBus,
    onMounted,
    onWillDestroy,
    onWillStart,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRef, useService } from "@web/core/utils/hooks";
import { addLoadingEffect } from "@web/core/utils/ui";
import { useSetupAction } from "@web/search/action_hook";

const DISABLED_PLUGINS = new Set([
    "PowerButtonsPlugin",
    "DoubleClickImagePreviewPlugin",
    "SeparatorPlugin",
    "StarPlugin",
    "BannerPlugin",
]);

/**
 * Mirror of `html_builder/.../builder.js adapted for mass_mailing
 * TODO EGGMAIL: re-read the original file and update this one to be sure
 * related parts match. Ideally we should have one generic builder for both
 * use cases.
 */
export class Builder extends Component {
    static template = "mass_mailing_egg.Builder";
    static components = {
        BlockTab,
        CustomizeTab,
        DesignTab,
    };
    static props = {
        config: { type: Object },
        discard: { type: Function },
        iframeLoaded: { type: Object },
        onChange: { type: Function },
        overlayRef: { type: Function },
        reloadEditor: { type: Function },
        save: { type: Function },
        Plugins: { type: Array, optional: true },
    };
    static defaultProps = {
        Plugins: [],
    };

    setup() {
        this.dialog = useService("dialog");
        this.builderSidebarRef = useRef("builderSidebar");
        this.noSelectionTab = "blocks";
        this.state = useState({
            canUndo: false,
            canRedo: false,
            activeTab: "blocks",
            currentOptionsContainers: undefined,
        });

        // TODO EGGMAIL: evaluate which plugins we need (not embedded components, ...)
        const mainPlugins = MAIN_PLUGINS;
        const corePlugins = CORE_PLUGINS;
        const Plugins = this.filterPlugins([...mainPlugins, ...corePlugins, ...this.props.Plugins]);
        const snippetModel = useState(useService("html_builder.snippets"));
        const editorBus = new EventBus();
        const editor = new Editor(
            {
                Plugins,
                // TODO EGGMAIL: evaluate what this implies
                allowCustomStyle: true,
                allowTargetBlank: true,
                getShared: () => editor.shared,
                localOverlayContainers: {
                    key: this.env.localOverlayContainerKey,
                    ref: this.props.overlayRef,
                },
                onChange: ({ isPreviewing }) => {
                    if (!isPreviewing) {
                        this.state.canRedo = editor.shared.history.canRedo();
                        this.state.canUndo = editor.shared.history.canUndo();
                        this.props.onChange();
                        editorBus.trigger("UPDATE_EDITING_ELEMENT");
                        editorBus.trigger("DOM_UPDATED");
                    }
                },
                reloadEditor: (param = {}) => {
                    this.props.reloadEditor({
                        initialTab: this.state.activeTab,
                        ...param,
                    });
                },
                resources: {
                    can_display_toolbar: (namespace) => !["image", "icon"].includes(namespace),
                    change_current_options_containers_listeners: (currentOptionsContainers) => {
                        this.state.currentOptionsContainers = currentOptionsContainers;
                        if (!currentOptionsContainers.length) {
                            // If there is no option, fallback on the current
                            // fallback tab.
                            this.setTab(this.noSelectionTab);
                            return;
                        }
                        this.setTab("customize");
                    },
                    on_mobile_preview_clicked: withSequence(20, () => {
                        editorBus.trigger("DOM_UPDATED");
                    }),
                    trigger_dom_updated: () => {
                        editorBus.trigger("DOM_UPDATED");
                    },
                    unsplittable_node_predicates: (/** @type {Node} */ node) =>
                        node.querySelector?.("[data-oe-translation-source-sha]"),
                },
                replaceSnippet: async (snippet) => await snippetModel.replaceSnippet(snippet),
                saveSnippet: (snippetEl, cleanForSaveHandlers) =>
                    snippetModel.saveSnippet(snippetEl, cleanForSaveHandlers),
                ...this.props.config,
            },
            this.env.services
        );

        useSubEnv({ editor, editorBus });
        onWillStart(async () => {
            await snippetModel.load();

            // Ensure that the iframe is loaded and the editor is created before
            // instantiating the sub components that potentially need the
            // editor.
            const iframeEl = await this.props.iframeLoaded;
            // TODO EGGMAIL check where the #wrapwrap thingy is set
            this.editor.attachTo(iframeEl.contentDocument.body.querySelector("#wrapwrap"));
        });
        onMounted(() => {
            editor.document.body.classLiist.add("editor_enable");
            this.setCSSVariables();
        });
        onWillDestroy(() => editor.destroy());

        useHotkey("control+z", () => this.undo());
        useHotkey("control+y", () => this.redo());
        useHotkey("control+shift+z", () => this.redo());
        // TODO EGGMAIL evaluate this in context of a standard form view
        useSetupAction({
            beforeUnload: (ev) => this.onBeforeUnload(ev),
            beforeLeave: () => this.onBeforeLeave(),
        });
    }

    discard() {
        if (this.state.canUndo) {
            this.dialog.add(ConfirmationDialog, {
                body: _t(
                    "If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."
                ),
                confirm: () => this.props.discard(),
                cancel: () => {},
            });
        } else {
            this.props.discard();
        }
    }

    filterPlugins(plugins) {
        return plugins.filter((p) => !DISABLED_PLUGINS.has(p.name));
    }

    async onBeforeLeave() {
        if (this.state.canUndo) {
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

    onBeforeUnload(ev) {
        if (!this.isSaving && this.state.canUndo) {
            ev.preventDefault();
            ev.returnValue = "Unsaved changes";
        }
    }

    onFullscreenClick() {
        // TODO EGGMAIL
    }

    onMobilePreviewClick() {
        // TODO EGGMAIL
        this.editor.resources["on_mobile_preview_clicked"].forEach((handler) => handler());
    }

    /**
     * Called when clicking on a tab. Sets the active tab to the given tab.
     *
     * @param {String} tab the tab to set
     */
    onTabClick(tab) {
        this.setTab(tab);
        // Deactivate the options when clicking on the "BLOCKS" or "DESIGN" tabs.
        if (tab === "design" || tab === "blocks") {
            this.editor.shared["builder-options"].deactivateContainers();
        }
    }

    redo() {
        this.env.editor.shared.history.redo();
    }

    async save() {
        this.isSaving = true;
        // TODO EGGMAIL: handle the urgent save and the fail of the save operation
        const snippetMenuEl = this.builderSidebarRef.el;
        // Add a loading effect on the save button and disable the other actions
        addLoadingEffect(snippetMenuEl.querySelector("[data-action='save']"));
        const actionButtonEls = snippetMenuEl.querySelectorAll("[data-action]");
        for (const actionButtonEl of actionButtonEls) {
            actionButtonEl.disabled = true;
        }
        // TODO EGGMAIL review the whole save process in concordance with a
        // standard form view (should concord with formstatusindicator and record
        // saving)
        await this.env.editor.shared.savePlugin.save();
        await this.props.save();
        this.isSaving = false;
    }

    setCSSVariables() {
        const el = this.builderSidebarRef.el;
        for (const style of EDITOR_COLOR_CSS_VARIABLES) {
            let value = getCSSVariableValue(style);
            if (value.startsWith("'") && value.endsWith("'")) {
                // Gradient values are recovered within a string.
                value = value.substring(1, value.length - 1);
            }
            // TODO EGGMAIL: check what we need to do about this
            el.style.setProperty(`--we-cp-${style}`, value);
        }
    }

    setTab(tab) {
        this.state.activeTab = tab;
        // Set the fallback tab on the "Design" tab if it was selected.
        this.noSelectionTab = tab === "design" ? "design" : "blocks";
    }

    undo() {
        this.env.editor.shared.history.undo();
    }
}

registry.category("lazy_components").add("mass_mailing_egg.Builder", Builder);
