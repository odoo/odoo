import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { Toolbar } from "./toolbar";

export class ToolbarPlugin extends Plugin {
    static name = "toolbar";
    static dependencies = ["overlay", "selection"];
    static shared = ["getToolbarInfo"];
    /** @type { (p: ToolbarPlugin) => Record<string, any> } */
    static resources = (p) => ({
        onSelectionChange: p.handleSelectionChange.bind(p),
    });

    setup() {
        this.buttonGroups = this.resources.toolbarGroup.sort((a, b) => a.sequence - b.sequence);
        this.overlay = this.shared.createOverlay(Toolbar, { position: "top-start" });
        this.state = reactive({
            buttonsActiveState: this.buttonGroups.flatMap((g) =>
                g.buttons.map((b) => [b.id, false])
            ),
            buttonsDisabledState: this.buttonGroups.flatMap((g) =>
                g.buttons.map((b) => [b.id, false])
            ),
            namespace: undefined,
        });
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CONTENT_UPDATED":
                if (this.overlay.isOpen) {
                    const sel = this.shared.getEditableSelection();
                    if (sel.isCollapsed) {
                        this.overlay.close();
                    }
                    this.updateButtonsStates(this.shared.getEditableSelection());
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

    handleSelectionChange(selection) {
        this.updateToolbarVisibility(selection);
        if (this.overlay.isOpen || this.config.disableFloatingToolbar) {
            const selectedNodes = this.shared.getSelectedNodes();
            if (
                selectedNodes.length &&
                selectedNodes[0].tagName &&
                selectedNodes.every((el) => el.tagName === selectedNodes[0].tagName)
            ) {
                this.state.namespace = selectedNodes[0].tagName;
            } else {
                this.state.namespace = undefined;
            }
            this.updateButtonsStates(selection);
        }
    }

    updateToolbarVisibility(sel) {
        if (this.config.disableFloatingToolbar) {
            return;
        }
        const props = { toolbar: this.getToolbarInfo(), class: "shadow rounded my-2" };

        const inEditable = sel.inEditable;
        if (this.overlay.isOpen) {
            if (!inEditable || sel.isCollapsed) {
                const selection = this.document.getSelection();
                const preventClosing = selection?.anchorNode?.closest?.(
                    "[data-prevent-closing-overlay]"
                );
                if (preventClosing?.dataset?.preventClosingOverlay === "true") {
                    return;
                }
                this.overlay.close();
            } else {
                this.overlay.open({ props }); // will update position
            }
        } else if (inEditable && !sel.isCollapsed) {
            this.overlay.open({ props });
        }
    }

    updateButtonsStates(selection) {
        if (selection.inEditable) {
            for (const buttonGroup of this.buttonGroups) {
                if (buttonGroup.namespace === this.state.namespace) {
                    for (const button of buttonGroup.buttons) {
                        this.state.buttonsActiveState[button.id] =
                            button.isFormatApplied?.(selection);
                        this.state.buttonsDisabledState[button.id] =
                            button.hasFormat != null && !button.hasFormat?.(selection);
                    }
                }
            }
        }
    }
}
