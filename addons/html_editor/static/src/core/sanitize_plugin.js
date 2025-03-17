import { selectElements } from "@html_editor/utils/dom_traversal";
import { Plugin } from "../plugin";

/**
 * @typedef { Object } SanitizeShared
 * @property { SanitizePlugin['sanitize'] } sanitize
 */

export class SanitizePlugin extends Plugin {
    static id = "sanitize";
    static shared = ["sanitize", "restoreSanitizedContentEditable"];
    setup() {
        if (!window.DOMPurify) {
            throw new Error("DOMPurify is not available");
        }
        this.DOMPurify = DOMPurify(this.document.defaultView);
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
            ADD_ATTR: ["contenteditable"],
        });
    }

    restoreSanitizedContentEditable(root) {
        for (const node of selectElements(root, ".o_not_editable, .o_editable")) {
            node.contentEditable = node.matches(".o_editable");
        }
    }
}
