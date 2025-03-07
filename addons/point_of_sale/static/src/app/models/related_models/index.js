import { uuidv4 } from "@point_of_sale/utils";
import { TrapDisabler } from "@point_of_sale/proxy_trap";
import { createLazyGetter } from "@point_of_sale/lazy_getter";
import { RecordStore } from "./record_store.js";
import {
    RELATION_TYPES,
    X2MANY_TYPES,
    DATE_TIME_TYPE,
    RAW_SYMBOL,
    STORE_SYMBOL,
    mapObj,
    convertDateTimeToRaw,
    BACKREF_PREFIX,
} from "./utils";
import { Base } from "./base";
import { processModelDefs } from "./model_defs";
import { computeBackLinks, processModelClasses } from "./model_classes.js";
import { ormSerialization } from "./serialization.js";

const AVAILABLE_EVENT = ["create", "update", "delete"];

export function createRelatedModels(modelDefs, modelClasses = {}, opts = {}) {
    const database = opts.databaseTable || {};
    const dynamicModels = opts.dynamicModels || [];
    const store = new RecordStore(Object.keys(modelDefs), opts.databaseIndex);
    const [inverseMap, processedModelDefs] = processModelDefs(modelDefs);
    processModelClasses(processedModelDefs, modelClasses);
    const callbacks = mapObj(processedModelDefs, () => []);
    const commands = mapObj(processedModelDefs, () => ({
        delete: new Map(),
        unlink: new Map(),
    }));
    function getFields(model) {
        return processedModelDefs[model];
    }
    const disabler = new TrapDisabler();

    /**
     * A model (e.g. pos.order) points to an instance of this class.
     */
    class Model {
        constructor(name) {
            this.name = name;
            // Ensures reactivity by accessing the recordStore directly from the instance
            this[STORE_SYMBOL] = store;
            this.records = store.getRecordsMap(this.name); // Used by some modules...
        }

        get models() {
            return models;
        }

        get fields() {
            return getFields(this.name);
        }

        get orderedRecords() {
            return this[STORE_SYMBOL].getOrderedRecords(this.name);
        }

        exists(id) {
            return !!this[STORE_SYMBOL].getById(this.name, id);
        }

        create(vals) {
            return disabler.call((...args) => this._create(...args), vals);
        }

        deserialize(vals) {
            return this.create(vals);
        }

        createMany(valsList) {
            const result = [];
            for (const vals of valsList) {
                result.push(this.create(vals));
            }
            return result;
        }

        update(record, vals, opts = {}) {
            return disabler.call((...args) => this._update(...args), record, vals, opts);
        }

        delete(record, opts = {}) {
            return disabler.call((...args) => this._delete(...args), record, opts);
        }

        deleteMany(toDelete, opts = {}) {
            const result = [];
            for (const d of toDelete) {
                result.push(this.delete(d, opts));
            }
            return result;
        }

        read(value) {
            const id = /^\d+$/.test(value) ? parseInt(value) : value; // In case of ID came from an input
            return this[STORE_SYMBOL].getById(this.name, id);
        }

        readFirst() {
            return this.orderedRecords[0];
        }

        readBy(key, val) {
            return this[STORE_SYMBOL].get(this.name, key, val);
        }

        readAll() {
            return this.orderedRecords;
        }

        readAllBy(key) {
            return this[STORE_SYMBOL].getRecordsByIds(this.name, key);
        }

        readMany(ids) {
            return ids.map((value) => this.read(value));
        }

        // aliases
        getAllBy() {
            return this.readAllBy(...arguments);
        }

        getAllIds() {
            return this[STORE_SYMBOL].getRecordsIds(this.name);
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
            return this[STORE_SYMBOL].getRecordCount(this.name);
        }

        getParentFields() {
            return Object.values(getFields(this.name)).filter((field) => {
                if (field.dummy || !["many2one", "many2many"].includes(field.type)) {
                    return false;
                }
                const inverseField = inverseMap.get(field);
                return inverseField && !inverseField.dummy;
            });
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

        _initRawData(vals, relationHandler = undefined, options = {}) {
            const { serverData = false } = options;
            if (!vals.uuid && database[this.name]?.key === "uuid") {
                vals.uuid = uuidv4();
            }
            vals.id = vals["id"] ?? (vals.uuid || uuidv4());
            const rawData = {
                id: vals.id,
            };
            const fields = getFields(this.name);
            const fieldKeys = Object.keys(fields);
            for (let i = 0; i < fieldKeys.length; i++) {
                const fieldName = fieldKeys[i];
                const field = fields[fieldName];
                const value = vals[fieldName];
                if (field.required && (value === undefined || value === null)) {
                    throw new Error(
                        `'${fieldName}' field is required when creating '${this.name}' record.`
                    );
                }
                if (RELATION_TYPES.has(field.type)) {
                    const data = rawData;
                    if (field.dummy) {
                        continue;
                    }
                    if (X2MANY_TYPES.has(field.type)) {
                        data[fieldName] = [];
                    } else if (field.type === "many2one") {
                        data[fieldName] = undefined;
                    }
                    if (!value) {
                        continue;
                    }
                    if (relationHandler) {
                        relationHandler(field, value, data);
                    } else {
                        rawData[field.name] = value;
                    }
                } else {
                    rawData[fieldName] = DATE_TIME_TYPE.has(field.type)
                        ? convertDateTimeToRaw(value)
                        : value;
                }
            }
            //Add other backend / extra fields
            const extraFields = {};
            const fieldNames = new Set(fieldKeys);
            for (const key in vals) {
                if (fieldNames.has(key)) {
                    continue;
                }
                if (serverData) {
                    rawData[key] = vals[key];
                }
                if (key[0] === "_" && key[1] !== "_") {
                    extraFields[key] = vals[key];
                }
            }
            return { rawData, extraFields };
        }

        _create(vals, opts = {}) {
            const { connectRecords = true, serverData = false } = opts;
            const relations = {};
            const { rawData, extraFields } = this._initRawData(
                vals,
                !connectRecords
                    ? undefined
                    : (field, value) => {
                          relations[field.name] = value;
                      },
                { serverData }
            );
            const ModelRecordClass = modelClasses[this.name];
            const record = new ModelRecordClass({
                model: this,
                raw: rawData,
            });
            Object.assign(record, extraFields);
            //The record store is assigned to each instance to enable store detection changes in the lazy getters
            record[STORE_SYMBOL] = this[STORE_SYMBOL];
            this[STORE_SYMBOL].add(record);
            if (connectRecords) {
                // Connect related records
                this._update(record, relations, { silent: true });
                if (serverData) {
                    // Must be done after connecting related records to ensure correct disconnection from previous records
                    // and connection to new ones.
                    Object.assign(record[RAW_SYMBOL], relations);
                }
            }

            record.setup(vals);
            record.initState();
            if (connectRecords) {
                record.model.triggerEvents("create", { ids: [record.id], model: this.name });
            }
            return record;
        }

        _update(record, vals, opts = {}) {
            const ownFields = getFields(this.name);
            let reIndexRecord = false;
            let fireUpdate = false;
            for (const name in vals) {
                if (name === "id" || (name === "uuid" && ownFields[name])) {
                    // id can be only updated using loadData
                    continue;
                }

                const field = ownFields[name];
                if (!field) {
                    if (opts.omitUnknownField) {
                        continue;
                    }
                    throw new Error(`The field '${name}' does not exist in model '${this.name}'`);
                }
                const relationModelName = field.relation;
                const relationModel = this.models[relationModelName];
                if (field.dummy) {
                    throw new Error(`The field '${field}' cannot be updated`);
                }
                if (this[STORE_SYMBOL].hasIndex(this.name, field.name)) {
                    reIndexRecord = true;
                }
                if (relationModel) {
                    fireUpdate = true;
                    if (X2MANY_TYPES.has(field.type)) {
                        const commands = [];
                        let defaultCommand;
                        const values = vals[name];
                        if (values.length === 0) {
                            commands.push(["clear"]);
                        } else {
                            for (const val of values) {
                                // Process command to convert [l1,l2] to [["set",l1,l2]]
                                if (Array.isArray(val)) {
                                    commands.push(val);
                                } else {
                                    if (!defaultCommand) {
                                        defaultCommand = ["set"];
                                        commands.push(defaultCommand);
                                    }
                                    defaultCommand.push(val);
                                }
                            }
                        }

                        for (const cmd of commands) {
                            const [command, ...records] = cmd;

                            if (command === "unlink") {
                                for (const record2 of records) {
                                    models.disconnect(field, record, record2);
                                }
                            } else if (command === "clear") {
                                const linkedRecs = record[name];
                                for (const record2 of [...linkedRecs]) {
                                    models.disconnect(field, record, record2);
                                }
                            } else if (command === "create") {
                                const newRecords = records.map((vals) =>
                                    relationModel.create(vals)
                                );
                                for (const record2 of newRecords) {
                                    models.connect(field, record, record2);
                                }
                            } else if (command === "link") {
                                for (const record2 of records) {
                                    models.connect(field, record, record2);
                                }
                            } else if (command === "set") {
                                const linkedRecs = record[name];
                                for (const record2 of [...linkedRecs]) {
                                    models.disconnect(field, record, record2);
                                }
                                for (const record2 of records) {
                                    models.connect(field, record, record2);
                                }
                            } else {
                                throw new Error("Command '" + command + "' not supported");
                            }
                        }
                    } else if (field.type === "many2one") {
                        if (vals[name]) {
                            const id = vals[name]?.id || vals[name];
                            const exist = relationModel.exists(id);
                            if (exist) {
                                models.connect(field, record, relationModel.get(id));
                            } else if (
                                this.models[field.relation] &&
                                typeof vals[name] === "object"
                            ) {
                                const newRecord = relationModel.create(vals[name]);
                                models.connect(field, record, newRecord);
                            }
                        } else if (record[name]) {
                            const linkedRec = record[name];
                            models.disconnect(field, record, linkedRec);
                        }
                    } else {
                        throw new Error(`Relation type '${field.type}' not supported`);
                    }
                } else {
                    const oldValue = record[RAW_SYMBOL][name];
                    let newValue = vals[name];
                    if (DATE_TIME_TYPE.has(field.type)) {
                        newValue = convertDateTimeToRaw(newValue);
                    }
                    if (newValue !== oldValue) {
                        record._markDirty(name);
                        record[RAW_SYMBOL][name] = newValue;
                        fireUpdate = true;
                    }
                }

                if (opts.fireFieldUpdate && fireUpdate) {
                    record.model.triggerEvents("update", {
                        field: name,
                        value: vals[name],
                        id: record.id,
                    });
                }
            }

            if (reIndexRecord) {
                this[STORE_SYMBOL].remove(record);
                this[STORE_SYMBOL].add(record);
            }

            if (!opts.silent && fireUpdate) {
                record.model.triggerEvents("update", { id: record.id });
            }
        }

        _delete(record, opts = {}) {
            const id = record.id;
            const ownFields = getFields(this.name);
            const handleCommand = (inverse, field, record, backend = false) => {
                if (inverse && !inverse.dummy && typeof id === "number") {
                    const modelCommands = commands[field.relation];
                    const map = backend ? modelCommands.delete : modelCommands.unlink;
                    const oldVal = map.get(inverse.name);
                    map.set(inverse.name, [
                        ...(oldVal || []),
                        { id: record.id, parentId: record[field.name].id },
                    ]);
                }
            };
            this[STORE_SYMBOL].remove(record);
            for (const name in ownFields) {
                const field = ownFields[name];
                const inverse = inverseMap.get(field);
                if (field.dummy) {
                    continue;
                }
                if (X2MANY_TYPES.has(field.type)) {
                    for (const record2 of [...record[name]]) {
                        handleCommand(inverse, field, record, opts.backend);
                        models.disconnect(field, record, record2);
                    }
                } else if (field.type === "many2one" && typeof record[name] === "object") {
                    handleCommand(inverse, field, record, opts.backend);
                    models.disconnect(field, record, record[name]);
                }
            }

            const key = database[this.name]?.key || "id";
            this.triggerEvents("delete", { key: record[key] });

            return id;
        }

        backLink(record, link) {
            if (!link.startsWith(BACKREF_PREFIX)) {
                link = BACKREF_PREFIX + link;
            }
            if (link in record) {
                return record[link];
            }
            const field = this.fields[link];
            if (!field) {
                return undefined;
            }
            createLazyGetter(record, link, computeBackLinks(field));
            return record[link];
        }

        serializeForORM(record, opts) {
            return ormSerialization(record, { dynamicModels, ...opts });
        }
    }

    class Models {
        constructor(processedModelDefs) {
            Object.assign(
                this,
                mapObj(processedModelDefs, (modelName) => new Model(modelName))
            );
            this[STORE_SYMBOL] = store;
        }

        get commands() {
            return commands;
        }

        loadData(rawData, load = [], opts = {}) {
            this._loadingData = true;
            try {
                return disabler.call((...args) => this._loadData(...args), rawData, load, opts);
            } finally {
                this._loadingData = false;
            }
        }

        _loadData(rawData, modelToLoad = [], opts = {}) {
            const results = {};
            const { serverData = true, connectRecords = true } = opts;
            for (const model in rawData) {
                if (!modelToLoad.includes(model) && modelToLoad.length !== 0) {
                    continue;
                } else if (!results[model]) {
                    results[model] = [];
                }
                const modelKey = database[model]?.key || "id";
                const valsArray = rawData[model];
                const recordStore = this[STORE_SYMBOL];
                for (const vals of valsArray) {
                    const existingRecord = recordStore.get(model, modelKey, vals[modelKey]);
                    let record;
                    if (existingRecord) {
                        // Remove olds references (id string -> id num)
                        recordStore.remove(existingRecord);
                        // Update values
                        const { rawData, extraFields } = this[model]._initRawData(vals, undefined, {
                            serverData,
                        });
                        existingRecord[RAW_SYMBOL] = rawData;
                        Object.assign(existingRecord, extraFields);
                        existingRecord.setup(vals);
                        record = existingRecord;
                        recordStore.add(record);
                    } else {
                        record = this[model]._create(vals, { connectRecords, serverData });
                    }
                    if (!(model in results)) {
                        results[model] = [];
                    }
                    results[model].push(record);
                }
            }
            for (const [model, values] of Object.entries(results)) {
                this[model].triggerEvents("create", {
                    ids: values.map((v) => v.id),
                    model: model,
                });
            }
            return results;
        }

        serializeForORM(record, opts) {
            return ormSerialization(record, { dynamicModels, ...opts });
        }

        connect(field, ownerRecord, recordOrIdToConnect) {
            if (!this[STORE_SYMBOL].hasIndex(field.relation, "id")) {
                // Not supported model
                return;
            }
            const inverse = inverseMap.get(field);
            const recordToConnect = this.getRecord(field.relation, recordOrIdToConnect);
            if (!recordToConnect) {
                return;
            }

            if (field.type === "many2one") {
                const prevConnectedRecordId = ownerRecord[RAW_SYMBOL][field.name];
                if (prevConnectedRecordId === recordToConnect.id) {
                    return;
                }
                if (!inverse.dummy && inverse.name in recordToConnect) {
                    this.addItem(recordToConnect, inverse, ownerRecord);
                }
                if (prevConnectedRecordId && !inverse.dummy) {
                    const prevRecord = this[STORE_SYMBOL].getById(
                        field.relation,
                        prevConnectedRecordId
                    );
                    this.removeItem(prevRecord, inverse, ownerRecord);
                }
                ownerRecord[RAW_SYMBOL][field.name] = recordToConnect.id;
                ownerRecord._markDirty(field.name);
            } else if (field.type === "one2many") {
                // It's necessary to remove the previous connected in one2many but it would cause issue for inherited one2many field.
                // Also, we don't do modification in PoS and we can ignore the removing part to prevent issue.
                if (!inverse.dummy) {
                    recordToConnect[RAW_SYMBOL][inverse.name] = ownerRecord.id;
                    recordToConnect._markDirty(inverse.name);
                }
                this.addItem(ownerRecord, field, recordToConnect);
            } else if (field.type === "many2many") {
                this.addItem(ownerRecord, field, recordToConnect);
                this.addItem(recordToConnect, inverse, ownerRecord);
            }
        }

        disconnect(field, ownerRecord, recordOrIdToConnect) {
            if (!this[STORE_SYMBOL].hasIndex(field.relation, "id")) {
                // Not supported model
                return;
            }

            const inverse = inverseMap.get(field);
            const recordToDisconnect = this.getRecord(field.relation, recordOrIdToConnect);
            if (!recordToDisconnect) {
                return;
            }

            if (field.type === "many2one") {
                const prevConnectedRecordId = ownerRecord[RAW_SYMBOL][field.name];
                if (prevConnectedRecordId === recordToDisconnect.id) {
                    ownerRecord[RAW_SYMBOL][field.name] = undefined;
                    ownerRecord._markDirty(field.name);
                    this.removeItem(recordToDisconnect, inverse, ownerRecord);
                }
            } else if (field.type === "one2many") {
                this.removeItem(ownerRecord, field, recordToDisconnect);
                if (!inverse.dummy) {
                    const prevConnectedRecordId = recordToDisconnect[inverse.name]?.id;
                    if (prevConnectedRecordId === ownerRecord.id) {
                        recordToDisconnect[RAW_SYMBOL][inverse.name] = undefined;
                        recordToDisconnect._markDirty(inverse.name);
                    }
                }
            } else if (field.type === "many2many") {
                this.removeItem(ownerRecord, field, recordToDisconnect);
                this.removeItem(recordToDisconnect, inverse, ownerRecord);
            }
        }

        getRecord(model, recordOrId) {
            if (!recordOrId) {
                throw new Error(`Record '${model}' is undefined`);
            }
            if (recordOrId instanceof Base) {
                return recordOrId;
            }
            return this[STORE_SYMBOL].getById(model, recordOrId);
        }

        removeItem(ownerRecord, field, recordToRemove) {
            if (field.dummy || !ownerRecord) {
                return;
            }
            const recordIds = ownerRecord[RAW_SYMBOL][field.name];
            const idToRemove = recordToRemove.id;

            if (!idToRemove) {
                return;
            }
            ownerRecord[RAW_SYMBOL][field.name] = recordIds.filter((id) => id !== idToRemove);
            ownerRecord._markDirty(field.name);
            ownerRecord.model.triggerEvents("update", { id: ownerRecord.id });
        }

        addItem(ownerRecord, field, recordToAdd) {
            if (field.dummy || !ownerRecord) {
                return;
            }
            const recordIds = ownerRecord[RAW_SYMBOL][field.name];
            const idToAdd = recordToAdd.id;
            if (!recordIds.includes(idToAdd)) {
                recordIds.push(idToAdd);
                ownerRecord._markDirty(field.name);
                ownerRecord.model.triggerEvents("update", { id: ownerRecord.id });
            }
        }
    }

    const models = new Models(processedModelDefs);
    return { models };
}

export { Base } from "./base";
