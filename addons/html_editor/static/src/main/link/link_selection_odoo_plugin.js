import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";

export class OdooLinkSelectionPlugin extends Plugin {
    static resources = () => ({
        blacklistLinkZwnbsp: [
            (link) =>
                [link, ...link.querySelectorAll("*")].some(
                    (el) => el.nodeName === "IMG" || isBlock(el)
                ),
            (link) => link.matches("nav a, a.nav-link"),
            (link) => link.matches(".btn"),
        ],
    });
}
