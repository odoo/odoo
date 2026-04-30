import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class EditableButtonPlugin extends Plugin {
    static id = "editableButton";
    resources = {
        normalize_handlers: this.wrapEditableButtons.bind(this),
    };

    /**
     * Buttons with `contenteditable="true"` cannot receive spaces because the
     * browser natively triggers a click on them when the space key is pressed.
     * To work around this, we listen to the keydown event on those buttons and
     * insert a non-breaking space when the space key is pressed.
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

            const onKeyDown = (ev) => {
                const isSpace = ev.key === ' ' || ev.key === 'Spacebar' || ev.keyCode === 32;
                if (!isSpace) {
                    return;
                }
                if (ev.shiftKey || ev.altKey || ev.ctrlKey || ev.metaKey) {
                    return;
                }
                ev.preventDefault();
                ev.stopPropagation();
                try {
                    const doc = root.ownerDocument || document;
                    let sel = doc.getSelection();
                    if (!sel) {
                        return;
                    }
                    if (sel.rangeCount === 0) {
                        const range = doc.createRange();
                        range.selectNodeContents(button);
                        range.collapse(false);
                        sel.removeAllRanges();
                        sel.addRange(range);
                    }
                    const range = sel.getRangeAt(0);
                    range.deleteContents();
                    const textNode = doc.createTextNode('\u00A0');
                    range.insertNode(textNode);
                    range.setStartAfter(textNode);
                    range.collapse(true);
                    sel.removeAllRanges();
                    sel.addRange(range);
                } catch {
                    // ignore
                }
            };
            button.addEventListener('keydown', onKeyDown);
        }
    }
}

registry.category("website-plugins").add(EditableButtonPlugin.id, EditableButtonPlugin);
