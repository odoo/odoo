/* @odoo-module */

import { registry } from "../core/registry";
import { KeepLast } from "../core/utils/concurrency";
import { Model } from "../views/helpers/model";
import { getIds, isRelational } from "./helpers/view_utils";

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
        this.orm = orm;
        this.batches = {};
        this.scheduled = false;
    }

    call() {
        return this._batch("call", ...arguments);
    }

    create() {
        return this._batch("create", ...arguments);
    }

    read() {
        return this._batchRead(...arguments);
    }

    readGroup() {
        return this._batch("readGroup", ...arguments);
    }

    search() {
        return this._batch("search", ...arguments);
    }

    searchRead() {
        return this._batch("searchRead", ...arguments);
    }

    unlink() {
        return this._batch("unlink", ...arguments);
    }

    webReadGroup() {
        return this._batch("webReadGroup", ...arguments);
    }

    webSearchRead() {
        return this._batch("webSearchRead", ...arguments);
    }

    write() {
        return this._batch("write", ...arguments);
    }

    /**
     * Entry point to batch generic ORM method. Only calls with the same method
     * and the exact same arguments can be "batched" (= return the same promise).
     * @param {string} ormMethod
     * @param  {...any} args
     * @returns {Promise<any>}
     */
    async _batch(ormMethod, ...args) {
        if (!this.batches[ormMethod]) {
            this.batches[ormMethod] = {};
        }
        const batches = this.batches[ormMethod];
        const key = JSON.stringify(args);
        if (!(key in batches)) {
            batches[key] = {
                promiseWrapper: makeResolvablePromise(),
                args,
            };
        }

        this._startSchedule();

        return batches[key].promiseWrapper.promise;
    }

    /**
     * Entry point to batch "read" calls. If the `fields` and `resModel`
     * arguments have already been called, the given ids are added to the
     * previous list of ids to perform a single read call. Once the server
     * responds, records are then dispatched to the callees based on the
     * given ids arguments (kept in the closure).
     * @param {string} resModel
     * @param {number[]} ids
     * @param {string[]} fields
     * @returns {Promise<any>}
     */
    async _batchRead(resModel, ids, fields) {
        if (!this.batches.read) {
            this.batches.read = {};
        }
        const batches = this.batches.read;
        const key = JSON.stringify([resModel, fields]);
        if (!(key in batches)) {
            batches[key] = {
                promiseWrapper: makeResolvablePromise(),
                args: [resModel, [], fields],
            };
        }
        const [, prevIds] = batches[key].args;
        batches[key].args[1] = [...new Set([...prevIds, ...ids])];

        this._startSchedule();

        const records = await batches[key].promiseWrapper.promise;
        return records.filter((r) => ids.includes(r.id));
    }

    /**
     * Starts flushing the current batches, if not already started.
     * A resolved promise is awaited to batch all methodes comprised in the same
     * microtask.
     */
    async _startSchedule() {
        if (this.scheduled) {
            return;
        }
        this.scheduled = true;

        await Promise.resolve();

        for (const action in this.batches) {
            for (const key in this.batches[action]) {
                const { args, promiseWrapper } = this.batches[action][key];
                this.orm[action](...args)
                    .then(promiseWrapper.resolve)
                    .catch(promiseWrapper.reject);
            }
        }

        this.batches = {};
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
     * @param {any} params
     * @param {any} params.fields
     * @param {string[]} params.activeFields
     */
    constructor(model, resModel, params) {
        this.model = model;
        this.resModel = resModel;
        this.id = DataRecord.nextId++;
        this.data = null;

        this.fields = params.fields;
        this.activeFields = params.activeFields;

        this.requestBatcher = this.model.requestBatcher;

        this.model.db[this.id] = this;
    }

    get hasData() {
        return Boolean(this.data);
    }

    createRecord(resModel, resId, rawParams = {}) {
        const existingRecord = this.model.get({ resModel, resId });
        if (existingRecord) {
            return existingRecord;
        }
        const params = { activeFields: this.activeFields, fields: this.fields, ...rawParams };
        return new DataRecord(this.model, resModel, resId, params);
    }

    createList(resModel, rawParams = {}) {
        const params = { activeFields: this.activeFields, fields: this.fields, ...rawParams };
        return new DataList(this.model, resModel, params);
    }
}

DataPoint.nextId = 1;

class DataRecord extends DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {string} resModel
     * @param {number} resId
     */
    constructor(model, resModel, resId, params) {
        super(model, resModel, params);

        this.resId = resId;
    }

    /**
     * @param {any} [params={}]
     * @param {string[]} [params.fields]
     * @param {any} [params.data] preloaded record data
     * @returns {Promise<DataRecord>}
     */
    async load(params = {}) {
        // Record data
        const fields = params.fields || this.activeFields;
        if (!fields.length) {
            return;
        }
        let { data } = params;
        if (!data) {
            const recordsData = await this.requestBatcher.read(this.resModel, [this.resId], fields);
            data = recordsData[0];
        }
        this.data = { ...data };

        // Relational data
        await Promise.all(Object.keys(this.fields).map((fname) => this.loadRelationalField(fname)));

        return this;
    }

    async loadRelationalField(fieldName) {
        const field = this.fields[fieldName];
        const { relation, views } = field;
        const activeFields = this.model.relations[relation] || [];

        if (!isRelational(field) || !(Object.keys(views || {}).length || activeFields.length)) {
            return;
        }

        const resIds = getIds(this.data[fieldName]);
        this.data[fieldName] = this.createList(relation, { activeFields, views, resIds });

        // Do not load record if created by nested view arch
        if (activeFields.length) {
            await this.data[fieldName].load();
        }
    }
}

class DataList extends DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {string} resModel
     * @param {any} [params={}]
     * @param {number[]} [params.resIds]
     * @param {any} [params.views]
     * @param {any} [params.groupData]
     */
    constructor(model, resModel, params = {}) {
        super(model, resModel, params);

        this.resIds = params.resIds || null;
        this.groupData = params.groupData || null;
        this.views = params.views || {};

        this.domain = [];
        this.groupBy = [];
        this.data = [];

        if (this.groupData) {
            this.domain = params.groupData.__domain;
        }
    }

    get hasData() {
        return Boolean(super.hasData && this.data.length);
    }

    get isGrouped() {
        return Boolean(this.groupBy.length);
    }

    /**
     * @param {any} [params={}]
     * @param {any[]} [params.domain]
     * @param {any[]} [params.groupBy]
     * @param {boolean} [params.defer]
     * @returns {Promise<any> | () => Promise<any>}
     */
    async load(params = {}) {
        if (params.domain && !this.groupData) {
            this.domain = params.domain;
        }
        if (params.groupBy) {
            this.groupBy = params.groupBy;
        }

        let preloadData;
        if (this.resIds) {
            preloadData = await this.loadRecords();
        } else if (this.groupBy.length) {
            preloadData = await this.loadGroups();
        } else {
            preloadData = await this.searchRecords();
        }
        const loadData = async () => (this.data = await preloadData());
        return params.defer ? loadData : loadData();
    }

    async searchRecords() {
        const recordsData = await this.requestBatcher.searchRead(
            this.resModel,
            this.domain,
            this.activeFields,
            {
                limit: 40,
            }
        );

        return () =>
            Promise.all(
                recordsData.map(async (data) => {
                    const record = this.createRecord(this.resModel, data.id);
                    await record.load({ data });
                    return record;
                })
            );
    }

    async loadRecords() {
        if (!this.resIds.length) {
            return () => [];
        }
        return () =>
            Promise.all(
                this.resIds.map(async (resId) => {
                    const record = this.createRecord(this.resModel, resId);
                    await record.load();
                    return record;
                })
            );
    }

    async loadGroups() {
        const { groups } = await this.requestBatcher.webReadGroup(
            this.resModel,
            this.domain,
            this.activeFields,
            this.groupBy,
            {
                limit: 40,
            }
        );

        const groupBy = this.groupBy.slice(1);

        return async () => {
            const preloadedLists = await Promise.all(
                groups.map(async (groupData) => {
                    const list = this.createList(this.resModel, { groupData });
                    const loadData = await list.load({ groupBy, defer: true });
                    return [list, loadData];
                })
            );
            return Promise.all(
                preloadedLists.map(async ([list, loadData]) => {
                    await loadData();
                    return list;
                })
            );
        };
    }

    setView(viewType) {
        this.fields = this.views[viewType === "list" ? "tree" : viewType].fields;
        this.activeFields = Object.keys(this.fields);
    }
}

export class RelationalModel extends Model {
    setup(params, { requestBatcher }) {
        window.basicmodel = this; // debug
        this.db = Object.create(null);

        this.resModel = params.resModel;
        this.resId = params.resId;
        this.resIds = params.resIds || [];

        this.relations = params.relations || {};
        this.fields = params.fields || {};
        this.activeFields = params.activeFields || [];

        this.requestBatcher = requestBatcher;
        this.keepLast = new KeepLast();
    }

    async load(params = {}) {
        if (params.resId) {
            this.resId = params.resId;
        }
        const dataPointParams = {
            activeFields: this.activeFields,
            fields: this.fields,
        };
        if (this.resIds.length) {
            dataPointParams.resIds = this.resIds;
        }
        if (this.resId) {
            this.root = new DataRecord(this, this.resModel, this.resId, dataPointParams);
        } else {
            this.root = new DataList(this, this.resModel, dataPointParams);
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
}

RelationalModel.services = ["requestBatcher"];
