import { reactive, toRaw } from "@odoo/owl";

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

    setDirty() {
        if (typeof this.id === "number") {
            this.models.commands[this.model.modelName].update.add(this.id);
        }
    }

    setupState(vals) {
        this.uiState = vals;
    }

    serializeState() {
        return { ...this.uiState };
    }

    update(vals, opts = {}) {
        this.model.update(this, vals, opts);
    }
    delete(opts = {}) {
        return this.model.delete(this, opts);
    }
    /**
     * @param {object} options
     * @param {boolean} options.orm - [true] if result is to be sent to the server
     */
    serialize(options = {}) {
        const orm = options.orm ?? false;
        const clear = options.clear ?? false;

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
                    serializedDataOrm[name] = serializedData[name]
                        .map((id) => {
                            let serData = false;
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
                                data = this.records[params.relation][id].serialize(options);
                                data.id = typeof id === "number" ? id : parseInt(id.split("_")[1]);
                            } else {
                                return typeof id === "number" ? id : parseInt(id.split("_")[1]);
                            }

                            if (
                                typeof id === "number" &&
                                this.models.commands[params.relation].update.has(id)
                            ) {
                                serData = [1, id, data];

                                if (clear) {
                                    this.models.commands[params.relation].update.delete(id);
                                }
                            } else if (typeof id !== "number") {
                                serData = [0, 0, data];
                            }

                            if (serData) {
                                for (const [key, value] of Object.entries(serData[2])) {
                                    if (
                                        this.models[params.relation].modelFields[key]?.relation &&
                                        typeof value === "string"
                                    ) {
                                        serData[2][key] = parseInt(value.split("_")[1]);
                                    }
                                }
                            }

                            return serData;
                        })
                        .filter((s) => s);

                    if (this.models.commands[params.model].delete.has(name)) {
                        const ids = this.models.commands[params.model].delete.get(name);
                        for (const id of ids) {
                            serializedDataOrm[name].push([3, id]);
                        }
                        if (clear) {
                            this.models.commands[params.model].delete.delete(name);
                        }
                    }
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
    _getCacheSet(fieldName) {
        const cacheName = `_${fieldName}`;
        if (!(cacheName in this)) {
            this[cacheName] = new Set();
        }
        return this[cacheName];
    }
    get raw() {
        return this._raw ?? {};
    }
}

export function createRelatedModels(modelDefs, modelClasses = {}, opts = {}) {
    const indexes = opts.databaseIndex || {};
    const keyByModel = opts.databaseTable.reduce((acc, { name, key }) => {
        acc[name] = key;
        return acc;
    }, {});
    const [inverseMap, processedModelDefs] = processModelDefs(modelDefs);
    const records = mapObj(processedModelDefs, () => reactive({}));
    const orderedRecords = mapObj(processedModelDefs, () => reactive([]));
    const callbacks = mapObj(processedModelDefs, () => []);
    const commands = mapObj(processedModelDefs, () => ({
        delete: new Map(),
        update: new Set(),
    }));
    const baseData = {};
    const missingFields = {};

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

    function removeItem(record, fieldName, item) {
        if (typeof record !== "object") {
            return;
        }

        const cacheSet = record._getCacheSet(fieldName);
        if (cacheSet.has(toRaw(item))) {
            cacheSet.delete(toRaw(item));
            const index = record[fieldName].indexOf(item);
            record[fieldName].splice(index, 1);
        }
    }

    function addItem(record, fieldName, item) {
        const cacheSet = record._getCacheSet(fieldName);
        if (!cacheSet.has(toRaw(item))) {
            cacheSet.add(toRaw(item));
            record[fieldName].push(item);
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
            if (toRaw(prevConnectedRecord) === toRaw(recordToConnect)) {
                return;
            }
            if (recordToConnect && inverse.name in recordToConnect) {
                addItem(recordToConnect, inverse.name, ownerRecord);
            }
            if (prevConnectedRecord) {
                removeItem(prevConnectedRecord, inverse.name, ownerRecord);
            }
            ownerRecord[field.name] = recordToConnect;
        } else if (field.type === "one2many") {
            // It's necessary to remove the previous connected in one2many but it would cause issue for inherited one2many field.
            // Also, we don't do modification in PoS and we can ignore the removing part to prevent issue.
            recordToConnect[inverse.name] = ownerRecord;
            addItem(ownerRecord, field.name, recordToConnect);
        } else if (field.type === "many2many") {
            addItem(ownerRecord, field.name, recordToConnect);
            addItem(recordToConnect, inverse.name, ownerRecord);
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
                removeItem(recordToDisconnect, inverse.name, ownerRecord);
            }
        } else if (field.type === "one2many") {
            removeItem(ownerRecord, field.name, recordToDisconnect);
            const prevConnectedRecord = recordToDisconnect[inverse.name];
            if (prevConnectedRecord === ownerRecord) {
                recordToDisconnect[inverse.name] = undefined;
            }
        } else if (field.type === "many2many") {
            removeItem(ownerRecord, field.name, recordToDisconnect);
            removeItem(recordToDisconnect, inverse.name, ownerRecord);
        }
    }

    function exists(model, id) {
        return model in records && id in records[model];
    }

    function create(
        model,
        vals,
        ignoreRelations = false,
        fromSerialized = false,
        delayedSetup = false
    ) {
        if (!("id" in vals)) {
            vals["id"] = uuid(model);
        }

        const Model = modelClasses[model] || Base;
        const record = reactive(new Model({ models, records, model: models[model] }));
        const id = vals["id"];
        record.id = id;

        if (!baseData[model][id]) {
            baseData[model][id] = vals;
        }

        record._raw = baseData[model][id];
        records[model][id] = record;

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
                                const newRecords = items.map((_vals) => {
                                    const result = create(comodelName, _vals);
                                    makeRecordsAvailable(
                                        { [comodelName]: [result] },
                                        { [comodelName]: [_vals] }
                                    );
                                    return result;
                                });
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
                        } else if (models[field.relation] && typeof val === "object") {
                            const newRecord = create(comodelName, val);
                            connect(field, record, newRecord);
                        } else {
                            record[name] = val;
                        }
                    }
                }
            } else {
                record[name] = vals[name];
            }
        }

        // Delayed setup is usefull when using loadData method.
        // Some records must be linked to other records before it can configure itself.
        if (!delayedSetup) {
            record.setup(vals);
        }

        return record;
    }

    function deserialize(model, vals) {
        return create(model, vals, false, true);
    }

    function update(model, record, vals, opts = {}) {
        const fields = getFields(model);
        Object.assign(baseData[model][record.id], vals);

        for (const name in vals) {
            if (!(name in fields) && name !== "id") {
                continue;
            } else if (name === "id" && vals[name] !== record.id) {
                delete records[model][record.id];
                delete baseData[model][record.id];

                for (const key of indexes[model] || []) {
                    const keyVal = record.raw[key];
                    if (Array.isArray(keyVal)) {
                        for (const val of keyVal) {
                            indexedRecords[model][key][val].delete(record.id);
                        }
                    }
                }

                record.id = vals[name];
                records[model][record.id] = record;
                baseData[model][record.id] = vals;
                continue;
            } else if (name === "id") {
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
                    } else if (type === "set") {
                        const linkedRecs = record[name];
                        const existingRecords = items.filter((record) =>
                            exists(comodelName, record.id)
                        );

                        for (const record2 of [...linkedRecs]) {
                            disconnect(field, record, record2);
                        }
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
                    } else if (models[field.relation] && typeof vals[name] === "object") {
                        const newRecord = create(comodelName, vals[name]);
                        connect(field, record, newRecord);
                    } else {
                        record[name] = vals[name];
                    }
                } else if (record[name]) {
                    const linkedRec = record[name];
                    disconnect(field, record, linkedRec);
                }
            } else {
                record[name] = vals[name];
            }
        }

        if (typeof record.id === "number" && !opts.silent) {
            commands[model].update.add(record.id);
        }
    }

    function delete_(model, record, opts = {}) {
        const id = record.id;
        const fields = getFields(model);
        const handleDelete = (inverse, field, record) => {
            if (inverse && !inverse.dummy && !opts.silent && typeof id === "number") {
                const oldVal = commands[field.relation].delete.get(inverse.name);
                commands[field.relation].delete.set(inverse.name, [...(oldVal || []), record.id]);
            }
        };

        for (const name in fields) {
            const field = fields[name];
            const inverse = inverseMap.get(field);

            if (X2MANY_TYPES.has(field.type)) {
                for (const record2 of [...record[name]]) {
                    handleDelete(inverse, field, record);
                    disconnect(field, record, record2);
                }
            } else if (field.type === "many2one" && typeof record[name] === "object") {
                handleDelete(inverse, field, record);
                disconnect(field, record, record[name]);
            }
        }

        orderedRecords[model] = orderedRecords[model].filter((rec) => rec.id !== record.id);
        delete records[model][id];

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
            create(vals, ignoreRelations = false, fromSerialized = false, delayedSetup = false) {
                const record = create(model, vals, ignoreRelations, fromSerialized, delayedSetup);
                makeRecordsAvailable({ [model]: [record] }, { [model]: [vals] });
                return record;
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
            update(record, vals, opts = {}) {
                return update(model, record, vals, opts);
            },
            delete(record, opts = {}) {
                return delete_(model, record, opts);
            },
            deleteMany(records, opts = {}) {
                const result = [];
                for (const record of records) {
                    result.push(delete_(model, record, opts));
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
                const result = this.indexedRecords[model][key][val];
                if (result instanceof Map) {
                    return Array.from(result.values());
                }
                return result;
            },
            readAll() {
                return this.orderedRecords[model];
            },
            readAllBy(key) {
                if (!this.indexes[model].includes(key)) {
                    throw new Error(`Unable to get record by '${key}'`);
                }
                const record = this.indexedRecords[model][key];
                if (record[Object.keys(record)[0]] instanceof Map) {
                    return Object.fromEntries(
                        Object.entries(record).map(([key, value]) => [
                            key,
                            Array.from(value.values()),
                        ])
                    );
                }
                return record;
            },
            readMany(ids) {
                if (!(model in records)) {
                    return [];
                }
                return ids.map((id) => records[model][id]);
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
                        result[name] =
                            record[name]?.id || (!orm && toRaw(record.raw[name])) || false;
                    } else if (X2MANY_TYPES.has(field.type)) {
                        const ids = [...record[name]].map((record) => record.id);
                        result[name] = ids.length ? ids : (!orm && toRaw(record.raw[name])) || [];
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
                return this.orderedRecords[model].map(fn);
            },
            reduce(fn, initialValue) {
                return this.orderedRecords[model].reduce(fn, initialValue);
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
            triggerEvents(event, data) {
                if (!(event in callbacks[model]) || callbacks[model][event].length === 0 || !data) {
                    return;
                }

                for (const callback of callbacks[model][event]) {
                    callback(data);
                }
            },
        };
    }

    const models = mapObj(processedModelDefs, (model, fields) => createCRUD(model, fields));

    /**
     * Load the data without the relations then link the related records.
     * @param {*} rawData
     */
    function loadData(rawData, load = [], fromSerialized = false, keepLocalRelation = false) {
        const results = {};
        const oldStates = {};
        const ignoreConnection = {};

        for (const model in rawData) {
            ignoreConnection[model] = [];
            const modelKey = keyByModel[model] || "id";

            if (!oldStates[model]) {
                oldStates[model] = {};
            }

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

                if (fromSerialized && typeof record.id === "string") {
                    const data = record.id.split("_");
                    const id = parseInt(data[1]);
                    const model = data[0];

                    if (id >= ID_CONTAINER[model] || !ID_CONTAINER[model]) {
                        ID_CONTAINER[model] = id + 1;
                    }
                }

                baseData[model][record.id] = record;

                const oldRecord = models[model].indexedRecords[model][modelKey][record[modelKey]];
                if (oldRecord) {
                    oldStates[model][oldRecord[modelKey]] = oldRecord.serializeState();
                    for (const [f, p] of Object.entries(modelClasses[model]?.extraFields || {})) {
                        if (X2MANY_TYPES.has(p.type)) {
                            record[f] = oldRecord[f]?.map((r) => r.id) || [];
                            continue;
                        }
                        record[f] = oldRecord[f]?.id || false;
                    }
                }

                if (oldRecord && keepLocalRelation) {
                    for (const [field, value] of Object.entries(record)) {
                        if (field === "id") {
                            continue;
                        }

                        const params = getFields(model)[field];
                        if (params && X2MANY_TYPES.has(params.type)) {
                            value.push(
                                ...oldRecord[field]
                                    .filter((r) => typeof r.id === "string")
                                    .map((r) => r.id)
                            );
                            record[field] = ["set", value];
                        }
                    }

                    oldRecord.update(record, { silent: true });
                    oldRecord.setup(record);
                    ignoreConnection[model].push(record.id);
                    results[model].push(oldRecord);
                    continue;
                }

                const result = create(model, record, true, false, true);
                if (oldRecord && oldRecord.id !== result.id) {
                    oldRecord.delete();
                }

                if (!(model in results)) {
                    results[model] = [];
                }

                results[model].push(result);
            }
        }

        const alreadyLinkedSet = new Set();
        const modelToSetup = [];

        // link the related records
        for (const model in rawData) {
            if (alreadyLinkedSet.has(model) || (!load.includes(model) && load.length !== 0)) {
                continue;
            }

            const rawRecords = rawData[model];
            const fields = getFields(model);

            for (const rawRec of rawRecords) {
                if (ignoreConnection[model].includes(rawRec.id)) {
                    continue;
                }

                const recorded = records[model][rawRec.id];

                // Check if there are any missing fields for this record
                const key = `${model}_${rawRec.id}`;
                if (missingFields[key]) {
                    for (const [record, field] of missingFields[key]) {
                        // Connect the `recorded` to the missing `field` in `record`
                        connect(field, record, recorded);
                    }
                    delete missingFields[key];
                }

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
                                    } else {
                                        const key = `${field.relation}_${id}`;
                                        if (!missingFields[key]) {
                                            missingFields[key] = [[recorded, field]];
                                        } else {
                                            missingFields[key].push([recorded, field]);
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
                            } else {
                                const key = `${field.relation}_${id}`;
                                if (!missingFields[key]) {
                                    missingFields[key] = [[recorded, field]];
                                } else {
                                    missingFields[key].push([recorded, field]);
                                }
                            }
                        }
                    }
                }

                modelToSetup.push({ raw: rawRec, record: recorded });
            }
        }

        // Setup all records when relations are linked
        for (const { raw, record } of modelToSetup) {
            record.setup(raw);
            const modelKey = keyByModel[record.model.modelName] || "id";

            if (oldStates[record.model.modelName][record[modelKey]]) {
                record.setupState(oldStates[record.model.modelName][record[modelKey]]);
            }
        }

        makeRecordsAvailable(results, rawData);
        return results;
    }

    function makeRecordsAvailable(results, rawData) {
        const indexRecord = (model, records) => {
            for (const key of indexes[model] || []) {
                for (const record of records) {
                    const keyVal = record[key];

                    if (!keyVal) {
                        continue;
                    }

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
        };

        for (const [models, values] of Object.entries(rawData)) {
            for (const value of values) {
                baseData[models][value.id] = value;
            }
        }

        for (const [model, values] of Object.entries(results)) {
            const valuesToAdd = [];
            const valuesToUpdate = [];

            if (!(model in orderedRecords)) {
                continue;
            }

            indexRecord(model, values);
            if (orderedRecords[model].length === 0) {
                orderedRecords[model] = values;
                valuesToAdd.push(...values);
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
            models[model].triggerEvents(event, {
                ids: values.map((v) => v.id),
                model: model,
            });
        }
    }

    models.loadData = loadData;
    models.commands = commands;

    return { models, records, indexedRecords, orderedRecords };
}
