import { Store } from "./store";
import {
    STORE_SYM,
    fields,
    isFieldDefinition,
    isRelation,
    modelRegistry,
    technicalKeysOnRecords,
} from "./misc";
import { Record } from "./record";
import { StoreInternal } from "./store_internal";
import { ModelInternal } from "./model_internal";
import { RecordInternal } from "./record_internal";

import { proxy, toRaw } from "@odoo/owl";

/** @returns {import("models").Store} */
export function makeStore(env, { localRegistry } = {}) {
    // fake store for now, until it becomes a model
    /** @type {import("models").Store} */
    let store = new Store();
    store.env = env;
    store.Model = Store;
    store._ = new StoreInternal();
    store._raw = store;
    store._proxyInternal = store;
    store._proxy = store;
    store.recordByLocalId = proxy(new Map());
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
        // classes cannot be made reactive because they are functions and they are not supported.
        // work-around: make an object whose prototype is the class, so that static props become
        // instance props.
        /** @type {typeof Record} */
        const Model = Object.create(OgClass);
        // Produce another class with changed prototype, so that there are automatic get/set on relational fields
        const Class = {
            [OgClass.getName()]: class extends OgClass {
                constructor() {
                    super();
                    this.setup();
                    const record = this;
                    record._raw = record;
                    record.Model = Model;
                    record._ = record[STORE_SYM] ? new StoreInternal() : new RecordInternal();
                    record._proxyInternal = new Proxy(record, {
                        get: (...args) => record._.proxyGet(...args),
                        deleteProperty: (...args) => record._.proxyDeleteProperty(...args),
                        /**
                         * Using record.update(data) is preferable for performance to batch process
                         * when updating multiple fields at the same time.
                         */
                        set: (...args) => record._.proxySet(...args),
                    });
                    record._proxy = proxy(record._proxyInternal);
                    if (record?.[STORE_SYM]) {
                        record.recordByLocalId = store.recordByLocalId;
                        record._ = store._;
                        store = record;
                        Record.store = store;
                    }
                    return record._proxy;
                }
            },
        }[OgClass.getName()];
        Model._ = new ModelInternal();
        Object.assign(Model, {
            Class,
            records: proxy({}),
        });
        Models[Model.getName()] = Model;
        store[Model.getName()] = Model;
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new OgClass();
        obj.setup();
        for (const [name, val] of Object.entries(obj)) {
            if (technicalKeysOnRecords.includes(name)) {
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
                ...Model._.fields.keys(),
                ...Object.getOwnPropertyNames(Model.prototype),
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
                // fields
                for (const fieldName of ParentModel._.fields.keys()) {
                    if (ownProperties.has(fieldName)) {
                        continue;
                    }
                    Model._.parentFields.set(fieldName, parentFieldName);
                }
                // getters and functions
                for (const key of Object.getOwnPropertyNames(ParentModel.prototype)) {
                    if (ownProperties.has(key)) {
                        continue;
                    }
                    const descriptor = Object.getOwnPropertyDescriptor(ParentModel.prototype, key);
                    if (descriptor.get || typeof descriptor.value === "function") {
                        Model._.parentFields.set(key, parentFieldName);
                    }
                }
            }
        }
    }
    /**
     * store/_rawStore are assigned on models at next step, but they are
     * required on Store model to make the initial store insert.
     */
    Object.assign(store.Store, { store, _rawStore: store });
    // Make true store (as a model)
    store = toRaw(store.Store.insert())._raw;
    for (const Model of Object.values(Models)) {
        Model._rawStore = store;
        Model.store = store._proxy;
        store._proxy[Model.getName()] = Model;
    }
    Object.assign(store, { Models, storeReady: true });
    return store._proxy;
}
