import { Reactive } from "@web/core/utils/reactive";
import { Base, createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { markRaw } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
import IndexedDB from "../models/utils/indexed_db";
import { DataServiceOptions } from "../models/data_service_options";
import { getOnNotified, uuidv4 } from "@point_of_sale/utils";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, rpc, RPCError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;
const INDEXED_DB_VERSION = 1;

export class PosData extends Reactive {
    static modelToLoad = []; // When empty all models are loaded
    static serviceDependencies = ["orm", "bus_service"];

    constructor() {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }

    async setup(env, { orm, bus_service }) {
        this.orm = orm;
        this.bus = bus_service;
        this.relations = [];
        this.custom = {};
        this.syncInProgress = false;
        this.mutex = markRaw(new Mutex());
        this.records = {};
        this.opts = new DataServiceOptions();
        this.channels = [];
        this.debouncedSynchronizeLocalDataInIndexedDB = debounce(
            this.synchronizeLocalDataInIndexedDB.bind(this),
            300
        );

        this.network = {
            warningTriggered: false,
            offline: false,
            loading: true,
            unsyncData: [],
        };

        if (!navigator.onLine) {
            await this.checkConnectivity();
        }

        this.initializeWebsocket();
        await this.intializeDataRelation();

        browser.addEventListener("online", () => this.checkConnectivity());
        browser.addEventListener("offline", () => this.checkConnectivity());
        this.bus.addEventListener("BUS:CONNECT", this.reconnectWebSocket.bind(this));
    }

    async checkConnectivity() {
        try {
            clearTimeout(this.checkConnectivityTimeout);
            this.checkConnectivityTimeout = null;
            // Runbot tests will soon be run in dockers with no access to the outside world,
            // so all their interfaces will be disconnected. The problem is that the browser
            // considers itself offline when no interface is connected. However, in this case,
            // if the Odoo server is still accessible.
            //
            // This method also makes it possible to run local tests when no connection is
            // available and an Odoo server is running locally.
            //
            // A ping is required to verify that the connection to the server is not possible.
            await rpc("/pos/ping");
            await this.syncData();

            this.network.offline = false;
            this.network.warningTriggered = false;

            window.dispatchEvent(new CustomEvent("pos-network-online"));
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.network.offline = true;
                if (navigator.onLine) {
                    this.checkConnectivityTimeout = setTimeout(
                        () => this.checkConnectivity(),
                        2000
                    );
                }
            }
        }
    }

    initializeWebsocket() {
        this.onNotified = getOnNotified(this.bus, odoo.access_token);
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
        const allModelNames = Array.from(
            new Set([...Object.keys(relations), ...Object.keys(this.opts.databaseTable)])
        );
        const models = allModelNames.map((model) => {
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
        const data = {};
        for (const [model, params] of modelsParams) {
            const put = [];
            const remove = [];
            const modelData = this.models[model].getAll();

            for (const record of modelData) {
                const isToRemove = params.condition(record);

                if (isToRemove === undefined || isToRemove === true) {
                    if (record[params.key]) {
                        remove.push(record[params.key]);
                    }
                } else {
                    put.push(record.serializeForIndexedDB());
                }
            }

            await this.indexedDB.delete(model, remove);
            await this.indexedDB.create(model, put);
            data[model] = put;

            if (remove.length) {
                await this.indexedDB.delete(model, remove);
            }

            if (put.length) {
                await this.indexedDB.create(model, put);
            }
        }

        return data;
    }

    async synchronizeServerDataInIndexedDB(serverData = {}) {
        try {
            const clone = JSON.parse(JSON.stringify(serverData));
            for (const [model, data] of Object.entries(clone)) {
                try {
                    await this.indexedDB.create(model, data);
                } catch {
                    console.info(`Error while updating ${model} in indexedDB.`);
                }
            }
        } catch {
            console.debug("Error while synchronizing server data in indexedDB.");
        }
    }

    async getLocalDataFromIndexedDB(data = false) {
        // Used to retrieve models containing states from the indexedDB.
        // This method will load the records directly via loadData.
        const models = Object.keys(this.opts.databaseTable);

        if (!data) {
            data = await this.indexedDB.readAll(models);
        }

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
        const results = this.models.loadConnectedData(missing, []);

        await this.checkAndDeleteMissingOrders(results);

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
            (!this.network.offline && session?.state !== "opened") ||
            session?.id !== odoo.pos_session_id ||
            odoo.from_backend
        ) {
            try {
                const limitedLoading = this.isLimitedLoading();
                const serverDate = localData["pos.config"]?.[0]?._data_server_date;
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

                const local_records_to_filter = {};
                for (const model of this.opts.cleanupModels) {
                    const local = localData[model] || [];
                    if (local.length > 0) {
                        local_records_to_filter[model] = local.map((r) => r.id);
                    }
                }

                const data_to_remove = await this.orm.call("pos.session", "filter_local_data", [
                    odoo.pos_session_id,
                    local_records_to_filter,
                ]);

                for (const [model, values] of Object.entries(data)) {
                    let local = localData[model] || [];

                    if (this.opts.uniqueModels.includes(model) && values.length > 0) {
                        this.indexedDB.delete(
                            model,
                            local.map((r) => r.id)
                        );
                        localData[model] = values;
                    } else {
                        if (data_to_remove[model] && data_to_remove[model].length > 0) {
                            const remove_ids = data_to_remove[model];
                            local = local.filter((r) => !remove_ids.includes(r.id));
                            this.indexedDB.delete(model, remove_ids);
                        }
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

        this.models.loadConnectedData(data, this.modelToLoad);
        this.models.loadConnectedData({ "pos.order": order, "pos.order.line": orderlines }, []);
        this.sanitizeData();
    }

    async sanitizeData() {
        const order_to_delete = this.models["pos.order"].filter((order) =>
            order.lines.some((line) => line.is_reward_line && !line.coupon_id)
        );
        for (const order of order_to_delete) {
            for (let i = order.lines.length - 1; i >= 0; i--) {
                order.lines[i].delete();
            }
        }
    }

    async loadFieldsAndRelations() {
        const key = `pos_data_params_${odoo.pos_config_id}`;
        if (this.network.offline) {
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

        const { models } = createRelatedModels(relations, modelClasses, this.opts);

        this.fields = fields;
        this.relations = relations;
        this.models = models;

        if (odoo.debug === "assets") {
            window.performance.mark("pos_data_service_init");
        }

        await this.initData();
        await this.getLocalDataFromIndexedDB();
        this.initListeners();

        if (odoo.debug === "assets") {
            window.performance.mark("pos_data_service_init_end");
            this.debugInfos();
        }

        this.network.loading = false;
    }

    debugInfos() {
        const sortedByLength = Object.keys(this.models)
            .map((m) => [m, this.models[m].length])
            .sort((a, b) => a[1] - b[1]);

        for (const [model, length] of sortedByLength) {
            console.debug(
                `[%c${model}%c]: %c${length}%c records`,
                "color:lime;",
                "",
                "font-weight:bold;color:#e67e22",
                ""
            );
        }

        const measure = window.performance.measure(
            "pos_loading",
            "pos_data_service_init",
            "pos_data_service_init_end"
        );

        console.debug(
            `%cPosDataService initialized in %c${measure.duration.toFixed(2)}ms%c`,
            "color:lime;font-weight:bold",
            "color:#e67e22;font-weight:bold",
            ""
        );
    }

    initListeners() {
        this.models["pos.order"].addEventListener(
            "update",
            this.debouncedSynchronizeLocalDataInIndexedDB.bind(this)
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
                const record = this.models[model].get(params.id)?.raw;
                if (!record) {
                    return; // the record may be deleted
                }
                for (const [key, value] of Object.entries(record)) {
                    if (value instanceof Base) {
                        record[key] = value.id;
                    } else if (Array.isArray(value) && value[0] instanceof Base) {
                        record[key] = value.map((v) => v.id);
                    }
                }

                this.synchronizeServerDataInIndexedDB({ [model]: [record] });
            });
        }
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
        if (this.network.offline) {
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
                if (["product.product", "product.template"].includes(model)) {
                    const domain = model === "product.product" ? "product_variant_ids.id" : "id";
                    await this.callRelated(
                        "product.template",
                        "load_product_from_pos",
                        [odoo.pos_config_id, [[domain, "in", Array.from(ids)]], 0, 0],
                        {
                            context: {
                                load_archived: true,
                            },
                        }
                    );
                    continue;
                }

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

    async checkAndDeleteMissingOrders(results) {
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
    }

    write(model, ids, vals) {
        const records = [];

        for (const id of ids) {
            const record = this.models[model].get(id);
            delete vals.id;
            record.update(vals, { omitUnknownField: true });

            const dataToUpdate = {};
            const keysToUpdate = Object.keys(vals);

            for (const key of keysToUpdate) {
                dataToUpdate[key] = vals[key];
            }

            records.push(record);
            if (typeof id === "number") {
                this.ormWrite(model, [record.id], dataToUpdate);
            }
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
        if (data) {
            this.deviceSync?.dispatch && this.deviceSync.dispatch(data);
            const result = this.models.connectNewData(data);
            this.synchronizeServerDataInIndexedDB(data);
            return result;
        }
        return false;
    }

    async create(model, values, queue = true) {
        return await this.execute({ type: "create", model, values, queue });
    }

    async ormWrite(model, ids, values, queue = true) {
        const result = await this.execute({ type: "write", model, ids, values, queue });
        this.deviceSync?.dispatch &&
            this.deviceSync.dispatch({ [model]: ids.map((id) => ({ id })) });
        return result;
    }

    async ormDelete(model, ids, queue = true) {
        return await this.execute({ type: "delete", model, ids, queue });
    }

    localDeleteCascade(record, removeFromServer = false) {
        const recordModel = record.constructor.pythonModel;

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
            this.indexedDB.delete(item.model.name, [item.uuid]);
            item.delete({ silent: !removeFromServer });
        }

        // Delete the main record
        const result = record.delete({ silent: !removeFromServer });
        return result;
    }

    deleteUnsyncData(uuid) {
        this.network.unsyncData = this.network.unsyncData.filter((d) => d.uuid !== uuid);
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
