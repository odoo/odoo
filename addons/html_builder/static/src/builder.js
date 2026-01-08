import { Editor } from "@html_editor/editor";
import {
    Component,
    EventBus,
    onMounted,
    onWillDestroy,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    status,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";
import { addLoadingEffect as addButtonLoadingEffect } from "@web/core/utils/ui";
import { InvisibleElementsPanel } from "@html_builder/sidebar/invisible_elements_panel";
import { BlockTab } from "@html_builder/sidebar/block_tab";
import { CustomizeTab } from "@html_builder/sidebar/customize_tab";
import { useSnippets } from "@html_builder/snippets/snippet_service";
import { setBuilderCSSVariables } from "@html_builder/utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";
import { getHtmlStyle } from "@html_editor/utils/formatting";
import { isVisible } from "@html_builder/utils/utils";

/**
 * @typedef {(() => void)[]} on_mobile_preview_clicked
 * @typedef {(() => void)[]} trigger_dom_updated
 * @typedef {{ Component: Component; props: object; }[]} lower_panel_entries
 */

export class Builder extends Component {
    static template = "html_builder.Builder";
    static components = { BlockTab, CustomizeTab };
    static props = {
        closeEditor: { type: Function, optional: true },
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
        editableSelector: { type: String },
        themeTabDisplayName: { type: String, optional: true },
        slots: { type: Object, optional: true },
        getCustomizeTranslationTab: { type: Function, optional: true },
    };
    static defaultProps = {
        config: {},
        themeTabDisplayName: _t("Theme"),
    };

    setup() {
        this.ThemeTab = this.props.getThemeTab?.();
        this.CustomizeTranslationTab = this.props.getCustomizeTranslationTab?.();
        // const actionService = useService("action");
        this.builder_sidebarRef = useRef("builder_sidebar");
        this.state = useState({
            canUndo: false,
            canRedo: false,
            activeTab: this.props.config.initialTab || "blocks",
            currentOptionsContainers: undefined,
        });
        this.invisibleElementsPanelState = useState({
            invisibleEls: [],
            invisibleSelector: this.getInvisibleSelector(),
        });
        useHotkey("control+z", () => this.undo());
        useHotkey("control+y", () => this.redo());
        useHotkey("control+shift+z", () => this.redo());
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.notification = useService("notification");

        this.snippetModel = useSnippets(this.props.snippetsName);

        this.lastTrigerUpdateId = 0;
        this.editorBus = new EventBus();
        this.colorPresetToShow = null;
        this.activeTargetEl = null;
        const mobileBreakpoint = this.props.config.mobileBreakpoint ?? "lg";

        // TODO: maybe do a different config for the translate mode and the
        // "regular" mode.
        /** @type {Editor} */
        this.editor = new Editor(
            {
                Plugins: this.props.Plugins,
                ...this.props.config,
                mobileBreakpoint,
                isMobileView: (targetEl) => {
                    const mobileViewThreshold =
                        MEDIAS_BREAKPOINTS[SIZES[mobileBreakpoint.toUpperCase()]].minWidth;
                    const clientWidth =
                        targetEl.ownerDocument.defaultView?.frameElement?.clientWidth ||
                        targetEl.ownerDocument.documentElement.clientWidth;
                    return !!clientWidth && clientWidth < mobileViewThreshold;
                },
                onChange: ({ isPreviewing }) => {
                    if (!isPreviewing) {
                        this.state.canUndo = this.editor.shared.history.canUndo();
                        this.state.canRedo = this.editor.shared.history.canRedo();
                        this.updateInvisibleEls();
                        this.editorBus.trigger("UPDATE_EDITING_ELEMENT");
                        this.triggerDomUpdated();
                        this.props.config.onChange?.();
                    }
                },
                reloadEditor: async (param = {}) => {
                    await this.props.reloadEditor?.({
                        initialTab: this.state.activeTab,
                        ...param,
                    });
                },
                closeEditor: async () => {
                    await this.props.closeEditor?.();
                },
                installSnippetModule: (snippet) => this.props.installSnippetModule?.(snippet),
                /** @type {import("plugins").BuilderResources} */
                resources: {
                    trigger_dom_updated: () => {
                        this.triggerDomUpdated();
                    },
                    on_mobile_preview_clicked: withSequence(20, () => {
                        this.triggerDomUpdated();
                    }),
                    before_save_handlers: () => {
                        const snippetMenuEl = this.builder_sidebarRef.el;
                        const saveButton = snippetMenuEl.querySelector("[data-action='save']");
                        delete this.removeLoadingEffect;
                        if (saveButton) {
                            // Add a loading effect on the save button and disable the other actions
                            this.removeLoadingEffect = addButtonLoadingEffect(
                                snippetMenuEl.querySelector("[data-action='save']")
                            );
                        }
                        this.actionButtonEls = snippetMenuEl.querySelectorAll("[data-action]");
                        for (const actionButtonEl of this.actionButtonEls) {
                            actionButtonEl.disabled = true;
                        }
                    },
                    after_save_handlers: () => {
                        for (const actionButtonEl of this.actionButtonEls) {
                            actionButtonEl.removeAttribute("disabled");
                        }
                        this.removeLoadingEffect?.();
                    },
                    on_snippet_dropped_handlers: () => {
                        this.activeTargetEl = null;
                    },
                    change_current_options_containers_listeners: (currentOptionsContainers) => {
                        this.state.currentOptionsContainers = currentOptionsContainers;
                        if (!currentOptionsContainers.length) {
                            // If there is no option, fallback on the current
                            // fallback tab.
                            this.setTab(this.noSelectionTab);
                            return;
                        }
                        this.activeTargetEl = null;
                        this.setTab("customize");
                    },
                    lower_panel_entries: withSequence(20, {
                        Component: InvisibleElementsPanel,
                        props: this.invisibleElementsPanelState,
                    }),
                    unsplittable_node_predicates: (/** @type {Node} */ node) =>
                        node.querySelector?.("[data-oe-translation-source-sha]"),
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
                updateInvisibleElementsPanel: () => this.updateInvisibleEls(),
                allowCustomStyle: true,
                allowTargetBlank: true,
                dropImageAsAttachment: true,
                getAnimateTextConfig: () => ({ editor: this.editor, editorBus: this.editorBus }),
                baseContainers: ["P"],
                cleanEmptyStructuralContainers: false,
                isEditableRTL: false,
            },
            this.env.services
        );
        this.props.onEditorLoad?.(this.editor);

        onWillStart(async () => {
            await this.snippetModel.load();
            // Ensure that the iframe is loaded and the editor is created before
            // instantiating the sub components that potentially need the
            // editor.
            const iframeEl = await this.props.iframeLoaded;
            if (status(this) === "destroyed") {
                return;
            }
            this.editableEl = iframeEl.contentDocument.body.querySelector(
                this.props.editableSelector
            );

            if (this.editableEl.matches(".o_rtl")) {
                this.editor.config.isEditableRTL = true;
            }

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
        });

        useSubEnv({
            editor: this.editor,
            editorBus: this.editorBus,
            triggerDomUpdated: this.triggerDomUpdated.bind(this),
            editColorCombination: this.editColorCombination.bind(this),
        });
        onWillDestroy(() => {
            this.editor.destroy();
        });

        onMounted(() => {
            this.editor.document.body.classList.add("editor_enable");
            setBuilderCSSVariables(getHtmlStyle(this.editor.document));
            // TODO: onload editor
            this.updateInvisibleEls();
            this.editableEl.addEventListener("dragstart", this.onDragStart);
        });
        onWillUnmount(() => {
            this.editableEl.removeEventListener("dragstart", this.onDragStart);
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.isMobile !== this.props.isMobile) {
                this.updateInvisibleEls(nextProps.isMobile);
                this.invisibleElementsPanelState.invisibleSelector = this.getInvisibleSelector(
                    nextProps.isMobile
                );
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
        return this.props.config.isTranslationMode;
    }

    getInvisibleSelector(isMobile = this.props.isMobile) {
        return `.o_snippet_invisible, ${
            isMobile ? ".o_snippet_mobile_invisible" : ".o_snippet_desktop_invisible"
        }`;
    }

    /**
     * Called when clicking on a tab. Sets the active tab to the given tab.
     *
     * @param {String} tab the tab to set
     * @param {Number | null} presetId the color preset expanding on "theme" tab
     * open.
     */
    onTabClick(tab, presetId = null) {
        if (this.state.activeTab === tab) {
            // If the tab is already active, do nothing.
            return;
        }
        this.setTab(tab);
        // Deactivate the options when clicking on the "BLOCKS" or "THEME" tabs.
        if (tab === "theme" || tab === "blocks") {
            this.colorPresetToShow = presetId;
            this.activeTargetEl = this.activeTargetEl || this.getActiveTarget();
            this.editor.shared.builderOptions.deactivateContainers();
        } else if (this.activeTargetEl) {
            if (isVisible(this.activeTargetEl)) {
                // Reactivate the previously active element.
                this.editor.shared.builderOptions.updateContainers(this.activeTargetEl);
            }
            this.activeTargetEl = null;
        }
    }

    setTab(tab) {
        this.state.activeTab = tab;
        // Set the fallback tab on the "THEME" tab if it was selected.
        this.noSelectionTab = tab === "theme" ? "theme" : "blocks";
    }

    undo() {
        this.editor.shared.operation.next(() => this.editor.shared.history.undo());
    }

    redo() {
        this.editor.shared.operation.next(() => this.editor.shared.history.redo());
    }

    onMobilePreviewClick() {
        this.props.toggleMobile();
        this.editor.resources["on_mobile_preview_clicked"].forEach((handler) => handler());
    }

    updateInvisibleEls(isMobile = this.props.isMobile) {
        this.invisibleElementsPanelState.invisibleEls = [
            ...this.editor.editable.querySelectorAll(this.getInvisibleSelector(isMobile)),
        ];
    }

    lowerPanelEntries() {
        return this.editor.resources["lower_panel_entries"] ?? [];
    }

    editColorCombination(presetId) {
        this.onTabClick("theme", presetId);
    }

    getActiveTarget() {
        return this.editor.shared["builderOptions"].getContainers().at(-1)?.element;
    }
}
