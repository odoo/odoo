/** @odoo-module */

import { Reactive } from "@web/core/utils/reactive";
import { createRelatedModels } from "@point_of_sale/app/models/related_models";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { markRaw } from "@odoo/owl";

// All records are automatically indexed by id
const INDEXED_DB_NAME = {
    "product.product": ["barcode", "pos_categ_ids", "write_date"],
    "account.fiscal.position": ["tax_ids"],
    "account.fiscal.position.tax": ["tax_src_id"],
    "product.packaging": ["barcode"],
    "loyalty.program": ["trigger_product_ids"],
    "calendar.event": ["appointment_resource_ids"],
};
const LOADED_ORM_METHODS = ["read", "search_read", "create"];

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

        this.network = {
            warningTriggered: false,
            offline: false,
            loading: true,
            unsyncData: [],
        };

        await this.initData();
    }

    setOffline() {
        if (!this.network.offline) {
            this.network.offline = true;
        }
    }

    setOnline() {
        if (this.network.offline) {
            this.network.offline = false;
            this.network.warningTriggered = false; // Avoid the display of the offline popup multiple times
        }

        this.syncData();
    }

    resetUnsyncQueue() {
        this.network.unsyncData = [];
        this.setOnline();
    }

    async initData() {
        const modelClasses = {};
        const response = await this.orm.call("pos.session", "load_data", [
            odoo.pos_session_id,
            PosData.modelToLoad,
        ]);

        for (const posModel of registry.category("pos_available_models").getAll()) {
            modelClasses[posModel.pythonModel] = posModel;
        }

        const [models, records] = createRelatedModels(
            response.relations,
            modelClasses,
            INDEXED_DB_NAME
        );

        this.fields = response.fields;
        this.relations = response.relations;
        this.custom = response.custom;
        this.models = models;
        this.models.loadData(response.data, this.modelToLoad);

        for (const [name, model] of Object.entries(records)) {
            this[name] = Object.values(model);
        }

        this.network.loading = false;
    }

    async loadMissingRecords(missingRecords) {
        for (const [model, ids] of Object.entries(missingRecords)) {
            await this.read(model, Array.from(ids), [], {}, false);
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
    }) {
        this.network.loading = true;

        try {
            let result = true;

            if (fields.length === 0) {
                fields = this.fields[model];
            }

            switch (type) {
                case "write":
                    result = await this.orm.write(model, ids, values);
                    break;
                case "delete":
                    result = await this.orm.delete(model, ids);
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

            if (this.models[model] && LOADED_ORM_METHODS.includes(type)) {
                const { results } = this.models.loadData({ [model]: result });
                result = results[model];
            }

            this.setOnline();
            return result;
        } catch (error) {
            if (queue) {
                this.network.unsyncData.push({ type, model, ids, values });
            }

            this.setOffline();
            throw error;
        } finally {
            this.network.loading = false;
        }
    }

    async syncData() {
        this.syncInProgress = true;

        await this.mutex.exec(async () => {
            while (this.network.unsyncData.length > 0) {
                const result = await this.execute(this.network.unsyncData[0]);

                if (result) {
                    this.network.unsyncData.shift();
                } else {
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
            record.update(vals);

            const dataToUpdate = {};
            const keysToUpdate = Object.keys(vals);
            const serializedRecords = record.serialize();

            for (const key of keysToUpdate) {
                dataToUpdate[key] = serializedRecords[key];
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
        const { results } = this.models.loadData(data);
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

    // FIXME From there is the old method, it will be removed when all the models will be migrated
    async loadServerMethodTemp(model, method, args = []) {
        const data = await this.call(model, method, args);

        let posOrder = {};
        if ("pos.order" in data) {
            posOrder = data["pos.order"];
            delete data["pos.order"];
        }

        const { results } = this.models.loadData(data);

        return {
            related: results,
            posOrder: posOrder,
        };
    }
}

export const PosDataService = {
    dependencies: PosData.serviceDependencies,
    async start(env, deps) {
        return new PosData(env, deps).ready;
    },
};

registry.category("services").add("pos_data", PosDataService);
