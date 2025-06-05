import { Editor } from "@html_editor/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import {
    Component,
    EventBus,
    onMounted,
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { addLoadingEffect as addButtonLoadingEffect } from "@web/core/utils/ui";
import { useSetupAction } from "@web/search/action_hook";
import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { BlockTab } from "@html_builder/sidebar/block_tab";
import { CustomizeTab } from "@html_builder/sidebar/customize_tab";
import { CORE_PLUGINS } from "@html_builder/core/core_plugins";
import { EDITOR_COLOR_CSS_VARIABLES, getCSSVariableValue } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";

export class Builder extends Component {
    static template = "html_builder.Builder";
    static components = { BlockTab, CustomizeTab, InvisibleElementsPanel };
    static props = {
        closeEditor: { type: Function },
        reloadEditor: { type: Function, optional: true },
        snippetsName: { type: String },
        toggleMobile: { type: Function },
        overlayRef: { type: Function },
        isTranslation: { type: Boolean },
        iframeLoaded: { type: Object },
        isMobile: { type: Boolean },
        Plugins: { type: Array, optional: true },
        config: { type: Object, optional: true },
        getThemeTab: { type: Function, optional: true },
    };
    static defaultProps = {
        config: {},
    };

    setup() {
        this.ThemeTab = this.props.getThemeTab?.();
        // const actionService = useService("action");
        this.builder_sidebarRef = useRef("builder_sidebar");
        this.state = useState({
            canUndo: false,
            canRedo: false,
            activeTab:
                this.props.config.initialTab || (this.props.isTranslation ? "customize" : "blocks"),
            currentOptionsContainers: undefined,
            invisibleEls: [],
        });
        useHotkey("control+z", () => this.undo());
        useHotkey("control+y", () => this.redo());
        useHotkey("control+shift+z", () => this.redo());
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.notification = useService("notification");

        const editorBus = new EventBus();

        const mainPlugins = removePlugins(
            [...MAIN_PLUGINS],
            [
                "PowerButtonsPlugin",
                "DoubleClickImagePreviewPlugin",
                "SeparatorPlugin",
                "StarPlugin",
                "BannerPlugin",
            ]
        );
        const corePlugins = this.props.isTranslation ? [] : CORE_PLUGINS;
        const Plugins = [...mainPlugins, ...corePlugins, ...(this.props.Plugins || [])];
        // TODO: maybe do a different config for the translate mode and the
        // "regular" mode.
        this.editor = new Editor(
            {
                Plugins,
                isTranslation: this.props.isTranslation,
                ...this.props.config,
                onChange: ({ isPreviewing }) => {
                    if (!isPreviewing) {
                        this.state.canUndo = this.editor.shared.history.canUndo();
                        this.state.canRedo = this.editor.shared.history.canRedo();
                        this.updateInvisibleEls();
                        editorBus.trigger("UPDATE_EDITING_ELEMENT");
                        editorBus.trigger("DOM_UPDATED");
                    }
                },
                reloadEditor: async (param = {}) => {
                    await this.props.reloadEditor({
                        initialTab: this.state.activeTab,
                        ...param,
                    });
                },
                closeEditor: async () => {
                    await this.props.closeEditor();
                },
                resources: {
                    trigger_dom_updated: () => {
                        editorBus.trigger("DOM_UPDATED");
                    },
                    on_mobile_preview_clicked: withSequence(20, () => {
                        editorBus.trigger("DOM_UPDATED");
                    }),
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
                    unsplittable_node_predicates: (/** @type {Node} */ node) =>
                        node.querySelector?.("[data-oe-translation-source-sha]"),
                    can_display_toolbar: (namespace) => !["image", "icon"].includes(namespace),

                    // disable the toolbar for images and icons
                },
                getRecordInfo: (editableEl) => {
                    if (!editableEl) {
                        editableEl = closestElement(
                            this.editor.shared.selection.getEditableSelection().anchorNode
                        );
                    }
                    return {
                        resModel: editableEl.dataset["oeModel"],
                        resId: editableEl.dataset["oeId"],
                        field: editableEl.dataset["oeField"],
                        type: editableEl.dataset["oeType"],
                    };
                },
                localOverlayContainers: {
                    key: this.env.localOverlayContainerKey,
                    ref: this.props.overlayRef,
                },
                saveSnippet: (snippetEl, cleanForSaveHandlers) =>
                    this.snippetModel.saveSnippet(snippetEl, cleanForSaveHandlers),
                getShared: () => this.editor.shared,
                updateInvisibleElementsPanel: () => this.updateInvisibleEls(),
                allowCustomStyle: true,
                allowTargetBlank: true,
            },
            this.env.services
        );

        this.snippetModel = useState(useService("html_builder.snippets"));
        this.snippetModel.registerBeforeReload(this.save.bind(this));

        onWillStart(async () => {
            await this.snippetModel.load();
            // Ensure that the iframe is loaded and the editor is created before
            // instantiating the sub components that potentially need the
            // editor.
            const iframeEl = await this.props.iframeLoaded;
            this.editableEl = iframeEl.contentDocument.body.querySelector("#wrapwrap");

            // Prevent image dragging in the website builder. Not via css because
            // if one of the image ancestor has a dragstart listener, the dragstart handler
            // can be called with the image as target.
            this.onDragStart = (ev) => {
                if (ev.target.nodeName === "IMG") {
                    ev.preventDefault();
                    ev.stopPropagation();
                }
            };
            this.editor.attachTo(this.editableEl);
            this.editableEl.addEventListener("dragstart", this.onDragStart);
        });

        useSubEnv({
            editor: this.editor,
            editorBus,
        });
        // onMounted(() => {
        //     // actionService.setActionMode("fullscreen");
        // });
        onWillDestroy(() => {
            this.editor.destroy();
            this.editableEl.removeEventListener("dragstart", this.onDragStart);
            this.snippetModel.unregisterBeforeReload();
            // actionService.setActionMode("current");
        });

        useSetupAction({
            beforeUnload: (ev) => this.onBeforeUnload(ev),
            beforeLeave: () => this.onBeforeLeave(),
        });

        onMounted(() => {
            this.editor.document.body.classList.add("editor_enable");
            this.setCSSVariables();
            // TODO: onload editor
            this.updateInvisibleEls();
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.isMobile !== this.props.isMobile) {
                this.updateInvisibleEls(nextProps.isMobile);
            }
        });
        // Fallback tab when no option is active.
        this.noSelectionTab = "blocks";
    }

    setCSSVariables() {
        const el = this.builder_sidebarRef.el;
        for (const style of EDITOR_COLOR_CSS_VARIABLES) {
            let value = getCSSVariableValue(style);
            if (value.startsWith("'") && value.endsWith("'")) {
                // Gradient values are recovered within a string.
                value = value.substring(1, value.length - 1);
            }
            el.style.setProperty(`--we-cp-${style}`, value);
        }
    }

    discard() {
        if (this.state.canUndo) {
            this.dialog.add(ConfirmationDialog, {
                body: _t(
                    "If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."
                ),
                confirm: () => this.props.closeEditor(),
                cancel: () => {},
            });
        } else {
            this.props.closeEditor();
        }
    }

    getInvisibleSelector(isMobile = this.props.isMobile) {
        return `.o_snippet_invisible, ${
            isMobile ? ".o_snippet_mobile_invisible" : ".o_snippet_desktop_invisible"
        }`;
    }

    async save() {
        this.isSaving = true;
        // TODO: handle the urgent save and the fail of the save operation
        const snippetMenuEl = this.builder_sidebarRef.el;
        // Add a loading effect on the save button and disable the other actions
        addButtonLoadingEffect(snippetMenuEl.querySelector("[data-action='save']"));
        const actionButtonEls = snippetMenuEl.querySelectorAll("[data-action]");
        for (const actionButtonEl of actionButtonEls) {
            actionButtonEl.disabled = true;
        }
        await this.editor.shared.savePlugin.save(this.props.isTranslation);
        this.props.closeEditor();
    }

    /**
     * Called when clicking on a tab. Sets the active tab to the given tab.
     *
     * @param {String} tab the tab to set
     */
    onTabClick(tab) {
        this.setTab(tab);
        // Deactivate the options when clicking on the "BLOCKS" or "THEME" tabs.
        if (tab === "theme" || tab === "blocks") {
            this.editor.shared["builder-options"].deactivateContainers();
        }
    }

    setTab(tab) {
        this.state.activeTab = tab;
        // Set the fallback tab on the "THEME" tab if it was selected.
        this.noSelectionTab = tab === "theme" ? "theme" : "blocks";
    }

    undo() {
        this.editor.shared.history.undo();
    }

    redo() {
        this.editor.shared.history.redo();
    }

    onBeforeUnload(event) {
        if (!this.isSaving && this.state.canUndo) {
            event.preventDefault();
            event.returnValue = "Unsaved changes";
        }
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

    onMobilePreviewClick() {
        this.props.toggleMobile();
        this.editor.resources["on_mobile_preview_clicked"].forEach((handler) => handler());
    }

    updateInvisibleEls(isMobile = this.props.isMobile) {
        this.state.invisibleEls = [
            ...this.editor.editable.querySelectorAll(this.getInvisibleSelector(isMobile)),
        ];
    }
}

/**
 * Removes the specified plugins from a given list of plugins.
 *
 * @param {Array<Plugin>} plugins the list of plugins
 * @param {Array<string>} pluginsToRemove the names of the plugins to remove
 * @returns {Array<Plugin>}
 */
function removePlugins(plugins, pluginsToRemove) {
    return plugins.filter((p) => !pluginsToRemove.includes(p.name));
}

registry.category("lazy_components").add("website.Builder", Builder);
