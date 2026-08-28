import { Store } from "./store";
import {
    fields,
    isComputedDefinition,
    isFieldDefinition,
    isRelation,
    modelRegistry,
    technicalKeysOnRecords,
} from "./misc";
import { Record } from "./record";
import { StoreInternal } from "./store_internal";
import { ModelInternal } from "./model_internal";

import { signal, useApp } from "@odoo/owl";

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
        Model._ = new ModelInternal();
        // `records` stays a property: business code reads it all over mail and enterprise.
        const records = signal.Map();
        Object.defineProperty(Model, "records", {
            configurable: true,
            enumerable: true,
            get: () => records(),
        });
        Models[Model.getName()] = Model;
        store[Model.getName()] = Model;
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new Proxy(new OgClass(), {
            set(target, name, value) {
                if (isComputedDefinition(target[name]) && isComputedDefinition(value)) {
                    throw new Error(
                        `${OgClass.getName()}.${name}: a computed cannot be redeclared, patch the method its compute calls`
                    );
                }
                return Reflect.set(target, name, value);
            },
        });
        obj.setup();
        for (const [name, val] of Object.entries(obj)) {
            if (technicalKeysOnRecords.has(name)) {
                continue;
            }
            if (isComputedDefinition(val)) {
                Model._.fieldsComputable.add(name);
                continue;
            }
            if (!isFieldDefinition(val)) {
                obj[name] = fields.Attr(val);
            }
            Model._.prepareField(name, obj[name]);
        }
    }
    // Sync inverse fields
    for (const Model of Object.values(Models)) {
        for (const name of Model._.fields.keys()) {
            if (!isRelation(Model, name)) {
                continue;
            }
            const targetModel = Model._.fieldsTargetModel.get(name);
            const inverse = Model._.fieldsInverse.get(name);
            if (targetModel && !Models[targetModel]) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            if (inverse) {
                const OtherModel = Models[targetModel];
                const rel2TargetModel = OtherModel._.fieldsTargetModel.get(inverse);
                const rel2Inverse = OtherModel._.fieldsInverse.get(inverse);
                if (rel2TargetModel && rel2TargetModel !== Model.getName()) {
                    throw new Error(
                        `Fields ${Models[
                            targetModel
                        ].getName()}.${inverse} has wrong targetModel. Expected: "${Model.getName()}" Actual: "${rel2TargetModel}"`
                    );
                }
                if (rel2Inverse && rel2Inverse !== name) {
                    throw new Error(
                        `Fields ${Models[
                            targetModel
                        ].getName()}.${inverse} has wrong inverse. Expected: "${name}" Actual: "${rel2Inverse}"`
                    );
                }
                OtherModel._.fieldsTargetModel.set(inverse, Model.getName());
                OtherModel._.fieldsInverse.set(inverse, name);
                // // FIXME: lazy fields are not working properly with inverse.
                Model._.fieldsEager.set(name, true);
                OtherModel._.fieldsEager.set(inverse, true);
            }
        }
    }
    // Map inherited properties
    for (const Model of Object.values(Models)) {
        if (Model._inherits) {
            const ownProperties = new Set([
                ...Model._.fieldsComputable,
                ...Model._.fields.keys(),
                // the model's own members live on the registry class, one layer above the
                // per-store subclass
                ...Object.getOwnPropertyNames(Object.getPrototypeOf(Model.prototype)),
                // a member of Record itself, `setup` in particular, never delegates
                ...Object.getOwnPropertyNames(Record.prototype),
            ]);
            for (const [parentModelName, parentFieldName] of Object.entries(Model._inherits)) {
                const inverseField = Model._.fieldsInverse.get(parentFieldName);
                if (!inverseField) {
                    throw new Error(
                        `Missing inverse field of "${parentFieldName}" for _inherits in "${Model.getName()}"`
                    );
                }
                Model._.inheritsFields.add(parentFieldName);
                const ParentModel = Models[parentModelName];
                ParentModel._.inheritsInverseFields.add(inverseField);
                // fields and computeds
                for (const fieldName of [
                    ...ParentModel._.fieldsComputable,
                    ...ParentModel._.fields.keys(),
                ]) {
                    if (ownProperties.has(fieldName)) {
                        continue;
                    }
                    Model._.parentFields.set(fieldName, parentFieldName);
                }
                // getters and functions
                const parentProto = Object.getPrototypeOf(ParentModel.prototype);
                for (const key of Object.getOwnPropertyNames(parentProto)) {
                    if (ownProperties.has(key)) {
                        continue;
                    }
                    const descriptor = Object.getOwnPropertyDescriptor(parentProto, key);
                    if (descriptor.get || typeof descriptor.value === "function") {
                        Model._.parentFields.set(key, parentFieldName);
                    }
                }
            }
        }
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
    return store._proxy;
}
