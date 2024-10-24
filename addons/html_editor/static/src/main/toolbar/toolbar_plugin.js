import { Plugin } from "@html_editor/plugin";
import { isZWS } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { isTextNode } from "@web/views/view_compiler";
import { Toolbar } from "./toolbar";
import { hasTouch } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { ToolbarMobile } from "./mobile_toolbar";
import { debounce } from "@web/core/utils/timing";

// Delay in ms for toolbar open after keyup, double click or triple click.
const DELAY_TOOLBAR_OPEN = 300;

export class ToolbarPlugin extends Plugin {
    static name = "toolbar";
    static dependencies = ["overlay", "selection", "user_command"];
    static shared = ["getToolbarInfo"];
    resources = {
        selectionchange_handlers: this.handleSelectionChange.bind(this),
        step_added_handlers: () => this.updateToolbar(),
    };

    setup() {
        const categoryIds = new Set();
        for (const category of this.getResource("toolbarCategory")) {
            if (categoryIds.has(category.id)) {
                throw new Error(`Duplicate toolbar category id: ${category.id}`);
            }
            categoryIds.add(category.id);
        }

        this.buttonGroups = this.getButtonGroups();

        this.isMobileToolbar = hasTouch() && window.visualViewport;

        if (this.isMobileToolbar) {
            this.overlay = new MobileToolbarOverlay(this.editable);
        } else {
            this.overlay = this.shared.createOverlay(Toolbar, {
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
            namespace: undefined,
        });
        this.updateSelection = null;

        this.onSelectionChangeActive = true;
        this.debouncedUpdateToolbar = debounce(this.updateToolbar, DELAY_TOOLBAR_OPEN);

        if (!this.isMobileToolbar) {
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
    }

    destroy() {
        this.debouncedUpdateToolbar.cancel();
        this.overlay.close();
        super.destroy();
    }

    getButtons() {
        const commands = this.shared.getCommands();
        const toolbarItems = this.getResource("toolbarItems");
        const buttons = toolbarItems.map((item) => {
            const command = commands[item.commandId] || {};
            const label = item.label || command.label;
            const isAvailable = item.isAvailable || command.isAvailable;
            const icon = item.icon || command.icon;
            const button = {
                ...item,
            };
            if (label) {
                button.label = label;
            }
            if (isAvailable) {
                button.isAvailable = isAvailable;
            }
            if (icon && !item.Component) {
                button.icon = icon;
            }
            return button;
        });
        const buttonsDict = Object.fromEntries(buttons.map((button) => [button.id, button]));
        const buttonsWithInheritance = buttons.map((button) => {
            if (!button.inherit) {
                return button;
            }
            const parentButton = buttonsDict[button.inherit];
            if (!parentButton) {
                throw new Error(`Inheritance button ${button.inherit} not found`);
            }
            return { ...parentButton, ...button };
        });
        const buttonsWithRun = buttonsWithInheritance.map((button) => {
            if (!button.Component) {
                const { commandId, commandParams } = button;
                button.run = () => this.shared.execCommand(commandId, commandParams);
            }
            delete button.commandId;
            delete button.commandParams;
            return button;
        });

        return buttonsWithRun;
    }

    getButtonGroups() {
        const buttons = this.getButtons();
        const categories = this.getResource("toolbarCategory");

        return categories.map((category) => ({
            ...category,
            buttons: buttons.filter((button) => button.category === category.id),
        }));
    }

    getToolbarInfo() {
        return {
            buttonGroups: this.buttonGroups,
            getSelection: () => this.shared.getEditableSelection(),
            state: this.state,
            focusEditable: () => this.shared.focusEditable(),
        };
    }

    handleSelectionChange(selectionData) {
        if (this.onSelectionChangeActive) {
            this.updateToolbar(selectionData);
        }
    }

    updateToolbar(selectionData = this.shared.getSelectionData()) {
        this.updateToolbarVisibility(selectionData);
        if (this.overlay.isOpen || this.config.disableFloatingToolbar) {
            this.updateNamespace();
            this.updateButtonsStates(selectionData.editableSelection);
        }
    }

    getFilterTraverseNodes() {
        return this.shared
            .getTraversedNodes()
            .filter((node) => !isTextNode(node) || (node.textContent !== "\n" && !isZWS(node)));
    }

    updateToolbarVisibility(selectionData) {
        if (this.config.disableFloatingToolbar) {
            return;
        }

        if (this.shouldBeVisible(selectionData)) {
            // Open toolbar or update its position
            const props = { toolbar: this.getToolbarInfo(), class: "shadow rounded my-2" };
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
        return !isCollapsed && this.getFilterTraverseNodes().length;
    }

    shouldPreventClosing(selectionData) {
        const preventClosing = selectionData.documentSelection?.anchorNode?.closest?.(
            "[data-prevent-closing-overlay]"
        );
        return preventClosing?.dataset?.preventClosingOverlay === "true";
    }

    updateNamespace() {
        const traversedNodes = this.getFilterTraverseNodes();
        for (const namespace of this.getResource("toolbarNamespace") || []) {
            if (namespace.isApplied(traversedNodes)) {
                this.state.namespace = namespace.id;
                return;
            }
        }
        this.state.namespace = undefined;
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
        const nodes = this.getFilterTraverseNodes();
        for (const buttonGroup of this.buttonGroups) {
            if (buttonGroup.namespace === this.state.namespace) {
                for (const button of buttonGroup.buttons) {
                    this.state.buttonsActiveState[button.id] = button.isFormatApplied?.(
                        selection,
                        nodes
                    );
                    this.state.buttonsDisabledState[button.id] =
                        button.hasFormat != null && !button.hasFormat?.(selection);
                    this.state.buttonsAvailableState[button.id] =
                        button.isAvailable === undefined || button.isAvailable(selection);
                }
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
