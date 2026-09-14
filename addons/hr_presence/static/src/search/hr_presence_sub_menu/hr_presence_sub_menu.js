/** @odoo-module native */
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

export class HrPresenceSubMenu extends Component {
    static template = "hr_presence.SubMenu";
    static components = { CogMenuItem, Dropdown };
    static props = {
        items: Array,
        onItemSelected: Function,
    };
}
