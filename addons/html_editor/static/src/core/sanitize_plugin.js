import { selectElements } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";

/**
 * @typedef { Object } SanitizeShared
 * @property { SanitizePlugin['sanitize'] } sanitize
 */

export class SanitizePlugin extends Plugin {
    static id = "sanitize";
    static shared = ["sanitize"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),
    };

    setup() {
        if (!window.DOMPurify) {
            throw new Error("DOMPurify is not available");
        }
        this.DOMPurify = DOMPurify(this.window);
    }
    /**
     * Sanitizes in place an html element. Current implementation uses the
     * DOMPurify library.
     *
     * @param {HTMLElement} elem
     * @returns {HTMLElement} the element itself
     */
    sanitize(elem) {
        return this.DOMPurify.sanitize(elem, {
            IN_PLACE: true,
            ADD_TAGS: ["#document-fragment", "fake-el"],
            ADD_ATTR: ["contenteditable", "t-field", "t-out", "t-esc"],
        });
    }

    normalize(element) {
        for (const el of selectElements(
            element,
            ".o-contenteditable-false, .o-contenteditable-true"
        )) {
            el.contentEditable = el.matches(".o-contenteditable-true");
        }
        for (const el of selectElements(element, "[data-oe-role]")) {
            el.setAttribute("role", el.dataset.oeRole);
        }
        for (const el of selectElements(element, "[data-oe-aria-label]")) {
            el.setAttribute("aria-label", el.dataset.oeAriaLabel);
        }
    }

    /**
     * Ensure that attributes sanitized by the server are properly removed before
     * the save, to avoid mismatches and a reset of the editable content.
     * Only attributes under the responsibility (associated with an editor
     * attribute or class) of the sanitize plugin are removed.
     *
     * /!\ CAUTION: using server-sanitized attributes without editor-specific
     * classes/attributes in a custom plugin should be managed by that same
     * custom plugin.
     */
    cleanForSave({ root }) {
        for (const el of selectElements(
            root,
            ".o-contenteditable-false, .o-contenteditable-true"
        )) {
            el.removeAttribute("contenteditable");
        }
        for (const el of selectElements(root, "[data-oe-role]")) {
            el.removeAttribute("role");
        }
        for (const el of selectElements(root, "[data-oe-aria-label]")) {
            el.removeAttribute("aria-label");
        }
    }
}
