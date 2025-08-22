import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const selector = "a.btn";
const exclude = ".s_donation_donate_btn, .s_website_form_send";

const styleClasses = [
    "btn-secondary",
    "btn-fill-primary",
    "btn-fill-secondary",
    "btn-outline-primary",
    "btn-outline-secondary",
];
const sizeClasses = ["btn-sm", "btn-lg"];

class ButtonOptionPlugin extends Plugin {
    static id = "buttonOption";
    resources = {
        on_cloned_handlers: this.onCloned.bind(this),
        // Drag and drop from sidebar: manage the button preview.
        on_snippet_over_dropzone_handlers: this.onSnippetPreview.bind(this),
        on_snippet_out_dropzone_handlers: ({ snippetEl, dragState }) =>
            this.resetPreview(snippetEl, dragState),
        on_snippet_dropped_over_handlers: ({ droppedEl, dragState }) =>
            this.resetPreview(droppedEl, dragState),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    onCloned({ cloneEl }) {
        if (cloneEl.matches(selector) && !cloneEl.matches(exclude)) {
            this.adaptButtons(cloneEl, { adaptAppearance: false });
        }
    }

    /**
     * Adapts the dragged "Button" snippet when it is over a dropzone, in order
     * to preview it correctly.
     *
     * @param {Object} - snippetEl: the dragged snippet
     *                 - dragState: the current drag state
     */
    onSnippetPreview({ snippetEl, dragState }) {
        if (snippetEl.matches(selector) && !snippetEl.matches(exclude)) {
            const dropzoneEl = dragState.currentDropzoneEl;
            // No need to preview if it is a grid item, as it is alone.
            if (dropzoneEl.classList.contains("oe_grid_zone")) {
                return;
            }

            // Preview the button.
            const initialState = this.adaptButtons(snippetEl, { isDragAndDropPreview: true });
            // Store the restore function to undo the preview.
            dragState.restoreButtonPreview = () => {
                const { isWrapped, previousClassName, nextClassName } = initialState;
                // Restore the classes and remove the added spaces.
                snippetEl.className = initialState.buttonClassName;
                if (previousClassName) {
                    initialState.previousSiblingEl.className = previousClassName;
                    snippetEl.previousSibling.remove();
                }
                if (nextClassName) {
                    initialState.nextSiblingEl.className = nextClassName;
                    snippetEl.nextSibling.remove();
                }
                // Unwrap the button.
                if (isWrapped) {
                    const wrapperEl = snippetEl.parentElement;
                    dropzoneEl.after(snippetEl);
                    wrapperEl.remove();
                }
            };
        }
    }

    /**
     * Resets the "Button" snippet drag and drop preview.
     *
     * @param {HTMLElement} snippetEl the snippet
     * @param {Object} dragState the current drag state
     */
    resetPreview(snippetEl, dragState) {
        if (snippetEl.matches(selector) && !snippetEl.matches(exclude)) {
            if ("restoreButtonPreview" in dragState) {
                dragState.restoreButtonPreview();
                delete dragState.restoreButtonPreview;
            }
        }
    }

    /**
     * Adapts the dropped "Button" snippet.
     *
     * @param {Object} - snippetEl: the dropped snippet.
     */
    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(selector) && !snippetEl.matches(exclude)) {
            this.adaptButtons(snippetEl, {});
        }
    }

    /**
     * Checks if there are buttons before or after the target element and
     * applies appropriate styling.
     *
     * @param {HTMLElement} editingElement
     * @param {Object}
     *   - [adaptAppearance=true]
     *   - [isDragAndDropPreview = false]
     * @returns {Object} the info needed to restore the drag and drop preview
     */
    adaptButtons(editingElement, { adaptAppearance = true, isDragAndDropPreview = false }) {
        let previousSiblingEl = editingElement.previousElementSibling;
        let nextSiblingEl = editingElement.nextElementSibling;
        // If we are in the case of a drag and drop preview, ignore the
        // dropzones.
        if (isDragAndDropPreview) {
            while (previousSiblingEl && previousSiblingEl.matches(".oe_drop_zone")) {
                previousSiblingEl = previousSiblingEl.previousElementSibling;
            }
            while (nextSiblingEl && nextSiblingEl.matches(".oe_drop_zone")) {
                nextSiblingEl = nextSiblingEl.nextElementSibling;
            }
        }

        let siblingButtonEl = null;
        const initialState = { buttonClassName: editingElement.className };
        // When multiple buttons follow each other, they may break on 2 lines or
        // more on mobile, so they need a margin-bottom. Also, if the button is
        // dropped next to another button add a space between them.
        if (nextSiblingEl?.matches(".btn")) {
            initialState.nextClassName = nextSiblingEl.className;
            nextSiblingEl.classList.add("mb-2");
            editingElement.after(" ");
            // It is first the next button that we put in this variable because
            // we want to copy as a priority the style of the previous button
            // if it exists.
            siblingButtonEl = nextSiblingEl;
        }
        if (previousSiblingEl?.matches(".btn")) {
            initialState.previousClassName = previousSiblingEl.className;
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
                // TODO this should consider the old option classes (for already
                // existing buttons) + custom ?
                const styleClass = styleClasses.find((c) => siblingButtonEl.classList.contains(c));
                const sizeClass = sizeClasses.find((c) => siblingButtonEl.classList.contains(c));

                if (styleClass) {
                    editingElement.classList.remove("btn-primary");
                    editingElement.classList.add(styleClass);
                }
                if (sizeClass) {
                    editingElement.classList.add(sizeClass);
                }
                if (siblingButtonEl.classList.contains("rounded-circle")) {
                    editingElement.classList.add("rounded-circle");
                }
            } else if (!siblingButtonEl) {
                // To align with the editor's behavior, we need to enclose the
                // button in a <p> tag if it's not dropped within a <p> tag. We
                // only put the dropped button in a <p> if it's not next to
                // another button, because some snippets have buttons that are
                // not inside a <p> (e.g. s_text_cover).
                // TODO: this definitely needs to be fixed at web_editor level.
                // Nothing should prevent adding buttons outside of a paragraph.
                const btnContainerEl = editingElement.closest("p");
                if (!btnContainerEl) {
                    const paragraphEl = document.createElement("p");
                    editingElement.parentNode.insertBefore(paragraphEl, editingElement);
                    paragraphEl.appendChild(editingElement);
                    initialState.isWrapped = true;
                }
            }
            editingElement.classList.remove("s_custom_button");
        }
        return { ...initialState, previousSiblingEl, nextSiblingEl };
    }
}

registry.category("website-plugins").add(ButtonOptionPlugin.id, ButtonOptionPlugin);
