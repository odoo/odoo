/* @odoo-module */

import { registry } from "../core/registry";
import { KeepLast } from "../core/utils/concurrency";
import { Model } from "../views/helpers/model";
import { isRelational } from "./helpers/view_utils";

/**
 * @returns {{
 *  promise: Promise<any>,
 *  resolve: (result: any) => any,
 *  reject: (reason: any) => any,
 * }}
 */
const makeResolvablePromise = () => {
    const promiseWrapper = {};
    promiseWrapper.promise = new Promise((resolve, reject) => {
        Object.assign(promiseWrapper, { resolve, reject });
    });
    return promiseWrapper;
};

class BenedictRequestbatch {
    constructor(orm) {
        this.toRead = {};
        this.toSearchRead = {};
        this.scheduled = false;
        this.orm = orm;
    }

    /**
     * Returns a function able to batch multiple similar read requests.
     * The similarity is determined by the given `resModel` and `fields` arguments.
     * When a similar call has been found, the new given ids are added to the ones that
     * have already been requested. The promise of each read call is fullfilled as
     * soon as each one of the querried ids returns a record.
     * @returns {Promise<any[]>}
     */
    async read(resModel, ids, fields) {
        const key = JSON.stringify([resModel, fields]);
        if (key in this.toRead) {
            const allIds = new Set([...this.toRead[key].args[1], ...ids]);
            this.toRead[key].args[1] = [...allIds];
        } else {
            this.toRead[key] = {
                promiseWrapper: makeResolvablePromise(),
                args: [resModel, [...new Set(ids)], fields],
            };
        }
        this._startSchedule();
        const records = await this.toRead[key].promiseWrapper.promise;
        return records.filter((r) => ids.includes(r.id));
    }

    /**
     * Returns a function able to batch multiple similar search_read requests.
     * The similarity is determined by all the given arguments, meaning that
     * two requests much share the exact same parameters to be batched.
     * @returns {Promise<any[]>}
     */
    searchRead(...args) {
        const key = JSON.stringify(args);
        if (!(key in this.toSearchRead)) {
            this.toSearchRead[key] = {
                promiseWrapper: makeResolvablePromise(),
                args,
            };
        }
        this._startSchedule();
        return this.toSearchRead[key].promiseWrapper.promise;
    }

    async _startSchedule() {
        if (this.scheduled) {
            return;
        }
        this.scheduled = true;
        await new Promise((resolve) => setTimeout(resolve));

        // Read
        for (const key in this.toRead) {
            const { args, promiseWrapper } = this.toRead[key];
            this.orm
                .read(...args)
                .then(promiseWrapper.resolve)
                .catch(promiseWrapper.reject);
        }

        // Search read
        for (const key in this.toSearchRead) {
            const { args, promiseWrapper } = this.toSearchRead[key];
            this.orm
                .searchRead(...args)
                .then(promiseWrapper.resolve)
                .catch(promiseWrapper.reject);
        }

        this.toRead = {};
        this.toSearchRead = {};
        this.scheduled = false;
    }
}

export const requestBatcherService = {
    dependencies: ["orm"],
    start: (env, { orm }) => new BenedictRequestbatch(orm),
};

registry.category("services").add("requestBatcher", requestBatcherService);

class DataPoint {
    /**
     * @param {RelationalModel} model
     */
    constructor(parent, model) {
        this.parent = parent;
        this.id = DataRecord.nextId++;
        this.model = model;
        this.requestBatcher = model.requestBatcher;
        model.db[this.id] = this;
        this.data = null;
    }

    get hasData() {
        return !!this.data;
    }

    get fields() {
        return this.parent ? this.parent.fields : this.model.fields;
    }
}

DataPoint.nextId = 1;

class DataRecord extends DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {string} resModel
     * @param {number} resId
     */
    constructor(parent, model, resModel, resId) {
        super(parent, model);
        this.resModel = resModel;
        this.resId = resId;
    }

    /**
     * @param {any} [params={}]
     * @param {string[]} [params.fields]
     * @param {any} [params.rawRecord] preloaded record data
     * @returns {Promise<DataRecord>}
     */
    async load(params = {}) {
        // Record data
        const { relations } = this.model;
        const fields = params.fields || Object.keys(this.fields);
        let { rawRecord } = params;
        if (!fields.length) {
            return;
        }
        if (!rawRecord) {
            const rawRecords = await this.requestBatcher.read(this.resModel, [this.resId], fields);
            rawRecord = rawRecords[0];
        }
        this.data = rawRecord;

        // Relational data
        const getRelatedFields = (field) => Object.keys(relations[field.relation] || {});
        const promises = Object.entries(this.fields)
            .filter(([fieldName, field]) => fieldName in this.data && isRelational(field))
            .map(([fieldName, field]) =>
                this.loadRelationalField(field.relation, fieldName, getRelatedFields(field))
            );
        await Promise.all(promises);
        return this;
    }

    async loadRelationalField(resModel, fieldName, fields) {
        const resIds = this.data[fieldName];
        const views = this.fields[fieldName].views;
        this.data[fieldName] = this.model.createList(this, resModel, views);
        await this.data[fieldName].load({ resIds, fields });
    }
}

class DataList extends DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {string} resModel
     */
    constructor(parent, model, resModel, views) {
        super(parent, model);
        this.resModel = resModel;
        this.data = null;
        this.views = views;
        this._viewType = null;
    }

    get hasData() {
        return super.hasData && this.data.length;
    }

    get fields() {
        if (this.viewType) {
            return this.views[this.viewType].fields;
        }
        return super.fields;
    }

    get viewType() {
        return this._viewType;
    }

    set viewType(viewType) {
        this._viewType = viewType === "list" ? "tree" : viewType;
    }
    /**
     * @param {any} [params={}]
     * @param {any[]} [params.domain]
     * @param {any[]} [params.resIds] preloaded records ids
     * @returns {Promise<DataList>}
     */
    async load(params = {}) {
        if (this.hasData && this.data[0].hasData) {
            //records have been loaded
            return;
        }
        const fields = params.fields || Object.keys(this.fields);

        if (!this.hasData && params.domain) {
            // LPE FIXME
            this.domain = params.domain;
            const rawRecords = params.resIds
                ? params.resIds.map((id) => ({ id }))
                : await this.requestBatcher.searchRead(this.resModel, this.domain, fields, {
                      limit: 40,
                  });
            this.data = await Promise.all(
                rawRecords.map(async (rawRecord) => {
                    const record = this.model.createRecord(this, this.resModel, rawRecord.id);
                    await record.load(params.resIds ? { fields: fields } : { rawRecord });
                    return record;
                })
            );
        } else if (this.hasData) {
            await Promise.all(this.data.map((dp) => dp.load({ fields })));
        } else {
            this.data = [];
        }
    }
}

export class RelationalModel extends Model {
    setup(params, { requestBatcher }) {
        window.basicmodel = this; // debug
        this.db = Object.create(null);
        this.resModel = params.resModel;
        this.resId = params.resId;
        this.resIds = params.resIds;
        this.fields = params.fields;
        this.relations = params.relations;
        this.activeFields = params.activeFields;

        this.requestBatcher = requestBatcher;
        this.keepLast = new KeepLast();
        this.type = this.resId ? "record" : "list";

        console.log(this);
    }

    async load(params = {}) {
        if (params.resId) {
            this.resId = params.resId;
        }
        if (this.resId) {
            this.root = this.createRecord(null, this.resModel, this.resId);
        } else if (this.type === "list") {
            this.root = this.createList(null, this.resModel);
        }
        await this.keepLast.add(this.root.load(params));
        this.notify();
    }

    get(...args) {
        return this.getAll(...args)[0] || null;
    }

    getAll(properties) {
        return Object.values(this.db).filter((record) => {
            for (const prop in properties) {
                if (record[prop] !== properties[prop]) {
                    return false;
                }
            }
            return true;
        });
    }

    createRecord(parent, resModel, resId) {
        return this.get({ resModel, resId }) || new DataRecord(parent, this, resModel, resId);
    }

    createList(parent, resModel, views) {
        return new DataList(parent, this, resModel, views);
    }
}

RelationalModel.services = ["requestBatcher"];
