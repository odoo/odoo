import { Plugin } from "@html_editor/plugin";
import { isZWS } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { isTextNode } from "@web/views/view_compiler";
import { Toolbar } from "./toolbar";
import { hasTouch } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { ToolbarMobile } from "./mobile_toolbar";

export class ToolbarPlugin extends Plugin {
    static name = "toolbar";
    static dependencies = ["overlay", "selection"];
    static shared = ["getToolbarInfo"];
    /** @type { (p: ToolbarPlugin) => Record<string, any> } */
    static resources = (p) => ({
        onSelectionChange: p.handleSelectionChange.bind(p),
    });

    setup() {
        const categoryIds = new Set();
        for (const category of this.resources.toolbarCategory) {
            if (categoryIds.has(category.id)) {
                throw new Error(`Duplicate toolbar category id: ${category.id}`);
            }
            categoryIds.add(category.id);
        }
        this.categories = this.resources.toolbarCategory.sort((a, b) => a.sequence - b.sequence);
        this.buttonGroups = [];
        for (const category of this.categories) {
            this.buttonGroups.push({
                ...category,
                buttons: this.resources.toolbarItems.filter(
                    (command) => command.category === category.id
                ),
            });
        }
        this.buttonsDict = Object.assign(
            {},
            ...this.resources.toolbarItems.map((button) => ({ [button.id]: button }))
        );
        this.isMobileToolbar = hasTouch() && window.visualViewport;

        if (this.isMobileToolbar) {
            this.overlay = new MobileToolbarOverlay(this.editable);
        } else {
            this.overlay = this.shared.createOverlay(Toolbar, { position: "top-start" });
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

        for (const button of Object.values(this.buttonsDict)) {
            this.resolveButtonInheritance(button.id);
        }
    }

    destroy() {
        super.destroy();
        this.overlay.close();
    }

    /**
     * Resolves the inheritance of a button.
     *
     * Copies the properties of the parent button to the child button.
     *
     * @param {string} buttonId - The id of the button to resolve inheritance for.
     * @throws {Error} If the inheritance button is not found.
     */
    resolveButtonInheritance(buttonId) {
        const button = this.buttonsDict[buttonId];
        if (button.inherit) {
            const parentButton = this.buttonsDict[button.inherit];
            if (!parentButton) {
                throw new Error(`Inheritance button ${button.inherit} not found`);
            }
            Object.assign(button, { ...parentButton, ...button });
        }
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CONTENT_UPDATED":
                if (this.overlay.isOpen) {
                    const selectionData = this.shared.getSelectionData();
                    if (selectionData.editableSelection.isCollapsed && !this.isMobileToolbar) {
                        this.overlay.close();
                    } else {
                        this.updateButtonsStates(selectionData.editableSelection);
                    }
                }
                break;
        }
    }

    getToolbarInfo() {
        return {
            dispatch: this.dispatch,
            buttonGroups: this.buttonGroups,
            getSelection: () => this.shared.getEditableSelection(),
            state: this.state,
        };
    }

    handleSelectionChange(selectionData) {
        this.updateToolbarVisibility(selectionData);
        if (this.overlay.isOpen || this.config.disableFloatingToolbar) {
            const selectedNodes = this.shared.getTraversedNodes();
            let foundNamespace = false;
            for (let i = 0; i < this.resources.toolbarNamespace.length && !foundNamespace; i++) {
                const namespace = this.resources.toolbarNamespace[i];
                if (namespace.isApplied(selectedNodes)) {
                    this.state.namespace = namespace.id;
                    foundNamespace = true;
                }
            }
            if (!foundNamespace) {
                this.state.namespace = undefined;
            }
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
        const props = { toolbar: this.getToolbarInfo(), class: "shadow rounded my-2" };

        const inEditable =
            selectionData.documentSelectionIsInEditable &&
            !selectionData.documentSelectionIsProtected &&
            !selectionData.documentSelectionIsProtecting;
        const isCollapsed = selectionData.editableSelection.isCollapsed;

        if (this.overlay.isOpen) {
            if (
                !inEditable ||
                ((isCollapsed || !this.getFilterTraverseNodes().length) && !this.isMobileToolbar)
            ) {
                const preventClosing = selectionData.documentSelection?.anchorNode?.closest?.(
                    "[data-prevent-closing-overlay]"
                );
                if (preventClosing?.dataset?.preventClosingOverlay === "true") {
                    return;
                }
                this.overlay.close();
            } else {
                this.overlay.open({ props }); // will update position
            }
        } else if (inEditable && (!isCollapsed || this.isMobileToolbar)) {
            this.overlay.open({ props });
        }
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
