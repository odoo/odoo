import { Reactive } from "@web/core/utils/reactive";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { DataServiceOptions } from "../models/data_service_options";
import { browser } from "@web/core/browser/browser";
import { RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import IndexedDB from "../models/utils/indexed_db";
const { DateTime } = luxon;
const INDEXED_DB_VERSION = 1;
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { batched, debounce } from "@web/core/utils/timing";
import { omit } from "@web/core/utils/objects";

export class PosData extends Reactive {
    static modelToLoad = []; // When empty all models are loaded
    static serviceDependencies = ["orm", "dialog"];

    constructor() {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }

    async setup(env, services) {
        Object.assign(this, services);
        this.relations = [];
        this.records = {};
        this.opts = new DataServiceOptions();

        this.network = {
            loading: true,
            get offline() {
                return !navigator.onLine;
            },
        };

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

    async synchronizeServerDataInIndexedDB(serverData) {
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
        const results = this.models.loadData(this.models, missing, [], true);
        for (const data of Object.values(results)) {
            for (const record of data) {
                if (record.raw.JSONuiState) {
                    record.setupState(JSON.parse(record.raw.JSONuiState));
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
        const sessionState = localData?.["pos.session"]?.[0]?.state;

        if (navigator.onLine && sessionState !== "opened") {
            try {
                const limitedLoading = this.isLimitedLoading();
                const serverDate = localData?.["pos.session"]?.[0]?._data_server_date;
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

        this.models.loadData(this.models, data, this.modelToLoad);
        this.models.loadData(this.models, { "pos.order": order, "pos.order.line": orderlines });
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

        const getId = (record) => {
            if (record?.id) {
                return typeof record.id === "number" ? record.id : record.uuid;
            }
            return record ?? false; // the orm service ignores undefined values, so we need to set it to false
        };
        const prepareValue = (record) => {
            if (record instanceof Array) {
                // this means that it's a many2many field field
                // ex: "attribute_value_ids":[["link",52]]
                return record.map(([command, record]) => [6, 0, [getId(record)]]);
            }
            return getId(record);
        };
        const { models, records, indexedRecords, baseData } = createRelatedModels(
            relations,
            modelClasses,
            {
                ...this.opts,
                onCreate: (model, vals) => {
                    if (!this.finishedLoading) {
                        return;
                    }
                    this.queue.push([
                        "CREATE",
                        model,
                        Object.fromEntries(
                            Object.entries(vals).map(([k, v]) => [k, prepareValue(v)])
                        ),
                    ]);
                    this.debouncedFlush();
                },
                onUpdate: (record, vals) => {
                    if (!this.finishedLoading) {
                        return;
                    }
                    vals = omit(vals, "id");
                    if (record.model.modelName === "pos.order") {
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
                        this.queue.at(-1)?.[1] === record.model.modelName
                    ) {
                        this.queue.at(-1)[2] = {
                            ...this.queue.at(-1)[2],
                            ...vals,
                        };
                        this.debouncedFlush();
                        return;
                    }
                    this.queue.push(["UPDATE", record.model.modelName, getId(record), vals]);
                    this.debouncedFlush();
                },
                onDelete: (model, recordUuid) => {
                    this.queue.push(["DELETE", model, recordUuid]);
                    this.debouncedFlush();
                },
            }
        );

        this.baseData = baseData;
        this.records = records;
        this.indexedRecords = indexedRecords;
        this.fields = fields;
        this.relations = relations;
        this.models = models;

        await this.initData();
        await this.getLocalDataFromIndexedDB();
        this.initListeners();
        this.network.loading = false;
        this.finishedLoading = true;
    }

    initListeners() {
        this.models["pos.order"].addEventListener(
            "update",
            batched(this.synchronizeLocalDataInIndexedDB.bind(this))
        );
        const ignore = Object.keys(this.opts.databaseTable);
        for (const model of Object.keys(this.relations)) {
            if (ignore.includes(model)) {
                continue;
            }

            this.models[model].addEventListener("delete", (params) => {
                this.indexedDB.delete(model, [params.key]);
            });

            this.models[model].addEventListener("update", (params) => {
                const record = this.models[model].get(params.id).raw;
                this.synchronizeServerDataInIndexedDB({ [model]: [record] });
            });
        }
    }

    async flush() {
        if (this.queue.length === 0) {
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
            await this.call(
                "pos.config",
                "sync_from_ui_2",
                [odoo.pos_config_id, this.queue],
                {},
                false
            );
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
            case "delete":
                result = await this.orm.unlink(model, ids);
                break;
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
                    return !record || !record.id;
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
    // TODO: this method is not used
    delete(model, ids) {
        const deleted = [];
        for (const id of ids) {
            const record = this.models[model].get(id);
            deleted.push(id);
            record.delete();
        }

        this.execute({ type: "delete", model, ids });
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

    async call(model, method, args = [], kwargs = {}) {
        // await this.flush();
        return await this.orm.call(model, method, args, kwargs);
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
        const results = this.models.loadData(this.models, data, [], true);
        return results;
    }

    localDeleteCascade(record, force = false) {
        const recordModel = record.constructor.pythonModel;
        if (typeof record.id === "number" && !force) {
            console.info(
                `Record ID ${record.id} MODEL ${recordModel}. If you want to delete a record saved on the server, you need to pass the force parameter as true.`
            );
            return;
        }

        // Delete the main record
        const result = record.delete();
        return result;
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
