import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef { Object } SetupEditorShared
 * @property { SetupEditorPlugin['getSavableAreas'] } getSavableAreas
 */

/**
 * @typedef {(() => void | true)[]} after_setup_editor_handlers
 * @typedef {(() => void)[]} before_setup_editor_handlers
 *
 * @typedef {CSSSelector[]} savable_selectors
 */

export class SetupEditorPlugin extends Plugin {
    static id = "setup_editor_plugin";
    static shared = ["getSavableAreas"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        closest_savable_providers: withSequence(10, (el) => el.closest(".o_savable")),
        savable_selectors: "[data-oe-model]",
        unremovable_node_predicates: (node) => node.classList?.contains("o_savable"),
    };

    setup() {
        for (const savableEl of selectElements(this.editable, ".o_editable")) {
            // Remove potential `o_editable` class from elements (that is there
            // due to wrong templates for example).
            savableEl.classList.remove("o_editable");
        }
        const welcomeMessageEl = this.editable.querySelector(
            "#wrap .o_homepage_editor_welcome_message"
        );
        welcomeMessageEl?.remove();
        this.dispatchTo("before_setup_editor_handlers");
        const savableSelectors = this.getResource("savable_selectors").join(", ");
        const savableEls = [...this.editable.querySelectorAll(savableSelectors)]
            .filter((el) => !el.closest(".o_not_editable"))
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
        for (const savableEl of savableEls) {
            savableEl.classList.add("o_savable");
        }
        if (this.delegateTo("after_setup_editor_handlers")) {
            return;
        }

        // Add automatic editor message on the editables where we can drag and
        // drop elements.
        const dragAndDropSavableEls = [
            ...this.editable.querySelectorAll(
                '.o_savable.oe_structure.oe_empty, .o_savable[data-oe-type="html"]'
            ),
        ];
        for (const el of dragAndDropSavableEls) {
            if (!el.hasAttribute("data-editor-message")) {
                el.setAttribute("data-editor-message-default", true);
                el.setAttribute("data-editor-message", _t("DRAG BUILDING BLOCKS HERE"));
            }
        }
    }

    cleanForSave({ root }) {
        for (const savableEl of selectElements(root, ".o_savable")) {
            savableEl.classList.remove("o_savable");
        }

        selectElements(root, "[data-editor-message]").forEach((el) => {
            el.removeAttribute("data-editor-message");
            el.removeAttribute("data-editor-message-default");
        });
    }

    /**
     * Gets all the savable elements contained in the given root element (or the
     * editable if none is specified), including this element.
     *
     * @param {HTMLElement|undefined} rootEl
     * @returns {Array<HTMLElement}
     */
    getSavableAreas(rootEl) {
        const editableEl = rootEl || this.editable;
        return selectElements(editableEl, ".o_savable");
    }
}
