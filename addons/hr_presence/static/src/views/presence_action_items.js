/** @odoo-module native */
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { HrPresenceSubMenu } from "../search/hr_presence_sub_menu/hr_presence_sub_menu.js";

const PRESENCE_GROUPS = {
    presence_group_1: 1,
    presence_group_2: 2,
};

export async function groupPresenceActionItems(orm, actionItems, onItemSelected) {
    const records = await orm.call("hr.employee", "get_presence_server_action_data", [
        [],
    ]);
    const presenceGroupByActionId = new Map(
        records.map((record) => [record.id, PRESENCE_GROUPS[record.value]]),
    );
    const presenceItems = [];
    const otherItems = [];
    for (const item of actionItems) {
        const presenceGroup = presenceGroupByActionId.get(item.action?.id);
        if (presenceGroup) {
            presenceItems.push({ ...item, groupNumber: presenceGroup });
        } else {
            otherItems.push(item);
        }
    }
    if (!presenceItems.length) {
        return otherItems;
    }
    return [
        ...otherItems,
        {
            key: "hr_presence_control",
            groupNumber: COG_GROUP.ACTIONS,
            Component: HrPresenceSubMenu,
            props: { items: presenceItems, onItemSelected },
        },
    ].toSorted((item1, item2) => item1.groupNumber - item2.groupNumber);
}
