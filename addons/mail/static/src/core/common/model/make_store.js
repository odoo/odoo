import { markRaw, reactive } from "@odoo/owl";
import {
    RECORD_SYM,
    STORE_SYM,
    modelRegistry,
    _0,
    isRelation,
    ATTR_SYM,
    FIELD_DEFINITION_SYM,
} from "./misc";
import { Store } from "./store";
import { assignDefined } from "@mail/utils/common/misc";
import { Record } from "./record";
import { RecordInternal } from "./record_internal";
import { StoreInternal } from "./store_internal";
import { ModelInternal } from "./model_internal";

export function makeStore(env) {
    const localIdToRecord = reactive(new Map());
    const objectIdToLocalId = new Map();
    const dummyStore = new Store();
    dummyStore.Model = Store;
    dummyStore._ = new StoreInternal();
    dummyStore.localIdToRecord = localIdToRecord;
    dummyStore.objectIdToLocalId = objectIdToLocalId;
    dummyStore.env = env;
    let store = dummyStore;
    Record.store0 = dummyStore;
    /** @type {Object<string, typeof Record>} */
    const Models = {};
    dummyStore._.Models = Models;
    const OgClasses = {};
    for (const [name, _OgClass] of modelRegistry.getEntries()) {
        /** @type {typeof Record} */
        const OgClass = _OgClass;
        OgClasses[name] = OgClass;
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
                [RECORD_SYM] = true;
                constructor() {
                    super();
                    const this0 = this;
                    this0._0 = this0;
                    this0.Model = Model;
                    this0._ = this0[STORE_SYM] ? new StoreInternal() : new RecordInternal();
                    const this1 = new Proxy(this0, {
                        get(this0, name, this3) {
                            if (this0._.gettingField) {
                                return Reflect.get(this0, name, this3);
                            }
                            this3 = this0._.downgrade(this0, this3);
                            if (!Model._.fields.has(name)) {
                                return Reflect.get(this0, name, this3);
                            }
                            if (Model._.fieldsCompute.get(name) && !Model._.fieldsEager.get(name)) {
                                this0._.fieldsComputeInNeed.set(name, true);
                                if (this0._.fieldsComputeOnNeed.get(name)) {
                                    this0._.computeField(this0, name);
                                }
                            }
                            if (Model._.fieldsSort.get(name) && !Model._.fieldsEager.get(name)) {
                                this0._.fieldsSortInNeed.set(name, true);
                                if (this0._.fieldsSortOnNeed.get(name)) {
                                    this0._.sortField(this0, name);
                                }
                            }
                            this0._.gettingField = true;
                            const val = this3[name];
                            this0._.gettingField = false;
                            if (isRelation(Model, name)) {
                                const reclist3 = val._1;
                                if (Model._.fieldsMany.get(name)) {
                                    return reclist3;
                                }
                                return reclist3[0];
                            }
                            return val;
                        },
                        deleteProperty(this0, name) {
                            return store.MAKE_UPDATE(function R_deleteProperty() {
                                if (isRelation(Model, name)) {
                                    const reclist = this0[name];
                                    reclist.clear();
                                    return true;
                                }
                                return Reflect.deleteProperty(this0, name);
                            });
                        },
                        /**
                         * Using record.update(data) is preferable for performance to batch process
                         * when updating multiple fields at the same time.
                         */
                        set(this0, name, val) {
                            if (this0._.customAssignThroughProxy) {
                                const fn = this0._.customAssignThroughProxy.bind(this0);
                                this0._.customAssignThroughProxy = undefined;
                                fn();
                                return true;
                            }
                            // ensure each field write goes through the _.update method exactly once
                            if (this0._.updatingAttrs.has(name)) {
                                this0[name] = val;
                                return true;
                            }
                            return store.MAKE_UPDATE(function R_set() {
                                this0._.updatingFieldsThroughProxy.add(name);
                                store._.update(this0, { [name]: val });
                                this0._.updatingFieldsThroughProxy.delete(name);
                                return true;
                            });
                        },
                    });
                    this0._1 = this1;
                    const this2 = reactive(this1);
                    this0._2 = this2;
                    if (this0?.[STORE_SYM]) {
                        Record.store0 = this0;
                        assignDefined(
                            this0,
                            dummyStore,
                            Object.keys(Model.INSTANCE_INTERNALS).filter(
                                (k) => !["UPDATE", "Model", "_"].includes(k)
                            )
                        );
                        dummyStore.channels = undefined;
                        dummyStore.cannedReponses = undefined;
                        dummyStore.Model = Model;
                        this0._ = dummyStore._;
                        store = this0;
                        Object.assign(dummyStore.Store, { store, store0: store });
                        Object.assign(dummyStore.Model, { store: this0, _store0: this0 });
                    }
                    for (const fieldName of Model._.fields.keys()) {
                        this0._.prepareField(this0, fieldName);
                    }
                    return this2;
                }
            },
        }[OgClass.name];
        // Produce _.id and _.objectIdFields
        // For more structured object id mapping and re-shape on change of object id.
        // Useful for support of multi-identification on records
        Model._ = markRaw(new ModelInternal({ Class }));
        if (Model.id) {
            for (const andExpr of Model.id) {
                const data = {};
                for (const item of andExpr) {
                    /** @type {string} */
                    let fieldName = item;
                    if (fieldName.endsWith("!")) {
                        fieldName = fieldName.substring(0, fieldName.length - 1);
                        data[fieldName] = (record) => !!record[fieldName];
                    } else {
                        data[fieldName] = 0; // falsy so it's easier to distinguish it from function
                    }
                    if (!Model._.objectIdFields[fieldName]) {
                        Model._.objectIdFields[fieldName] = true;
                    }
                }
                Model._.id.push(data);
            }
        }
        Object.assign(Model, {
            env,
            records: reactive({}),
        });
        Models[name] = Model;
        store[name] = Model;
    }
    for (const Model of Object.values(Models)) {
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new OgClasses[Model.name]();
        for (const [name, val] of Object.entries(obj)) {
            if (obj?.[STORE_SYM] && name in Models) {
                continue;
            }
            if (Model.INSTANCE_INTERNALS[name]) {
                continue;
            }
            if (val?.[FIELD_DEFINITION_SYM]) {
                Model._.prepareField(name, val);
            } else {
                Model._.prepareField(name, { [ATTR_SYM]: true, defaultAsInit: true });
            }
        }
    }
    // Sync inverse fields
    for (const Model of Object.values(Models)) {
        for (const fieldName of Model._.fields.keys()) {
            if (!isRelation(Model, fieldName)) {
                continue;
            }
            const targetModel = Model._.fieldsTargetModel.get(fieldName);
            const inverse = Model._.fieldsInverse.get(fieldName);
            if (targetModel && !Models[targetModel]) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            if (inverse) {
                const OtherModel = Models[targetModel];
                const rel2TargetModel = OtherModel._.fieldsTargetModel.get(inverse);
                const rel2Inverse = OtherModel._.fieldsInverse.get(inverse);
                if (rel2TargetModel && rel2TargetModel !== Model.name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong targetModel. Expected: "${Model.name}" Actual: "${rel2TargetModel}"`
                    );
                }
                if (rel2Inverse && rel2Inverse !== fieldName) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong inverse. Expected: "${fieldName}" Actual: "${rel2Inverse}"`
                    );
                }
                OtherModel._.fieldsTargetModel.set(inverse, Model.name);
                OtherModel._.fieldsInverse.set(inverse, fieldName);
                // FIXME: lazy fields are not working properly with inverse.
                Model._.fieldsEager.set(fieldName, true);
                OtherModel._.fieldsEager.set(inverse, true);
            }
        }
    }
    /**
     * store/store0 are assigned on models at next step, but they are
     * required on Store model to make the initial store insert.
     */
    Object.assign(store.Store, { store, store0: store });
    // Make true store (as a model)
    store = _0(store.Store.insert());
    for (const Model of Object.values(Models)) {
        Model.store0 = store;
        Model.store = store._2;
        store._2[Model.name] = Model;
    }
    Object.assign(store, { storeReady: true });
    return store._2;
}
