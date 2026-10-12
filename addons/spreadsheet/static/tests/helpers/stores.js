// @ts-check

import { stores, owlPlugins } from "@odoo/o-spreadsheet";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { makeOwlPluginManager } from "@spreadsheet/../tests/helpers/owl_plugins";

const { ModelStore } = stores;
const { NotificationPlugin } = owlPlugins;

/**
 * @template T
 * @typedef {import("@odoo/o-spreadsheet").StoreConstructor<T>} StoreConstructor<T>
 *
 * @typedef {import("./owl_plugins").OwlPluginGetter} OwlPluginGetter
 */

/**
 * @typedef {import("@spreadsheet").OdooSpreadsheetModel} OdooSpreadsheetModel
 */

/**
 * @template T
 * @param {StoreConstructor<T>} Store
 * @param  {any[]} args
 * @return {Promise<{ store: T, container: InstanceType<DependencyContainer>, model: OdooSpreadsheetModel }>}
 */
export async function makeStore(Store, ...args) {
    const { model } = await createModelWithDataSource();
    return makeStoreWithModel(model, Store, ...args);
}

/**
 * @template T
 * @param {import("@odoo/o-spreadsheet").Model} model
 * @param {StoreConstructor<T>} Store
 * @param  {any[]} args
 * @return {{ store: T, container: InstanceType<DependencyContainer>, model: OdooSpreadsheetModel, getPlugin: OwlPluginGetter }}
 */
export function makeStoreWithModel(model, Store, ...args) {
    const { getPlugin, container } = makeOwlPluginManager([NotificationPlugin]);

    const notificationPlugin = getPlugin(NotificationPlugin);
    container.inject(ModelStore, model);
    notificationPlugin.updateNotificationCallbacks({
        notifyUser: () => {},
        raiseError: () => {},
        askConfirmation: () => {},
    });
    return {
        store: container.instantiate(Store, ...args),
        container,
        // @ts-ignore
        model: container.get(ModelStore),
        getPlugin,
    };
}
