import { Reactive, effect } from "@web/core/utils/reactive";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { markRaw } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";
import IndexedDB from "./utils/indexed_db";
import { DataServiceOptions } from "./data_service_options";
import { uuidv4 } from "@point_of_sale/utils";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;
const INDEXED_DB_VERSION = 1;

export class PosData extends Reactive {
    static modelToLoad = []; // When empty all models are loaded
    static serviceDependencies = ["orm"];

    constructor() {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }

    async setup(env, { orm }) {
        this.orm = orm;
        this.relations = [];
        this.custom = {};
        this.syncInProgress = false;
        this.mutex = markRaw(new Mutex());
        this.records = {};
        this.opts = new DataServiceOptions();

        this.network = {
            warningTriggered: false,
            offline: false,
            loading: true,
            unsyncData: [],
        };

        this.initIndexedDB();
        await this.initData();

        effect(
            batched((records) => {
                this.syncDataWithIndexedDB(records);
            }),
            [this.records]
        );

        browser.addEventListener("online", () => {
            if (this.network.offline) {
                this.network.offline = false;
                this.network.warningTriggered = false; // Avoid the display of the offline popup multiple times
            }

            this.syncData();
        });

        browser.addEventListener("offline", () => {
            this.network.offline = true;
        });
    }

    initIndexedDB() {
        // In web tests info is not defined
        const models = Object.entries(this.opts.databaseTable).map(([name, data]) => [
            data.key,
            name,
        ]);
        this.indexedDB = new IndexedDB(this.databaseName, INDEXED_DB_VERSION, models);
    }

    deleteDataIndexedDB(model, uuid) {
        this.indexedDB.delete(model, [{ uuid }]);
    }

    syncDataWithIndexedDB(records) {
        // Will separate records to remove from indexedDB and records to add
        const dataSorter = (records, isFinalized, key) =>
            records.reduce(
                (acc, record) => {
                    const finalizedState = isFinalized(record);

                    if (finalizedState === undefined || finalizedState === true) {
                        if (record[key]) {
                            acc.remove.push(record[key]);
                        }
                    } else {
                        acc.put.push(dataFormatter(record));
                    }

                    return acc;
                },
                { put: [], remove: [] }
            );

        // This methods will add uiState to the serialized object
        const dataFormatter = (record) => {
            const serializedData = record.serialize();
            const uiState = typeof record.uiState === "object" ? record.serializeState() : "{}";
            return { ...serializedData, JSONuiState: JSON.stringify(uiState), id: record.id };
        };

        const dataToDelete = {};

        for (const [model, params] of Object.entries(this.opts.databaseTable)) {
            const modelRecords = Array.from(records[model].values());

            if (!modelRecords.length) {
                continue;
            }

            const data = dataSorter(modelRecords, params.condition, params.key);
            this.indexedDB.create(model, data.put);
            dataToDelete[model] = data.remove;
        }

        this.indexedDB.readAll(Object.keys(this.opts.databaseTable)).then((data) => {
            if (!data) {
                return;
            }

            for (const [model, records] of Object.entries(data)) {
                const key = this.opts.databaseTable[model].key;
                let keysToDelete = [];

                if (dataToDelete[model]) {
                    const keysInIndexedDB = new Set(records.map((record) => record[key]));
                    keysToDelete = dataToDelete[model].filter((key) => keysInIndexedDB.has(key));
                }
                for (const record of records) {
                    const localRecord = this.models[model].get(record.id);
                    if (!localRecord) {
                        keysToDelete.push(record[key]);
                    }
                }

                if (keysToDelete.length) {
                    this.indexedDB.delete(model, keysToDelete);
                }
            }
        });
    }

    async preLoadData(data) {
        return data;
    }

    async loadIndexedDBData() {
        const data = await this.indexedDB.readAll();

        if (!data) {
            return;
        }

        const newData = {};
        for (const model of Object.keys(this.opts.databaseTable)) {
            const rawRec = data[model];

            if (rawRec) {
                newData[model] = rawRec.filter((r) => !this.models[model].get(r.id));
            }
        }

        if (data["product.product"]) {
            data["product.product"] = data["product.product"].filter(
                (p) => !this.models["product.product"].get(p.id)
            );
        }

        const preLoadData = await this.preLoadData(data);
        const missing = await this.missingRecursive(preLoadData);
        const results = this.models.loadData(missing, [], true);
        for (const [model, data] of Object.entries(results)) {
            for (const record of data) {
                if (record.raw.JSONuiState) {
                    const loadedRecords = this.models[model].find((r) => r.uuid === record.uuid);

                    if (loadedRecords) {
                        loadedRecords.setupState(JSON.parse(record.raw.JSONuiState));
                    }
                }
            }
        }

        return results;
    }

    resetUnsyncQueue() {
        this.network.unsyncData = [];
    }

    async loadInitialData() {
        try {
            return await this.orm.call("pos.session", "load_data", [
                odoo.pos_session_id,
                PosData.modelToLoad,
            ]);
        } catch (error) {
            let message = _t("An error occurred while loading the Point of Sale: \n");
            if (error instanceof RPCError) {
                message += error.data.message;
            } else {
                message += error.message;
            }
            window.alert(message);
        }
    }
    async initData() {
        const modelClasses = {};
        const relations = {};
        const fields = {};
        const data = {};
        const response = await this.loadInitialData();
        for (const [model, values] of Object.entries(response)) {
            relations[model] = values.relations;
            fields[model] = values.fields;
            data[model] = values.data;
        }

        for (const posModel of registry.category("pos_available_models").getAll()) {
            const pythonModel = posModel.pythonModel;
            const extraFields = posModel.extraFields || {};

            modelClasses[pythonModel] = posModel;
            relations[pythonModel] = {
                ...relations[pythonModel],
                ...extraFields,
            };
        }

        const { models, records, indexedRecords } = createRelatedModels(
            relations,
            modelClasses,
            this.opts
        );

        this.records = records;
        this.indexedRecords = indexedRecords;
        this.fields = fields;
        this.relations = relations;
        this.models = models;

        const order = data["pos.order"] || [];
        const orderlines = data["pos.order.line"] || [];

        delete data["pos.order"];
        delete data["pos.order.line"];

        this.models.loadData(data, this.modelToLoad);
        this.models.loadData({ "pos.order": order, "pos.order.line": orderlines });
        const dbData = await this.loadIndexedDBData();
        this.loadedIndexedDBProducts = dbData ? dbData["product.product"] : [];
        this.network.loading = false;
    }

    async execute({
        type,
        model,
        ids,
        values,
        method,
        queue,
        args = [],
        kwargs = {},
        fields = [],
        options = [],
        uuid = "",
    }) {
        this.network.loading = true;

        try {
            if (this.network.offline) {
                throw new ConnectionLostError();
            }

            let result = true;
            let limitedFields = false;
            if (fields.length === 0) {
                fields = this.fields[model] || [];
            }

            if (
                this.fields[model] &&
                fields.sort().join(",") !== this.fields[model].sort().join(",")
            ) {
                limitedFields = true;
            }

            switch (type) {
                case "write":
                    result = await this.orm.write(model, ids, values);
                    break;
                case "delete":
                    result = await this.orm.unlink(model, ids);
                    break;
                case "call":
                    result = await this.orm.call(model, method, args, kwargs);
                    break;
                case "read":
                    queue = false;
                    result = await this.orm.read(model, ids, fields, {
                        ...options,
                        load: false,
                    });
                    break;
                case "search_read":
                    queue = false;
                    result = await this.orm.searchRead(model, args, fields, {
                        ...options,
                        load: false,
                    });
            }

            if (type === "create") {
                const response = await this.orm.create(model, values);
                values[0].id = response[0];
                result = values;
            }

            const nonExistentRecords = [];
            if (limitedFields) {
                const X2MANY_TYPES = new Set(["many2many", "one2many"]);

                for (const record of result) {
                    const localRecord = this.models[model].get(record.id);

                    if (localRecord) {
                        const formattedForUpdate = {};
                        for (const [field, value] of Object.entries(record)) {
                            const fieldsParams = this.relations[model][field];

                            if (!fieldsParams) {
                                console.info("Warning, attempt to load a non-existent field.");
                                continue;
                            }

                            if (X2MANY_TYPES.has(fieldsParams.type)) {
                                formattedForUpdate[field] = value
                                    .filter((id) => this.models[fieldsParams.relation].get(id))
                                    .map((id) => [
                                        "link",
                                        this.models[fieldsParams.relation].get(id),
                                    ]);
                            } else if (fieldsParams.type === "many2one") {
                                if (this.models[fieldsParams.relation].get(value)) {
                                    formattedForUpdate[field] = [
                                        "link",
                                        this.models[fieldsParams.relation].get(value),
                                    ];
                                }
                            } else {
                                formattedForUpdate[field] = value;
                            }
                        }
                        localRecord.update(formattedForUpdate);
                    } else {
                        nonExistentRecords.push(record);
                    }
                }

                if (nonExistentRecords.length) {
                    console.warn(
                        "Warning, attempt to load a non-existent record with limited fields."
                    );
                    result = nonExistentRecords;
                }
            }

            if (
                this.models[model] &&
                this.opts.autoLoadedOrmMethods.includes(type) &&
                (!limitedFields || nonExistentRecords.length)
            ) {
                const data = await this.missingRecursive({ [model]: result });
                const results = this.models.loadData(data);
                result = results[model];
            }

            if (result === null || result === undefined) {
                // if request does not return something, we consider it went well
                return true;
            }
            return result;
        } catch (error) {
            let throwErr = true;
            const uuids = this.network.unsyncData.map((d) => d.uuid);
            if (
                queue &&
                !uuids.includes(uuid) &&
                method !== "sync_from_ui" &&
                error instanceof ConnectionLostError
            ) {
                this.network.unsyncData.push({
                    args: [...arguments],
                    date: DateTime.now(),
                    try: 1,
                    uuid: uuidv4(),
                });

                throwErr = false;
            }

            if (throwErr) {
                throw error;
            }
        } finally {
            this.network.loading = false;
        }
    }

    async missingRecursive(recordMap, idsMap = {}, acc = {}) {
        const missingRecords = {};
        const recordInMapByModelIds = Object.entries(recordMap).reduce((acc, [model, records]) => {
            acc[model] = new Set(records.map((r) => r.id));
            return acc;
        }, {});

        for (const [model, records] of Object.entries(recordMap)) {
            if (!acc[model]) {
                acc[model] = records;
            } else {
                acc[model] = acc[model].concat(records);
            }

            if (!this.relations[model]) {
                continue;
            }

            const relations = Object.entries(this.relations[model]).filter(
                ([, rel]) => rel.relation && rel.type && this.models[rel.relation]
            );

            for (const [, rel] of relations) {
                if (this.opts.pohibitedAutoLoadedModels.includes(rel.relation)) {
                    continue;
                }

                const values = records.map((record) => record[rel.name]).flat();
                const missing = values.filter((value) => {
                    if (!value || typeof value !== "number" || idsMap[rel.relation]?.has(value)) {
                        return false;
                    }

                    const record = this.models[rel.relation].get(value);
                    return (
                        (!record || !record.id) && !recordInMapByModelIds[rel.relation]?.has(value)
                    );
                });

                if (missing.length > 0) {
                    if (!missingRecords[rel.relation]) {
                        missingRecords[rel.relation] = new Set(missing);
                    } else {
                        missingRecords[rel.relation] = new Set([
                            ...missingRecords[rel.relation],
                            ...missing,
                        ]);
                    }
                }
            }
        }

        const newRecordMap = {};
        for (const [model, ids] of Object.entries(missingRecords)) {
            if (!idsMap[model]) {
                idsMap[model] = new Set(ids);
            } else {
                idsMap[model] = idsMap[model] = new Set([...idsMap[model], ...ids]);
            }

            const data = await this.orm.read(model, Array.from(ids), this.fields[model], {
                load: false,
            });
            newRecordMap[model] = data;
        }

        if (Object.keys(newRecordMap).length > 0) {
            return await this.missingRecursive(newRecordMap, idsMap, acc);
        } else {
            return acc;
        }
    }

    async syncData() {
        this.syncInProgress = true;

        await this.mutex.exec(async () => {
            while (this.network.unsyncData.length > 0) {
                const data = this.network.unsyncData[0];
                const result = await this.execute({ ...data.args[0], uuid: data.uuid });

                if (result) {
                    this.network.unsyncData.shift();
                } else {
                    this.network.unsyncData[0].try += 1;
                    break;
                }
            }
        });

        this.syncInProgress = false;
    }

    write(model, ids, vals) {
        const records = [];

        for (const id of ids) {
            const record = this.models[model].get(id);
            delete vals.id;
            record.update(vals);

            const dataToUpdate = {};
            const keysToUpdate = Object.keys(vals);

            for (const key of keysToUpdate) {
                dataToUpdate[key] = vals[key];
            }

            records.push(record);
            this.ormWrite(model, [record.id], dataToUpdate);
        }

        return records;
    }

    delete(model, ids) {
        const deleted = [];
        for (const id of ids) {
            const record = this.models[model].get(id);
            deleted.push(id);
            record.delete();
        }

        this.ormDelete(model, ids);
        return deleted;
    }

    async searchRead(model, domain = [], fields = [], options = {}, queue = false) {
        return await this.execute({
            type: "search_read",
            model,
            args: domain,
            fields,
            options,
            queue,
        });
    }

    async read(model, ids, fields = [], options = [], queue = false) {
        return await this.execute({ type: "read", model, ids, fields, options, queue });
    }

    async call(model, method, args = [], kwargs = {}, queue = false) {
        return await this.execute({ type: "call", model, method, args, kwargs, queue });
    }

    // In a silent call we ignore the error and return false instead
    async silentCall(model, method, args = [], kwargs = {}, queue = false) {
        try {
            return await this.execute({ type: "call", model, method, args, kwargs, queue });
        } catch (e) {
            console.warn("Silent call failed:", e);
            return false;
        }
    }

    async callRelated(model, method, args = [], kwargs = {}, queue = true) {
        const data = await this.execute({ type: "call", model, method, args, kwargs, queue });
        const results = this.models.loadData(data, [], true);
        return results;
    }

    async create(model, values, queue = true) {
        return await this.execute({ type: "create", model, values, queue });
    }

    async ormWrite(model, ids, values, queue = true) {
        return await this.execute({ type: "write", model, ids, values, queue });
    }

    async ormDelete(model, ids, queue = true) {
        return await this.execute({ type: "delete", model, ids, queue });
    }

    localDeleteCascade(record, force = false) {
        const recordModel = record.constructor.pythonModel;
        if (typeof record.id === "number" && !force) {
            console.info(
                `Record ID ${record.id} MODEL ${recordModel}. If you want to delete a record saved on the server, you need to pass the force parameter as true.`
            );
            return;
        }

        const relationsToDelete = Object.values(this.relations[recordModel])
            .filter((rel) => this.opts.cascadeDeleteModels.includes(rel.relation))
            .map((rel) => rel.name);
        const recordsToDelete = Object.entries(record)
            .filter(([idx, values]) => relationsToDelete.includes(idx) && values)
            .map(([idx, values]) => values)
            .flat();

        // Delete all children records before main record
        this.indexedDB.delete(recordModel, [record.uuid]);
        for (const item of recordsToDelete) {
            this.indexedDB.delete(item.model.modelName, [item.uuid]);
            item.delete();
        }

        // Delete the main record
        const result = record.delete();
        return result;
    }

    deleteUnsyncData(uuid) {
        this.network.unsyncData = this.network.unsyncData.filter((d) => d.uuid !== uuid);
    }
}

export const PosDataService = {
    dependencies: PosData.serviceDependencies,
    async start(env, deps) {
        return new PosData(env, deps).ready;
    },
};

registry.category("services").add("pos_data", PosDataService);
