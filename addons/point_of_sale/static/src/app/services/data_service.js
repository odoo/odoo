import { Reactive } from "@web/core/utils/reactive";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { DataServiceOptions } from "../models/data_service_options";
import { getOnNotified } from "@point_of_sale/utils";
import { browser } from "@web/core/browser/browser";
import { RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import IndexedDB from "../models/utils/indexed_db";
const { DateTime } = luxon;
const INDEXED_DB_VERSION = 1;
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { debounce } from "@web/core/utils/timing";
import { omit } from "@web/core/utils/objects";
import { serializeDateTime } from "@web/core/l10n/dates";

export class PosData extends Reactive {
    static modelToLoad = []; // When empty all models are loaded
    static serviceDependencies = ["orm", "bus_service", "dialog"];

    constructor() {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }

    async setup(env, services) {
        this.relations = [];
        this.records = {};
        Object.assign(this, services);
        this.opts = new DataServiceOptions();
        this.channels = [];

        this.network = {
            loading: true,
            get offline() {
                return !navigator.onLine;
            },
        };

        this.initializeWebsocket();
        await this.intializeDataRelation();

        browser.addEventListener("offline", () => {
            this.dialog.add(AlertDialog, {
                title: _t("Connection Lost"),
                body: _t(
                    "Until the connection is reestablished, Odoo Point of Sale will operate with limited functionality."
                ),
                confirmLabel: _t("Continue with limited functionality"),
            });
        });

        this.bus_service.addEventListener("connect", this.reconnectWebSocket.bind(this));
    }

    initializeWebsocket() {
        this.onNotified = getOnNotified(this.bus_service, odoo.access_token);
    }

    reconnectWebSocket() {
        this.initializeWebsocket();
        const channels = [...this.channels];
        this.channels = [];
        while (channels.length) {
            const channel = channels.pop();
            this.connectWebSocket(channel.channel, channel.method);

            console.warn("Reconnecting to channel", channel.channel);
        }
    }

    connectWebSocket(channel, method) {
        this.channels.push({
            channel,
            method,
        });

        this.onNotified(channel, method);
    }
    get databaseName() {
        return `config-id_${odoo.pos_config_id}_${odoo.access_token}`;
    }

    get serverDateKey() {
        return `data_server_date_${odoo.pos_config_id}`;
    }

    async resetIndexedDB() {
        // Remove data_server_date since it's used to determine the last time the data was loaded
        await this.indexedDB.reset();
    }

    async initIndexedDB(relations) {
        // This method initializes indexedDB with all models loaded into the PoS. The default key is ID.
        // But some models have another key configured in data_service_options.js. These models are
        // generally those that can be created in the frontend.
        const models = Object.keys(relations).map((model) => {
            const key = this.opts.databaseTable[model]?.key || "id";
            return [key, model];
        });

        return new Promise((resolve) => {
            this.indexedDB = new IndexedDB(this.databaseName, INDEXED_DB_VERSION, models, resolve);
        });
    }
    async synchronizeLocalDataInIndexedDB() {
        // This methods will synchronize local data and state in indexedDB. This methods is mostly
        // used with models like pos.order, pos.order.line, pos.payment etc. These models are created
        // in the frontend and are not loaded from the backend.
        const modelsParams = Object.entries(this.opts.databaseTable);
        for (const [model, params] of modelsParams) {
            const put = [];
            const remove = [];
            const data = this.models[model].getAll();

            for (const record of data) {
                const isToRemove = params.condition(record);

                if (isToRemove === undefined || isToRemove === true) {
                    if (record[params.key]) {
                        remove.push(record[params.key]);
                    }
                } else {
                    const serializedData = record.serialize();
                    const uiState =
                        typeof record.uiState === "object" ? record.serializeState() : "{}";
                    const serializedRecord = {
                        ...serializedData,
                        JSONuiState: JSON.stringify(uiState),
                        id: record.id,
                    };
                    put.push(serializedRecord);
                }
            }

            await this.indexedDB.delete(model, remove);
            await this.indexedDB.create(model, put);
        }
    }

    async synchronizeServerDataInIndexedDB(serverData = {}) {
        // for (const [model, data] of Object.entries(serverData)) {
        //     try {
        //         await this.indexedDB.create(model, data);
        //     } catch {
        //         console.info(`Error while updating ${model} in indexedDB.`);
        //     }
        // }
    }
    async getLocalDataFromIndexedDB() {
        // Used to retrieve models containing states from the indexedDB.
        // This method will load the records directly via loadData.
        const models = Object.keys(this.opts.databaseTable);
        const data = await this.indexedDB.readAll(models);

        if (!data) {
            return;
        }

        const newData = {};
        for (const model of models) {
            const rawRec = data[model];

            if (rawRec) {
                newData[model] = rawRec.filter((r) => !this.models[model].get(r.id));
            }
        }

        const preLoadData = await this.preLoadData(data);
        const missing = await this.missingRecursive(preLoadData);
        const results = this.models.loadData(missing, [], true, true);
        for (const data of Object.values(results)) {
            for (const record of data) {
                if (record.raw.JSONuiState) {
                    record.setupState(JSON.parse(record.raw.JSONuiState));
                }
            }
        }

        if (results && results["pos.order"]) {
            const ids = results["pos.order"]
                .map((o) => o.id)
                .filter((id) => typeof id === "number");

            if (ids.length) {
                const result = await this.read("pos.order", ids);
                const serverIds = result.map((r) => r.id);

                for (const id of ids) {
                    if (!serverIds.includes(id)) {
                        this.localDeleteCascade(this.models["pos.order"].get(id));
                    }
                }
            }
        }

        return results;
    }

    async getCachedServerDataFromIndexedDB() {
        // Used to load models that have not yet been loaded into related_models.
        // These models have been sent to the indexedDB directly after the RPC load_data.
        const data = await this.indexedDB.readAll();
        const modelToIgnore = Object.keys(this.opts.databaseTable);
        const results = {};

        for (const name in data) {
            if (name in modelToIgnore) {
                continue;
            }
            results[name] = data[name];
        }

        return results;
    }
    async loadInitialData() {
        let localData = await this.getCachedServerDataFromIndexedDB();
        const session = localData?.["pos.session"]?.[0];

        if (
            (navigator.onLine && session?.state !== "opened") ||
            session?.id !== odoo.pos_session_id ||
            odoo.from_backend
        ) {
            try {
                const limitedLoading = this.isLimitedLoading();
                const serverDate = localData["pos.session"]?.[0]?._data_server_date;
                const lastConfigChange = DateTime.fromSQL(odoo.last_data_change);
                const serverDateTime = DateTime.fromSQL(serverDate);

                if (serverDateTime < lastConfigChange) {
                    await this.resetIndexedDB();
                    await this.initIndexedDB(this.relations);
                    localData = [];
                }

                const data = await this.orm.call(
                    "pos.session",
                    "load_data",
                    [odoo.pos_session_id, PosData.modelToLoad],
                    {
                        context: {
                            pos_last_server_date: serverDateTime > lastConfigChange && serverDate,
                            pos_limited_loading: limitedLoading,
                        },
                    }
                );

                for (const [model, values] of Object.entries(data)) {
                    const local = localData[model] || [];

                    if (this.opts.uniqueModels.includes(model) && values.length > 0) {
                        this.indexedDB.delete(
                            model,
                            local.map((r) => r.id)
                        );
                        localData[model] = values;
                    } else {
                        localData[model] = local.concat(values);
                    }
                }

                this.synchronizeServerDataInIndexedDB(localData);
            } catch (error) {
                let message = _t("An error occurred while loading the Point of Sale: \n");
                if (error instanceof RPCError) {
                    message += error.data.message;
                } else {
                    message += error.message;
                }
                window.alert(message);
                return localData;
            }
        }

        return localData;
    }

    async initData(hard = false, limit = true) {
        const data = await this.loadInitialData(hard, limit);
        const order = data["pos.order"] || [];
        const orderlines = data["pos.order.line"] || [];

        delete data["pos.order"];
        delete data["pos.order.line"];

        this.models.loadData(data, this.modelToLoad);
        this.models.loadData({ "pos.order": order, "pos.order.line": orderlines });
    }

    async loadFieldsAndRelations() {
        const key = `pos_data_params_${odoo.pos_config_id}`;
        if (!navigator.onLine) {
            return JSON.parse(localStorage.getItem(key));
        }

        try {
            const params = await this.orm.call("pos.session", "load_data_params", [
                odoo.pos_session_id,
            ]);
            localStorage.setItem(key, JSON.stringify(params));
            return params;
        } catch {
            return JSON.parse(localStorage.getItem(key));
        }
    }

    async intializeDataRelation() {
        // Here the order is important. loadFieldsAndRelations will load all the information
        // about the models loaded in the PoS. Then initIndexedDB needs it to update/create
        // the indexedDB. loadInitialData needs indexedDB, so it comes at the end.
        const modelClasses = {};
        const fields = {};
        const relations = {};
        const dataParams = await this.loadFieldsAndRelations();
        await this.initIndexedDB(dataParams);

        for (const [model, values] of Object.entries(dataParams)) {
            relations[model] = values.relations;
            fields[model] = values.fields;
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
        this.queue = JSON.parse(
            localStorage.getItem(`pos_config_${odoo.pos_config_id}_changes_queue`) || "[]"
        );
        // if (this.queue.length) {
        //     // This means that we have unsynced data from the last session.
        //     // We sync this data with the server and then we restart the initData method
        //     // to get the latest data from the server.
        //     // This means that we don't have to manually deal with the "merging" of this unsynced data
        //     await this.flush();
        //     return this.initData();
        // }
        const MIN_FLUSH_INTERVAL_MILLIS = 1000;
        this.debouncedFlush = debounce(this.flush.bind(this), MIN_FLUSH_INTERVAL_MILLIS);

        const getId = (record) => record?.id ?? record ?? false; // the orm service ignores undefined values, so we need to set it to false
        const prepareValue = (record) => {
            if (record instanceof Array) {
                // this means that it's a many2many field field
                // ex: "attribute_value_ids":[["link",52]]
                // return record.map((r) => [6, 0, [getId(r)]]);
                return record.map((r) => getId(r));
            }
            // if (DATE_TIME_TYPE.has(field.type) && typeof record[name] === "object") {
            //     result[name] = serializeDateTime(record[name]);
            // }
            return getId(record);
        };
        const { models, baseData } = createRelatedModels(relations, modelClasses, {
            ...this.opts,
            onCreate: (model, vals) => {
                if (!this.shouldSync) {
                    return;
                }
                // if (model === "pos.preparation.orderline") {
                //     debugger;
                // }
                const dateTypeVals = Object.keys(vals).filter((v) =>
                    Object.values(this.models[model].fields)
                        .filter((v) => ["date", "datetime"].includes(v.type))
                        .map((k) => k.name)
                        .includes(v)
                );
                for (const dateTypeVal of dateTypeVals) {
                    vals[dateTypeVal] = serializeDateTime(vals[dateTypeVal]);
                }
                this.queue.push([
                    "CREATE",
                    model,
                    Object.fromEntries(Object.entries(vals).map(([k, v]) => [k, prepareValue(v)])),
                ]);
                this.debouncedFlush();
            },
            onUpdate: (record, vals) => {
                if (!this.shouldSync) {
                    return;
                }
                vals = omit(vals, "id");
                if (record.model.name === "pos.order") {
                    vals = omit(vals, "lines", "payment_ids");
                }
                vals = Object.fromEntries(
                    Object.entries(vals).map(([k, v]) => [k, prepareValue(v)])
                );
                if (
                    this.queue.at(-1)?.[0] === "UPDATE" &&
                    this.queue.at(-1)?.[2] === getId(record)
                ) {
                    this.queue.at(-1)[3] = {
                        ...this.queue.at(-1)[3],
                        ...vals,
                    };
                    this.debouncedFlush();
                    return;
                }
                if (
                    this.queue.at(-1)?.[0] === "CREATE" &&
                    this.queue.at(-1)?.[1] === record.model.name
                ) {
                    this.queue.at(-1)[2] = {
                        ...this.queue.at(-1)[2],
                        ...vals,
                    };
                    this.debouncedFlush();
                    return;
                }
                this.queue.push(["UPDATE", record.model.name, getId(record), vals]);
                this.debouncedFlush();
            },
            onDelete: (record) => {
                if (!this.shouldSync) {
                    return;
                }
                this.queue.push(["DELETE", record.model.name, record.uuid]);
                this.debouncedFlush();
            },
        });

        this.baseData = baseData;
        this.fields = fields;
        this.relations = relations;
        this.models = models;

        await this.initData();
        await this.getLocalDataFromIndexedDB();
        this.initListeners();
        this.network.loading = false;
        this.shouldSync = true;
        this.connectWebSocket("DATA_CHANGED", (newData) => {
            this.withoutSyncing(async () => {
                console.log("DATA_CHANGED", newData);

                for (const [command, ...data] of newData) {
                    const findRecord = async (modelName, id) =>
                        this.models[modelName].find((x) => x.uuid === id || x.id === id) ||
                        (await this.searchRead(modelName, [["uuid", "=", id]]))[0];

                    const linkVals = async (modelName, vals) => {
                        for (const key in vals) {
                            const field = this.models[modelName]?.fields[key];

                            if (field?.type === "many2one" && vals[key]) {
                                vals[key] = await findRecord(field.relation, vals[key]);
                            }
                            if (field.type === "many2many") {
                                // TODO: correctly choose between link and update
                                const values = await Promise.all(
                                    vals[key].map(
                                        async (id) => await findRecord(field.relation, id)
                                    )
                                );
                                vals[key] = [["link", ...values]];
                            }
                        }
                        return vals;
                    };

                    if (command === "CREATE") {
                        const [model, vals] = data;
                        this.models[model].create(vals, false, true, false);
                    } else if (command === "UPDATE") {
                        const [model, id, vals] = data;
                        const modelToUpdate = await findRecord(model, id);
                        if (modelToUpdate) {
                            const linkedVals = await linkVals(model, vals);
                            modelToUpdate.update(linkedVals);
                        }
                    } else if (command === "DELETE") {
                        const [model, id] = data;
                        const recordToDelete = this.models[model].find(
                            (x) => x.uuid === id || x.id === id
                        );
                        if (recordToDelete) {
                            recordToDelete.delete();
                        }
                    }
                }
            });
        });
    }
    async withoutSyncing(callback) {
        this.shouldSync = false;
        await callback();
        this.shouldSync = true;
    }

    initListeners() {
        // this.models["pos.order"].addEventListener(
        //     "update",
        //     batched(this.synchronizeLocalDataInIndexedDB.bind(this))
        // );
        // const ignore = Object.keys(this.opts.databaseTable);
        // for (const model of Object.keys(this.relations)) {
        //     if (ignore.includes(model)) {
        //         continue;
        //     }
        //     this.models[model].addEventListener("delete", (params) => {
        //         this.indexedDB.delete(model, [params.key]);
        //     });
        //     this.models[model].addEventListener("update", (params) => {
        //         const record = this.models[model].get(params.id).raw;
        //         for (const [key, value] of Object.entries(record)) {
        //             if (value instanceof Base) {
        //                 record[key] = value.id;
        //             } else if (Array.isArray(value) && value[0] instanceof Base) {
        //                 record[key] = value.map((v) => v.id);
        //             }
        //         }
        //         this.synchronizeServerDataInIndexedDB({ [model]: [record] });
        //     });
        // }
    }

    async verifyCurrentSession() {
        // If another device close the session we need to invalided the indexedDB on
        // on the current device during the next reload
        const localSessionId = localStorage.getItem(`pos.session.${odoo.pos_config_id}`);
        if (
            parseInt(localSessionId) &&
            parseInt(localSessionId) !== parseInt(odoo.pos_session_id)
        ) {
            await this.resetIndexedDB();
            localStorage.removeItem(`pos.session.${odoo.pos_config_id}`);
            window.location.reload();
            localStorage.setItem(`pos.session.${odoo.pos_config_id}`, odoo.pos_session_id);
        }
    }

    async flush() {
        // return;
        if (this.queue.length === 0 || !navigator.onLine) {
            return;
        }
        console.log("Flushing queue");
        const log = (data) =>
            console.log(
                "%c" + JSON.stringify(data, null, 2),
                "color: white; font-family: monospace; white-space: pre;"
            );
        this.queue.forEach((data) => log(data));
        try {
            const idUpdates = await this.orm.call(
                "pos.config",
                "sync_from_ui_2",
                [odoo.pos_config_id, this.queue],
                {},
                false
            );
            this.idUpdates ||= [];
            this.idUpdates.push(...idUpdates);
            // for (const [model, uuid, id] of idUpdates) {
            // this.baseData[model][id] = this.models[model].find((x) => x.uuid === uuid);
            // this.baseData[model][id].id = id;
            // delete this.baseData[model][uuid];
            // }
            this.queue = [];
            console.log("Queue flushed");
            return true;
        } catch (error) {
            localStorage.setItem(
                `pos_config_${odoo.pos_config_id}_changes_queue`,
                JSON.stringify(this.queue)
            );
            console.error("Flush failed", error);
            return false;
        }
    }

    async execute({ type, model, ids, args = [], fields = [], options = [] }) {
        this.network.loading = true;

        let result = true;
        if (fields.length === 0) {
            fields = this.fields[model] || [];
        }

        switch (type) {
            case "read":
                result = await this.orm.read(model, ids, fields, {
                    ...options,
                    load: false,
                });
                break;
            case "search_read":
                result = await this.orm.searchRead(model, args, fields, {
                    ...options,
                    load: false,
                });
        }

        if (this.models[model] && this.opts.autoLoadedOrmMethods.includes(type)) {
            const data = await this.missingRecursive({ [model]: result });
            const results = this.models.loadData(data);
            result = results[model];
        }

        this.network.loading = false;
        return result;
    }

    async missingRecursive(recordMap, idsMap = {}, acc = {}) {
        if (!navigator.onLine) {
            return acc;
        }

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

            try {
                const data = await this.orm.read(model, Array.from(ids), this.fields[model], {
                    load: false,
                });
                newRecordMap[model] = data;
            } catch {
                newRecordMap[model] = [];
            }
        }

        if (Object.keys(newRecordMap).length > 0) {
            return await this.missingRecursive(newRecordMap, idsMap, acc);
        } else {
            return acc;
        }
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

    async call(model, method, args = [], kwargs = {}) {
        await this.flush();
        if (this.queue.length > 0) {
            throw new Error("There are unsynced changes in the queue.");
        }
        // TODO: check api.model methods
        let ids;
        if (typeof args[0] === "number") {
            ids = args[0];
        } else if (typeof args[0] === "string") {
            // const record = this.models[model].find((x) => x.uuid === args[0]);
            ids = this.idUpdates.find((x) => x[1] === args[0])?.[2];
        } else if (args[0] instanceof Array) {
            ids = args[0].map((id) => {
                if (typeof id === "number") {
                    return id;
                }
                return this.idUpdates.find((x) => x[1] === id)?.[2];
            });
        }
        return await this.orm.call(model, method, [ids, ...args.slice(1)], kwargs);
    }

    // In a silent call we ignore the error and return false instead
    async silentCall(model, method, args = [], kwargs = {}, preFlush = false) {
        try {
            return this.call(model, method, args, kwargs, preFlush);
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

    async preLoadData(data) {
        return data;
    }

    isLimitedLoading() {
        const url = new URL(window.location.href);
        const limitedLoading = url.searchParams.get("limited_loading") === "0" ? false : true;

        if (!limitedLoading) {
            url.searchParams.delete("limited_loading");
            window.history.replaceState({}, "", url);
        }

        return limitedLoading;
    }
}

export const PosDataService = {
    dependencies: PosData.serviceDependencies,
    async start(env, deps) {
        return new PosData(env, deps).ready;
    },
};

registry.category("services").add("pos_data", PosDataService);
