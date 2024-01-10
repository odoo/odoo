/* @odoo-module */

import { reactive } from "@odoo/owl";

const ID_CONTAINER = {};

function uuid(model) {
    if (!(model in ID_CONTAINER)) {
        ID_CONTAINER[model] = 1;
    }
    return `${model}_${ID_CONTAINER[model]++}`;
}

let dummyNameId = 1;

function getDummyName(model, suffix) {
    return `__dummy_${model}_${dummyNameId++}_${suffix}__`;
}

function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

function mapObj(obj, fn) {
    return Object.fromEntries(Object.entries(obj).map(([k, v], i) => [k, fn(k, v, i)]));
}

const RELATION_TYPES = new Set(["many2many", "many2one", "one2many"]);
const X2MANY_TYPES = new Set(["many2many", "one2many"]);
const EXEMPTED_AUTOMATIC_LOAD = ["pos.session", "pos.config"];
const AVAILABLE_EVENT = ["create", "update", "delete"];

function processModelDefs(modelDefs) {
    modelDefs = clone(modelDefs);
    const inverseMap = new Map();
    const many2oneFields = [];
    for (const model in modelDefs) {
        const fields = modelDefs[model];
        for (const fieldName in fields) {
            const field = fields[fieldName];
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
                let [inverseField, ...others] = Object.entries(comodel).filter(
                    (model_name, f) => model_name === field.relation
                );
                if (others.length > 0) {
                    throw new Error("Many2many relation must have only one inverse");
                }
                if (!inverseField) {
                    const dummyName = getDummyName(model, "ids");
                    inverseField = {
                        name: dummyName,
                        type: "many2many",
                        relation: model,
                        dummy: true,
                    };
                    comodel[dummyName] = inverseField;
                }
                inverseMap.set(field, inverseField);
                inverseMap.set(inverseField, field);
            } else if (field.type === "one2many") {
                let inverseField = Object.values(comodel).find(
                    (f) => f.relation === model && f.name === field.inverse_name
                );
                if (!inverseField) {
                    const dummyName = getDummyName(model, "id");
                    inverseField = {
                        name: dummyName,
                        type: "many2one",
                        relation: model,
                        dummy: true,
                    };
                    comodel[dummyName] = inverseField;
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

        const dummyName = getDummyName(model, "ids");
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

export class Base {
    constructor({ models, records, model, raw }) {
        this.models = models;
        this.records = records;
        this.model = model;
        this._raw = raw;
    }
    /**
     * Called during instantiation when the instance is fully-populated with field values.
     * Check @create inside `createRelatedModels` below.
     * @param {*} _vals
     */
    setup(_vals) {}
    update(vals) {
        this.model.update(this, vals);
    }
    delete() {
        this.model.delete(this);
    }
    serialize(orm = false) {
        const serializedData = this.model.serialize(this);

        if (orm) {
            const fields = this.model.modelFields;
            const serializedDataOrm = {};

            for (const [name, params] of Object.entries(fields)) {
                if (name.startsWith("__") && name.endsWith("__")) {
                    continue;
                }

                if (X2MANY_TYPES.has(params.type)) {
                    serializedDataOrm[name] = serializedData[name].map((id) => [4, id]);
                } else {
                    serializedDataOrm[name] = serializedData[name];
                }
            }

            return serializedDataOrm;
        }

        return serializedData;
    }
    get raw() {
        if (this.id in this._raw) {
            return this._raw[this.id];
        }

        return {};
    }
}

export function createRelatedModels(modelDefs, modelClasses = {}, indexes = {}) {
    const [inverseMap, processedModelDefs] = processModelDefs(modelDefs);
    const records = reactive(mapObj(processedModelDefs, () => reactive({})));
    const orderedRecords = reactive(mapObj(processedModelDefs, () => reactive([])));
    const callbacks = mapObj(processedModelDefs, () => []);
    const baseData = {};

    // object: model -> key -> keyval -> record
    const indexedRecords = reactive(
        mapObj(processedModelDefs, (model) => {
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
        })
    );

    function getFields(model) {
        return processedModelDefs[model];
    }

    function removeItem(array, item) {
        const index = array.indexOf(item);
        if (index >= 0) {
            array.splice(index, 1);
        }
    }

    function addItem(array, item) {
        const index = array.indexOf(item);
        if (index === -1) {
            array.push(item);
        }
    }

    function connect(field, ownerRecord, recordToConnect) {
        const inverse = inverseMap.get(field);

        if (typeof ownerRecord !== "object") {
            const model = field.model;
            ownerRecord = records[model][ownerRecord];
        }

        if (typeof recordToConnect !== "object") {
            const model = field.relation;
            recordToConnect = records[model][recordToConnect];
        }

        if (field.type === "many2one") {
            const prevConnectedRecord = ownerRecord[field.name];
            if (prevConnectedRecord === recordToConnect) {
                return;
            }
            if (recordToConnect && inverse.name in recordToConnect) {
                addItem(recordToConnect[inverse.name], ownerRecord);
            }
            if (prevConnectedRecord) {
                removeItem(prevConnectedRecord[inverse.name], ownerRecord);
            }
            ownerRecord[field.name] = recordToConnect;
        } else if (field.type === "one2many") {
            const prevConnectedRecord = recordToConnect[inverse.name];
            if (prevConnectedRecord === ownerRecord) {
                return;
            }
            recordToConnect[inverse.name] = ownerRecord;
            if (prevConnectedRecord) {
                removeItem(prevConnectedRecord[field.name], recordToConnect);
            }
            addItem(ownerRecord[field.name], recordToConnect);
        } else if (field.type === "many2many") {
            addItem(ownerRecord[field.name], recordToConnect);
            addItem(recordToConnect[inverse.name], ownerRecord);
        }
    }

    function disconnect(field, ownerRecord, recordToDisconnect) {
        if (!recordToDisconnect) {
            throw new Error("recordToDisconnect is undefined");
        }
        const inverse = inverseMap.get(field);
        if (field.type === "many2one") {
            const prevConnectedRecord = ownerRecord[field.name];
            if (prevConnectedRecord === recordToDisconnect) {
                ownerRecord[field.name] = undefined;
                removeItem(recordToDisconnect[inverse.name], ownerRecord);
            }
        } else if (field.type === "one2many") {
            removeItem(ownerRecord[field.name], recordToDisconnect);
            const prevConnectedRecord = recordToDisconnect[inverse.name];
            if (prevConnectedRecord === ownerRecord) {
                recordToDisconnect[inverse.name] = undefined;
            }
        } else if (field.type === "many2many") {
            removeItem(ownerRecord[field.name], recordToDisconnect);
            removeItem(recordToDisconnect[inverse.name], ownerRecord);
        }
    }

    function exists(model, id) {
        return id in records[model];
    }

    function create(model, vals, ignoreRelations = false, fromSerialized = false) {
        if (!("id" in vals)) {
            vals["id"] = uuid(model);
        }

        const Model = modelClasses[model] || Base;
        const record = reactive(
            new Model({ models, records, model: models[model], raw: baseData[model] })
        );
        const id = vals["id"];
        record.id = id;
        records[model][id] = record;

        const indexRecord = (key, keyVal, many) => {
            if (!(typeof keyVal === "string" || typeof keyVal === "number")) {
                return;
            }

            if (many) {
                if (!indexedRecords[model][key][keyVal]) {
                    indexedRecords[model][key][keyVal] = [];
                }

                indexedRecords[model][key][keyVal].push(record);
            } else {
                indexedRecords[model][key][keyVal] = record;
            }
        };

        // Save records in the corresponding indexes.
        for (const key of indexes[model] || []) {
            const keyVal = vals[key];

            if (Array.isArray(keyVal)) {
                for (const val of keyVal) {
                    indexRecord(key, val, true);
                }
            }

            indexRecord(key, keyVal, false);
        }

        const fields = getFields(model);
        for (const name in fields) {
            if (name === "id") {
                continue;
            }

            const field = fields[name];

            if (field.required && !(name in vals)) {
                throw new Error(`'${name}' field is required when creating '${model}' record.`);
            }

            if (RELATION_TYPES.has(field.type)) {
                if (X2MANY_TYPES.has(field.type)) {
                    record[name] = [];
                } else if (field.type === "many2one") {
                    record[name] = undefined;
                }

                if (ignoreRelations) {
                    continue;
                }

                const comodelName = field.relation;
                if (!(name in vals) || !vals[name]) {
                    continue;
                }

                if (X2MANY_TYPES.has(field.type)) {
                    if (fromSerialized) {
                        const ids = vals[name];
                        for (const id of ids) {
                            if (exists(comodelName, id)) {
                                connect(field, record, records[comodelName][id]);
                            }
                        }
                    } else {
                        for (const [command, ...items] of vals[name]) {
                            if (command === "create") {
                                const newRecords = items.map((_vals) => create(comodelName, _vals));
                                for (const record2 of newRecords) {
                                    connect(field, record, record2);
                                }
                            } else if (command === "link") {
                                const existingRecords = items.filter((record) =>
                                    exists(comodelName, record.id)
                                );
                                for (const record2 of existingRecords) {
                                    connect(field, record, record2);
                                }
                            }
                        }
                    }
                } else if (field.type === "many2one") {
                    const val = vals[name];
                    if (fromSerialized) {
                        if (exists(comodelName, val)) {
                            connect(field, record, records[comodelName][val]);
                        }
                    } else {
                        if (val instanceof Base) {
                            if (exists(comodelName, val.id)) {
                                connect(field, record, val);
                            }
                        } else {
                            const newRecord = create(comodelName, val);
                            connect(field, record, newRecord);
                        }
                    }
                }
            } else {
                record[name] = vals[name];
            }
        }

        record.setup(vals);
        return record;
    }

    function deserialize(model, vals) {
        return create(model, vals, false, true);
    }

    function update(model, record, vals) {
        const fields = getFields(model);
        for (const name in vals) {
            if (!(name in fields)) {
                continue;
            }
            const field = fields[name];
            const comodelName = field.relation;
            if (X2MANY_TYPES.has(field.type)) {
                for (const command of vals[name]) {
                    const [type, ...items] = command;
                    if (type === "unlink") {
                        for (const record2 of items) {
                            disconnect(field, record, record2);
                        }
                    } else if (type === "clear") {
                        const linkedRecs = record[name];
                        for (const record2 of [...linkedRecs]) {
                            disconnect(field, record, record2);
                        }
                    } else if (type === "create") {
                        const newRecords = items.map((vals) => create(comodelName, vals));
                        for (const record2 of newRecords) {
                            connect(field, record, record2);
                        }
                    } else if (type === "link") {
                        const existingRecords = items.filter((record) =>
                            exists(comodelName, record.id)
                        );
                        for (const record2 of existingRecords) {
                            connect(field, record, record2);
                        }
                    }
                }
            } else if (field.type === "many2one") {
                if (vals[name]) {
                    const id = vals[name]?.id || vals[name];
                    const exist = exists(comodelName, id);

                    if (exist) {
                        connect(field, record, vals[name]);
                    } else {
                        const newRecord = create(comodelName, vals[name]);
                        connect(field, record, newRecord);
                    }
                } else if (record[name]) {
                    const linkedRec = record[name];
                    disconnect(field, record, linkedRec);
                }
            } else {
                record[name] = vals[name];
            }
        }
    }

    function delete_(model, record) {
        const id = record.id;
        const fields = getFields(model);
        for (const name in fields) {
            const field = fields[name];
            if (X2MANY_TYPES.has(field.type)) {
                for (const record2 of [...record[name]]) {
                    disconnect(field, record, record2);
                }
            } else if (field.type === "many2one" && record[name]) {
                disconnect(field, record, record[name]);
            }
        }

        for (const [index, values] of Object.entries(indexedRecords[model])) {
            for (const [idx, vals] of Object.entries(values)) {
                if (Array.isArray(vals)) {
                    indexedRecords[model][index] = vals.filter((val) => val.id !== record.id);
                } else {
                    delete indexedRecords[model][index][idx];
                }
            }
        }

        orderedRecords[model] = orderedRecords[model].filter((rec) => rec.id !== record.id);

        delete records[model][id];

        models[model].triggerEvents("delete", id);
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
                return orderedRecords;
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
            create(vals) {
                return create(model, vals);
            },
            deserialize(vals) {
                return deserialize(model, vals);
            },
            createMany(valsList) {
                const result = [];
                for (const vals of valsList) {
                    result.push(create(model, vals));
                }
                return result;
            },
            update(record, vals) {
                return update(model, record, vals);
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
                return this.records[model][id];
            },
            readFirst() {
                if (!(model in this.records)) {
                    return;
                }
                return this.orderedRecords[model][0];
            },
            readBy(key, val) {
                if (!indexes[model].includes(key)) {
                    throw new Error(`Unable to get record by '${key}'`);
                }
                return this.indexedRecords[model][key][val];
            },
            readAll() {
                return this.orderedRecords[model];
            },
            readAllBy(key) {
                if (!this.indexes[model].includes(key)) {
                    throw new Error(`Unable to get record by '${key}'`);
                }
                return this.indexedRecords[model][key];
            },
            readMany(ids) {
                if (!(model in records)) {
                    return [];
                }
                return ids.map((id) => records[model][id]);
            },
            serialize(record) {
                const result = {};
                for (const name in fields) {
                    const field = fields[name];
                    if (field.type === "many2one") {
                        result[name] = record[name] ? record[name].id : undefined;
                    } else if (X2MANY_TYPES.has(field.type)) {
                        result[name] = [...record[name]].map((record) => record.id);
                    } else {
                        result[name] = record[name];
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
                return this.orderedRecords[model].map(fn);
            },
            flatMap(fn) {
                return this.orderedRecords[model].flatMap(fn);
            },
            forEach(fn) {
                return this.orderedRecords[model].forEach(fn);
            },
            some(fn) {
                return this.orderedRecords[model].some(fn);
            },
            every(fn) {
                return this.orderedRecords[model].every(fn);
            },
            find(fn) {
                return this.orderedRecords[model].find(fn);
            },
            filter(fn) {
                return this.orderedRecords[model].filter(fn);
            },
            sort(fn) {
                return this.orderedRecords[model].sort(fn);
            },
            indexOf(record) {
                return this.orderedRecords[model].indexOf(record);
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

    /**
     * Load the data without the relations then link the related records.
     * @param {*} rawData
     */
    function loadData(rawData, load = []) {
        const results = {};
        const missingRecords = {};

        for (const model in rawData) {
            if (!load.includes(model) && load.length !== 0) {
                continue;
            } else if (!results[model]) {
                results[model] = [];
            }

            const _records = rawData[model];
            for (const record of _records) {
                if (!baseData[model]) {
                    baseData[model] = {};
                }

                baseData[model][record.id] = record;
                const result = create(model, record, true);

                if (!(model in results)) {
                    results[model] = [];
                }

                results[model].push(result);
            }
        }

        const alreadyLinkedSet = new Set();

        // link the related records
        for (const model in rawData) {
            if (alreadyLinkedSet.has(model) || (!load.includes(model) && load.length !== 0)) {
                continue;
            }

            const rawRecords = rawData[model];
            const fields = getFields(model);
            for (const rawRec of rawRecords) {
                const recorded = records[model][rawRec.id];
                for (const name in fields) {
                    const field = fields[name];
                    alreadyLinkedSet.add(field);
                    if (X2MANY_TYPES.has(field.type)) {
                        if (name in rawRec) {
                            for (const id of rawRec[name]) {
                                if (field.relation in records) {
                                    const toConnect = records[field.relation][id];
                                    if (toConnect) {
                                        connect(field, recorded, toConnect);
                                    } else if (
                                        this[field.relation] &&
                                        !EXEMPTED_AUTOMATIC_LOAD.includes(field.relation)
                                    ) {
                                        if (!missingRecords[field.relation]) {
                                            missingRecords[field.relation] = new Set([id]);
                                        } else {
                                            missingRecords[field.relation].add(id);
                                        }
                                    }
                                }
                            }
                        }
                    } else if (field.type === "many2one" && rawRec[name]) {
                        if (field.relation in records) {
                            const id = rawRec[name];
                            const toConnect = records[field.relation][id];
                            if (toConnect) {
                                connect(field, recorded, toConnect);
                            } else if (
                                this[field.relation] &&
                                !EXEMPTED_AUTOMATIC_LOAD.includes(field.relation)
                            ) {
                                if (!missingRecords[field.relation]) {
                                    missingRecords[field.relation] = new Set([id]);
                                } else {
                                    missingRecords[field.relation].add(id);
                                }
                            }
                        }
                    }
                }
            }
        }

        for (const [model, values] of Object.entries(results)) {
            const valuesToAdd = [];
            const valuesToUpdate = [];

            if (!(model in orderedRecords)) {
                continue;
            }

            if (orderedRecords[model].length === 0) {
                orderedRecords[model] = values;
            } else {
                for (const value of values) {
                    const index = orderedRecords[model].findIndex((or) => or.id === value.id);

                    if (index === -1) {
                        valuesToAdd.push(value);
                    } else {
                        valuesToUpdate.push([index, value]);
                    }
                }

                for (const [index, value] of valuesToUpdate) {
                    orderedRecords[model][index] = value;
                }
                orderedRecords[model].unshift(...valuesToAdd);
            }

            const event = valuesToAdd.length > 0 ? "create" : "update";
            models[model].triggerEvents(event, values);
        }

        return { results, missingRecords };
    }

    models.loadData = loadData;
    return [models, records, indexedRecords];
}
