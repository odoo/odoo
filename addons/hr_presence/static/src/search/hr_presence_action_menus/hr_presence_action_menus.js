/** @odoo-module native */
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { groupPresenceActionItems } from "../../views/presence_action_items.js";

export class HrPresenceActionMenus extends ActionMenus {
    /** @override */
    async getActionItems(props) {
        return groupPresenceActionItems(
            this.orm,
            await super.getActionItems(props),
            (item) => this.onItemSelected(item),
        );
    }
}
