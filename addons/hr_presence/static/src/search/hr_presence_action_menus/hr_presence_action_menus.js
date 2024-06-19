import { ActionMenus } from "@web/search/action_menus/action_menus";
import { getActionRecords, getPresenceActionItems } from "../../views/hooks";

/**
 * @extends ActionMenus
 */
export class HrPresenceActionMenus extends ActionMenus {
    static template = "hr_presence.actionmenu";

    get PresenceActionItems() {
        return (this.presenceActionItems || []).map((action) => {
            return {
                action,
                description: action.name,
                key: action.id,
                groupNumber: action.groupNumber,
            };
        });
    }

    /**
     * @override
     */
    async getActionItems(props) {
        const records = await getActionRecords(props.items.action, this.orm);
        const result = getPresenceActionItems(props.items.action, records);

        props.items.action = result[0];
        this.presenceActionItems = result[1];

        return await super.getActionItems(props);
    }
}
