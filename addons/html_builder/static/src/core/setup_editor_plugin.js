import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";

export class SetupEditorPlugin extends Plugin {
    static id = "setup_editor_plugin";
    static shared = ["getEditableAreas"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: withSequence(0, this.setContenteditable.bind(this)),
    };

    setup() {
        const welcomeMessageEl = this.editable.querySelector(
            "#wrap .o_homepage_editor_welcome_message"
        );
        welcomeMessageEl?.remove();
        this.editable.setAttribute("contenteditable", false);
        if (this.delegateTo("after_setup_editor_handlers")) {
            return;
        }
        // Add the `o_editable` class on the editable elements
        let editableEls = this.getEditableElements("[data-oe-model]")
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
        editableEls.concat(Array.from(this.editable.querySelectorAll(".o_editable")));
        editableEls.forEach((el) => el.classList.add("o_editable"));

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
                const parent = el.closest(".o_editable, .o_not_editable");
                return !parent || parent.matches(".o_editable");
            });
        return editableEls;
    }

    cleanForSave({ root }) {
        root.classList.remove("o_editable");
        root.querySelectorAll(".o_editable").forEach((el) => {
            el.classList.remove("o_editable");
        });

        [root, ...root.querySelectorAll("[data-editor-message]")].forEach((el) => {
            el.removeAttribute("data-editor-message");
            el.removeAttribute("data-editor-message-default");
        });

        [root, ...root.querySelectorAll("[contenteditable]")].forEach((el) =>
            el.removeAttribute("contenteditable")
        );
    }

    setContenteditable(root = this.editable) {
        // TODO: Should be imp, we need to check _getReadOnlyAreas etc
        const editableEls = this.getEditableElements(".o_editable");
        editableEls.forEach((el) =>
            el.setAttribute("contenteditable", !el.matches(":empty:not([placeholder])"))
        );

        const uneditableEls = root.querySelectorAll(".o_not_editable");
        uneditableEls.forEach((el) => el.setAttribute("contenteditable", false));
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
        const editablesAreaEls = [...editableEl.querySelectorAll(".o_editable")];
        if (editableEl.matches(".o_editable")) {
            editablesAreaEls.unshift(editableEl);
        }
        return editablesAreaEls;
    }
}
