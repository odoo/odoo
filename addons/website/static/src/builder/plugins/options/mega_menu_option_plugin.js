import { prepareElementForSave } from "@html_builder/core/save_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MegaMenuOptionPlugin extends Plugin {
    static id = "megaMenuOptionPlugin";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selectors: [
            {
                selector: ".o_mega_menu .nav > .nav-link",
                dropIn: ".o_mega_menu nav",
                dropNear: ".o_mega_menu .nav-link",
            },
            {
                // Should be removed when floating snippets are restricted from being added in mega
                // menu.
                selector: ".s_whatsapp",
                excludeAncestor: ".o_mega_menu",
            },
        ],
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
        content_editable_selectors:
            ".s_mega_menu_thumbnails_footer, .s_mega_menu_menus_logos_wrapper",
    };

    async saveMegaMenuClasses() {
        const proms = [];
        for (const megaMenuEl of this.editable.querySelectorAll(
            "[data-oe-field='mega_menu_content'].o_dirty"
        )) {
            const cleanedMegaMenuEl = prepareElementForSave(this, megaMenuEl);
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            const classes = [...cleanedMegaMenuEl.classList].filter(
                (megaMenuClass) => !["dropdown-menu", "o_mega_menu"].includes(megaMenuClass)
            );

            proms.push(
                this.services.orm.write(
                    "website.menu",
                    [parseInt(cleanedMegaMenuEl.dataset.oeId)],
                    { mega_menu_classes: classes.join(" ") }
                )
            );
        }
        await Promise.all(proms);
    }
}

registry.category("website-plugins").add(MegaMenuOptionPlugin.id, MegaMenuOptionPlugin);
