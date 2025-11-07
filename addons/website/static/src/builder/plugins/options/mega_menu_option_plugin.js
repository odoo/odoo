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
    static dependencies = [];
    static shared = ["getTemplatePrefix"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(SNIPPET_SPECIFIC_NEXT, MegaMenuOption)],
        dropzone_selector: {
            selector: ".o_mega_menu .nav > .nav-link",
            dropIn: ".o_mega_menu nav",
            dropNear: ".o_mega_menu .nav-link",
        },
        save_handlers: this.saveMegaMenuClasses.bind(this),
        no_parent_containers: ".o_mega_menu",
        is_unremovable_selector: ".o_mega_menu > section",
        unsplittable_node_predicates: (node) =>
            node?.nodeType === Node.ELEMENT_NODE && node.matches(".o_mega_menu .nav > .nav-link"), //avoid merge
    };

    getTemplatePrefix() {
        return "website.";
    }

    async saveMegaMenuClasses() {
        const proms = [];
        for (const megaMenuEl of this.editable.querySelectorAll(
            "[data-oe-field='mega_menu_content']"
        )) {
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            const classes = [...megaMenuEl.classList].filter(
                (megaMenuClass) =>
                    !["dropdown-menu", "o_mega_menu", "o_editable"].includes(megaMenuClass)
            );

            proms.push(
                this.services.orm.write("website.menu", [parseInt(megaMenuEl.dataset.oeId)], {
                    mega_menu_classes: classes.join(" "),
                })
            );
        }
        await Promise.all(proms);
    }
}

registry.category("website-plugins").add(MegaMenuOptionPlugin.id, MegaMenuOptionPlugin);
