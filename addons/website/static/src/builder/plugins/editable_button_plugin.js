import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

class EditableButtonPlugin extends Plugin {
    static id = "editableButton";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        normalize_processors: this.wrapEditableButtons.bind(this),
        clean_for_save_processors: this.cleanEditableButtons.bind(this),
    };

    /**
     * Buttons with `contenteditable="true"` cannot receive spaces because the
     * browser natively triggers a click on them when the space key is pressed.
     * To work around this, we move the `contenteditable` attribute down to a
     * inner <span>, allowing text editing (including spaces) to work
     * correctly without triggering the button's click handler.
     */
    wrapEditableButtons(root) {
        const editableButtons = selectElements(root, "button[contenteditable='true']");
        for (const button of editableButtons) {
            button.removeAttribute("contenteditable");

            if (button.querySelector(":scope > .o_inner_button_editable_span")) {
                continue;
            }

            const span = this.document.createElement("span");
            span.setAttribute("contenteditable", "true");
            span.classList.add("o_inner_button_editable_span");
            span.append(...button.childNodes);
            button.append(span);
        }
        return root;
    }
    cleanEditableButtons(root) {
        for (const span of root.querySelectorAll(".o_inner_button_editable_span")) {
            unwrapContents(span);
        }
        return root;
    }
}

registry.category("website-plugins").add(EditableButtonPlugin.id, EditableButtonPlugin);
