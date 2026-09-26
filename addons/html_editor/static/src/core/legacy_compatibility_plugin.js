import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class LegacyCompatibilityPlugin extends Plugin {
    static id = "legacyCompatibility";
    /** @type {import("plugins").EditorResources} */
    resources = {
        html_compatibility_processors: this.renameLastHistorySteps.bind(this),
    };

    /**
     * Rename all `data-last-history-steps` attributes to
     * `data-last-history-commits` to ensure compatibility with the old naming.
     *
     * @param {HTMLElement} root
     */
    renameLastHistorySteps(root) {
        const OLD_NAME = "data-last-history-steps";
        const NEW_NAME = "data-last-history-commits";
        for (const element of selectElements(root, `[${OLD_NAME}]`)) {
            element.setAttribute(NEW_NAME, element.getAttribute(OLD_NAME));
            element.removeAttribute(OLD_NAME);
        }
        return root;
    }
}
