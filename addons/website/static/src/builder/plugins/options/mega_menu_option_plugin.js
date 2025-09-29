import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } MegaMenuOptionShared
 * @property { MegaMenuOptionPlugin['getTemplatePrefix'] } getTemplatePrefix
 */

export class MegaMenuOptionPlugin extends Plugin {
    static id = "megaMenuOptionPlugin";
    static shared = ["getTemplatePrefix"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: {
            selector: ".o_mega_menu .nav > .nav-link",
            dropIn: ".o_mega_menu nav",
            dropNear: ".o_mega_menu .nav-link",
        },
        no_parent_containers: ".o_mega_menu",
        is_unremovable_selectors: ".o_mega_menu > section",
        is_node_splittable_predicates: (node) => {
            //avoid merge
            if (
                node?.nodeType === Node.ELEMENT_NODE &&
                node.matches(".o_mega_menu .nav > .nav-link")
            ) {
                return false;
            }
        },
        dirt_marks: {
            id: "mega-menu-class",
            setDirtyOnMutation: (mutation, targetNode) =>
                mutation.type === "classList" && targetNode.dataset.oeField === "mega_menu_content"
                    ? mutation.target
                    : null,
            save: (el) =>
                this.services.orm.write("website.menu", [parseInt(el.dataset.oeId)], {
                    mega_menu_classes: [...el.classList]
                        .filter((c) => !["dropdown-menu", "o_mega_menu", "o_savable"].includes(c))
                        .join(" "),
                }),
        },
    };

    getTemplatePrefix() {
        return "website.";
    }
}

registry.category("website-plugins").add(MegaMenuOptionPlugin.id, MegaMenuOptionPlugin);
