/* @odoo-module */

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { ORM } from "@web/core/orm_service";
import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/views/helpers/model";
import { getIds, getX2MViewModes, isRelational } from "@web/views/helpers/view_utils";

const LOADED_GROUP_LIMIT = 10;
const DEFAULT_LIMIT = 40;

class RequestBatcherORM extends ORM {
    constructor() {
        super(...arguments);
        this.searchReadBatchId = 1;
        this.searchReadBatches = {};
        this.readBatches = {};
    }

    /**
     * Entry point to batch "read" calls. If the `fields` and `resModel`
     * arguments have already been called, the given ids are added to the
     * previous list of ids to perform a single read call. Once the server
     * responds, records are then dispatched to the callees based on the
     * given ids arguments (kept in the closure).
     *
     * @param {string} resModel
     * @param {number[]} resIds
     * @param {string[]} fields
     * @returns {Promise<any>}
     */
    async read(resModel, resIds, fields) {
        const key = JSON.stringify([resModel, fields]);
        let batch = this.readBatches[key];
        if (!batch) {
            batch = {
                deferred: new Deferred(),
                resModel,
                fields,
                resIds: [],
                scheduled: false,
            };
            this.readBatches[key] = batch;
        }
        const prevIds = this.readBatches[key].resIds;
        this.readBatches[key].resIds = [...new Set([...prevIds, ...resIds])];

        if (!batch.scheduled) {
            batch.scheduled = true;
            await Promise.resolve();
            delete this.readBatches[key];
            const allRecords = await super.read(resModel, batch.resIds, fields);
            batch.deferred.resolve(allRecords);
        }

        const records = await batch.deferred;
        const rec = records.filter((r) => resIds.includes(r.id));
        return rec;
    }

    async searchRead(/*model*/) {
        // FIXME: discriminate on model? (it is always the same in our usecase)
        const batchId = this.searchReadBatchId;
        let batch = this.searchReadBatches[batchId];
        if (!batch) {
            batch = {
                deferred: new Deferred(),
                count: 0,
            };
            Promise.resolve().then(() => this.searchReadBatchId++);
            this.searchReadBatches[batchId] = batch;
        }
        batch.count++;
        const result = await super.searchRead(...arguments);
        batch.count--;
        if (batch.count === 0) {
            delete this.searchReadBatches[batchId];
            batch.deferred.resolve();
        }
        await batch.deferred;
        return result;
    }
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
        if ("resId" in params) {
            this.resId = params.resId; // FIXME: don't update internal state directly
        }
        let { data } = params;
        if (!data) {
            if (this.resId) {
                const result = await this.model.orm.read(
                    this.resModel,
                    [this.resId],
                    this.activeFields,
                    { bin_size: true }
                );
                data = this._sanitizeValues(result[0]);
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
        return this._sanitizeValues(result.value);
    }

    _getOnchangeSpec() {
        const onChangeSpec = {};
        for (const fieldName in this.activeFields) {
            onChangeSpec[fieldName] = "1"; // FIXME: need to on_change info from arch
        }
        return onChangeSpec;
    }

    _sanitizeValues(values) {
        if (this.resModel !== this.model.resModel) {
            return values;
        }
        const sanitizedValues = {};
        for (const fieldName in values) {
            if (this.fields[fieldName].type === "char") {
                sanitizedValues[fieldName] = values[fieldName] || "";
            } else {
                sanitizedValues[fieldName] = values[fieldName];
            }
        }
        return sanitizedValues;
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

        this.openGroupsByDefault = params.openGroupsByDefault;

        this.resIds = params.resIds || null;

        this.domains = {};
        this.groupBy = params.groupBy || [];
        this.groupByField = this.fields[this.groupBy[0]];
        this.limit = params.limit;
        this.groupLimit = params.groupLimit;
        this.data = [];
        this.views = {};
        this.orderByColumn = {};

        // Group parameters
        this.updateGroupParams(params);

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
    get dataPointContext() {
        return {
            limit: this.limit,
            groupLimit: this.groupLimit,
            ...super.dataPointContext,
        };
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
     * @param {{ domains?: any[], groupBy?: string[], defer?: boolean, orderByColumn?: { name: string, asc: boolean } }} [params={}]
     * @returns {Promise<void> | () => Promise<void>}
     */
    async load(params = {}) {
        this.offset = 0;

        if (params.domain && !this.groupData) {
            this.domains.main = params.domain; // FIXME: do not modify internal state directly
        }
        if (params.groupBy) {
            this.groupBy = params.groupBy;
            this.groupByField = this.fields[this.groupBy[0]];
        }
        if ("orderByColumn" in params) {
            this.orderByColumn = params.orderByColumn; // FIXME: incorrect param name (could come from a favorite)
        }

        if (this.resIds) {
            this.data = await this.loadRecords();
        } else if (this.isGrouped) {
            this.data = await this.loadGroups();
        } else {
            this.data = await this.searchRecords();
        }

        this.offset = this.data.length;
        this.isLoaded = true;
    }

    /**
     * @private
     * @returns {Promise<DataRecord>}
     */
    async searchRecords() {
        const order = this.orderByColumn.name
            ? `${this.orderByColumn.name} ${this.orderByColumn.asc ? "ASC" : "DESC"}`
            : "";
        const recordsData = await this.model.orm.searchRead(
            this.resModel,
            this.getDomain(),
            this.activeFields,
            {
                limit: this.limit,
                order,
                offset: this.offset,
            },
            { bin_size: true }
        );

        return Promise.all(
            recordsData.map(async (data) => {
                const record = this.createRecord(this.resModel, data.id);
                await record.load({ data });
                return record;
            })
        );
    }

    /**
     * @private
     * @returns {Promise<DataRecord>}
     */
    async loadRecords() {
        if (!this.resIds.length) {
            return [];
        }
        return Promise.all(
            this.resIds.map(async (resId) => {
                const record = this.createRecord(this.resModel, resId);
                await record.load();
                return record;
            })
        );
    }

    async loadMore() {
        const nextRecords = await this.searchRecords();
        this.data.push(...nextRecords);
        this.offset = this.data.length;
        this.model.notify();
    }

    /**
     * @private
     * @returns {Promise<DataRecord>}
     */
    async loadGroups() {
        const { groups, length } = await this.model.orm.webReadGroup(
            this.resModel,
            this.getDomain(),
            this.activeFields,
            this.groupBy,
            {
                limit: this.groupLimit,
                lazy: true,
            }
        );
        this.count = length;

        const groupBy = this.groupBy.slice(1);
        let loadedGroups = 0;
        return Promise.all(
            groups.map(async (groupData) => {
                const groupParams = {
                    groupAggregates: Object.create(null),
                    groupBy,
                };
                let shouldFold = false;
                for (const key in groupData) {
                    const value = groupData[key];
                    switch (key) {
                        case this.groupByField.name: {
                            let [groupValue, groupDisplay] = Array.isArray(value)
                                ? value
                                : [value, value];
                            if (isRelational(this.fields[this.groupByField.name])) {
                                groupValue = groupValue || false;
                                groupDisplay = groupDisplay || _t("Undefined");
                            }
                            Object.assign(groupParams, { groupValue, groupDisplay });
                            break;
                        }
                        case `${this.groupByField.name}_count`: {
                            groupParams.groupCount = value;
                            break;
                        }
                        case "__domain": {
                            groupParams.groupDomain = value;
                            break;
                        }
                        case "__fold": {
                            shouldFold = value || false;
                            break;
                        }
                        default: {
                            if (key in this.fields) {
                                groupParams.groupAggregates[key] = value;
                            }
                        }
                    }
                }
                // FIXME: only retrieve the former group if groupby same field
                let group = this.data.find((g) => g.value === groupParams.groupValue);
                if (group && group.isLoaded) {
                    group.updateGroupParams(groupParams);
                } else {
                    group = this.createList(this.resModel, groupParams);
                }
                if (
                    !shouldFold &&
                    loadedGroups < LOADED_GROUP_LIMIT &&
                    (this.openGroupsByDefault || group.isLoaded)
                ) {
                    loadedGroups++;
                    const loadParams = { groupBy, orderByColumn: this.orderByColumn };
                    if (groupParams.groupDomain) {
                        loadParams.domain = groupParams.groupDomain;
                    }
                    await group.load(loadParams);
                }
                return group;
            })
        );
    }

    async toggle() {
        if (this.isLoaded) {
            this.data = [];
            this.isLoaded = false;
        } else {
            await this.load();
        }
        this.model.notify();
    }

    getDomain() {
        return Domain.and(Object.values(this.domains)).toList();
    }

    updateGroupParams(params) {
        if (params.groupDomain) {
            this.domains.main = params.groupDomain;
        }
        this.count = params.groupCount;
        this.displayName = params.groupDisplay;
        this.value = params.groupValue;
        this.aggregates = params.groupAggregates;
    }
}

export class RelationalModel extends Model {
    setup(params, { rpc, user }) {
        window.basicmodel = this; // debug
        this.db = Object.create(null);

        this.resModel = params.resModel;
        this.resId = params.resId; // not sure
        this.resIds = params.resIds || []; // not sure

        this.relations = params.relations || {};
        // this.fields = params.fields || {};
        // this.activeFields = params.activeFields || {};
        // this.viewMode = params.viewMode || null;

        const dataPointParams = {
            activeFields: params.activeFields || {},
            fields: params.fields || {},
            viewMode: params.viewMode || null,
        };
        if (this.resIds.length) {
            dataPointParams.resIds = this.resIds;
        }
        if (params.rootType === "record") {
            this.root = new DataRecord(this, this.resModel, this.resId, dataPointParams);
        } else {
            dataPointParams.openGroupsByDefault = params.openGroupsByDefault || false;
            dataPointParams.limit = params.limit || DEFAULT_LIMIT;
            dataPointParams.groupLimit = params.groupLimit || DEFAULT_LIMIT;
            this.root = new DataList(this, this.resModel, dataPointParams);
        }

        this.orm = new RequestBatcherORM(rpc, user);
        this.keepLast = new KeepLast();

        console.group("Current model");
        console.log(this);
        console.groupEnd();
    }

    /**
     * @param {{ resId?: number }} params
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        if ("resId" in params) {
            this.resId = params.resId;
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

    async sortByColumn(column) {
        const { name, asc } = this.root.orderByColumn;
        let orderByColumn = {
            name: column.name,
        };
        orderByColumn.asc = column.name === name ? !asc : true;
        await this.keepLast.add(this.root.load({ orderByColumn }));
        this.notify();
    }
}

RelationalModel.services = ["rpc", "user"];
