import { toRaw } from "@odoo/owl";
import { uuidv4 } from "@point_of_sale/utils";
import { TrapDisabler } from "@point_of_sale/proxy_trap";
import { WithLazyGetterTrap } from "@point_of_sale/lazy_getter";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";

const ID_CONTAINER = {};
const { DateTime } = luxon;

function getLocalId(model) {
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

const DATE_TIME_TYPE = new Set(["date", "datetime"]);
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

export class Base extends WithLazyGetterTrap {
    constructor({ model, traps }) {
        super({ traps });
        this.model = model;
    }
    get models() {
        return this.model.models;
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
            if (key in this.model.fields) {
                continue;
            }

            if (key.startsWith("_") && !key.startsWith("__")) {
                this[key] = val;
            }
        }
    }

    setDirty() {
        if (typeof this.id === "number") {
            this.models.commands[this.model.name].update.add(this.id);
        }
    }

    formatDateOrTime(field, type = "datetime") {
        if (type == "date") {
            return this[field].toLocaleString(DateTime.DATE_SHORT);
        }
        return this[field].toLocaleString(DateTime.DATETIME_SHORT);
    }

    setupState(vals) {
        this.uiState = vals;
    }

    serializeState() {
        return { ...this.uiState };
    }

    isEqual(other) {
        return toRaw(this) === toRaw(other);
    }

    update(vals) {
        return this.model.update(this, vals);
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
            const fields = this.model.fields;
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
                                const records = this.model.records;
                                data = records[params.relation].get(id).serialize(options);
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
                                        this.models[params.relation].fields[key]?.relation &&
                                        typeof value === "string"
                                    ) {
                                        serData[2][key] = parseInt(value.split("_")[1]);
                                    }
                                }
                            }

                            return serData;
                        })
                        .filter((s) => s);

                    if (
                        this.models.commands[params.model].unlink.has(name) ||
                        this.models.commands[params.model].delete.has(name)
                    ) {
                        const unlinks = this.models.commands[params.model].unlink.get(name);
                        const deletes = this.models.commands[params.model].delete.get(name);
                        for (const id of unlinks || []) {
                            serializedDataOrm[name].push([3, id]);
                        }
                        for (const id of deletes || []) {
                            serializedDataOrm[name].push([2, id]);
                        }
                        if (clear) {
                            this.models.commands[params.model].unlink.delete(name);
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
    getCacheMap(fieldName) {
        const cacheName = `_${fieldName}`;
        if (!(cacheName in this)) {
            this[cacheName] = new Map();
        }
        return this[cacheName];
    }
    get raw() {
        return this._raw ?? {};
    }
}

export function createRelatedModels(modelDefs, modelClasses = {}, opts = {}) {
    const indexes = opts.databaseIndex || {};
    const database = opts.databaseTable || {};
    const [inverseMap, processedModelDefs] = processModelDefs(modelDefs);
    const records = mapObj(processedModelDefs, () => new Map());
    const callbacks = mapObj(processedModelDefs, () => []);
    const commands = mapObj(processedModelDefs, () => ({
        delete: new Map(),
        unlink: new Map(),
        update: new Set(),
    }));
    const baseData = {};
    const missingFields = {};

    // object: model -> key -> keyval -> record
    const indexedRecords = mapObj(processedModelDefs, (model) => {
        const container = {};

        // We always want an index by id
        if (!indexes[model]) {
            indexes[model] = ["id"];
        } else {
            indexes[model].push("id");
        }

        for (const key of indexes[model] || []) {
            container[key] = {};
        }

        baseData[model] = {};
        return container;
    });

    function getFields(model) {
        return processedModelDefs[model];
    }

    function removeItem(record, fieldName, item) {
        const cacheMap = record.getCacheMap(fieldName);
        const key = database[item.model.name]?.key || "id";
        const keyVal = item[key];

        if (cacheMap.has(keyVal)) {
            cacheMap.delete(keyVal);
            const index = record[fieldName].findIndex((r) => r[key] === keyVal);
            record[fieldName].splice(index, 1);
        }
    }

    function addItem(record, fieldName, item) {
        const cacheMap = record.getCacheMap(fieldName);
        const key = database[item.model.name]?.key || "id";
        const keyVal = item[key];

        if (!keyVal) {
            console.warn(`Key ${key} not found in ${item.model.name}`);
        }

        if (!cacheMap.has(keyVal)) {
            cacheMap.set(keyVal, item);
            record[fieldName].push(item);
        } else {
            const index = record[fieldName].findIndex((r) => r[key] === keyVal);
            record[fieldName].splice(index, 1, item);
        }
    }

    function connect(field, ownerRecord, recordToConnect) {
        const inverse = inverseMap.get(field);
        if (field.type === "many2one") {
            const prevConnectedRecord = ownerRecord[field.name];
            if (prevConnectedRecord?.isEqual(recordToConnect)) {
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
            if (prevConnectedRecord?.isEqual(recordToDisconnect)) {
                ownerRecord[field.name] = undefined;
                removeItem(recordToDisconnect, inverse.name, ownerRecord);
            }
        } else if (field.type === "one2many") {
            removeItem(ownerRecord, field.name, recordToDisconnect);
            const prevConnectedRecord = recordToDisconnect[inverse.name];
            if (prevConnectedRecord?.isEqual(ownerRecord)) {
                recordToDisconnect[inverse.name] = undefined;
            }
        } else if (field.type === "many2many") {
            removeItem(ownerRecord, field.name, recordToDisconnect);
            removeItem(recordToDisconnect, inverse.name, ownerRecord);
        }
    }

    function handleDatetime(model, value, prop) {
        // Verify if is already a valid dateobject
        if (!(value instanceof Object) && value) {
            const datetime = deserializeDateTime(value);
            if (!datetime.isValid) {
                throw new Error(
                    `Invalid date: ${value} for model ${model.modelName} in field ${prop}`
                );
            }
            return datetime;
        } else if (value instanceof Object && value.isValid) {
            return value;
        }

        return false;
    }

    /**
     * This check assumes that if the first element is a command, then the rest are commands.
     */
    function isX2ManyCommands(value) {
        return (
            Array.isArray(value) &&
            Array.isArray(value[0]) &&
            ["unlink", "clear", "create", "link"].includes(value[0][0])
        );
    }

    const disabler = new TrapDisabler();
    const setTrapsCache = {};

    function createNewRecord(model) {
        const modelName = model.name;
        const fields = model.fields;
        const Model = modelClasses[modelName] || Base;
        if (!(modelName in setTrapsCache)) {
            setTrapsCache[modelName] = function setTrap(target, prop, value, receiver) {
                if (disabler.isDisabled() || !(prop in fields)) {
                    return Reflect.set(target, prop, value, receiver);
                }
                return disabler.call(() => {
                    const field = fields[prop];
                    if (field && X2MANY_TYPES.has(field.type)) {
                        if (!isX2ManyCommands(value)) {
                            value = [["clear"], ["link", ...value]];
                        }
                    }
                    receiver.update({ [prop]: value });
                    target.model.triggerEvents("update", { field: prop, value, id: target.id });
                    return true;
                });
            };
        }
        return new Model({
            model,
            traps: { set: setTrapsCache[modelName] },
        });
    }

    /**
     * A model (e.g. pos.order) points to an instance of this class.
     */
    class CRUD {
        constructor(name) {
            this.name = name;
        }
        get models() {
            return models;
        }
        get records() {
            return records;
        }
        get fields() {
            return getFields(this.name);
        }
        get orderedRecords() {
            return Array.from(this.records[this.name].values());
        }
        exists(id) {
            return this.records[this.name].has(id);
        }
        create(vals, ignoreRelations = false, fromSerialized = false, delayedSetup = false) {
            const record = disabler.call(
                (...args) => this._create(...args),
                vals,
                ignoreRelations,
                fromSerialized,
                delayedSetup
            );
            this.models.makeRecordsAvailable({ [this.name]: [record] }, { [this.name]: [vals] });
            return record;
        }
        deserialize(vals) {
            return this.create(vals, false, true);
        }
        createMany(valsList) {
            const result = [];
            for (const vals of valsList) {
                result.push(this.create(vals));
            }
            return result;
        }
        update(record, vals) {
            return disabler.call((...args) => this._update(...args), record, vals);
        }
        delete(record, opts = {}) {
            return disabler.call((...args) => this._delete(...args), record, opts);
        }
        deleteMany(toDelete) {
            const result = [];
            let mustBreak = 0;
            while (toDelete.length) {
                result.push(this.delete(toDelete[toDelete.length - 1]));
                mustBreak += 1;

                if (mustBreak > 1000) {
                    console.warn("Too many records to delete. Breaking the loop.");
                    break;
                }
            }
            return result;
        }
        read(value) {
            const id = /^\d+$/.test(value) ? parseInt(value) : value; // In case of ID came from an input
            if (!this.records[this.name].has(id)) {
                return;
            }
            return this.records[this.name].get(id);
        }
        readFirst() {
            if (!(this.name in this.records)) {
                return;
            }
            return this.orderedRecords[0];
        }
        readBy(key, val) {
            if (!indexes[this.name].includes(key)) {
                throw new Error(`Unable to get record by '${key}'`);
            }
            const result = this.models.indexedRecords[this.name][key][val];
            if (result instanceof Map) {
                return Array.from(result.values());
            }
            return result;
        }
        readAll() {
            return this.orderedRecords;
        }
        readAllBy(key) {
            if (!indexes[this.name].includes(key)) {
                throw new Error(`Unable to get record by '${key}'`);
            }
            const record = this.models.indexedRecords[this.name][key];
            if (record[Object.keys(record)[0]] instanceof Map) {
                return Object.fromEntries(
                    Object.entries(record).map(([key, value]) => [key, Array.from(value.values())])
                );
            }
            return record;
        }
        readMany(ids) {
            if (!(this.name in this.records)) {
                return [];
            }
            return ids.map((value) => this.read(value));
        }
        /**
         * @param {object} options
         * @param {boolean} options.orm - Exclude local & related fields from the serialization
         */
        serialize(record, options = {}) {
            const orm = options.orm ?? false;
            const result = {};
            const ownFields = getFields(this.name);
            for (const name in ownFields) {
                const field = ownFields[name];
                if ((orm && field.local) || (orm && field.related) || (orm && field.compute)) {
                    continue;
                }

                if (field.type === "many2one") {
                    result[name] = record[name]?.id || record.raw[name] || false;
                } else if (X2MANY_TYPES.has(field.type)) {
                    const ids = [...record[name]].map((record) => record.id);
                    result[name] = ids.length ? ids : (!orm && record.raw[name]) || [];
                } else if (DATE_TIME_TYPE.has(field.type) && typeof record[name] === "object") {
                    result[name] = serializeDateTime(record[name]);
                } else if (typeof record[name] === "object") {
                    result[name] = JSON.stringify(record[name]);
                } else {
                    result[name] = record[name] !== undefined ? record[name] : false;
                }
            }
            return result;
        }
        // aliases
        getAllBy() {
            return this.readAllBy(...arguments);
        }
        getAll() {
            return this.readAll(...arguments);
        }
        getBy() {
            return this.readBy(...arguments);
        }
        get() {
            return this.read(...arguments);
        }
        getFirst() {
            return this.readFirst(...arguments);
        }
        // array prototype
        map(fn) {
            return this.orderedRecords.map(fn);
        }
        reduce(fn, initialValue) {
            return this.orderedRecords.reduce(fn, initialValue);
        }
        flatMap(fn) {
            return this.orderedRecords.flatMap(fn);
        }
        forEach(fn) {
            return this.orderedRecords.forEach(fn);
        }
        some(fn) {
            return this.orderedRecords.some(fn);
        }
        every(fn) {
            return this.orderedRecords.every(fn);
        }
        find(fn) {
            return this.orderedRecords.find(fn);
        }
        filter(fn) {
            return this.orderedRecords.filter(fn);
        }
        sort(fn) {
            return this.orderedRecords.sort(fn);
        }
        indexOf(record) {
            return this.orderedRecords.indexOf(record);
        }
        get length() {
            return this.records[this.name].size;
        }
        // External callbacks
        addEventListener(event, callback) {
            if (!AVAILABLE_EVENT.includes(event)) {
                throw new Error(`Event '${event}' is not available`);
            }

            if (!(event in callbacks[this.name])) {
                callbacks[this.name][event] = [];
            }

            callbacks[this.name][event].push(callback);
        }
        triggerEvents(event, data) {
            if (
                !(event in callbacks[this.name]) ||
                callbacks[this.name][event].length === 0 ||
                !data
            ) {
                return;
            }

            for (const callback of callbacks[this.name][event]) {
                callback(data);
            }
        }

        _create(vals, ignoreRelations = false, fromSerialized = false, delayedSetup = false) {
            if (!("id" in vals)) {
                vals["id"] = getLocalId(this.name);
            }

            const record = createNewRecord(this);

            const id = vals["id"];
            record.id = id;
            if (!vals.uuid && database[this.name]?.key === "uuid") {
                record.uuid = uuidv4();
                vals.uuid = record.uuid;
            }

            if (!baseData[this.name][id]) {
                baseData[this.name][id] = vals;
            }

            record._raw = baseData[this.name][id];
            this.records[this.name].set(id, record);

            const fields = getFields(this.name);
            for (const name in fields) {
                if (name === "id") {
                    continue;
                }

                const field = fields[name];

                if (field.required && !(name in vals)) {
                    throw new Error(
                        `'${name}' field is required when creating '${this.name}' record.`
                    );
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
                    const comodel = this.models[comodelName];
                    if (!(name in vals) || !vals[name]) {
                        continue;
                    }

                    if (X2MANY_TYPES.has(field.type)) {
                        if (fromSerialized) {
                            const ids = vals[name];
                            for (const id of ids) {
                                if (comodel.exists(id)) {
                                    connect(field, record, this.records[comodelName].get(id));
                                }
                            }
                        } else {
                            for (const [command, ...items] of vals[name]) {
                                if (command === "create") {
                                    const newRecords = items.map((_vals) => {
                                        const result = comodel.create(_vals);
                                        this.models.makeRecordsAvailable(
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
                                        comodel.exists(record.id)
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
                            if (comodel.exists(val)) {
                                connect(field, record, this.records[comodelName].get(val));
                            }
                        } else {
                            if (val instanceof Base) {
                                if (comodel.exists(val.id)) {
                                    connect(field, record, val);
                                }
                            } else if (this.models[field.relation]) {
                                const newRecord = comodel.create(val);
                                connect(field, record, newRecord);
                            } else {
                                record[name] = val;
                            }
                        }
                    }
                } else if (DATE_TIME_TYPE.has(field.type)) {
                    record[name] = handleDatetime(this, vals[name], name);
                } else {
                    record[name] = vals[name];
                }
            }

            // Delayed setup is usefull when using loadData method.
            // Some records must be linked to other records before it can configure itself.
            if (!delayedSetup) {
                record.setup(vals);
            }

            return this.records[this.name].get(id);
        }
        _update(record, vals) {
            const ownFields = getFields(this.name);
            Object.assign(baseData[this.name][record.id], vals);

            for (const name in vals) {
                if (!(name in ownFields)) {
                    continue;
                }
                const field = ownFields[name];
                const comodelName = field.relation;
                const comodel = this.models[comodelName];
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
                            const newRecords = items.map((vals) => comodel.create(vals));
                            for (const record2 of newRecords) {
                                connect(field, record, record2);
                            }
                        } else if (type === "link") {
                            const existingRecords = items.filter((record) =>
                                comodel.exists(record.id)
                            );
                            for (const record2 of existingRecords) {
                                connect(field, record, record2);
                            }
                        }
                    }
                } else if (field.type === "many2one") {
                    if (vals[name]) {
                        const id = vals[name]?.id || vals[name];
                        const exist = comodel.exists(id);
                        if (exist) {
                            connect(field, record, comodel.get(id));
                        } else if (this.models[field.relation]) {
                            const newRecord = comodel.create(vals[name]);
                            connect(field, record, newRecord);
                        } else {
                            record[name] = vals[name];
                        }
                    } else if (record[name]) {
                        const linkedRec = record[name];
                        disconnect(field, record, linkedRec);
                    }
                } else if (DATE_TIME_TYPE.has(field.type)) {
                    record[name] = handleDatetime(this, vals[name], name);
                } else {
                    record[name] = vals[name];
                }
            }

            if (typeof record.id === "number") {
                commands[this.name].update.add(record.id);
            }
        }
        _delete(record, opts = {}) {
            const id = record.id;
            const ownFields = getFields(this.name);
            const handleCommand = (inverse, field, record, backend = false) => {
                if (inverse && !inverse.dummy && !opts.silent && typeof id === "number") {
                    const modelCommands = commands[field.relation];
                    const map = backend ? modelCommands.delete : modelCommands.unlink;
                    const oldVal = map.get(inverse.name);
                    map.set(inverse.name, [...(oldVal || []), record.id]);
                }
            };

            for (const name in ownFields) {
                const field = ownFields[name];
                const inverse = inverseMap.get(field);

                if (X2MANY_TYPES.has(field.type)) {
                    for (const record2 of [...record[name]]) {
                        handleCommand(inverse, field, record, opts.backend);
                        disconnect(field, record, record2);
                    }
                } else if (field.type === "many2one" && typeof record[name] === "object") {
                    handleCommand(inverse, field, record, opts.backend);
                    disconnect(field, record, record[name]);
                }
            }

            const key = database[this.name]?.key || "id";
            this.triggerEvents("delete", { key: record[key] });
            this.records[this.name].delete(id);
            for (const key of indexes[this.name] || []) {
                const keyVal = record.raw[key];
                if (Array.isArray(keyVal)) {
                    for (const val of keyVal) {
                        this.models.indexedRecords[this.name][key][val].delete(record.id);
                    }
                } else {
                    delete this.models.indexedRecords[this.name][key][keyVal];
                }
            }

            return id;
        }
    }

    class Models {
        constructor(processedModelDefs) {
            Object.assign(
                this,
                mapObj(processedModelDefs, (modelName) => new CRUD(modelName))
            );
        }
        get commands() {
            return commands;
        }
        get records() {
            return records;
        }
        get indexedRecords() {
            return indexedRecords;
        }
        loadData(rawData, load = [], fromSerialized = false) {
            return disabler.call(
                (...args) => this._loadData(...args),
                rawData,
                load,
                fromSerialized
            );
        }
        makeRecordsAvailable(results, rawData) {
            return disabler.call(
                (...args) => this._makeRecordsAvailable(...args),
                results,
                rawData
            );
        }
        _loadData(rawData, load = [], fromSerialized = false) {
            const results = {};
            const oldStates = {};

            for (const model in rawData) {
                const modelKey = database[model]?.key || "id";
                if (!oldStates[model]) {
                    oldStates[model] = {};
                }

                if (!load.includes(model) && load.length !== 0) {
                    continue;
                } else if (!results[model]) {
                    results[model] = [];
                }

                const valsArray = rawData[model];
                for (const vals of valsArray) {
                    if (!baseData[model]) {
                        baseData[model] = {};
                    }

                    if (fromSerialized && typeof vals.id === "string") {
                        const data = vals.id.split("_");
                        const id = parseInt(data[1]);
                        const model = data[0];

                        if (id >= ID_CONTAINER[model] || !ID_CONTAINER[model]) {
                            ID_CONTAINER[model] = id + 1;
                        }
                    }

                    baseData[model][vals.id] = vals;

                    const oldRecord = this.indexedRecords[model][modelKey][vals[modelKey]];
                    if (oldRecord) {
                        oldStates[model][oldRecord[modelKey]] = oldRecord.serializeState();
                        for (const [f, p] of Object.entries(
                            modelClasses[model]?.extraFields || {}
                        )) {
                            if (X2MANY_TYPES.has(p.type)) {
                                vals[f] = oldRecord[f]?.map((r) => r.id) || [];
                                continue;
                            }
                            vals[f] = oldRecord[f]?.id || false;
                        }
                    }

                    const result = this[model]._create(vals, true, false, true);
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
            for (const modelName in rawData) {
                if (
                    alreadyLinkedSet.has(modelName) ||
                    (!load.includes(modelName) && load.length !== 0)
                ) {
                    continue;
                }

                const rawRecords = rawData[modelName];
                const fields = getFields(modelName);

                for (const rawRec of rawRecords) {
                    const recorded = this.records[modelName].get(rawRec.id);

                    // Check if there are any missing fields for this record
                    const key = `${modelName}_${rawRec.id}`;
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
                                    if (field.relation in this.records) {
                                        const toConnect = this.records[field.relation].get(id);
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
                            if (field.relation in this.records) {
                                const id = rawRec[name];
                                const toConnect = this.records[field.relation].get(id);
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
                        } else if (DATE_TIME_TYPE.has(field.type)) {
                            recorded[name] = handleDatetime(this[modelName], rawRec[name], name);
                        }
                    }

                    modelToSetup.push({ raw: rawRec, record: recorded });
                }
            }

            // Setup all records when relations are linked
            for (const { raw, record } of modelToSetup) {
                record.setup(raw);
                const model = record.model.name;
                const modelKey = database[model]?.key || "id";
                const states = oldStates[model][record[modelKey]];
                if (states) {
                    record.setupState(states);
                }
            }

            this.makeRecordsAvailable(results, rawData);
            return results;
        }
        _makeRecordsAvailable(results, rawData) {
            const indexRecord = (model, records) => {
                for (const key of indexes[model] || []) {
                    for (const record of records) {
                        const keyVal = record[key];

                        if (!keyVal) {
                            continue;
                        }

                        if (Array.isArray(keyVal)) {
                            for (const keyV of keyVal) {
                                if (!this.indexedRecords[model][key][keyV.id]) {
                                    this.indexedRecords[model][key][keyV.id] = new Map();
                                }
                                this.indexedRecords[model][key][keyV.id].set(record.id, record);
                            }
                        } else {
                            this.indexedRecords[model][key][keyVal] = record;
                        }
                    }
                }
            };

            for (const [modelName, values] of Object.entries(rawData)) {
                for (const value of values) {
                    baseData[modelName][value.id] = value;
                }
            }

            for (const [model, values] of Object.entries(results)) {
                indexRecord(model, values);
                this[model].triggerEvents("create", {
                    ids: values.map((v) => v.id),
                    model: model,
                });
            }
        }
    }

    const models = new Models(processedModelDefs);

    return { models, baseData };
}
