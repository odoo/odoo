import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";

export class OdooLinkSelectionPlugin extends Plugin {
    resources = {
        excludeLinkZwnbsp: [
            (link) =>
                [link, ...link.querySelectorAll("*")].some(
                    (el) => el.nodeName === "IMG" || isBlock(el)
                ),
            (link) => link.matches("nav a, a.nav-link"),
        ],
        excludeLinkVisualIndication: (link) => link.matches(".btn"),
    };
}
