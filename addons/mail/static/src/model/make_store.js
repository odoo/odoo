import { reactive, toRaw } from "@odoo/owl";
import { Store } from "./store";
import {
    IS_FIELD_SYM,
    IS_RECORD_LIST_SYM,
    IS_RECORD_SYM,
    isField,
    isMany,
    isRelation,
    modelRegistry,
} from "./misc";
import { RecordList } from "./record_list";
import { onChange } from "@mail/utils/common/misc";
import { Record } from "./record";
import { StoreInternal } from "./store_internal";

/** @returns {import("models").Store} */
export function makeStore(env, { localRegistry } = {}) {
    const recordByLocalId = reactive(new Map());
    // fake store for now, until it becomes a model
    /** @type {import("models").Store} */
    Store.env = env;
    let store = new Store();
    store.env = env;
    store.Model = Store;
    store._ = new StoreInternal();
    store._raw = store;
    store._proxyInternal = store;
    store._proxy = store;
    store.recordByLocalId = recordByLocalId;
    Record.store = store;
    /** @type {Object<string, typeof Record>} */
    const Models = {};
    const chosenModelRegistry = localRegistry ?? modelRegistry;
    for (const [name, _OgClass] of chosenModelRegistry.getEntries()) {
        /** @type {typeof Record} */
        const OgClass = _OgClass;
        if (store[name]) {
            throw new Error(`There must be no duplicated Model Names (duplicate found: ${name})`);
        }
        // classes cannot be made reactive because they are functions and they are not supported.
        // work-around: make an object whose prototype is the class, so that static props become
        // instance props.
        /** @type {typeof Record} */
        const Model = Object.create(OgClass);
        // Produce another class with changed prototype, so that there are automatic get/set on relational fields
        const Class = {
            [OgClass.name]: class extends OgClass {
                [IS_RECORD_SYM] = true;
                constructor() {
                    super();
                    const record = this;
                    record._proxyUsed = new Set();
                    record._updateFields = new Set();
                    record._raw = record;
                    record.Model = Model;
                    const recordProxyInternal = new Proxy(record, {
                        get(record, name, recordFullProxy) {
                            recordFullProxy = record._downgradeProxy(recordFullProxy);
                            const field = record._fields.get(name);
                            if (field) {
                                if (field.compute && !field.eager) {
                                    field.computeInNeed = true;
                                    if (field.computeOnNeed) {
                                        field.compute();
                                    }
                                }
                                if (field.sort && !field.eager) {
                                    field.sortInNeed = true;
                                    if (field.sortOnNeed) {
                                        field.sort();
                                    }
                                }
                                if (isRelation(field)) {
                                    const recordList = field.value;
                                    const recordListFullProxy =
                                        recordFullProxy._fields.get(name).value._proxy;
                                    if (isMany(recordList)) {
                                        return recordListFullProxy;
                                    }
                                    return recordListFullProxy[0];
                                }
                            }
                            return Reflect.get(record, name, recordFullProxy);
                        },
                        deleteProperty(record, name) {
                            return store.MAKE_UPDATE(function recordDeleteProperty() {
                                const field = record._fields.get(name);
                                if (field && isRelation(field)) {
                                    const recordList = field.value;
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
                        set(record, name, val) {
                            // ensure each field write goes through the updateFields method exactly once
                            if (record._updateFields.has(name)) {
                                record[name] = val;
                                return true;
                            }
                            return store.MAKE_UPDATE(function recordSet() {
                                record._proxyUsed.add(name);
                                store.updateFields(record, { [name]: val });
                                record._proxyUsed.delete(name);
                                return true;
                            });
                        },
                    });
                    record._proxyInternal = recordProxyInternal;
                    const recordProxy = reactive(recordProxyInternal);
                    record._proxy = recordProxy;
                    if (record instanceof Store) {
                        record.recordByLocalId = store.recordByLocalId;
                        record._ = store._;
                        store = record;
                        Record.store = store;
                    }
                    for (const [name, fieldDefinition] of Model._fields) {
                        const SYM = record[name]?.[0];
                        const field = { [SYM]: true, eager: fieldDefinition.eager, name };
                        record._fields.set(name, field);
                        if (isRelation(SYM)) {
                            // Relational fields contain symbols for detection in original class.
                            // This constructor is called on genuine records:
                            // - 'one' fields => undefined
                            // - 'many' fields => RecordList
                            // record[name]?.[0] is ONE_SYM or MANY_SYM
                            const recordList = new RecordList();
                            Object.assign(recordList, {
                                [IS_RECORD_LIST_SYM]: true,
                                [SYM]: true,
                                field,
                                name,
                                owner: record,
                                _raw: recordList,
                            });
                            recordList.store = store;
                            field.value = recordList;
                        } else {
                            record[name] = fieldDefinition.default;
                        }
                        if (fieldDefinition.compute) {
                            if (!fieldDefinition.eager) {
                                onChange(recordProxy, name, () => {
                                    if (field.computing) {
                                        /**
                                         * Use a reactive to reset the computeInNeed flag when there is
                                         * a change. This assumes when other reactive are still
                                         * observing the value, its own callback will reset the flag to
                                         * true through the proxy getters.
                                         */
                                        field.computeInNeed = false;
                                    }
                                });
                                // reset flags triggered by registering onChange
                                field.computeInNeed = false;
                                field.sortInNeed = false;
                            }
                            const proxy2 = reactive(recordProxy, function computeObserver() {
                                field.requestCompute();
                            });
                            Object.assign(field, {
                                compute: () => {
                                    field.computing = true;
                                    field.computeOnNeed = false;
                                    store.updateFields(record, {
                                        [name]: fieldDefinition.compute.call(proxy2),
                                    });
                                    field.computing = false;
                                },
                                requestCompute: ({ force = false } = {}) => {
                                    if (store._.UPDATE !== 0 && !force) {
                                        store.ADD_QUEUE(field, "compute");
                                    } else {
                                        if (field.eager || field.computeInNeed) {
                                            field.compute();
                                        } else {
                                            field.computeOnNeed = true;
                                        }
                                    }
                                },
                            });
                        }
                        if (fieldDefinition.sort) {
                            if (!fieldDefinition.eager) {
                                onChange(recordProxy, name, () => {
                                    if (field.sorting) {
                                        /**
                                         * Use a reactive to reset the inNeed flag when there is a
                                         * change. This assumes if another reactive is still observing
                                         * the value, its own callback will reset the flag to true
                                         * through the proxy getters.
                                         */
                                        field.sortInNeed = false;
                                    }
                                });
                                // reset flags triggered by registering onChange
                                field.computeInNeed = false;
                                field.sortInNeed = false;
                            }
                            const proxy2 = reactive(recordProxy, function sortObserver() {
                                field.requestSort();
                            });
                            Object.assign(field, {
                                sort: () => {
                                    field.sortOnNeed = false;
                                    field.sorting = true;
                                    store.sortRecordList(
                                        proxy2._fields.get(name).value._proxy,
                                        fieldDefinition.sort.bind(proxy2)
                                    );
                                    field.sorting = false;
                                },
                                requestSort: ({ force } = {}) => {
                                    if (store._.UPDATE !== 0 && !force) {
                                        store.ADD_QUEUE(field, "sort");
                                    } else {
                                        if (field.eager || field.sortInNeed) {
                                            field.sort();
                                        } else {
                                            field.sortOnNeed = true;
                                        }
                                    }
                                },
                            });
                        }
                        if (fieldDefinition.onUpdate) {
                            /** @type {Function} */
                            let observe;
                            Object.assign(field, {
                                onUpdate: () => {
                                    /**
                                     * Forward internal proxy for performance as onUpdate does not
                                     * need reactive (observe is called separately).
                                     */
                                    fieldDefinition.onUpdate.call(record._proxyInternal);
                                    observe?.();
                                },
                            });
                            store._onChange(recordProxy, name, (obs) => {
                                observe = obs;
                                if (store._.UPDATE !== 0) {
                                    store.ADD_QUEUE(field, "onUpdate");
                                } else {
                                    field.onUpdate();
                                }
                            });
                        }
                    }
                    return recordProxy;
                }
            },
        }[OgClass.name];
        Object.assign(Model, {
            Class,
            env,
            records: reactive({}),
            _fields: new Map(),
        });
        Models[name] = Model;
        store[name] = Model;
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new OgClass();
        for (const [name, val] of Object.entries(obj)) {
            const SYM = val?.[0];
            if (!isField(SYM)) {
                continue;
            }
            Model._fields.set(name, { [IS_FIELD_SYM]: true, [SYM]: true, ...val[1] });
        }
    }
    // Sync inverse fields
    for (const Model of Object.values(Models)) {
        for (const [name, fieldDefinition] of Model._fields) {
            if (!isRelation(fieldDefinition)) {
                continue;
            }
            const { targetModel, inverse } = fieldDefinition;
            if (targetModel && !Models[targetModel]) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            if (inverse) {
                const rel2 = Models[targetModel]._fields.get(inverse);
                if (rel2.targetModel && rel2.targetModel !== Model.name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong targetModel. Expected: "${Model.name}" Actual: "${rel2.targetModel}"`
                    );
                }
                if (rel2.inverse && rel2.inverse !== name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong inverse. Expected: "${name}" Actual: "${rel2.inverse}"`
                    );
                }
                Object.assign(rel2, { targetModel: Model.name, inverse: name });
                // // FIXME: lazy fields are not working properly with inverse.
                fieldDefinition.eager = true;
                rel2.eager = true;
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
        store._proxy[Model.name] = Model;
    }
    Object.assign(store, { Models, storeReady: true });
    return store._proxy;
}
