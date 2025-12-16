import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class OdooLinkSelectionPlugin extends Plugin {
    static id = "odooLinkSelection";
    /** @type {import("plugins").EditorResources} */
    resources = {
        ineligible_link_for_zwnbsp_predicates: [
            (link) => selectElements(link, "*").some((el) => el.nodeName === "IMG" || isBlock(el)),
        ],
        ineligible_link_for_selection_indication_predicates: (link) => link.matches(".btn"),
    };
}
