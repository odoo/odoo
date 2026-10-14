import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class OdooLinkSelectionPlugin extends Plugin {
    static id = "odooLinkSelection";
    /** @type {import("plugins").EditorResources} */
    resources = {
        properties: {
            predicate: (link) =>
                selectElements(link, "*").some((el) => el.nodeName === "IMG" || isBlock(el)),
            feff: false,
        },
    };
}
