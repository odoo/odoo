import { reactive } from "@odoo/owl";

const ID_CONTAINER = {};

function uuid(model) {
    if (!(model in ID_CONTAINER)) {
        ID_CONTAINER[model] = 1;
    }
    return `${model}_${ID_CONTAINER[model]++}`;
}

function getBackRef(model, fieldName) {
    return `<-${model}.${fieldName}`;
}

function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function mapObj(obj, fn) {
    return Object.fromEntries(Object.entries(obj).map(([k, v], i) => [k, fn(k, v, i)]));
}

const RELATION_TYPES = new Set(["many2many", "many2one", "one2many"]);
const X2MANY_TYPES = new Set(["many2many", "one2many"]);
const AVAILABLE_EVENT = ["create", "update", "delete"];
const SERIALIZABLE_MODELS = [
    "pos.order",
    "pos.order.line",
    "pos.payment",
    "pos.pack.operation.lot",
    "product.attribute.custom.value",
    "event.registration", // FIXME should be overrided from pos_event
    "event.registration.answer",
];

function processModelDefs(modelDefs) {
    modelDefs = clone(modelDefs);
    const inverseMap = new Map();
    const many2oneFields = [];
    for (const model in modelDefs) {
        const fields = modelDefs[model];
        for (const fieldName in fields) {
            const field = fields[fieldName];

            // Make sure that the field has a name and consistent with the key.
            if (field.name) {
                if (fieldName !== field.name) {
                    throw new Error(`Field name mismatch: ${fieldName} !== ${field.name}`);
                }
            } else {
                field.name = fieldName;
            }

            if (!RELATION_TYPES.has(field.type)) {
                continue;
            }

            if (inverseMap.has(field)) {
                continue;
            }

            const comodel = modelDefs[field.relation];
            if (!comodel) {
                continue;
                // throw new Error(`Model ${field.relation} not found`);
            }

            if (field.type === "many2many") {
                let [inverseField, ...others] = Object.values(comodel).filter(
                    (f) =>
                        model === f.relation &&
                        f.relation_table === field.relation_table &&
                        field.name !== f.name
                );
                if (others.length > 0) {
                    throw new Error("Many2many relation must have only one inverse");
                }
                if (!inverseField) {
                    const backRefName = getBackRef(model, field.name);
                    inverseField = {
                        name: backRefName,
                        type: "many2many",
                        relation: model,
                        inverse_name: field.name,
                        dummy: true,
                    };
                    comodel[backRefName] = inverseField;
                }
                inverseMap.set(field, inverseField);
                inverseMap.set(inverseField, field);
            } else if (field.type === "one2many") {
                let inverseField = Object.values(comodel).find(
                    (f) => f.relation === model && f.name === field.inverse_name
                );
                if (!inverseField) {
                    const backRefName = getBackRef(model, field.name);
                    inverseField = {
                        name: backRefName,
                        type: "many2one",
                        relation: model,
                        inverse_name: field.name,
                        dummy: true,
                    };
                    comodel[backRefName] = inverseField;
                }
                inverseMap.set(field, inverseField);
                inverseMap.set(inverseField, field);
            } else if (field.type === "many2one") {
                many2oneFields.push([model, field]);
            }
        }
    }

    for (const [model, field] of many2oneFields) {
        if (inverseMap.has(field)) {
            continue;
        }

        const comodel = modelDefs[field.relation];
        if (!comodel) {
            continue;
            // throw new Error(`Model ${field.relation} not found`);
        }

        const dummyName = getBackRef(model, field.name);
        const dummyField = {
            name: dummyName,
            type: "one2many",
            relation: model,
            inverse_name: field.name,
            dummy: true,
        };
        comodel[dummyName] = dummyField;
        inverseMap.set(field, dummyField);
        inverseMap.set(dummyField, field);
    }
    return [inverseMap, modelDefs];
}

function makeRelatedProxy(target) {
    const PROXY_BYPASS = ["model", "models", "records", "uiState"];

    const processGet = function (target, prop, receiver) {
        const fieldProps = target.model.modelFields[prop];
        const relation = target.models[fieldProps?.relation];

        if (!fieldProps && !relation && typeof target[prop] !== "function") {
            return Reflect.get(target, prop, receiver);
        }

        let value;
        if (fieldProps && X2MANY_TYPES.has(fieldProps.type)) {
            value = [];
        }

        if (fieldProps && X2MANY_TYPES.has(fieldProps.type)) {
            value = relation?.readMany(Reflect.get(target, prop, receiver) || []) || [];
        } else if (fieldProps && fieldProps.type === "many2one") {
            value = relation?.read(Reflect.get(target, prop, receiver));
        } else {
            value = Reflect.get(target, prop, receiver);
        }

        return value;
    };

    const processSet = function (prop, value) {
        let val;
        if (Array.isArray(value)) {
            val = value.map((v) => v?.id || v);
        } else {
            val = value?.id || value;
        }

        return val;
    };

    return new Proxy(target, {
        get: function (target, prop, receiver) {
            if (PROXY_BYPASS.includes(prop)) {
                return Reflect.get(target, prop, receiver);
            }

            return processGet(target, prop, receiver);
        },
        set: function (target, prop, value, receiver) {
            if (PROXY_BYPASS.includes(prop)) {
                Reflect.set(target, prop, value, receiver);
                return true;
            }

            Reflect.set(target, prop, processSet(prop, value), receiver);
            return true;
        },
    });
}

export class Base {
    constructor({ models, records, model }) {
        this.models = models;
        this.records = records;
        this.model = model;
    }
    /**
     * Called during instantiation when the instance is fully-populated with field values.
     * Check @create inside `createRelatedModels` below.
     * @param {*} _vals
     */
    setup(_vals) {
        // Allow custom fields
        for (const [key, val] of Object.entries(_vals)) {
            // Prevent extra fields that begin by _ to be overrided
            if (key in this.model.modelFields) {
                continue;
            }

            if (key.startsWith("_") && !key.startsWith("__")) {
                this[key] = val;
            }
        }
    }

    setupState(vals) {
        this.uiState = vals;
    }

    serializeState() {
        return { ...this.uiState };
    }

    delete() {
        return this.model.delete(this);
    }
    /**
     * @param {object} options
     * @param {boolean} options.orm - [true] if result is to be sent to the server
     */
    serialize(options = {}) {
        const orm = options.orm ?? false;

        const serializedData = this.model.serialize(this, { orm });

        if (orm) {
            const fields = this.model.modelFields;
            const serializedDataOrm = {};

            // We only care about the fields present in python model
            for (const [name, params] of Object.entries(fields)) {
                if (params.dummy) {
                    continue;
                }
                if (params.local || params.related || params.compute) {
                    continue;
                }

                if (X2MANY_TYPES.has(params.type)) {
                    serializedDataOrm[name] = serializedData[name].map((id) => {
                        let serData = {};
                        let data = {};

                        if (
                            !SERIALIZABLE_MODELS.includes(params.relation) &&
                            typeof id === "number"
                        ) {
                            return [4, id];
                        } else if (!SERIALIZABLE_MODELS.includes(params.relation)) {
                            throw new Error(
                                "Trying to create a non serializable record" + params.relation
                            );
                        }

                        if (params.relation !== params.model) {
                            data = this.records[params.relation].get(id).serialize(options);
                            data.id = typeof id === "number" ? id : parseInt(id.split("_")[1]);
                        } else {
                            return typeof id === "number" ? id : parseInt(id.split("_")[1]);
                        }

                        serData = typeof id === "number" ? [1, id, data] : [0, 0, data];

                        for (const [key, value] of Object.entries(serData[2])) {
                            if (
                                this.models[params.relation].modelFields[key]?.relation &&
                                typeof value === "string"
                            ) {
                                serData[2][key] = parseInt(value.split("_")[1]);
                            }
                        }

                        return serData;
                    });
                } else {
                    let value = serializedData[name];
                    if (name === "id" && typeof value === "string") {
                        value = serializedData[name].split("_")[1];
                    }
                    serializedDataOrm[name] = value !== undefined ? value : false;
                }
            }

            return serializedDataOrm;
        }

        return serializedData;
    }
    get raw() {
        return this._raw ?? {};
    }
}

export function createRelatedModels(modelDefs, modelClasses = {}, indexes = {}) {
    const [inverseMap, processedModelDefs] = processModelDefs(modelDefs);
    const records = mapObj(processedModelDefs, () => reactive(new Map()));
    const callbacks = mapObj(processedModelDefs, () => []);
    const orderedArrayCaches = {};
    const baseData = {};

    // object: model -> key -> keyval -> record
    const indexedRecords = mapObj(processedModelDefs, (model) => {
        const container = reactive({});

        // We always want an index by id
        if (!indexes[model]) {
            indexes[model] = ["id"];
        } else {
            indexes[model].push("id");
        }

        for (const key of indexes[model] || []) {
            container[key] = reactive({});
        }

        baseData[model] = {};
        return container;
    });

    function getFields(model) {
        return processedModelDefs[model];
    }

    function index(model, record) {
        for (const key of indexes[model] || []) {
            const keyVal = record.raw[key] || record[key];
            if (Array.isArray(keyVal)) {
                for (const keyV of keyVal) {
                    if (!indexedRecords[model][key][keyV.id]) {
                        indexedRecords[model][key][keyV.id] = new Map();
                    }
                    indexedRecords[model][key][keyV.id].set(record.id, record);
                }
            } else {
                indexedRecords[model][key][keyVal] = record;
            }
        }
    }

    function create(model, vals, delayedSetup = false) {
        if (!("id" in vals)) {
            vals["id"] = uuid(model);
        }
        delete orderedArrayCaches[model];
        const Model = modelClasses[model] || Base;
        const recordWoProxy = new Model({ models, records, model: models[model] });
        const id = vals["id"];

        recordWoProxy._raw = baseData[model][id];
        recordWoProxy.id = id;
        const record = makeRelatedProxy(recordWoProxy);
        records[model].set(record.id, record);

        for (const name in vals) {
            const field = processedModelDefs[model][name];
            const inverse = inverseMap.get(field);

            record[name] = vals[name];

            if (inverse && !delayedSetup && !inverse.dummy) {
                let inverseId = vals[name]?.id || vals[name];

                if (Array.isArray(vals[name]) && vals[name].length) {
                    const newRecs = vals[name]
                        .filter((v) => !v.id)
                        .map((val) => {
                            val[inverse.name] = id;
                            return create(inverse.model, val);
                        });
                    inverseId = newRecs.map((rec) => rec.id);
                } else if (
                    !vals[name]?.id &&
                    typeof vals[name] === "object" &&
                    !Array.isArray(vals[name])
                ) {
                    vals[name][inverse.name] = id;
                    const newRec = create(inverse.model, vals[name]);
                    inverseId = newRec.id;
                }

                if (!inverseId) {
                    continue;
                }

                if (X2MANY_TYPES.has(inverse.type)) {
                    if (X2MANY_TYPES.has(field.type)) {
                        for (const rec of vals[name]) {
                            records[inverse.model].get(rec.id)[inverse.name] = [
                                ...records[inverse.model].get(rec.id)[inverse.name],
                                id,
                            ].filter((v) => v);
                        }
                    } else {
                        records[inverse.model].get(inverseId)[inverse.name] = [
                            ...records[inverse.model].get(inverseId)[inverse.name],
                            id,
                        ].filter((v) => v);
                    }
                } else {
                    if (X2MANY_TYPES.has(field.type)) {
                        for (const rec of vals[name]) {
                            records[inverse.model].get(rec.id)[inverse.name] = id;
                        }
                    } else {
                        records[inverse.model].get(inverseId)[inverse.name] = id;
                    }
                }
            }
        }

        // Delayed setup is usefull when using loadData method.
        // Some records must be linked to other records before it can configure itself.
        if (!delayedSetup) {
            record.setup(vals);
        }

        index(model, record);
        return record;
    }

    function delete_(model, record) {
        const id = record.id;
        delete orderedArrayCaches[model];

        for (const field in record) {
            const fieldParams = processedModelDefs[model][field];
            const inverse = inverseMap.get(fieldParams);

            if (inverse && !inverse.dummy) {
                const inverseId = record[field]?.id || record[field];
                const invRec = records[inverse.model].get(inverseId);

                if (!invRec) {
                    continue;
                }

                if (X2MANY_TYPES.has(inverse.type)) {
                    invRec[inverse.name] = records[inverse.model]
                        .get(inverseId)
                        [inverse.name].filter((rec) => rec.id !== record.id);
                } else {
                    invRec[inverse.name] = false;
                }
            }
        }

        records[model].delete(id);

        for (const key of indexes[model] || []) {
            const keyVal = record.raw[key];
            if (Array.isArray(keyVal)) {
                for (const val of keyVal) {
                    indexedRecords[model][key][val].delete(record.id);
                }
            } else {
                delete indexedRecords[model][key][keyVal];
            }
        }
        models[model].triggerEvents("delete", id);
        return id;
    }

    function createCRUD(model, fields) {
        return {
            // We need to read these object from this to keep
            // the reactivity. Otherwise, we read the fields on
            // reactive with no callback.
            get records() {
                return records;
            },
            get orderedRecords() {
                if (!orderedArrayCaches[model]) {
                    orderedArrayCaches[model] = Array.from(records[model].values());
                }
                return orderedArrayCaches[model];
            },
            get indexedRecords() {
                return indexedRecords;
            },
            get indexes() {
                return indexes;
            },
            get modelName() {
                return model;
            },
            get modelFields() {
                return getFields(this.modelName);
            },
            create(vals, ignoreRelations = false, fromSerialized = false, delayedSetup = false) {
                return create(model, vals, ignoreRelations, fromSerialized, delayedSetup);
            },
            createMany(valsList) {
                const result = [];
                for (const vals of valsList) {
                    result.push(create(model, vals));
                }
                return result;
            },
            delete(record) {
                return delete_(model, record);
            },
            deleteMany(records) {
                const result = [];
                for (const record of records) {
                    result.push(delete_(model, record));
                }
                return result;
            },
            read(id) {
                if (!(model in this.records)) {
                    return;
                }
                return this.records[model].get(id);
            },
            readFirst() {
                if (!(model in this.records)) {
                    return;
                }
                return this.orderedRecords[0];
            },
            readBy(key, val) {
                if (!indexes[model].includes(key)) {
                    throw new Error(`Unable to get record by '${key}'`);
                }
                const result = this.indexedRecords[model][key][val];
                if (result instanceof Map) {
                    return Array.from(result.values());
                }
                return result;
            },
            readAll() {
                return this.orderedRecords;
            },
            readAllBy(key) {
                if (!this.indexes[model].includes(key)) {
                    throw new Error(`Unable to get record by '${key}'`);
                }
                if (!X2MANY_TYPES.has(fields[key].type)) {
                    return this.indexedRecords[model][key];
                } else {
                    return mapObj(this.indexedRecords[model][key], (_, v) =>
                        Array.from(v.values())
                    );
                }
            },
            readMany(ids) {
                if (!(model in records)) {
                    return [];
                }
                return ids.map((id) => records[model].get(id));
            },
            /**
             * @param {object} options
             * @param {boolean} options.orm - Exclude local & related fields from the serialization
             */
            serialize(record, options = {}) {
                const orm = options.orm ?? false;
                const result = {};
                for (const name in fields) {
                    const field = fields[name];
                    if ((orm && field.local) || (orm && field.related) || (orm && field.compute)) {
                        continue;
                    }

                    if (field.type === "many2one") {
                        result[name] = record[name]?.id || (!orm && record.raw[name]) || false;
                    } else if (X2MANY_TYPES.has(field.type)) {
                        const ids = [...record[name]].map((record) => record.id);
                        result[name] = ids.length ? ids : (!orm && record.raw[name]) || [];
                    } else if (typeof record[name] === "object") {
                        result[name] = JSON.stringify(record[name]);
                    } else {
                        result[name] = record[name] !== undefined ? record[name] : false;
                    }
                }
                return result;
            },
            // aliases
            getAllBy() {
                return this.readAllBy(...arguments);
            },
            getAll() {
                return this.readAll(...arguments);
            },
            getBy() {
                return this.readBy(...arguments);
            },
            get() {
                return this.read(...arguments);
            },
            getFirst() {
                return this.readFirst(...arguments);
            },
            // array prototype
            map(fn) {
                return this.orderedRecords.map(fn);
            },
            reduce(fn, initialValue) {
                return this.orderedRecords.reduce(fn, initialValue);
            },
            flatMap(fn) {
                return this.orderedRecords.flatMap(fn);
            },
            forEach(fn) {
                return this.orderedRecords.forEach(fn);
            },
            some(fn) {
                return this.orderedRecords.some(fn);
            },
            every(fn) {
                return this.orderedRecords.every(fn);
            },
            find(fn) {
                return this.orderedRecords.find(fn);
            },
            filter(fn) {
                return this.orderedRecords.filter(fn);
            },
            sort(fn) {
                return this.orderedRecords.sort(fn);
            },
            indexOf(record) {
                return this.orderedRecords.indexOf(record);
            },
            get length() {
                return Object.keys(this.records[model]).length;
            },
            // External callbacks
            addEventListener(event, callback) {
                if (!AVAILABLE_EVENT.includes(event)) {
                    throw new Error(`Event '${event}' is not available`);
                }

                if (!(event in callbacks[model])) {
                    callbacks[model][event] = [];
                }

                callbacks[model][event].push(callback);
            },
            triggerEvents(event, values) {
                if (
                    !(event in callbacks[model]) ||
                    callbacks[model][event].length === 0 ||
                    values.length === 0
                ) {
                    return;
                }

                for (const callback of callbacks[model][event]) {
                    callback(values);
                }
            },
        };
    }

    const models = mapObj(processedModelDefs, (model, fields) => createCRUD(model, fields));

    function replaceDataByKey(key, rawData) {
        const newRecords = {};
        for (const model in rawData) {
            const uiState = {};
            const rawDataIdx = rawData[model].map((r) => r[key]);
            const rec = records[model];

            for (const data of Object.values(rec)) {
                if (rawDataIdx.includes(data[key])) {
                    if (data.uiState) {
                        uiState[data[key]] = { ...data.uiState };
                    }
                    data.delete();
                }
            }

            const data = rawData[model];
            const newRec = this.loadData({ [model]: data });
            for (const record of newRec[model]) {
                if (uiState[record[key]]) {
                    record.setupState(uiState[record[key]]);
                }
            }

            if (!newRecords[model]) {
                newRecords[model] = [];
            }

            newRecords[model].push(...newRec[model]);
        }

        return newRecords;
    }

    /**
     * Load the data without the relations then link the related records.
     * @param {*} rawData
     */
    function loadData(rawData, load = [], fromSerialized = false) {
        const eventToTrigger = mapObj(processedModelDefs, () => ({
            updated: new Map(),
            created: new Map(),
        }));
        const results = {};
        const modelToSetup = [];

        for (const model in rawData) {
            if (!load.includes(model) && load.length !== 0) {
                continue;
            } else if (!results[model]) {
                results[model] = [];
                baseData[model] = {};
            }

            for (const rawRec of rawData[model]) {
                baseData[model][rawRec.id] = rawRec;

                const toUpdate = records[model].get(rawRec.id);
                const newRecord = create(model, rawRec, true);
                if (toUpdate) {
                    eventToTrigger[model].updated.set(newRecord.id, newRecord);
                } else {
                    eventToTrigger[model].created.set(newRecord.id, newRecord);
                }

                results[model].push(newRecord);
                modelToSetup.push({ raw: rawRec, record: newRecord });
            }
        }

        // Setup all records when relations are linked
        for (const { raw, record } of modelToSetup) {
            record.setup(raw);
        }

        for (const [model, values] of Object.entries(eventToTrigger)) {
            const modelInst = models[model];
            if (values.created.size !== 0) {
                modelInst.triggerEvents("create", Array.from(values.created.values()));
            }

            if (values.updated.size !== 0) {
                modelInst.triggerEvents("update", Array.from(values.updated.values()));
            }
        }

        return results;
    }

    models.loadData = loadData;
    models.replaceDataByKey = replaceDataByKey;

    return { models, records, indexedRecords };
}
