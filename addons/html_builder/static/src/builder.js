import { Editor } from "@html_editor/editor";
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
import { useService } from "@web/core/utils/hooks";
import { addLoadingEffect as addButtonLoadingEffect } from "@web/core/utils/ui";
import { useSetupAction } from "@web/search/action_hook";
import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { BlockTab } from "@html_builder/sidebar/block_tab";
import { CustomizeTab } from "@html_builder/sidebar/customize_tab";
import { useSnippets } from "@html_builder/snippets/snippet_service";
import { setBuilderCSSVariables } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";
import { getHtmlStyle } from "@html_editor/utils/formatting";

export class Builder extends Component {
    static template = "html_builder.Builder";
    static components = { BlockTab, CustomizeTab, InvisibleElementsPanel };
    static props = {
        closeEditor: { type: Function },
        reloadEditor: { type: Function, optional: true },
        onEditorLoad: { type: Function, optional: true },
        installSnippetModule: { type: Function, optional: true },
        snippetsName: { type: String },
        toggleMobile: { type: Function },
        overlayRef: { type: Function },
        iframeLoaded: { type: Object },
        isMobile: { type: Boolean },
        Plugins: { type: Array, optional: true },
        config: { type: Object, optional: true },
        getThemeTab: { type: Function, optional: true },
    };
    static defaultProps = {
        onEditorLoad: () => {},
        config: {},
    };

    setup() {
        this.ThemeTab = this.props.getThemeTab?.();
        // const actionService = useService("action");
        this.builder_sidebarRef = useRef("builder_sidebar");
        this.state = useState({
            canUndo: false,
            canRedo: false,
            activeTab: this.props.config.initialTab || "blocks",
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

        this.snippetModel = useSnippets(this.props.snippetsName);

        this.lastTrigerUpdateId = 0;
        this.editorBus = new EventBus();

        // TODO: maybe do a different config for the translate mode and the
        // "regular" mode.
        this.editor = new Editor(
            {
                Plugins: this.props.Plugins,
                ...this.props.config,
                onChange: ({ isPreviewing }) => {
                    if (!isPreviewing) {
                        this.state.canUndo = this.editor.shared.history.canUndo();
                        this.state.canRedo = this.editor.shared.history.canRedo();
                        this.updateInvisibleEls();
                        this.editorBus.trigger("UPDATE_EDITING_ELEMENT");
                        this.triggerDomUpdated();
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
                installSnippetModule: async (snippet) =>
                    this.props.installSnippetModule(snippet, this.save.bind(this)),
                resources: {
                    trigger_dom_updated: () => {
                        this.triggerDomUpdated();
                    },
                    on_mobile_preview_clicked: withSequence(20, () => {
                        this.triggerDomUpdated();
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
                localOverlayContainers: {
                    key: this.env.localOverlayContainerKey,
                    ref: this.props.overlayRef,
                },
                saveSnippet: (snippetEl, cleanForSaveHandlers, wrapWithSaveSnippetHandlers) =>
                    this.snippetModel.saveSnippet(
                        snippetEl,
                        cleanForSaveHandlers,
                        wrapWithSaveSnippetHandlers
                    ),
                snippetModel: this.snippetModel,
                getShared: () => this.editor.shared,
                updateInvisibleElementsPanel: () => this.updateInvisibleEls(),
                allowCustomStyle: true,
                allowTargetBlank: true,
                dropImageAsAttachment: true,
                getAnimateTextConfig: () => ({ editor: this.editor, editorBus: this.editorBus }),
                cleanEmptyStructuralContainers: false,
            },
            this.env.services
        );
        this.props.onEditorLoad(this.editor);

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
            editorBus: this.editorBus,
            triggerDomUpdated: this.triggerDomUpdated.bind(this),
        });
        // onMounted(() => {
        //     // actionService.setActionMode("fullscreen");
        // });
        onWillDestroy(() => {
            this.editor.destroy();
            this.editableEl.removeEventListener("dragstart", this.onDragStart);
            // actionService.setActionMode("current");
        });

        useSetupAction({
            beforeUnload: (ev) => this.onBeforeUnload(ev),
            beforeLeave: () => this.onBeforeLeave(),
        });

        onMounted(() => {
            this.editor.document.body.classList.add("editor_enable");
            setBuilderCSSVariables(getHtmlStyle(this.editor.document));
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
    async triggerDomUpdated() {
        this.lastTrigerUpdateId++;
        const currentTriggerId = this.lastTrigerUpdateId;
        const getStatePromises = [];
        const { promise: updatePromise, resolve } = Promise.withResolvers();
        this.editorBus.trigger("DOM_UPDATED", { getStatePromises, updatePromise });
        await Promise.all(getStatePromises);
        const isLastTriggerId = this.lastTrigerUpdateId === currentTriggerId;
        resolve(isLastTriggerId);
    }

    get displayOnlyCustomizeTab() {
        return !!this.props.config.customizeTab;
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
        this.editor.shared.operation.next(this._save.bind(this), { withLoadingEffect: false });
    }

    async _save() {
        this.isSaving = true;
        // TODO: handle the urgent save and the fail of the save operation
        const snippetMenuEl = this.builder_sidebarRef.el;
        // Add a loading effect on the save button and disable the other actions
        const removeLoadingEffect = addButtonLoadingEffect(
            snippetMenuEl.querySelector("[data-action='save']")
        );
        const actionButtonEls = snippetMenuEl.querySelectorAll("[data-action]");
        for (const actionButtonEl of actionButtonEls) {
            actionButtonEl.disabled = true;
        }
        try {
            await this.editor.shared.savePlugin.save();
            this.props.closeEditor();
        } catch (error) {
            for (const actionButtonEl of actionButtonEls) {
                actionButtonEl.removeAttribute("disabled");
            }
            removeLoadingEffect();
            this.editor.shared.edit_interaction.restartInteractions();
            throw error;
        }
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
            this.editor.shared["builderOptions"].deactivateContainers();
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
        if (this.state.canUndo && !this.editor.shared.savePlugin.isAlreadySaved()) {
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
