import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class OdooLinkSelectionPlugin extends Plugin {
    static id = "odooLinkSelection";
    /** @type {import("plugins").EditorResources} */
    resources = {
        eligible_link_for_zwnbsp_predicates: [
            (link) => {
                if (selectElements(link, "*").some((el) => el.nodeName === "IMG" || isBlock(el))) {
                    return false;
                }
            },
        ],
        eligible_link_for_selection_indication_predicates: (link) => {
            if (link.matches(".btn")) {
                return false;
            }
        },
    };
}
