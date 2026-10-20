import { signal, usePlugin } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";

/**
 * @param {Object} hub the hub of the current controller (``config.hub``)
 * @returns {import("@odoo/owl").Signal<Object[]>} the items of ``hub`` shown
 *  for its record, from the lazy session (empty until loaded): the items hidden
 *  for the record are left out, except the opened one
 */
export function useHubItems(hub) {
    const items = signal([]);
    usePlugin(LazySessionPlugin).getValue("hubs", (hubs) => {
        const hubItems = hubs?.[hub.resModel]?.item_ids || [];
        items.set(
            hubItems.filter(
                (item) =>
                    item.id === hub.activeItemId || !hub.invisibleItemIds.includes(item.id)
            )
        );
    });
    return items;
}

function hubSettingKey(hubId, resId) {
    return `${hubId},${resId}`;
}

/**
 * @param {number} hubId
 * @param {number} resId
 * @returns {{ pinned_item_ids: number[], show_tabs: boolean }} the setting of
 *  the user for the hub opened for the record: the ids of the pinned items, in
 *  display order, and whether the tabs are shown
 */
export function getHubSetting(hubId, resId) {
    return {
        pinned_item_ids: [],
        show_tabs: false,
        ...user.settings.hub_config_ids?.[hubSettingKey(hubId, resId)],
    };
}

/**
 * Save the setting ``vals`` (``pinned_item_ids`` and/or ``show_tabs``) of
 * ``hub`` for its record. The displayed tabs and the local copy of the user
 * settings are updated before the server, so that what is opened meanwhile
 * already uses them.
 *
 * @param {Object} orm
 * @param {Object} hub the hub of the current controller (``config.hub``)
 * @param {{ pinned_item_ids?: number[], show_tabs?: boolean }} vals
 */
export async function saveHubSetting(orm, hub, vals) {
    if ("pinned_item_ids" in vals) {
        hub.pinnedItemIds.set(vals.pinned_item_ids);
    }
    if ("show_tabs" in vals) {
        hub.showTabs.set(vals.show_tabs);
    }
    const key = hubSettingKey(hub.id, hub.resId);
    user.updateUserSettings("hub_config_ids", {
        ...user.settings.hub_config_ids,
        [key]: { ...getHubSetting(hub.id, hub.resId), ...vals },
    });
    await orm.call("res.users.settings", "set_hub_setting", [
        user.settings.id,
        hub.id,
        hub.resId,
        vals,
    ]);
}

/**
 * @param {Object} hub the hub of the current controller (``config.hub``)
 * @returns {Function} shows or hides the tabs of ``hub`` for its record. The
 *  first time they are shown, the pinned items start from the default setting
 *  of the server (e.g. the ones of the project manager on a project); when they
 *  are shown with no item pinned, the default item is pinned
 */
export function useToggleHubTabs(hub) {
    const orm = useService("orm");
    const items = useHubItems(hub);
    return async () => {
        const vals = { show_tabs: !hub.showTabs() };
        if (vals.show_tabs && !(hubSettingKey(hub.id, hub.resId) in (user.settings.hub_config_ids || {}))) {
            const defaultSetting = await orm.call("res.users.settings", "get_default_hub_setting", [
                user.settings.id,
                hub.id,
                hub.resId,
            ]);
            if (defaultSetting.pinned_item_ids) {
                vals.pinned_item_ids = defaultSetting.pinned_item_ids;
            }
        }
        if (vals.show_tabs && !(vals.pinned_item_ids || hub.pinnedItemIds()).length && items().length) {
            vals.pinned_item_ids = [items()[0].id];
        }
        return saveHubSetting(orm, hub, vals);
    };
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
    const pinnedItemIds = getHubSetting(hub.id, resId).pinned_item_ids;
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

/**
 * Open the hub of the active record on its default item, resolved client side
 * to spare a server round trip, e.g. <kanban action="hub_default" type="action">.
 */
async function hubDefaultAction(action, options) {
    const actionPlugin = useService("action");
    const lazySession = usePlugin(LazySessionPlugin);
    const { active_model: resModel, active_id: resId } = action.context || {};
    const hubs = await new Promise((resolve) => lazySession.getValue("hubs", resolve));
    const item = resId && getDefaultHubItem(hubs, resModel, resId);
    if (!item) {
        throw new Error(`No hub to open for ${resModel} record ${resId}`);
    }
    return openHubItem(actionPlugin, item, { resModel, resId }, options);
}

registry.category("actions").add("hub_default", hubDefaultAction);
