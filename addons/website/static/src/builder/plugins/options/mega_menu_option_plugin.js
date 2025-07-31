import { MegaMenuOption } from "@website/builder/plugins/options/mega_menu_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";

export class MegaMenuOptionPlugin extends Plugin {
    static id = "megaMenuOptionPlugin";
    static dependencies = [];
    static shared = ["getTemplatePrefix"];

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_NEXT, {
                OptionComponent: MegaMenuOption,
                selector: ".o_mega_menu",
                props: {
                    getTemplatePrefix: this.getTemplatePrefix.bind(this),
                },
            }),
        ],
        save_handlers: this.saveMegaMenuClasses.bind(this),
        no_parent_containers: ".o_mega_menu",
        is_unremovable_selector: ".o_mega_menu > section",
    };

    getTemplatePrefix() {
        return "website.";
    }

    async saveMegaMenuClasses() {
        const megaMenuEl = this.editable.querySelector("[data-oe-field='mega_menu_content'");
        if (megaMenuEl) {
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            const classes = [...megaMenuEl.classList].filter(
                (megaMenuClass) =>
                    !["dropdown-menu", "o_mega_menu", "o_savable"].includes(megaMenuClass)
            );

            await this.services.orm.write("website.menu", [parseInt(megaMenuEl.dataset.oeId)], {
                mega_menu_classes: classes.join(" "),
            });
        }
    }
}

registry.category("website-plugins").add(MegaMenuOptionPlugin.id, MegaMenuOptionPlugin);
