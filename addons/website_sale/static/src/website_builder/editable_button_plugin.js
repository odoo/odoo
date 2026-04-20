import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class EditableButtonPlugin extends Plugin {
    static id = "editableButton";
    resources = {
        normalize_processors: this.wrapEditableButtons.bind(this),
    };

    /**
     * Buttons with `contenteditable="true"` cannot receive spaces because the
     * browser natively triggers a click on them when the space key is pressed.
     * To work around this, we move the `contenteditable` attribute up to a
     * wrapping <span>, allowing text editing (including spaces) to work
     * correctly without triggering the button's click handler.
     */
    wrapEditableButtons(root) {
        const editableButtons = root.querySelectorAll("button.o_savable[contenteditable='true']");
        for (const button of editableButtons) {
            const parent = button.parentElement;
            const isOnlyChildOfEditableParent =
                parent.childNodes.length === 1 && parent.getAttribute("contenteditable") === "true";

            if (isOnlyChildOfEditableParent) {
                continue;
            }

            const span = this.document.createElement("span");
            span.setAttribute("contenteditable", "true");
            button.removeAttribute("contenteditable");
            button.after(span);
            span.append(button);
        }
    }
}

registry.category("website-plugins").add(EditableButtonPlugin.id, EditableButtonPlugin);
