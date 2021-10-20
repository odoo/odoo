/* @odoo-module */

import { ORM } from "@web/core/orm_service";
import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { Model } from "./helpers/model";
import { getIds, getX2MViewModes, isRelational } from "./helpers/view_utils";
import { _t } from "@web/core/l10n/translation";

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
        let { data } = params;
        if (!data) {
            if (this.resId) {
                const result = await this.model.orm.read(
                    this.resModel,
                    [this.resId],
                    this.activeFields
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

        this.domain = [];
        this.groupBy = params.groupBy || [];
        this.data = [];
        this.views = {};
        this.orderByColumn = {};

        if (params.groupDomain) {
            this.domain = params.groupDomain;
        }
        this.count = params.groupCount;
        this.displayName = params.groupDisplay;
        this.value = params.groupValue;

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
     * @param {{ domain?: any[], groupBy?: string[], defer?: boolean, orderByColumn?: { name: string, asc: boolean } }} [params={}]
     * @returns {Promise<void> | () => Promise<void>}
     */
    async load(params = {}) {
        if (params.domain && !this.groupData) {
            this.domain = params.domain; // FIXME: do not modify internal state directly
        }
        if (params.groupBy) {
            this.groupBy = params.groupBy;
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
        this.isLoaded = true;
    }

    /**
     * @private
     * @returns {Promise<() => Promise<DataRecord>>}
     */
    async searchRecords() {
        const order = this.orderByColumn.name
            ? `${this.orderByColumn.name} ${this.orderByColumn.asc ? "ASC" : "DESC"}`
            : "";
        const recordsData = await this.model.orm.searchRead(
            this.resModel,
            this.domain,
            this.activeFields,
            {
                limit: 40,
                order,
            }
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
     * @returns {Promise<() => Promise<DataRecord>>}
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

    /**
     * @private
     * @returns {Promise<() => Promise<DataRecord>>}
     */
    async loadGroups() {
        const { groups, length } = await this.model.orm.webReadGroup(
            this.resModel,
            this.domain,
            this.activeFields,
            this.groupBy,
            {
                limit: 40,
            }
        );
        this.count = length;

        const groupBy = this.groupBy.slice(1);
        return Promise.all(
            groups.map(async (groupData) => {
                let groupDisplay = groupData[`${this.groupBy[0]}`];
                let groupValue = groupData[`${this.groupBy[0]}`];
                if (this.fields[this.groupBy[0]].type === "many2one") {
                    groupDisplay = groupDisplay ? groupDisplay[1] : _t("Undefined");
                    groupValue = groupValue ? groupValue[0] : false;
                }
                // FIXME: only retrieve the former group if groupby same field
                let group = this.data.find((g) => g.value === groupValue);
                if (!group || !group.isLoaded) {
                    const params = {
                        groupCount: groupData[`${this.groupBy[0]}_count`],
                        groupDisplay,
                        groupValue,
                        groupDomain: groupData.__domain,
                        groupBy,
                    };
                    group = this.createList(this.resModel, params);
                }
                if (this.openGroupsByDefault || group.isLoaded) {
                    await group.load({ groupBy, orderByColumn: this.orderByColumn });
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
            this.root = new DataList(this, this.resModel, dataPointParams);
        }

        this.orm = new RequestBatcherORM(rpc, user);
        this.keepLast = new KeepLast();
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

        console.log(this);
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
