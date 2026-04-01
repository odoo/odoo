import { markRaw, reactive, toRaw } from "@odoo/owl";
import { Store } from "./store";
import { STORE_SYM, isFieldDefinition, isMany, isRelation, modelRegistry } from "./misc";
import { Record } from "./record";
import { StoreInternal } from "./store_internal";
import { ModelInternal } from "./model_internal";
import { RecordInternal } from "./record_internal";

/** @returns {import("models").Store} */
export function makeStore(env, { localRegistry } = {}) {
    const recordByLocalId = reactive(new Map());
    // fake store for now, until it becomes a model
    /** @type {import("models").Store} */
    let store = new Store();
    store.env = env;
    store.Model = Store;
    store._ = markRaw(new StoreInternal());
    store._raw = store;
    store._proxyInternal = store;
    store._proxy = store;
    store.recordByLocalId = recordByLocalId;
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
                    record._ = markRaw(
                        record[STORE_SYM] ? new StoreInternal() : new RecordInternal()
                    );
                    const recordProxyInternal = new Proxy(record, {
                        /**
                         * @param {Record} record
                         * @param {string} name
                         * @param {Record} recordFullProxy
                         */
                        get(record, name, recordFullProxy) {
                            recordFullProxy = record._.downgradeProxy(record, recordFullProxy);
                            if (record._.gettingField || !Model._.fields.get(name)) {
                                let res = Reflect.get(...arguments);
                                if (typeof res === "function") {
                                    res = res.bind(recordFullProxy);
                                }
                                return res;
                            }
                            if (Model._.fieldsCompute.get(name) && !Model._.fieldsEager.get(name)) {
                                record._.fieldsComputeInNeed.set(name, true);
                                if (record._.fieldsComputeOnNeed.get(name)) {
                                    record._.compute(record, name);
                                }
                            }
                            if (Model._.fieldsSort.get(name) && !Model._.fieldsEager.get(name)) {
                                record._.fieldsSortInNeed.set(name, true);
                                if (record._.fieldsSortOnNeed.get(name)) {
                                    record._.sort(record, name);
                                }
                            }
                            record._.gettingField = true;
                            const val = recordFullProxy[name];
                            record._.gettingField = false;
                            if (isRelation(Model, name)) {
                                const recordListFullProxy = val._proxy;
                                if (isMany(Model, name)) {
                                    return recordListFullProxy;
                                }
                                return recordListFullProxy[0];
                            }
                            return Reflect.get(record, name, recordFullProxy);
                        },
                        /**
                         * @param {Record} record
                         * @param {string} name
                         */
                        deleteProperty(record, name) {
                            return store.MAKE_UPDATE(function recordDeleteProperty() {
                                if (isRelation(Model, name)) {
                                    const recordList = record[name];
                                    recordList.clear();
                                    return true;
                                }
                                return Reflect.deleteProperty(record, name);
                            });
                        },
                        /**
                         * Using record.update(data) is preferable for performance to batch process
                         * when updating multiple fields at the same time.
                         */
                        set(record, name, val, receiver) {
                            // ensure each field write goes through the updatingAttrs method exactly once
                            if (record._.updatingAttrs.has(name)) {
                                record[name] = val;
                                return true;
                            }
                            return store.MAKE_UPDATE(function recordSet() {
                                const reactiveSet = receiver !== record._proxyInternal;
                                if (reactiveSet) {
                                    record._.proxyUsed.set(name, true);
                                }
                                store._.updateFields(record, { [name]: val });
                                if (reactiveSet) {
                                    record._.proxyUsed.delete(name);
                                }
                                return true;
                            });
                        },
                    });
                    record._proxyInternal = recordProxyInternal;
                    const recordProxy = reactive(recordProxyInternal);
                    record._proxy = recordProxy;
                    if (record?.[STORE_SYM]) {
                        record.recordByLocalId = store.recordByLocalId;
                        record._ = markRaw(toRaw(store._));
                        store = record;
                        Record.store = store;
                    }
                    for (const name of Model._.fields.keys()) {
                        record._.prepareField(record, name, recordProxy);
                    }
                    return recordProxy;
                }
            },
        }[OgClass.getName()];
        Model._ = markRaw(new ModelInternal());
        Object.assign(Model, {
            Class,
            records: reactive({}),
        });
        Models[Model.getName()] = Model;
        store[Model.getName()] = Model;
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new OgClass();
        obj.setup();
        for (const [name, val] of Object.entries(obj)) {
            if (isFieldDefinition(val)) {
                Model._.prepareField(name, val);
            }
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
