import { Plugin } from "@html_editor/plugin";
import { isZWS } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { composeToolbarButton, Toolbar } from "./toolbar";
import { hasTouch } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { ToolbarMobile } from "./mobile_toolbar";
import { debounce } from "@web/core/utils/timing";
import { omit, pick } from "@web/core/utils/objects";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { memoize } from "@web/core/utils/functions";

/** @typedef { import("@html_editor/core/selection_plugin").EditorSelection } EditorSelection */
/** @typedef { import("@html_editor/core/user_command_plugin").UserCommand } UserCommand */
/** @typedef { import("@web/core/l10n/translation.js")._t} _t */
/** @typedef { ReturnType<_t> } TranslatedString */
/** @typedef { (selection: EditorSelection, nodes: Node[]) => TranslatedString } TranslatedStringGetter */

/**
 * @typedef {Object} ToolbarNamespace
 * @property {string} id
 * @property {(targetedNodes: Node[]) => boolean} isApplied
 *
 *
 * @typedef {Object} ToolbarGroup
 * @property {string} id
 * @property {string[]} [namespaces]
 *
 *
 * @typedef {ToolbarCommandItem | ToolbarComponentItem} ToolbarItem
 *
 * @typedef {Object} ToolbarCommandItem
 * Regular button: derives from a user command specified by commandId.
 * The properties maked with * can be omitted if they are present in the user command.
 * The ones marked with ?* are both optional and derivable from the user command.
 * @property {string} id
 * @property {string} groupId Id of a toolbar group
 * @property {string} commandId
 * @property {string[]} [namespaces]
 * @property {Object} [commandParams] Passed to the command's `run` function
 * @property {TranslatedString | TranslatedStringGetter} [description] * - becomes the button's title (and tooltip content)
 * @property {string} [icon] *
 * @property {string} [text] Can be used with (or instead of) `icon`
 * @property {(selection: EditorSelection) => boolean} [isAvailable] ? *
 * @property {(selection: EditorSelection, nodes: Node[]) => boolean} [isActive]
 * @property {(selection: EditorSelection, nodes: Node[]) => boolean} [isDisabled]
 *
 * @typedef {Object} ToolbarComponentItem
 * Adds a custom component to the toolbar.
 * @property {string} id
 * @property {string} groupId
 * @property {string[]} [namespaces]
 * @property {TranslatedString | TranslatedStringGetter} [description]
 * @property {Function} Component
 * @property {Object} props
 * @property {(selection: EditorSelection) => boolean} [isAvailable]
 *
 * ToolbarItem.id maps to the button's `name` attribute
 * ToolbarItem.description maps to the button's `title` attribute (tooltip content)
 */

/**
 * A ToolbarCommandItem must derive from a user command ( @see UserCommand )
 * specified by commandId. Properties defined in a toolbar item override those
 * from a user command.
 *
 * Example:
 *
 * resources = {
 *     user_commands: [
 *         @type {UserCommand}
 *         {
 *             id: myCommand,
 *             run: myCommandFunction,
 *             description: _t("My Command"),
 *             icon: "fa-bug",
 *         },
 *     ],
 *     toolbar_groups: [
 *         @type {ToolbarGroup}
 *         { id: "myGroup" },
 *     ],
 *     toolbar_items: [
 *         @type {ToolbarCommandItem}
 *         {
 *             id: "myButton",
 *             groupId: "myGroup",
 *             commandId: "myCommand",
 *             description: _t("My Toolbar Command Button"), // overrides the user command's `description`
 *             // `icon` is inferred from the user command
 *         },
 *         @type {ToolbarComponentItem}
 *         {
 *             id: "myComponentButton",
 *             groupId: "myGroup",
 *             description: _t("My Toolbar Component Button"),
 *             Component: MyComponent,
 *             props: { myProp: "myValue" },
 *         },
 *     ],
 * };
 */

/**
 * Types after conversion to renderable toolbar buttons:
 *
 * @typedef {Object} ToolbarCommandButton
 * @property {string} id
 * @property {string} groupId
 * @property {TranslatedStringGetter} description
 * @property {Function} run
 * @property {string} [icon]
 * @property {string} [text]
 * @property {(selection: EditorSelection) => boolean} isAvailable
 * @property {(selection: EditorSelection, nodes: Node[]) => boolean} [isActive]
 * @property {(selection: EditorSelection, nodes: Node[]) => boolean} [isDisabled]
 *
 * @typedef {Object} ToolbarComponentButton
 * Adds a custom component to the toolbar (processed version with required fields).
 * @property {string} id
 * @property {string} groupId
 * @property {string[]} [namespaces]
 * @property {TranslatedStringGetter} description
 * @property {Function} Component
 * @property {Object} props
 * @property {(selection: EditorSelection) => boolean} isAvailable
 *
 * @typedef {ToolbarCommandButton | ToolbarComponentButton} ToolbarButton
 */

/** Delay in ms for toolbar open after keyup, double click or triple click. */
const DELAY_TOOLBAR_OPEN = 300;
/** Number of buttons below which toolbar will open directly in its expanded form */
const MIN_SIZE_FOR_COMPACT = 7;

/**
 * @typedef { Object } ToolbarShared
 * @property { ToolbarPlugin['getToolbarInfo'] } getToolbarInfo
 */

export class ToolbarPlugin extends Plugin {
    static id = "toolbar";
    static dependencies = ["overlay", "selection", "userCommand"];
    static shared = ["getToolbarInfo"];
    resources = {
        selectionchange_handlers: this.handleSelectionChange.bind(this),
        selection_leave_handlers: () => this.closeToolbar(),
        prevent_closing_overlay_predicates: (ev) => this.overlay.overlayContainsElement(ev.target),
        step_added_handlers: () => this.updateToolbar(),
        user_commands: {
            id: "expandToolbar",
            run: () => {
                this.isToolbarExpanded = true;
                this.updateToolbar();
            },
        },
        toolbar_groups: [
            withSequence(100, { id: "expand_toolbar", namespaces: ["compact"] }),
            withSequence(30, { id: "layout" }),
        ],
        toolbar_items: {
            id: "expand_toolbar",
            groupId: "expand_toolbar",
            commandId: "expandToolbar",
            description: _t("Expand toolbar"),
            icon: "oi-ellipsis-v",
        },
        toolbar_namespaces: [
            withSequence(99, { id: "compact", isApplied: () => !this.isToolbarExpanded }),
            withSequence(100, { id: "expanded", isApplied: () => true }),
        ],
    };

    setup() {
        const groupIds = new Set();
        for (const group of this.getResource("toolbar_groups")) {
            if (groupIds.has(group.id)) {
                throw new Error(`Duplicate toolbar group id: ${group.id}`);
            }
            groupIds.add(group.id);
        }
        this.buttonGroups = this.getButtonGroups();
        this.buttonsByNamespace = this.getButtonsByNamespace();

        this.isMobileToolbar = hasTouch() && window.visualViewport;

        if (this.isMobileToolbar) {
            this.overlay = new MobileToolbarOverlay(this.editable);
        } else {
            this.overlay = this.dependencies.overlay.createOverlay(Toolbar, {
                positionOptions: {
                    position: "top-start",
                },
                closeOnPointerdown: false,
            });
        }
        this.state = reactive({ buttonGroups: [], namespace: undefined });

        this.onSelectionChangeActive = true;
        this.debouncedUpdateToolbar = debounce(this._updateToolbar, DELAY_TOOLBAR_OPEN);

        if (this.isMobileToolbar) {
            this.addDomListener(this.editable, "pointerup", () => {
                // Collapse toolbar to compact mode when tapping outside of it
                this.isToolbarExpanded = false;
            });
        } else {
            // Mouse interaction behavior:
            // Close toolbar on mousedown and prevent it from opening until mouseup.
            this.addDomListener(this.editable, "mousedown", (ev) => {
                // Don't close if the mousedown is on an overlay.
                if (!ev.target?.closest?.(".o-overlay-item")) {
                    this.closeToolbar();
                    this.debouncedUpdateToolbar.cancel();
                    this.onSelectionChangeActive = false;
                }
            });
            this.addGlobalDomListener("mouseup", (ev) => {
                if (ev.detail >= 2) {
                    // Delayed open, waiting for a possible triple click.
                    this.onSelectionChangeActive = true;
                    this.debouncedUpdateToolbar();
                } else {
                    // Fast open, just wait for a possible selection change due
                    // to mouseup.
                    setTimeout(() => {
                        this.updateToolbar();
                        this.onSelectionChangeActive = true;
                    });
                }
            });

            // Keyboard interaction behavior:
            // Close toolbar on keydown Arrows and prevent it from opening until
            // keyup. Opening is debounced to avoid open/close between
            // sequential keystrokes.
            this.addDomListener(this.editable, "keydown", (ev) => {
                // reason for "key?":
                // On Chrome, if there is a password saved for a login page,
                // a mouse click trigger a keydown event without any key
                if (ev.key?.startsWith("Arrow")) {
                    this.closeToolbar();
                    this.onSelectionChangeActive = false;
                }
            });
            this.addDomListener(this.editable, "keyup", (ev) => {
                if (ev.key?.startsWith("Arrow")) {
                    this.onSelectionChangeActive = true;
                    this.debouncedUpdateToolbar();
                }
            });
        }
        this.isToolbarExpanded = false;
        this.toolbarProps = {
            class: "shadow rounded my-2",
            getSelection: () => this.dependencies.selection.getSelectionData(),
            focusEditable: () => this.dependencies.selection.focusEditable(),
            state: this.state,
        };
    }

    destroy() {
        this.debouncedUpdateToolbar.cancel();
        this.updateToolbar.cancel();
        this.overlay.close();
        super.destroy();
    }

    /**
     * @returns {ToolbarButton[]}
     */
    getButtons() {
        /** @type {ToolbarItem[]} */
        const toolbarItems = this.getResource("toolbar_items");

        /** @type {(item: ToolbarCommandItem) => ToolbarCommandButton} */
        const commandItemToButton = (item) => {
            const command = this.dependencies.userCommand.getCommand(item.commandId);
            return composeToolbarButton(command, item);
        };
        /** @type {(item: ToolbarComponentItem) => ToolbarComponentButton} */
        const componentItemToButton = (item) => ({
            isAvailable: () => true,
            ...item,
            description:
                item.description instanceof Function ? item.description : () => item.description,
        });

        return toolbarItems.map((item) =>
            "Component" in item ? componentItemToButton(item) : commandItemToButton(item)
        );
    }

    getButtonGroups() {
        const buttons = this.getButtons();
        /** @type {ToolbarGroup[]} */
        const groups = this.getResource("toolbar_groups");

        return groups.map((group) => ({
            ...omit(group, "namespaces"),
            buttons: buttons
                .filter((button) => button.groupId === group.id)
                .map((button) => ({
                    ...button,
                    namespaces: button.namespaces || group.namespaces || ["expanded"],
                })),
        }));
    }

    /**
     * @returns {Object<string, ToolbarButton[]>}
     */
    getButtonsByNamespace() {
        const namespaces = this.getResource("toolbar_namespaces").map((ns) => ns.id);
        const buttonsByNamespace = {};
        for (const namespace of namespaces) {
            buttonsByNamespace[namespace] = this.buttonGroups.flatMap((group) =>
                group.buttons.filter((btn) => btn.namespaces.includes(namespace))
            );
        }
        return buttonsByNamespace;
    }

    getToolbarInfo() {
        return {
            buttonGroups: this.buttonGroups,
        };
    }

    handleSelectionChange(selectionData) {
        if (this.onSelectionChangeActive) {
            this.updateToolbar(selectionData);
        }
    }

    /**
     * Different handlers might call updateToolbar (e.g. step added and
     * selection change) in the same tick. To avoid unnecessary updates, we
     * batch the calls.
     */
    updateToolbar = debounce(this._updateToolbar, 0, { trailing: true });
    _updateToolbar(selectionData = this.dependencies.selection.getSelectionData()) {
        const targetedNodes = this.getFilteredTargetedNodes();
        this.updateNamespace(targetedNodes);
        this.updateToolbarVisibility(selectionData, targetedNodes);
        if (!this.overlay.isOpen) {
            return;
        }
        this.updateButtonsStates(selectionData.editableSelection, targetedNodes);
    }

    getFilteredTargetedNodes() {
        return this.dependencies.selection
            .getTargetedNodes()
            .filter(
                (node) =>
                    this.dependencies.selection.isNodeEditable(node) &&
                    (node.nodeType !== Node.TEXT_NODE ||
                        (node.textContent.trim().length && !isZWS(node)))
            );
    }

    updateToolbarVisibility(selectionData, targetedNodes) {
        if (this.shouldBeVisible(selectionData, targetedNodes)) {
            // Do not reposition the toolbar if it's already open.
            if (!this.overlay.isOpen) {
                this.overlay.open({ props: this.toolbarProps });
            }
        } else if (this.overlay.isOpen && !this.shouldPreventClosing()) {
            this.closeToolbar();
        }
    }

    shouldBeVisible(selectionData, targetedNodes) {
        const inEditable =
            selectionData.currentSelectionIsInEditable &&
            !selectionData.documentSelectionIsProtected &&
            !selectionData.documentSelectionIsProtecting;
        if (!inEditable) {
            return false;
        }
        const canDisplayToolbar = this.getResource("can_display_toolbar").every((fn) =>
            fn(this.state.namespace)
        );
        if (!canDisplayToolbar) {
            return false;
        }
        if (this.isMobileToolbar) {
            return true;
        }
        const isCollapsed = selectionData.editableSelection.isCollapsed;
        if (isCollapsed) {
            return this.getResource("collapsed_selection_toolbar_predicate").some((fn) =>
                fn(selectionData)
            );
        }
        return !!targetedNodes.length;
    }

    shouldPreventClosing() {
        const anchorNode = document.getSelection()?.anchorNode;
        return anchorNode && this.overlay.overlayContainsElement(anchorNode);
    }

    updateNamespace(targetedNodes) {
        const namespaces = this.getResource("toolbar_namespaces");
        const activeNamespace = namespaces.find((ns) => ns.isApplied(targetedNodes));
        this.state.namespace = activeNamespace?.id;
    }

    /**
     * @param {EditorSelection} selection
     * @param {Node[]} targetedNodes
     */
    updateButtonsStates(selection, targetedNodes) {
        const availableButtons = this.getAvailableButtonsSet(selection);
        const buttonGroups = this.buttonGroups
            .map((group) => ({
                id: group.id,
                buttons: group.buttons
                    .filter((button) => availableButtons.has(button))
                    .map((button) => ({
                        id: button.id,
                        description: button.description(selection, targetedNodes),
                        isDisabled: !!button.isDisabled?.(selection, targetedNodes),
                        ...(button.Component
                            ? pick(button, "Component", "props")
                            : {
                                  ...pick(button, "run", "icon", "text"),
                                  isActive: !!button.isActive?.(selection, targetedNodes),
                              }),
                    })),
            }))
            // Filter out groups left empty
            .filter((group) => group.buttons.length > 0);

        this.state.buttonGroups = buttonGroups;
    }

    /**
     * Get the set of available buttons for the current namespace and selection.
     *
     * @param {EditorSelection} selection
     * @returns {Set<ToolbarButton>}
     */
    getAvailableButtonsSet(selection) {
        if (this.state.namespace === "compact") {
            return this.getAvailableButtonsCompact(selection);
        }
        const isAvailable = (button) => button.isAvailable(selection);
        return new Set(this.buttonsByNamespace[this.state.namespace].filter(isAvailable));
    }

    /**
     * We only display the toolbar in its compact form if the expanded form is
     * larger than a threshold, and larger than the compact version itself.
     * Otherwise, we display the expanded toolbar directly.
     *
     * @param {EditorSelection} selection
     * @returns {Set<ToolbarButton>}
     */
    getAvailableButtonsCompact(selection) {
        const isAvailable = memoize((button) => button.isAvailable(selection));
        const compact = this.buttonsByNamespace["compact"].filter(isAvailable);
        const expanded = this.buttonsByNamespace["expanded"].filter(isAvailable);
        const shouldDisplayCompactToolbar =
            // Expanded version is big enough
            expanded.length >= MIN_SIZE_FOR_COMPACT &&
            // Expanded version is bigger than the compact version
            expanded.length > compact.length;
        if (shouldDisplayCompactToolbar) {
            return new Set(compact);
        }
        this.state.namespace = "expanded";
        return new Set(expanded);
    }

    closeToolbar() {
        this.overlay.close();
        this.isToolbarExpanded = false;
    }
}

class MobileToolbarOverlay {
    constructor(editable) {
        this.isOpen = false;
        this.overlayId = `mobile_toolbar_${Math.random().toString(16).slice(2)}`;
        this.editable = editable;
    }

    open({ props }) {
        props.class = "shadow";
        if (!this.isOpen) {
            const modal = this.editable.closest(".o_modal_full");
            if (modal) {
                // Same height of the toolbar
                modal.style.paddingBottom = "40px";
            }
            registry.category("main_components").add(this.overlayId, {
                Component: ToolbarMobile,
                props,
            });
            this.isOpen = true;
        }
    }

    close() {
        const modal = this.editable.closest(".o_modal_full");
        if (modal) {
            modal.style.paddingBottom = "";
        }
        registry.category("main_components").remove(this.overlayId, "MobileToolbar");
        this.isOpen = false;
    }
}
