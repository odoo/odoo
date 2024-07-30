import { boundariesIn } from "@html_editor/utils/position";
import { Plugin } from "../plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";

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
            } else {
                const element = closestElement(selection.anchorNode);
                if (element.hasAttribute("data-oe-zws-empty-inline")) {
                    // Select its ZWS content to make sure the text will be
                    // inserted inside the element, and not before (outside) it.
                    // This addresses an undesired behavior of the
                    // contenteditable.
                    const [anchorNode, anchorOffset, focusNode, focusOffset] =
                        boundariesIn(element);
                    this.shared.setSelection({ anchorNode, anchorOffset, focusNode, focusOffset });
                }
            }
            // Default behavior: insert text and trigger input event
        }
    }
}
