import { Plugin } from "@html_editor/plugin";
import { isZWS } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { isTextNode } from "@web/views/view_compiler";
import { composeToolbarButton, Toolbar } from "./toolbar";
import { hasTouch } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { ToolbarMobile } from "./mobile_toolbar";
import { debounce } from "@web/core/utils/timing";
import { omit } from "@web/core/utils/objects";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

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
 * @property {TranslatedString} description
 * @property {Function} run
 * @property {string} [icon]
 * @property {string} [text]
 * @property {(selection: EditorSelection) => boolean} [isAvailable]
 * @property {(selection: EditorSelection, nodes: Node[]) => boolean} [isActive]
 * @property {(selection: EditorSelection, nodes: Node[]) => boolean} [isDisabled]
 *
 * @typedef {ToolbarComponentItem} ToolbarComponentButton
 */

/** Delay in ms for toolbar open after keyup, double click or triple click. */
const DELAY_TOOLBAR_OPEN = 300;

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
        toolbar_namespaces: withSequence(100, {
            id: "compact",
            isApplied: () => !this.isToolbarExpanded,
        }),
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
        this.state = reactive({
            buttonsActiveState: this.buttonGroups.flatMap((g) =>
                g.buttons.map((b) => [b.id, false])
            ),
            buttonsDisabledState: this.buttonGroups.flatMap((g) =>
                g.buttons.map((b) => [b.id, false])
            ),
            buttonsAvailableState: this.buttonGroups.flatMap((g) =>
                g.buttons.map((b) => [b.id, true])
            ),
            buttonsTitleState: this.buttonGroups.flatMap((g) => g.buttons.map((b) => [b.id, ""])),
            namespace: undefined,
        });
        this.updateSelection = null;

        this.onSelectionChangeActive = true;
        this.debouncedUpdateToolbar = debounce(this.updateToolbar, DELAY_TOOLBAR_OPEN);

        if (this.isMobileToolbar) {
            this.addDomListener(this.editable, "pointerup", () => {
                // Collapse toolbar to compact mode when tapping outside of it
                this.isToolbarExpanded = false;
            });
        } else {
            // Mouse interaction behavior:
            // Close toolbar on mousedown and prevent it from opening until mouseup.
            this.addDomListener(this.editable, "mousedown", () => {
                this.overlay.close();
                this.debouncedUpdateToolbar.cancel();
                this.onSelectionChangeActive = false;
            });
            this.addDomListener(this.document, "mouseup", (ev) => {
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
                if (ev.key.startsWith("Arrow")) {
                    this.overlay.close();
                    this.onSelectionChangeActive = false;
                }
            });
            this.addDomListener(this.editable, "keyup", (ev) => {
                if (ev.key.startsWith("Arrow")) {
                    this.onSelectionChangeActive = true;
                    this.debouncedUpdateToolbar();
                }
            });
        }
        this.isToolbarExpanded = false;
    }

    destroy() {
        this.debouncedUpdateToolbar.cancel();
        this.overlay.close();
        super.destroy();
    }

    /**
     * @returns {(ToolbarCommandButton| ToolbarComponentButton)[]}
     */
    getButtons() {
        /** @type {ToolbarItem[]} */
        const toolbarItems = this.getResource("toolbar_items");

        /** @returns {ToolbarCommandButton} */
        const commandItemToButton = (/** @type {ToolbarCommandItem}*/ item) => {
            const command = this.dependencies.userCommand.getCommand(item.commandId);
            return composeToolbarButton(command, item);
        };

        return toolbarItems.map((item) => ("Component" in item ? item : commandItemToButton(item)));
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

    getToolbarInfo() {
        return {
            buttonGroups: this.buttonGroups,
            getSelection: () => this.dependencies.selection.getSelectionData(),
            state: this.state,
            focusEditable: () => this.dependencies.selection.focusEditable(),
        };
    }

    handleSelectionChange(selectionData) {
        if (this.onSelectionChangeActive) {
            this.updateToolbar(selectionData);
        }
    }

    updateToolbar(selectionData = this.dependencies.selection.getSelectionData()) {
        this.updateToolbarVisibility(selectionData);
        if (this.overlay.isOpen || this.config.disableFloatingToolbar) {
            this.updateNamespace();
            this.updateButtonsStates(selectionData.editableSelection);
        }
    }

    /**
     * @deprecated
     */
    getFilterTraverseNodes() {
        return this.getFilteredTargetedNodes();
    }

    getFilteredTargetedNodes() {
        return this.dependencies.selection
            .getTargetedNodes()
            .filter(
                (node) => !isTextNode(node) || (node.textContent.trim().length && !isZWS(node))
            );
    }

    updateToolbarVisibility(selectionData) {
        if (this.config.disableFloatingToolbar) {
            return;
        }

        if (this.shouldBeVisible(selectionData)) {
            // Open toolbar or update its position
            const props = { toolbar: this.getToolbarInfo(), class: "shadow rounded my-2" };
            if (!this.overlay.isOpen) {
                // Open toolbar in compact mode
                this.isToolbarExpanded = false;
            }
            this.overlay.open({ props });
        } else if (this.overlay.isOpen && !this.shouldPreventClosing(selectionData)) {
            // Close toolbar
            this.overlay.close();
        }
    }

    shouldBeVisible(selectionData) {
        const inEditable =
            selectionData.documentSelectionIsInEditable &&
            !selectionData.documentSelectionIsProtected &&
            !selectionData.documentSelectionIsProtecting;
        if (!inEditable) {
            return false;
        }
        if (this.isMobileToolbar) {
            return true;
        }
        const isCollapsed = selectionData.editableSelection.isCollapsed;
        if (isCollapsed) {
            return !!closestElement(selectionData.editableSelection.anchorNode, "td.o_selected_td");
        }
        return this.getFilteredTargetedNodes().length;
    }

    shouldPreventClosing(selectionData) {
        const preventClosing = selectionData.documentSelection?.anchorNode?.closest?.(
            "[data-prevent-closing-overlay]"
        );
        return preventClosing?.dataset?.preventClosingOverlay === "true";
    }

    updateNamespace() {
        const targetedNodes = this.getFilteredTargetedNodes();
        const namespaces = this.getResource("toolbar_namespaces");
        const activeNamespace = namespaces.find((ns) => ns.isApplied(targetedNodes));
        this.state.namespace = activeNamespace?.id || "expanded";
    }

    updateButtonsStates(selection) {
        if (!this.updateSelection) {
            queueMicrotask(() => {
                if (!this.isDestroyed) {
                    this._updateButtonsStates();
                }
            });
        }
        this.updateSelection = selection;
    }
    _updateButtonsStates() {
        const selection = this.updateSelection;
        if (!selection) {
            return;
        }
        const nodes = this.getFilteredTargetedNodes();
        for (const buttonGroup of this.buttonGroups) {
            for (const button of buttonGroup.buttons) {
                if (!button.namespaces.includes(this.state.namespace)) {
                    continue;
                }
                this.state.buttonsActiveState[button.id] = button.isActive?.(selection, nodes);
                this.state.buttonsDisabledState[button.id] = button.isDisabled?.(selection, nodes);
                this.state.buttonsAvailableState[button.id] =
                    button.isAvailable === undefined || button.isAvailable(selection);
                this.state.buttonsTitleState[button.id] =
                    button.description instanceof Function
                        ? button.description(selection, nodes)
                        : button.description;
            }
        }
        this.updateSelection = null;
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
