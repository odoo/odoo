import { Store } from "./store";
import { modelRegistry } from "./misc";
import { Record } from "./record";
import { StoreInternal } from "./store_internal";
import { ModelInternal } from "./model_internal";

import { onWillDestroy, signal, useApp } from "@odoo/owl";

/** @returns {import("models").Store} */
export function makeStore(env, { localRegistry } = {}) {
    // fake store for now, until it becomes a model
    /** @type {import("models").Store} */
    let store = new Store();
    store.env = env;
    store.Model = Store;
    store._ = new StoreInternal();
    // services start in the scope of the app, which every record scope needs
    store._.app = useApp();
    store._raw = store;
    store._proxy = store;
    Record.store = store;
    /** @type {Object<string, typeof Record>} */
    const Models = {};
    const chosenModelRegistry = localRegistry ?? modelRegistry;
    for (const [, _OgClass] of chosenModelRegistry.getEntries()) {
        /** @type {typeof Record} */
        const OgClass = _OgClass;
        if (store[OgClass.getName()]) {
            throw new Error(
                `There must be no duplicated Model Names (duplicate found: ${OgClass.getName()})`
            );
        }
        const Model = {
            [OgClass.getName()]: class extends OgClass {},
        }[OgClass.getName()];
        Model._ = new ModelInternal(Model, Models);
        // `records` stays a property: business code reads it all over mail and enterprise.
        const records = signal.Map();
        Object.defineProperty(Model, "records", {
            configurable: true,
            enumerable: true,
            get: () => records(),
        });
        Models[Model.getName()] = Model;
        store[Model.getName()] = Model;
    }
    // point store/_rawStore at the temporary store, so the initial store
    // insert can write through the proxy
    for (const Model of Object.values(Models)) {
        Model._rawStore = store;
        Model.store = store._proxy;
    }
    // Make true store (as a model)
    store = store.Store.insert()._raw;
    Record.store = store;
    for (const Model of Object.values(Models)) {
        Model._rawStore = store;
        Model.store = store._proxy;
        store[Model.getName()] = Model;
    }
    Object.assign(store, { Models, storeReady: true });
    onWillDestroy(() => store._runDisposeFns());
    return store._proxy;
}
