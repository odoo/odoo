import { Reactive } from "@web/core/utils/reactive";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { DataServiceOptions } from "./data_service_options";
import { browser } from "@web/core/browser/browser";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";

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

        await this.initData();

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

    async preLoadData(data) {
        return data;
    }

    async loadInitialData() {
        return await this.orm.call("pos.session", "load_data", [
            odoo.pos_session_id,
            PosData.modelToLoad,
        ]);
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
        this.queue = JSON.parse(
            localStorage.getItem(`pos_config_${odoo.pos_config_id}_changes_queue`) || "[]"
        );
        if (this.queue.length) {
            // This means that we have unsynced data from the last session.
            // We sync this data with the server and then we restart the initData method
            // to get the latest data from the server.
            // This means that we don't have to manually deal with the "merging" of this unsynced data
            await this.flush();
            return this.initData();
        }
        const MIN_FLUSH_INTERVAL_MILLIS = 1000;
        this.debouncedFlush = debounce(this.flush.bind(this), MIN_FLUSH_INTERVAL_MILLIS);

        const { models, records, indexedRecords } = createRelatedModels(
            relations,
            modelClasses,
            this.opts,
            (record, key) => {
                if (!this.finishedLoading) {
                    return;
                }
                console.log(record, record.model.modelName, record.id, key, record[key]);
                if (key === "id") {
                    return;
                }
                const getId = (record) => {
                    if (record?.id) {
                        return typeof record.id === "number" ? record.id : record.uuid;
                    }
                    return record ?? false; // the orm service ignores undefined values, so we need to set it to false
                };
                const prepareValue = (record) => {
                    if (record instanceof Array) {
                        return record.map((r) => getId(r));
                    }
                    return getId(record);
                };
                if (this.queue.at(-1)?.[1] === getId(record)) {
                    this.queue.at(-1)[2][key] = prepareValue(record[key]);
                    this.debouncedFlush();
                    return;
                }
                this.queue.push([
                    record.model.modelName,
                    getId(record),
                    { [key]: prepareValue(record[key]) },
                ]);
                this.debouncedFlush();
            }
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
        this.network.loading = false;
        this.finishedLoading = true;
    }

    async flush() {
        console.log("Flushing queue");
        localStorage.setItem(
            `pos_config_${odoo.pos_config_id}_changes_queue`,
            JSON.stringify(this.queue)
        );
        // FIXME: what happens if part of the queue fails? Will the first part be written to the db or not?
        await this.call(
            "pos.config",
            "sync_from_ui_2",
            [odoo.pos_config_id, this.queue],
            {},
            false
        );
        this.queue = [];
        localStorage.setItem(
            `pos_config_${odoo.pos_config_id}_changes_queue`,
            JSON.stringify(this.queue)
        );
        console.log("Queue flushed");
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

    async call(model, method, args = [], kwargs = {}, preFlush = true) {
        if (preFlush) {
            await this.flush();
        }
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
        const results = this.models.loadData(data, [], true);
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
}

export const PosDataService = {
    dependencies: PosData.serviceDependencies,
    async start(env, deps) {
        return new PosData(env, deps).ready;
    },
};

registry.category("services").add("pos_data", PosDataService);
