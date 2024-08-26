import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { StatusBarDropdownItems } from "../status_bar_dropdown_items/status_bar_dropdown_items";

export class FormCogMenu extends CogMenu {
    static template = "web.FormCogMenu";
    static components = {
        ...CogMenu.components,
        StatusBarDropdownItems,
    };
    static props = {
        ...CogMenu.props,
        slots: { type: Object, optional: true },
    };
}
