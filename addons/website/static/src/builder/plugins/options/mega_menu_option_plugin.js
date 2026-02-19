import { MegaMenuOption } from "@website/builder/plugins/options/mega_menu_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";

/**
 * @typedef { Object } MegaMenuOptionShared
 * @property { MegaMenuOptionPlugin['getTemplatePrefix'] } getTemplatePrefix
 */

export class MegaMenuOptionPlugin extends Plugin {
    static id = "megaMenuOptionPlugin";
    static shared = ["getTemplatePrefix"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC_NEXT, MegaMenuOption)],
        dropzone_selector: {
            selector: ".o_mega_menu .nav > .nav-link",
            dropIn: ".o_mega_menu nav",
            dropNear: ".o_mega_menu .nav-link",
        },
        no_parent_containers: ".o_mega_menu",
        is_unremovable_selector: ".o_mega_menu > section",
        unsplittable_node_predicates: (node) =>
            node?.nodeType === Node.ELEMENT_NODE && node.matches(".o_mega_menu .nav > .nav-link"), //avoid merge
        dirt_marks: {
            id: "mega-menu-class",
            setDirtyOnMutation: (record) =>
                record.type === "classList" && record.target.dataset.oeField === "mega_menu_content"
                    ? record.target
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
