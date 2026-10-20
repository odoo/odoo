import { computed, Plugin, signal, usePlugin } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { user } from "@web/core/user";
import { Mutex } from "@web/core/utils/concurrency";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";
import { HubTabs } from "./hub_tabs";

/**
 * @typedef {Object} Hub the hub of a controller (``config.hub``)
 * @property {number} id id of the hub
 * @property {string} resModel model of the hub's record
 * @property {number} resId id of the hub's record
 * @property {number} activeItemId id of the item currently opened
 * @property {number[]} invisibleItemIds ids of the items hidden for the hub's record
 * @property {import("@odoo/owl").Signal<number[]>} pinnedItemIds ids of the items pinned by the user, in display order
 * @property {import("@odoo/owl").Signal<boolean>} showTabs whether the user shows the tabs of the hub
 * @property {() => Object[]} items the items shown for the record (empty until loaded)
 * @property {() => Promise} toggleTabs shows or hides the tabs
 * @property {(vals: Object) => Promise} saveSetting saves ``pinned_item_ids`` and/or ``show_tabs``
 * @property {(item: Object, options?: Object) => Promise} openItem opens ``item`` in place of the current action
 */

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
function getHubSetting(hubId, resId) {
    return {
        pinned_item_ids: [],
        show_tabs: false,
        ...user.settings.hub_config_ids?.[hubSettingKey(hubId, resId)],
    };
}

/**
 * Builds the hub of the actions that have one (``action.hub``), and puts it on
 * the config of their controllers (``config.hub``), with the component of its
 * tabs (``config.HubTabs``).
 */
export class HubPlugin extends Plugin {
    #action = usePlugin(ActionPlugin);
    #lazySession = usePlugin(LazySessionPlugin);
    #orm = usePlugin(ORM);
    /** hubs per model, from the lazy session info (null until loaded) */
    #hubs = signal(null);
    #hubsPromise = null;
    /** the saves of the settings, run one after the other */
    #saveMutex = new Mutex();

    setup() {
        this.#action.controllerSetups.use(({ action, config }) => {
            if (action.hub && action.target !== "new") {
                config.hub = this.makeHub(action.hub);
                config.HubTabs = HubTabs;
            }
        });
    }

    /**
     * @returns {Promise<Object>} hubs per model, from the lazy session info
     */
    loadHubs() {
        this.#hubsPromise ||= new Promise((resolve) =>
            this.#lazySession.getValue("hubs", (hubs) => {
                this.#hubs.set(hubs || {});
                resolve(this.#hubs());
            })
        );
        return this.#hubsPromise;
    }

    /**
     * @param {Object} hubInfo the hub of an action, from the server (``action.hub``)
     * @returns {Hub}
     */
    makeHub(hubInfo) {
        this.loadHubs();
        const setting = getHubSetting(hubInfo.id, hubInfo.res_id);
        const hub = {
            id: hubInfo.id,
            resModel: hubInfo.res_model,
            resId: hubInfo.res_id,
            activeItemId: hubInfo.active_item_id,
            invisibleItemIds: hubInfo.invisible_item_ids || [],
            pinnedItemIds: signal(setting.pinned_item_ids),
            showTabs: signal(setting.show_tabs),
            items: computed(() => this.#getShownItems(hub)),
            toggleTabs: () => this.#toggleTabs(hub),
            saveSetting: (vals) => this.#saveSetting(hub, vals),
            openItem: (item, options = {}) =>
                this.openItem(item, hub, { stackPosition: "replaceCurrentAction", ...options }),
        };
        return hub;
    }

    /**
     * @param {Hub} hub
     * @returns {Object[]} the items of ``hub`` shown for its record (none until
     *  the hubs are loaded): the ones not hidden for the record, and the opened
     *  one even if it is
     */
    #getShownItems(hub) {
        const items = this.#hubs()?.[hub.resModel]?.item_ids || [];
        return items.filter((item) => {
            if (item.id === hub.activeItemId) {
                return true;
            }
            return !hub.invisibleItemIds.includes(item.id);
        });
    }

    /**
     * Save the setting ``vals`` (``pinned_item_ids`` and/or ``show_tabs``) of
     * ``hub`` for its record. The displayed tabs and the local copy of the user
     * settings are updated before the server, so that what is opened meanwhile
     * already uses them.
     *
     * @param {Hub} hub
     * @param {{ pinned_item_ids?: number[], show_tabs?: boolean }} vals
     */
    async #saveSetting(hub, vals) {
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
        await this.#saveMutex.exec(() =>
            this.#orm.call("res.users.settings", "set_hub_setting", [
                user.settings.id,
                hub.id,
                hub.resId,
                vals,
            ])
        );
    }

    /**
     * Shows or hides the tabs of ``hub`` for its record. The first time they
     * are shown, the pinned items start from the default setting of the server
     * (e.g. the ones of the project manager on a project); when they are shown
     * with no item pinned, the default item is pinned.
     *
     * @param {Hub} hub
     */
    async #toggleTabs(hub) {
        const vals = { show_tabs: !hub.showTabs() };
        if (
            vals.show_tabs &&
            !(hubSettingKey(hub.id, hub.resId) in (user.settings.hub_config_ids || {}))
        ) {
            const defaultSetting = await this.#orm.call(
                "res.users.settings",
                "get_default_hub_setting",
                [user.settings.id, hub.id, hub.resId]
            );
            if (defaultSetting.pinned_item_ids) {
                vals.pinned_item_ids = defaultSetting.pinned_item_ids;
            }
        }
        const items = hub.items();
        if (
            vals.show_tabs &&
            !(vals.pinned_item_ids || hub.pinnedItemIds()).length &&
            items.length
        ) {
            vals.pinned_item_ids = [items[0].id];
        }
        return this.#saveSetting(hub, vals);
    }

    /**
     * @param {string} resModel
     * @param {number} resId
     * @returns {Promise<Object|null>} the item to open by default for the
     *  record: the first one pinned by the user, or the first one of the hub
     */
    async getDefaultItem(resModel, resId) {
        const hub = (await this.loadHubs())[resModel];
        if (!hub?.item_ids.length) {
            return null;
        }
        const pinnedItems = getHubSetting(hub.id, resId)
            .pinned_item_ids.map((id) => hub.item_ids.find((item) => item.id === id))
            .filter(Boolean);
        return pinnedItems[0] || hub.item_ids[0];
    }

    /**
     * @param {Object} item
     * @param {{ resModel: string, resId: number }} record the hub's record
     * @param {Object} [options] options of the action
     */
    openItem(item, { resModel, resId }, options = {}) {
        const activeContext = { active_id: resId, active_ids: [resId], active_model: resModel };
        const context = makeContext([item.context], activeContext);
        if (item.action_id) {
            return this.#action.doAction(item.action_id[0], {
                additionalContext: { ...context, ...activeContext },
                ...options,
            });
        }
        return this.#action.doActionButton(
            {
                type: "object",
                name: item.python_method,
                resModel,
                resId,
                context,
                ...options,
            },
            { newWindow: options.newWindow }
        );
    }
}

services.add(HubPlugin);

/**
 * Open the hub of the active record on its default item, resolved client side
 * to spare a server round trip, e.g. <kanban action="hub_default" type="action">.
 */
async function hubDefaultAction(action, options) {
    const hubPlugin = usePlugin(HubPlugin);
    const { active_model: resModel, active_id: resId } = action.context || {};
    const item = resId && (await hubPlugin.getDefaultItem(resModel, resId));
    if (!item) {
        throw new Error(`No hub to open for ${resModel} record ${resId}`);
    }
    return hubPlugin.openItem(item, { resModel, resId }, options);
}

registry.category("actions").add("hub_default", hubDefaultAction);
