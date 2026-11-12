import { makeContext } from "@web/core/context";
import { user } from "@web/core/user";

function hubSettingKey(hubId, resId) {
    return `${hubId},${resId}`;
}

/**
 * @param {number} hubId
 * @param {number} resId
 * @returns {number[]} ids of the items pinned by the user, in display order
 */
export function getPinnedItemIds(hubId, resId) {
    return user.settings.hub_config_ids?.[hubSettingKey(hubId, resId)] || [];
}

/**
 * Pin the items ``pinnedItemIds`` of ``hub``, in that order, for its record.
 * The displayed tabs and the local copy of the user settings are updated
 * before the server, so that what is opened meanwhile already uses them.
 *
 * @param {Object} orm
 * @param {Object} hub the hub of the current controller (``config.hub``)
 * @param {number[]} pinnedItemIds
 */
export async function savePinnedItemIds(orm, hub, pinnedItemIds) {
    hub.pinnedItemIds.set(pinnedItemIds);
    user.updateUserSettings("hub_config_ids", {
        ...user.settings.hub_config_ids,
        [hubSettingKey(hub.id, hub.resId)]: pinnedItemIds,
    });
    await orm.call("res.users.settings", "set_hub_setting", [
        user.settings.id,
        hub.id,
        hub.resId,
        pinnedItemIds,
    ]);
}

/**
 * @param {Object} hubs hubs per model, from the lazy session info
 * @param {string} resModel
 * @param {number} resId
 * @returns {Object|null} the item to open by default for the record: the first
 *  one pinned by the user, or the first one of the hub
 */
export function getDefaultHubItem(hubs, resModel, resId) {
    const hub = hubs?.[resModel];
    if (!hub?.item_ids.length) {
        return null;
    }
    const pinnedItemIds = getPinnedItemIds(hub.id, resId);
    const pinnedItems = pinnedItemIds
        .map((id) => hub.item_ids.find((item) => item.id === id))
        .filter(Boolean);
    return pinnedItems[0] || hub.item_ids[0];
}

export function openHubItem(actionPlugin, item, {resModel, resId}, options = {}){
    const activeContext = { active_id: resId, active_ids: [resId], active_model: resModel };
    const context = makeContext([item.context], activeContext);
    if (item.action_id) {
       return actionPlugin.doAction(item.action_id[0], {
            additionalContext: {
                ...context,
                ...activeContext,
            },
            ...options
        })
    } else {
        return actionPlugin.doActionButton({
            type: "object",
            name: item.python_method,
            resModel,
            resId,
            context,
            ...options
        }, { newWindow: options.newWindow });
    }
}
