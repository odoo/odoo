import { Store } from "./store";
import { modelRegistry } from "./misc";
import { StoreInternal } from "./store_internal";
import { ModelInternal } from "./model_internal";

import { onWillDestroy, proxy, signal, useApp } from "@odoo/owl";

/** @returns {import("models").Store} */
export function makeStore(env, { localRegistry } = {}) {
    // fake store for now, until it becomes a model
    /** @type {import("models").Store} */
    const store = new Store();
    store.env = env;
    store.Model = Store;
    store._ = new StoreInternal();
    // services start in the scope of the app, which every record scope needs
    store._.app = useApp();
    store.recordByLocalId = proxy(new Map());
    /** @type {Object<string, typeof import("./record").Record>} */
    const Models = {};
    const chosenModelRegistry = localRegistry ?? modelRegistry;

    /**
     * Attach a store subclass of the registry class `OgClass` to `hostStore`: the
     * bootstrap object during boot, the true store record afterwards. The subclass
     * carries the per-store state, so the registry class, shared with the next
     * store, stays stateless.
     *
     * @param {typeof import("./record").Record} OgClass
     * @param {import("models").Store} hostStore
     */
    function addModel(OgClass, hostStore) {
        const name = OgClass.getName();
        if (Models[name]) {
            throw new Error(`There must be no duplicated Model Names (duplicate found: ${name})`);
        }
        /** @type {typeof import("./record").Record} */
        const Model = { [name]: class extends OgClass {} }[name];
        Model._ = new ModelInternal();
        // `records` stays a property: business code reads it all over mail and enterprise.
        const records = signal.Map();
        Object.defineProperty(Model, "records", {
            configurable: true,
            enumerable: true,
            get: () => records(),
        });
        Model.store = hostStore;
        Model._.Model = Model;
        Models[name] = Model;
        Object.defineProperty(hostStore, name, {
            value: Model,
            configurable: true,
            enumerable: true,
        });
    }

    for (const [, OgClass] of chosenModelRegistry.getEntries()) {
        addModel(OgClass, store);
    }
    store.Models = Models;
    return store.MAKE_UPDATE(function makeTrueStore() {
        const trueStore = store.Store.insert();
        for (const Model of Object.values(Models)) {
            Model.store = trueStore;
        }
        onWillDestroy(() => trueStore._runDisposeFns());
        return trueStore;
    });
}
