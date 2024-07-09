import { Plugin } from "../plugin";

export class InsertTextPlugin extends Plugin {
    static name = "insertText";
    static dependencies = ["selection"];
    static resources = (p) => ({
        onBeforeInput: p.onBeforeInput.bind(p),
    });

    onBeforeInput(ev) {
        if (ev.inputType === "insertText") {
            const selection = this.shared.getEditableSelection();
            if (!selection.isCollapsed) {
                this.dispatch("DELETE_SELECTION");
            }
            // Default behavior: insert text and trigger input event
        }
    }
}
