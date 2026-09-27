import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";

export class MegaMenuOption extends BaseOptionComponent {
    static id = "mega_menu_option";
    static template = "website.MegaMenuOption";
    static dependencies = ["megaMenuOptionPlugin"];
}
registry.category("website-options").add(MegaMenuOption.id, MegaMenuOption);
