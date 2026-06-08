import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class OdooLinkSelectionPlugin extends Plugin {
    static id = "odooLinkSelection";
    /** @type {import("plugins").EditorResources} */
    resources = {
        is_link_eligible_for_zwnbsp_predicates: [
            (link) => {
                if (selectElements(link, "*").some((el) => el.nodeName === "IMG" || isBlock(el))) {
                    return false;
                }
            },
        ],
        is_link_eligible_for_visual_indication_predicates: (link) => {
            if (link.matches(".btn")) {
                return false;
            }
        },
    };
}
