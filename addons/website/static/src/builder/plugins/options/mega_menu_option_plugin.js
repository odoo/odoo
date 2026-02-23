import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

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
        dropzone_selectors: {
            selector: ".o_mega_menu .nav > .nav-link",
            dropIn: ".o_mega_menu nav",
            dropNear: ".o_mega_menu .nav-link",
        },
        on_ready_to_save_document_handlers: this.saveMegaMenuClasses.bind(this),
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
                    !["dropdown-menu", "o_mega_menu", "o_savable"].includes(megaMenuClass)
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
