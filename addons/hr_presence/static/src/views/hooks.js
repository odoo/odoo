export async function getActionRecords(orm) {
    return await orm.call("hr.employee.base", "get_presence_server_action_data", [[]]);
}
export function getPresenceActionItems(actions, records) {
    const presenceActionItems = [];
    const presenceRecords = {
        group_1: records
            .filter((record) => record.value === "presence_group_1")
            .map((record) => record.id),
        group_2: records
            .filter((record) => record.value === "presence_group_2")
            .map((record) => record.id),
    };
    actions = (actions || []).filter((action) => {
        const isInGroup1 = presenceRecords["group_1"].includes(action.key || action.id);
        const isInGroup2 = presenceRecords["group_2"].includes(action.key || action.id);
        if (isInGroup1 || isInGroup2) {
            action.groupNumber = isInGroup1 ? 50 : 60;
            presenceActionItems.push(action);
            return false; // Exclude this object from the resulting array
        }
        return true; // Include this object in the resulting array
    });
    return [actions, presenceActionItems];
}
