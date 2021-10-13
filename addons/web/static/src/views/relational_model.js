/* @odoo-module */

import { registry } from "../core/registry";
import { KeepLast } from "../core/utils/concurrency";
import { Model } from "../views/helpers/model";
import { getIds, getX2MViewModes, isRelational } from "./helpers/view_utils";

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
     * @returns {Promise<void>}
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

function sanitizeValues(values, fields) {
    const sanitizedValues = {};
    for (const fieldName in values) {
        if (fields[fieldName].type === "char") {
            sanitizedValues[fieldName] = values[fieldName] || "";
        } else {
            sanitizedValues[fieldName] = values[fieldName];
        }
    }
    return sanitizedValues;
}

class DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {{ fields: any, activeFields: string[] }} params
     */
    constructor(model, resModel, params) {
        this.model = model;
        this.resModel = resModel;
        this.id = DataRecord.nextId++;
        this.data = null;

        this.fields = params.fields;
        this.activeFields = params.activeFields;
        this.viewMode = params.viewMode || null;

        this.requestBatcher = this.model.requestBatcher;

        this.model.db[this.id] = this;
    }

    /**
     * @returns {boolean}
     */
    get hasData() {
        return Boolean(this.data);
    }

    /**
     * Transmits the current informations to a child datapoint
     * @private
     * @returns {any}
     */
    get dataPointContext() {
        return {
            activeFields: this.activeFields,
            fields: this.fields,
            viewMode: this.viewMode,
        };
    }

    /**
     * Returns the existing record with the samel resModel and resId if any, or
     * creates and returns a new one.
     * @param {string} resModel
     * @param {number} resId
     * @param {any} params
     * @returns {DataRecord}
     */
    createRecord(resModel, resId, params = {}) {
        const existingRecord = this.model.get({ resModel, resId });
        if (existingRecord) {
            return existingRecord;
        }
        return new DataRecord(this.model, resModel, resId, { ...this.dataPointContext, ...params });
    }

    /**
     * Creates and returns a new data list with the given parameters.
     * @param {string} resModel
     * @param {any} params
     * @returns {DataList}
     */
    createList(resModel, params = {}) {
        return new DataList(this.model, resModel, { ...this.dataPointContext, ...params });
    }
}

DataPoint.nextId = 1;

class DataRecord extends DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {string} resModel
     * @param {number} resId
     * @param {any} params
     */
    constructor(model, resModel, resId, params) {
        super(model, resModel, params);
        this.resId = resId;
        this.data = {};
        this._values = {};
        this._changes = {};
    }

    /**
     * @param {{ fields?: string[], data?: any }} [params={}]
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        // Record data
        const fields = params.fields || this.activeFields;
        if (!fields.length) {
            return;
        }
        let { data } = params;
        if (!data) {
            if (this.resId) {
                const result = await this.requestBatcher.read(
                    this.resModel,
                    [this.resId],
                    this.activeFields
                );
                data = sanitizeValues(result[0], this.fields);
            } else {
                data = await this._performOnchange();
            }
        }
        this._values = data;
        this._changes = {};
        this.data = data;
        // this.data = Object.freeze(data);

        // Relational data
        await Promise.all(Object.keys(this.fields).map((fname) => this.loadRelationalField(fname)));
    }

    /**
     * @param {string} fieldName
     * @returns {Promise<void>}
     */
    async loadRelationalField(fieldName) {
        const field = this.fields[fieldName];
        const { relation, views, viewMode } = field;
        const activeFields = this.model.relations[relation] || [];

        if (!isRelational(field) || !(Object.keys(views || {}).length || activeFields.length)) {
            return;
        }

        const resIds = getIds(this.data[fieldName]);
        const dataList = this.createList(relation, { activeFields, resIds, views, viewMode });
        const alteredData = { ...this.data, [fieldName]: dataList };

        this.data = alteredData;
        // this.data = Object.freeze(alteredData);

        await this.data[fieldName].load();
    }

    async update(fieldName, value) {
        this.data[fieldName] = value;
        this._changes[fieldName] = value;
        Object.assign(this._changes, await this._performOnchange(fieldName));
        this.model.notify();
    }

    async save() {
        const changes = this._getChanges();
        if (this.resId) {
            await this.model.orm.write(this.resModel, [this.resId], changes);
        } else {
            this.resId = await this.model.orm.create(this.resModel, changes);
        }
        await this.load();
        this.model.notify();
    }

    _getChanges(allFields = false) {
        const changes = Object.assign({}, allFields ? this.data : this._changes);
        for (const fieldName in changes) {
            const fieldType = this.fields[fieldName].type;
            if (fieldType === "one2many" || fieldType === "many2many") {
                // TODO: need to generate commands
                changes[fieldName] = [];
            } else if (fieldType === "many2one") {
                changes[fieldName] = changes[fieldName] ? changes[fieldName][0] : false;
            }
        }
        return changes;
    }

    async _performOnchange(fieldName) {
        const result = await this.model.orm.call(this.resModel, "onchange", [
            [],
            this._getChanges(true),
            fieldName ? [fieldName] : [],
            this._getOnchangeSpec(),
        ]);
        return sanitizeValues(result.value, this.fields);
    }

    _getOnchangeSpec() {
        const onChangeSpec = {};
        for (const fieldName in this.aciveFields) {
            onChangeSpec[fieldName] = "1"; // FIXME: need to on_change info from arch
        }
        return onChangeSpec;
    }
}

class DataList extends DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {string} resModel
     * @param {{
     *  resIds?: number[],
     *  groupData?: any,
     *  views?: any,
     * }} [params={}]
     */
    constructor(model, resModel, params = {}) {
        super(model, resModel, params);

        this.resIds = params.resIds || null;
        this.groupData = params.groupData || null;

        this.domain = [];
        this.groupBy = [];
        this.data = [];
        this.views = {};

        if (this.groupData) {
            this.domain = params.groupData.__domain;
        }

        for (const type in params.views || {}) {
            const [mode] = getX2MViewModes(type);
            this.views[mode] = Object.freeze(params.views[type]);
        }

        if (this.viewMode && this.views[this.viewMode]) {
            this.fields = this.views[this.viewMode].fields;
            this.activeFields = Object.keys(this.fields);
        }
    }

    /**
     * @override
     */
    get hasData() {
        return Boolean(super.hasData && this.data.length);
    }

    /**
     * @returns {boolean}
     */
    get isGrouped() {
        return Boolean(this.groupBy.length);
    }

    /**
     * @param {{ domain?: any[], groupBy?: string[], defer?: boolean }} [params={}]
     * @returns {Promise<void> | () => Promise<void>}
     */
    async load(params = {}) {
        if (params.domain && !this.groupData) {
            this.domain = params.domain;
        }
        if (params.groupBy) {
            this.groupBy = params.groupBy;
        }

        let fetchData;
        if (this.resIds) {
            fetchData = await this.loadRecords();
        } else if (this.groupBy.length) {
            fetchData = await this.loadGroups();
        } else {
            fetchData = await this.searchRecords();
        }

        const loadData = async () => {
            this.data = await fetchData();
        };

        return params.defer ? loadData : loadData();
    }

    /**
     * @private
     * @returns {Promise<() => Promise<DataRecord>>}
     */
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

    /**
     * @private
     * @returns {Promise<() => Promise<DataRecord>>}
     */
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

    /**
     * @private
     * @returns {Promise<() => Promise<DataRecord>>}
     */
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
        this.activeFields = params.activeFields || {};
        this.viewMode = params.viewMode || null;

        this.requestBatcher = requestBatcher;
        this.keepLast = new KeepLast();
    }

    /**
     * @param {{ resId?: number }} params
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        if (params.resId) {
            this.resId = params.resId;
        }
        const dataPointParams = {
            activeFields: this.activeFields,
            fields: this.fields,
            viewMode: this.viewMode,
        };
        if (this.resIds.length) {
            dataPointParams.resIds = this.resIds;
        }
        if (this.resId) {
            // FIXME: what if it's a new record in form view?
            this.root = new DataRecord(this, this.resModel, this.resId, dataPointParams);
        } else {
            this.root = new DataList(this, this.resModel, dataPointParams);
        }

        await this.keepLast.add(this.root.load(params));
        this.notify();
    }

    /**
     * @param  {...any} args
     * @returns {DataPoint | null}
     */
    get(...args) {
        return this.getAll(...args)[0] || null;
    }

    /**
     * @param  {any} properties
     * @returns {DataPoint[]}
     */
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
