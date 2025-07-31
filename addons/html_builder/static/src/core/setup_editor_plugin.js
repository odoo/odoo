import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";

export class SetupEditorPlugin extends Plugin {
    static id = "setup_editor_plugin";
    static shared = ["getEditableAreas"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        savable_selectors: "[data-oe-model]",
    };

    setup() {
        const welcomeMessageEl = this.editable.querySelector(
            "#wrap .o_homepage_editor_welcome_message"
        );
        welcomeMessageEl?.remove();
        if (this.delegateTo("after_setup_editor_handlers")) {
            return;
        }
        // Add the `o_savable` class on the savable elements
        const savableSelectors = this.getResource("savable_selectors").join(",");
        let editableEls = [...this.editable.querySelectorAll(savableSelectors)]
            .filter((el) => !el.matches("link, script"))
            .filter((el) => !el.hasAttribute("data-oe-readonly"))
            .filter(
                (el) =>
                    !el.matches(
                        'img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]'
                    )
            )
            .filter((el) => !el.classList.contains("oe_snippet_editor"))
            .filter((el) => !el.matches("hr, br, input, textarea"))
            .filter((el) => !el.hasAttribute("data-oe-sanitize-prevent-edition"));
        editableEls.forEach((el) => el.classList.add("o_savable"));

        // Add automatic editor message on the editables where we can drag and
        // drop elements.
        editableEls = this.getEditableElements('.oe_structure.oe_empty, [data-oe-type="html"]');
        editableEls.forEach((el) => {
            if (!el.hasAttribute("data-editor-message")) {
                el.setAttribute("data-editor-message-default", true);
                el.setAttribute("data-editor-message", _t("DRAG BUILDING BLOCKS HERE"));
            }
        });
    }

    getEditableElements(selector) {
        const editableEls = [...this.editable.querySelectorAll(selector)]
            .filter((el) => !el.matches(".o_not_editable"))
            .filter((el) => {
                const parent = el.closest(".o_savable, .o_not_editable");
                return !parent || parent.matches(".o_savable");
            });
        return editableEls;
    }

    cleanForSave({ root }) {
        for (const savableEl of selectElements(root, ".o_savable")) {
            savableEl.classList.remove("o_savable");
        }

        [root, ...root.querySelectorAll("[data-editor-message]")].forEach((el) => {
            el.removeAttribute("data-editor-message");
            el.removeAttribute("data-editor-message-default");
        });
    }

    /**
     * Gets all the editable elements contained in the given root element (or
     * the editable if none is specified), including this element.
     *
     * @param {HTMLElement|undefined} rootEl
     * @returns {Array<HTMLElement}
     */
    getEditableAreas(rootEl) {
        const editableEl = rootEl || this.editable;
        const editablesAreaEls = [...editableEl.querySelectorAll(".o_savable")];
        if (editableEl.matches(".o_savable")) {
            editablesAreaEls.unshift(editableEl);
        }
        return editablesAreaEls;
    }
}
