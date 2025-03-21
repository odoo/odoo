import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ButtonOptionPlugin extends Plugin {
    static id = "buttonOption";
    resources = {
        on_clone_handlers: this.onClone.bind(this),
        on_add_element_handlers: this.onAddElement.bind(this),
    };

    onClone({ cloneEl }) {
        if (cloneEl.matches("a.btn[data-snippet='s_button']")) {
            this.adaptButtons(cloneEl, false);
        }
    }

    onAddElement({ elementToAdd }) {
        if (elementToAdd.matches("a.btn[data-snippet='s_button']")) {
            this.adaptButtons(elementToAdd);
        }
    }

    /**
     * Checks if there are buttons before or after the target element and
     * applies appropriate styling.
     *
     * @private
     * @param {Boolean} [adaptAppearance=true]
     */
    adaptButtons(editingElement, adaptAppearance = true) {
        const previousSiblingEl = editingElement.previousElementSibling;
        const nextSiblingEl = editingElement.nextElementSibling;
        let siblingButtonEl = null;
        // When multiple buttons follow each other, they may break on 2 lines or
        // more on mobile, so they need a margin-bottom. Also, if the button is
        // dropped next to another button add a space between them.
        if (nextSiblingEl?.matches(".btn")) {
            nextSiblingEl.classList.add("mb-2");
            editingElement.after(" ");
            // It is first the next button that we put in this variable because
            // we want to copy as a priority the style of the previous button
            // if it exists.
            siblingButtonEl = nextSiblingEl;
        }
        if (previousSiblingEl?.matches(".btn")) {
            previousSiblingEl.classList.add("mb-2");
            editingElement.before(" ");
            siblingButtonEl = previousSiblingEl;
        }
        if (siblingButtonEl) {
            editingElement.classList.add("mb-2");
        }
        if (adaptAppearance) {
            if (siblingButtonEl && !editingElement.matches(".s_custom_button")) {
                // If the dropped button is not a custom button then we adjust
                // its appearance to match its sibling.
                // TODO: this should aligh with html_editor
                if (siblingButtonEl.classList.contains("btn-secondary")) {
                    editingElement.classList.remove("btn-primary");
                    editingElement.classList.add("btn-secondary");
                }
                if (siblingButtonEl.classList.contains("btn-fill-secondary")) {
                    editingElement.classList.remove("btn-primary");
                    editingElement.classList.add("btn-fill-secondary");
                }
                if (siblingButtonEl.classList.contains("btn-fill-primary")) {
                    editingElement.classList.remove("btn-primary");
                    editingElement.classList.add("btn-fill-primary");
                }
                if (siblingButtonEl.classList.contains("rounded-circle")) {
                    editingElement.classList.add("rounded-circle");
                }
                if (siblingButtonEl.classList.contains("btn-sm")) {
                    editingElement.classList.add("btn-sm");
                } else if (siblingButtonEl.classList.contains("btn-lg")) {
                    editingElement.classList.add("btn-lg");
                }
            } else {
                // To align with the editor's behavior, we need to enclose the
                // button in a <p> tag if it's not dropped within a <p> tag. We only
                // put the dropped button in a <p> if it's not next to another
                // button, because some snippets have buttons that aren't inside a
                // <p> (e.g. s_text_cover).
                // TODO: this definitely needs to be fixed at web_editor level.
                // Nothing should prevent adding buttons outside of a paragraph.
                const btnContainerEl = editingElement.closest("p");
                if (!btnContainerEl) {
                    const paragraphEl = document.createElement("p");
                    editingElement.parentNode.insertBefore(paragraphEl, editingElement);
                    paragraphEl.appendChild(editingElement);
                }
            }
            editingElement.classList.remove("s_custom_button");
        }
    }
}

registry.category("website-plugins").add(ButtonOptionPlugin.id, ButtonOptionPlugin);
