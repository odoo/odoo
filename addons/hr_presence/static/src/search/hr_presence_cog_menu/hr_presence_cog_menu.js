/** @odoo-module native */
import { FormCogMenu } from "@web/views/form";
import { groupPresenceActionItems } from "../../views/presence_action_items.js";

export class HrPresenceCogMenu extends FormCogMenu {
    /** @override */
    async getActionItems(props) {
        return groupPresenceActionItems(
            this.orm,
            await super.getActionItems(props),
            (item) => this.onItemSelected(item),
        );
    }
}
