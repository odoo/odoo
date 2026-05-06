import { patch } from "@web/core/utils/patch";
import { HrActionMenus } from "@hr/search/hr_action_menus/hr_action_menus";
import { getActionRecords, getPresenceActionItems } from "../../views/hooks";

patch(HrActionMenus.prototype, {
    get PresenceActionItems() {
        return (this.presenceActionItems || []).map((action) => {
            return {
                action,
                description: action.name,
                key: action.id,
                groupNumber: action.groupNumber,
            };
        });
    },

    async getActionItems(props) {
        const records = await getActionRecords(this.orm);
        const result = getPresenceActionItems(props.items.action, records);

        props.items.action = result[0];
        this.presenceActionItems = result[1];

        return await super.getActionItems(props);
    }
});
