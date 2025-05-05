import { Reactive } from "@web/core/utils/reactive";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { DataServiceOptions } from "../models/data_service_options";
import { getOnNotified } from "@point_of_sale/utils";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import IndexedDB from "../models/utils/indexed_db";
const { DateTime } = luxon;
const INDEXED_DB_VERSION = 1;
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { debounce } from "@web/core/utils/timing";
import { serializeDateTime } from "@web/core/l10n/dates";
import { omit } from "@web/core/utils/objects";
import { Mutex } from "@web/core/utils/concurrency";

const MIN_FLUSH_INTERVAL_MILLIS = 10;

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
        this.idUpdates = {};

        this.network = {
            loading: true,
            get offline() {
                return !navigator.onLine;
            },
        };
        this.flushMutex = new Mutex();
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

            console.debug("Reconnecting to channel", channel.channel);
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
        return `point-of-sale-${odoo.pos_config_id}-${odoo.info?.db}`;
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
        const models = Object.keys(relations).map((model) => ["id", model]);

        return new Promise((resolve) => {
            this.indexedDB = new IndexedDB(this.databaseName, INDEXED_DB_VERSION, models, resolve);
        });
    }

    async synchronizeServerDataInIndexedDB(serverData = {}) {
        for (const [model, data] of Object.entries(serverData)) {
            try {
                await this.indexedDB.create(model, data);
            } catch {
                console.info(`Error while updating ${model} in indexedDB.`);
            }
        }
    }
    async loadInitialData() {
        let localData = await this.indexedDB.readAll();
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
                    localData[model] = local.concat(values);
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

    async initData() {
        const data = await this.loadInitialData();
        this.models.connectNewData(data);
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
        // this.queue = JSON.parse(
        //     localStorage.getItem(`pos_config_${odoo.pos_config_id}_changes_queue`) || "[]"
        // );
        this.queue = [];
        // if (this.queue.length) {
        //     // This means that we have unsynced data from the last session.
        //     // We sync this data with the server and then we restart the initData method
        //     // to get the latest data from the server.
        //     // This means that we don't have to manually deal with the "merging" of this unsynced data
        //     await this.flush();
        //     return this.initData();
        // }
        this.debouncedFlush = debounce(this.flush.bind(this), MIN_FLUSH_INTERVAL_MILLIS);
        // this.debouncedFlush = this.flush.bind(this);

        const prepareVals = (vals) =>
            Object.fromEntries(
                Object.entries(vals).map(([k, v]) => {
                    const getId = (record) => record?.id ?? record ?? false; // the orm service ignores undefined values, so we need to set it to false
                    if (v?.isValid) {
                        return [k, serializeDateTime(v)];
                    }
                    if (v instanceof Array) {
                        return [k, v.map((r) => getId(r))];
                    }
                    return [k, getId(v)];
                })
            );
        const { models } = createRelatedModels(relations, modelClasses, this.opts);
        Object.entries(models).forEach(([modelName, _]) => {
            models[modelName].addEventListener("create", ({ ids }) => {
                if (!this.shouldSync) {
                    return;
                }
                if (!ids.length) {
                    return;
                }
                const vals = models[modelName].getBy("uuid", ids[0]).raw;
                // Skip IndexedDB calls if it hasn't been initialized (e.g., in prepDisplay, kiosk)
                this.indexedDB?.create(modelName, [vals]);
                this.queue.push(["CREATE", modelName, omit(vals, "id")]);
                this.debouncedFlush();
            });
            models[modelName].addEventListener("update", ({ id, vals }) => {
                if (!this.shouldSync || !vals) {
                    return;
                }
                this.indexedDB?.update(modelName, id, prepareVals(vals));
                this.queue.push(["UPDATE", modelName, id, prepareVals(vals)]);
                this.debouncedFlush();
            });
            models[modelName].addEventListener("delete", ({ id }) => {
                if (!this.shouldSync) {
                    return;
                }
                this.indexedDB?.delete(modelName, [id]);
                this.queue.push(["DELETE", modelName, id]);
                this.debouncedFlush();
            });
        });

        this.fields = fields;
        this.relations = relations;
        this.models = models;
        await this.withoutSyncing(this.initData.bind(this));
        this.network.loading = false;
        this.connectWebSocket("DATA_CHANGED", ({ queue: newData, login_number, config_id }) => {
            if (config_id == odoo.pos_config_id && login_number == odoo.login_number) {
                return;
            }
            const findRecord = async (modelName, id) =>
                this.models[modelName].find((x) => x.uuid === id || x.id === id) ||
                (
                    await this.searchRead(modelName, [
                        [typeof id === "string" ? "uuid" : "id", "=", id],
                    ])
                )[0];
            const linkVals = async (modelName, vals) => {
                for (const key in vals) {
                    const field = this.models[modelName]?.fields[key];

                    if (field?.type === "many2one" && vals[key]) {
                        vals[key] = await findRecord(field.relation, vals[key]);
                    }
                    if (field.type === "many2many" || field.type === "one2many") {
                        const records = await Promise.all(
                            [...vals[key]].map(async (id) => await findRecord(field.relation, id))
                        );
                        vals[key] = [["set", ...records.filter((x) => x)]];
                    }
                }
                return vals;
            };
            this.withoutSyncing(async () => {
                for (const [command, ...data] of newData) {
                    if (command === "CREATE") {
                        const [model, vals] = data;
                        this.models[model].create(await linkVals(model, vals));
                    } else if (command === "UPDATE") {
                        const [model, id, vals] = data;
                        (await findRecord(model, id))?.update(await linkVals(model, vals));
                    } else if (command === "DELETE") {
                        const [model, id] = data;
                        this.models[model].find((x) => x.uuid === id || x.id === id)?.delete();
                    }
                }
            });
        });
    }
    async withoutSyncing(callback) {
        try {
            this.shouldSync = false;
            return await callback();
        } finally {
            this.shouldSync = true;
        }
    }

    async flush() {
        await this.flushMutex.exec(async () => {
            if (this.queue.length === 0 || !navigator.onLine) {
                return;
            }
            try {
                console.debug("Flushing: ");
                console.debug(
                    "%c" + JSON.stringify(this.queue, null, 2),
                    "color: white; font-family: monospace; white-space: pre;"
                );
                const queueLength = this.queue.length;
                const idUpdates = await this.orm.call(
                    "pos.config",
                    "flush",
                    [odoo.pos_config_id, this.queue, odoo.login_number],
                    {},
                    false
                );
                Object.assign(this.idUpdates, idUpdates);
                localStorage.setItem(`pos_config_${odoo.pos_config_id}_changes_queue`, "[]");
                // Items can be added to the queue while flushing, so we have to
                // remove only the flushed items
                this.queue = this.queue.slice(queueLength);
            } catch (error) {
                localStorage.setItem(
                    `pos_config_${odoo.pos_config_id}_changes_queue`,
                    JSON.stringify(this.queue)
                );
                console.error("Flush failed", error);
            }
        });
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
                    break;
                case "call":
                    result = await this.orm.call(model, method, args, kwargs);
                    break;
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

                        localRecord.update(formattedForUpdate, { omitUnknownField: true });
                        this.synchronizeServerDataInIndexedDB({ [model]: [localRecord.raw] });
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
                this.synchronizeServerDataInIndexedDB(data);
                const results = this.models.connectNewData(data);
                result = results[model];
            } else if (type === "write") {
                const localRecord = this.models[model].get(ids[0]);
                if (localRecord) {
                    localRecord.update(values, { omitUnknownField: true });
                    this.synchronizeServerDataInIndexedDB({ [model]: [localRecord.raw] });
                }
            }

            if (result === null || result === undefined) {
                // if request does not return something, we consider it went well
                return true;
            }
            return result;
        } catch (error) {
            const throwErr = true;

            if (throwErr) {
                throw error;
            }
        } finally {
            this.network.loading = false;
        }
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

                if (this.opts.prohibitedAutoLoadedFields[rel.model]?.includes(rel.name)) {
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
        // Needs to flush so that `mapUuidToId` works correctly.
        await this.flush();
        return await this.execute({
            type: "read",
            model,
            ids: this.mapUuidToId(ids),
            fields,
            options,
            queue,
        });
    }

    /**
     * @param {number | string | (string | number)[]} idOrIds
     * @returns {number | number[]}
     */
    mapUuidToId(idOrIds) {
        if (typeof idOrIds === "number") {
            return idOrIds;
        }
        if (typeof idOrIds === "string") {
            return this.idUpdates[idOrIds];
        }
        if (Array.isArray(idOrIds)) {
            return idOrIds.map((id) => this.mapUuidToId(id));
        }
    }

    async call(model, method, args = [], kwargs = {}) {
        if (!navigator.onLine) {
            throw new ConnectionLostError();
        }
        await this.flush();
        if (this.queue.length > 0) {
            throw new Error("There are unsynced changes in the queue.");
        }
        if (Array.isArray(args) && args.length == 0) {
            // This is for static (api.model) methods.
            return await this.orm.call(model, method, args, kwargs);
        }

        const ids = this.mapUuidToId(args[0]);
        return await this.orm.call(model, method, [ids, ...args.slice(1)], kwargs);
    }

    // In a silent call we ignore the error and return false instead
    async silentCall(model, method, args = [], kwargs = {}) {
        try {
            return this.call(model, method, args, kwargs);
        } catch (e) {
            console.warn("Silent call failed:", e);
            return false;
        }
    }

    async callRelated(model, method, args = [], kwargs = {}, queue = true) {
        const data = await this.execute({ type: "call", model, method, args, kwargs, queue });
        if (data) {
            return this.models.connectNewData(data);
        }
        return false;
    }

    async preLoadData(data) {
        return data;
    }

    // FIXME a method of type isXYZ should not have side effects
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
