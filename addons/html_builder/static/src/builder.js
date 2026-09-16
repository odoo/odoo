import { useSubEnv } from "@web/owl2/utils";
import { useEditor } from "@html_editor/editor";
import {
    Component,
    EventBus,
    onMounted,
    onWillDestroy,
    onWillStart,
    onWillUnmount,
    providePlugins,
    signal,
    status,
    proxy,
    useProps,
    t,
} from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_utils";
import { useService } from "@web/core/utils/hooks";
import { addLoadingEffect as addButtonLoadingEffect } from "@web/core/utils/ui";
import { BlockTab } from "@html_builder/sidebar/block_tab";
import { CustomizeTab } from "@html_builder/sidebar/customize_tab";
import { useSnippets } from "@html_builder/snippets/snippet_service";
import { setBuilderCSSVariables } from "@html_builder/utils/utils_css";
import { TextTruncateTooltipPlugin } from "@web/core/tooltip/text_truncate_tooltip_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { getHtmlStyle } from "@html_editor/utils/formatting";

const TAB_TRANSITION_FALLBACK_DELAY = 400;

/**
 * @typedef {((args: {isMobileView: boolean}) => ())[]} on_mobile_view_switched_handlers
 * called when the screen size switches between mobile and desktop view
 * @typedef {(() => void)[]} on_dom_updated_handlers
 * @typedef {{ Component: Component; props: object; }[]} lower_panel_entries
 */

export class Builder extends Component {
    static template = "html_builder.Builder";
    static components = { BlockTab, CustomizeTab };
    props = useProps({
        closeEditor: t.function().optional(),
        reloadEditor: t.function().optional(() => () => {}),
        onEditorLoad: t.function().optional(),
        newInstalledModule: t.string().optional(),
        installSnippetModule: t.function().optional(),
        snippetsName: t.string(),
        toggleMobile: t.function(),
        iframeLoaded: t.object(),
        isMobile: t.boolean(),
        Plugins: t.array().optional(),
        // This fragment of config will be passed to the Editor and be
        // available to the plugins in `config`
        config: t.object().optional({}),
        getThemeTab: t.function().optional(),
        editableSelector: t.string(),
        themeTabDisplayName: t.string().optional(_t("Theme")),
        slots: t.object().optional(),
        initialTab: t.string().optional("blocks"),
        onlyCustomizeTab: t.boolean().optional(false),
        animateThemeTabSwitch: t.boolean().optional(false),
        localOverlayContainerKey: t.string(),
    });

    // Ref on the local overlay container element, owned by the parent.
    overlayRef = useProps.static("overlayRef", t.signal(t.ref()));

    builderSidebarRef = signal.ref();

    setup() {
        this.ThemeTab = this.props.getThemeTab?.();
        providePlugins([TextTruncateTooltipPlugin], { rootRef: this.builderSidebarRef });
        this.state = proxy({
            canUndo: false,
            canRedo: false,
            activeTab: this.props.onlyCustomizeTab ? "customize" : this.props.initialTab,
            pendingTab: undefined,
            currentOptionsContainers: undefined,
            themeColorPresetToShow: null,
            themeTargetRowId: null,
            themeTargetContainerId: null,
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
        this.activeTargetEl = null;
        const mobileBreakpoint = this.props.config.mobileBreakpoint ?? "lg";
        // TODO: maybe do a different config for the translate mode and the
        // "regular" mode.
        const config = {
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
                    this.editorBus.trigger("UPDATE_EDITING_ELEMENT");
                    this.triggerDomUpdated();
                    this.props.config.onChange?.();
                }
            },
            reloadEditor: ({ url, editingElement } = {}) =>
                this.props.reloadEditor(
                    url,
                    this.editor.processThrough("reload_context_processors", {}, editingElement)
                ),
            closeEditor: async () => {
                await this.props.closeEditor?.();
            },
            installSnippetModule: (snippet) => this.props.installSnippetModule?.(snippet),
            /** @type {import("plugins").BuilderResources} */
            resources: {
                on_dom_updated_handlers: () => {
                    this.triggerDomUpdated();
                },
                on_mobile_view_switched_handlers: withSequence(20, () => {
                    this.triggerDomUpdated();
                }),
                on_will_save_handlers: () => {
                    const snippetMenuEl = this.builderSidebarRef();
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
                on_saved_handlers: () => {
                    for (const actionButtonEl of this.actionButtonEls) {
                        actionButtonEl.removeAttribute("disabled");
                    }
                    this.removeLoadingEffect?.();
                },
                on_snippet_dropped_handlers: () => {
                    this.activeTargetEl = null;
                },
                on_current_options_containers_changed_handlers: (currentOptionsContainers) => {
                    this.state.currentOptionsContainers = currentOptionsContainers;
                    if (currentOptionsContainers.length || this.props.onlyCustomizeTab) {
                        this.activeTargetEl = null;
                        this.setTab("customize");
                    } else if (this.state.activeTab === "customize") {
                        // If there is no option, go to add blocks
                        this.setTab("blocks");
                    }
                },
                reload_context_processors: (context) => ({
                    ...context,
                    initialTab: this.state.activeTab,
                }),
                is_node_splittable_predicates: (/** @type {Node} */ node) => {
                    if (node.querySelector?.("[data-oe-translation-source-sha]")) {
                        return false;
                    }
                },
            },
            localOverlayContainers: {
                key: this.props.localOverlayContainerKey,
                ref: this.overlayRef,
            },
            saveSnippet: (snippetEl, cleanForSaveProcessors, wrapWithSaveSnippetHandlers) =>
                this.snippetModel.saveSnippet(
                    snippetEl,
                    cleanForSaveProcessors,
                    wrapWithSaveSnippetHandlers
                ),
            snippetModel: this.snippetModel,
            hideStylingInLinkPopover: true,
            allowTargetBlank: true,
            allowTextColumnResize: false,
            dropImageAsAttachment: true,
            getAnimateTextConfig: () => ({ editor: this.editor, editorBus: this.editorBus }),
            baseContainers: ["P"],
            cleanEmptyStructuralContainers: false,
            isEditableRTL: false,
            publicAttachments: true,
            direction: "ltr",
            maxFontSize: 400,
        };
        this.editor = useEditor(config);
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
                this.editor.config.direction = "rtl";
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

            // Use a resize observer to trigger `on_mobile_view_switched_handlers`
            // when the view size switches between desktop and mobile view
            let isMobileView = this.editor.config.isMobileView(this.editableEl);
            this.resizeObserver = new ResizeObserver(() => {
                const wasMobileView = isMobileView;
                isMobileView = this.editor.config.isMobileView(this.editableEl);
                if (wasMobileView !== isMobileView) {
                    this.editor.trigger("on_mobile_view_switched_handlers", { isMobileView });
                }
            });
            this.resizeObserver.observe(this.editableEl);

            this.editor.attachTo(this.editableEl);
        });

        useSubEnv({
            editor: this.editor,
            editorBus: this.editorBus,
            triggerDomUpdated: this.triggerDomUpdated.bind(this),
            editColorCombination: this.editColorCombination.bind(this),
            editThemeOption: this.editThemeOption.bind(this),
        });
        onWillDestroy(() => {
            clearTimeout(this.tabTransitionFallbackTimeout);
            this.resizeObserver?.disconnect();
            this.editor.destroy();
        });

        onMounted(() => {
            this.editor.document.body.classList.add("editor_enable");
            setBuilderCSSVariables(getHtmlStyle(this.editor.document));
            // TODO: onload editor
            this.editableEl.addEventListener("dragstart", this.onDragStart);
        });
        onWillUnmount(() => {
            this.editableEl.removeEventListener("dragstart", this.onDragStart);
        });
    }
    async triggerDomUpdated() {
        this.lastTrigerUpdateId++;
        const currentTriggerId = this.lastTrigerUpdateId;
        const getStatePromises = [];
        const { promise: updatePromise, resolve } = Promise.withResolvers();
        this.editorBus.trigger("DOM_UPDATED", { getStatePromises, updatePromise });
        await Promise.allSettled(getStatePromises);
        const isLastTriggerId = this.lastTrigerUpdateId === currentTriggerId;
        resolve(isLastTriggerId);
    }

    /**
     * Called when clicking on a tab. Sets the active tab to the given tab.
     *
     * @param {String} tab the tab to set
     */
    onTabClick(tab) {
        if (this.state.activeTab === tab) {
            // If the tab is already active, do nothing.
            return;
        }
        if (tab === "theme") {
            this.setThemeReveal();
        }
        this.switchTab(tab, { animated: false });
    }

    setThemeReveal({ presetId = null, targetRowId = null, targetContainerId = null } = {}) {
        this.state.themeColorPresetToShow = presetId;
        this.state.themeTargetRowId = targetRowId;
        this.state.themeTargetContainerId = targetContainerId;
    }

    updateOptionsForTab(tab) {
        // Deactivate the options when clicking on the "BLOCKS" or "THEME" tabs.
        if (tab === "theme" || tab === "blocks") {
            this.activeTargetEl = this.activeTargetEl || this.getActiveTarget();
            this.editor.shared.builderOptions.deactivateContainers();
        } else if (this.activeTargetEl) {
            if (!this.editor.shared.visibility.isElementHidden(this.activeTargetEl)) {
                // Reactivate the previously active element.
                this.editor.shared.builderOptions.updateContainers(this.activeTargetEl);
            }
            this.activeTargetEl = null;
        }
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    switchTab(tab, { animated = false } = {}) {
        if (this.state.activeTab === tab) {
            return;
        }

        if (!animated) {
            clearTimeout(this.tabTransitionFallbackTimeout);
            this.setTab(tab);
            this.updateOptionsForTab(tab);
            this.state.pendingTab = undefined;
        } else {
            this.state.pendingTab = tab;
            clearTimeout(this.tabTransitionFallbackTimeout);
            // Set a timeout to ensure the tab switch even when transitions
            // are disabled on .o-tab-content
            this.tabTransitionFallbackTimeout = setTimeout(
                () => this.completeTabSwitch(),
                TAB_TRANSITION_FALLBACK_DELAY
            );
        }
    }

    onTabTransitionEnd(ev) {
        if (ev.target === ev.currentTarget && ev.propertyName === "opacity") {
            this.completeTabSwitch();
        }
    }

    completeTabSwitch() {
        if (!this.state.pendingTab) {
            return;
        }
        clearTimeout(this.tabTransitionFallbackTimeout);
        this.setTab(this.state.pendingTab);
        this.updateOptionsForTab(this.state.pendingTab);
        this.state.pendingTab = undefined;
    }

    get themeTabProps() {
        return {
            colorPresetToShow: this.state.themeColorPresetToShow,
            targetRowId: this.state.themeTargetRowId,
            targetContainerId: this.state.themeTargetContainerId,
        };
    }

    undo() {
        this.editor.shared.operation.next(() => this.editor.shared.history.undo());
    }

    redo() {
        this.editor.shared.operation.next(() => this.editor.shared.history.redo());
    }

    onMobilePreviewClick() {
        this.props.toggleMobile();
    }

    lowerPanelEntries() {
        return this.editor.getResource("lower_panel_entries");
    }

    editColorCombination(presetId) {
        this.openThemeOption({ presetId });
    }

    editThemeOption(targetRowId, targetContainerId) {
        this.openThemeOption({ targetRowId, targetContainerId });
    }

    openThemeOption({ presetId = null, targetRowId = null, targetContainerId = null } = {}) {
        this.setThemeReveal({
            presetId,
            targetRowId,
            targetContainerId,
        });
        this.switchTab("theme", { animated: this.props.animateThemeTabSwitch });
    }

    getActiveTarget() {
        return this.editor.shared["builderOptions"].getContainers().at(-1)?.element;
    }
}
