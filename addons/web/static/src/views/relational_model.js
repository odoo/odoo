/* @odoo-module */

import { Domain } from "@web/core/domain";
import { ORM } from "@web/core/orm_service";
import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { Model } from "@web/views/helpers/model";
import { isX2Many } from "@web/views/helpers/view_utils";
import { registry } from "../core/registry";
import { evaluateExpr } from "@web/core/py_js/py";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";

const preloadedDataRegistry = registry.category("preloadedData");

function orderByToString(orderBy) {
    return orderBy.map((o) => `${o.name} ${o.asc ? "ASC" : "DESC"}`).join(", ");
}

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
    async read(resModel, resIds, fields, context) {
        const key = JSON.stringify([resModel, fields, context]);
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
            const allRecords = await super.read(resModel, batch.resIds, fields, context);
            batch.deferred.resolve(allRecords);
        }

        const records = await batch.deferred;
        const rec = records.filter((r) => resIds.includes(r.id));
        return rec;
    }

    async webSearchRead(/*model*/) {
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
        const result = await super.webSearchRead(...arguments);
        batch.count--;
        if (batch.count === 0) {
            delete this.searchReadBatches[batchId];
            batch.deferred.resolve();
        }
        await batch.deferred;
        return result;
    }
}

let nextId = 0;
class DataPoint {
    constructor(model, params) {
        this.id = `datapoint_${nextId++}`;

        this.model = model;
        this.resModel = params.resModel;
        this.fields = params.fields;
        this.activeFields = params.activeFields;
        this.fieldNames = Object.keys(params.activeFields);
        this.context = params.context;
    }

    exportState() {
        return {};
    }

    load() {
        throw new Error("load must be implemented");
    }

    _parseServerValue(field, value) {
        let parsedValue = value;
        if (field.type === "char") {
            parsedValue = value || "";
        } else if (field.type === "date" || field.type === "datetime") {
            // process date(time): convert into a Luxon DateTime object
            const parser = registry.category("parsers").get(field.type);
            parsedValue = parser(value, { isUTC: true });
        } else if (field.type === "selection" && value === false) {
            // process selection: convert false to 0, if 0 is a valid key
            const hasKey0 = field.selection.find((option) => option[0] === 0);
            parsedValue = hasKey0 ? 0 : value;
        }
        return parsedValue;
    }

    _parseServerValues(values) {
        const parsedValues = {};
        if (!values) {
            return parsedValues;
        }
        for (const fieldName in values) {
            const value = values[fieldName];
            const field = this.fields[fieldName];
            parsedValues[fieldName] = this._parseServerValue(field, value);
        }
        return parsedValues;
    }
}
export class Record extends DataPoint {
    constructor(model, params) {
        super(...arguments);

        this.resId = params.resId;
        this._values = params.values;
        this._changes = {};
        this.data = { ...this._values };
        this.preloadedData = {};
        this.selected = false;
    }

    get evalContext() {
        const evalContext = {};
        for (const fieldName in this.activeFields) {
            const value = this.data[fieldName];
            if ([undefined, null, ""].includes(value)) {
                evalContext[fieldName] = false;
            } else if (isX2Many(this.fields[fieldName])) {
                evalContext[fieldName] = value.records.map((r) => r.resId);
            } else {
                evalContext[fieldName] = value;
            }
        }
        return evalContext;
    }

    async load() {
        if (!this.fieldNames.length) {
            return;
        }
        let data;
        if (this.resId) {
            data = await this._read();
        } else {
            data = await this._performOnchange();
        }
        this._values = data; // FIXME: don't update internal state directly
        this._changes = {};
        this.data = { ...data };

        this.evaluateActiveFields();

        // Relational data
        await this.loadRelationalData();
        await this.loadPreloadedData();
    }

    evaluateActiveFields() {
        const context = this.data;
        for (const fieldName of this.fieldNames) {
            const activeField = this.activeFields[fieldName];
            if (activeField.modifiersAttribute) {
                activeField.modifiers = evaluateExpr(activeField.modifiersAttribute, context);
            }
            if (activeField.optionsAttribute) {
                activeField.options = Object.assign(
                    evaluateExpr(activeField.optionsAttribute, context),
                    activeField.options
                );
            }
            if (activeField.decorationAttributes) {
                activeField.decorations = {};
                for (const decorationName in activeField.decorationAttributes) {
                    activeField.decorations[decorationName] = evaluateExpr(
                        activeField.decorationAttributes[decorationName],
                        context
                    );
                }
            }
        }
    }

    loadPreloadedData() {
        const fetchPreloadedData = async (fetchFn, fieldName) => {
            this.preloadedData[fieldName] = await fetchFn(this, fieldName);
        };

        const proms = [];
        for (const fieldName in this.activeFields) {
            const activeField = this.activeFields[fieldName];
            // @FIXME type should not be get like this
            const type = activeField.widget || this.fields[fieldName].type;
            if (!activeField.invisible && preloadedDataRegistry.contains(type)) {
                proms.push(fetchPreloadedData(preloadedDataRegistry.get(type), fieldName));
            }
        }
        return Promise.all(proms);
    }

    async loadRelationalData() {
        const proms = [];
        for (const fieldName in this.activeFields) {
            if (!isX2Many(this.fields[fieldName])) {
                continue;
            }
            const field = this.activeFields[fieldName];
            const { invisible, relatedFields = {}, relation, views = {}, viewMode } = field;

            const fields = {
                id: { name: "id", type: "integer", readonly: true },
                ...relatedFields,
            };
            const list = this.model.createDataPoint("list", {
                resModel: relation,
                fields,
                activeFields: (views[viewMode] && views[viewMode].activeFields) || {},
                resIds: this.data[fieldName] || [],
                views,
                viewMode,
            });
            this._values[fieldName] = list;
            this.data[fieldName] = list;
            if (!invisible) {
                proms.push(list.load());
            }
        }
        return Promise.all(proms);
    }

    async update(fieldName, value) {
        this.data[fieldName] = value;
        this._changes[fieldName] = this.data[fieldName];
        const activeField = this.activeFields[fieldName];
        if (activeField && activeField.onChange) {
            const onChangeValues = await this._performOnchange(fieldName);
            Object.assign(this.data, onChangeValues);
            Object.assign(this._changes, onChangeValues);
        }
        this.model.notify();
    }

    async save() {
        const changes = this._getChanges();
        if (this.resId) {
            await this.model.orm.write(this.resModel, [this.resId], changes);
        } else {
            const keys = Object.keys(changes);
            if (keys.length === 1 && keys[0] === "display_name") {
                const [resId] = await this.model.orm.call(
                    this.resModel,
                    "name_create",
                    [changes.display_name],
                    { context: this.context }
                );
                this.resId = resId;
            } else {
                this.resId = await this.model.orm.create(this.resModel, changes, this.context);
            }
        }
        await this.load();
        this.model.notify();
    }

    toggleSelection(selected) {
        if (typeof selected === "boolean") {
            this.selected = selected;
        } else {
            this.selected = !this.selected;
        }
        this.model.notify();
    }

    discard() {
        this.data = { ...this._values };
        this._changes = {};
        this.model.notify();
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _read() {
        const result = await this.model.orm.read(this.resModel, [this.resId], this.fieldNames, {
            bin_size: true,
        });
        return this._parseServerValues(result[0]);
    }

    async _performOnchange(fieldName) {
        const result = await this.model.orm.call(this.resModel, "onchange", [
            [],
            this._getChanges(true),
            fieldName ? [fieldName] : [],
            this._getOnchangeSpec(),
        ]);
        return this._parseServerValues(result.value);
    }

    _getOnchangeSpec() {
        return {};
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
            } else if (fieldType === "date") {
                changes[fieldName] = changes[fieldName] ? serializeDate(changes[fieldName]) : false;
            } else if (fieldType === "datetime") {
                changes[fieldName] = changes[fieldName]
                    ? serializeDateTime(changes[fieldName])
                    : false;
            }
        }
        return changes;
    }
}

class DynamicList extends DataPoint {
    constructor(model, params, state) {
        super(...arguments);

        this.groupBy = params.groupBy || [];
        this.domain = params.domain || [];
        this.orderBy = params.orderBy || []; // rename orderBy + get back from state
        this.offset = 0;
        this.count = 0;
        this.limit = params.limit || state.limit || this.constructor.DEFAULT_LIMIT;
        this.isDomainSelected = false;
    }

    get selection() {
        return this.records.filter((r) => r.selected);
    }

    exportState() {
        return {
            limit: this.limit,
        };
    }

    async _resequence(list, targetId, insertAfter = 0) {
        if (targetId) {
            const target = list.find((r) => r.id === targetId);
            const index = insertAfter ? list.findIndex((r) => r.id === insertAfter) : 0;
            list = list.filter((r) => r.id !== targetId);
            list.splice(index, 0, target);
        }
        const model = this.resModel;
        const ids = list.map((r) => r.resId);
        // FIMME: can't go though orm, so no context given
        await this.model.rpc("/web/dataset/resequence", { model, ids });
        this.model.notify();
        return list;
    }

    async sortBy(fieldName) {
        if (this.orderBy.length && this.orderBy[0].name === fieldName) {
            this.orderBy[0].asc = !this.orderBy[0].asc;
        } else {
            this.orderBy = this.orderBy.filter((o) => o.name !== fieldName);
            this.orderBy.unshift({
                name: fieldName,
                asc: true,
            });
        }

        await this.load();
        this.model.notify();
    }

    selectDomain(value) {
        this.isDomainSelected = value;
        this.model.notify();
    }
}

export class DynamicRecordList extends DynamicList {
    constructor() {
        super(...arguments);

        this.records = [];
        this.type = "record-list";
    }

    async load() {
        this.records = await this._loadRecords();
    }

    async archive() {
        const resIds = this.records.map((r) => r.resId);
        await this.model.orm.call(this.resModel, "action_archive", [resIds]);
        await this.model.load();
    }

    async unarchive() {
        const resIds = this.records.map((r) => r.resId);
        await this.model.orm.call(this.resModel, "action_unarchive", [resIds]);
        await this.model.load();
    }

    async resequence() {
        this.records = await this._resequence(this.records, ...arguments);
    }

    async unlink({ resId }) {
        const result = await this.model.orm.unlink(this.resModel, [resId], this.context);
        if (result) {
            await this.model.load();
        }
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _loadRecords() {
        const order = orderByToString(this.orderBy);
        const { records, length } = await this.model.orm.webSearchRead(
            this.resModel,
            this.domain,
            this.fieldNames,
            {
                limit: this.limit,
                order,
                offset: this.offset,
            },
            {
                bin_size: true,
                ...this.context,
            }
        );
        this.count = length;

        return Promise.all(
            records.map(async (data) => {
                data = this._parseServerValues(data);
                const record = this.model.createDataPoint("record", {
                    resModel: this.resModel,
                    resId: data.id,
                    values: data,
                    fields: this.fields,
                    activeFields: this.activeFields,
                });
                record.evaluateActiveFields();
                await record.loadRelationalData();
                await record.loadPreloadedData();
                return record;
            })
        );
    }
}

DynamicRecordList.DEFAULT_LIMIT = 80;

export class DynamicGroupList extends DynamicList {
    constructor(model, params, state) {
        super(...arguments);

        this.groupLimit = params.groupLimit || state.groupLimit || this.constructor.DEFAULT_LIMIT;
        this.groupByInfo = params.groupByInfo || {}; // FIXME: is this something specific to the list view?
        this.openGroupsByDefault = params.openGroupsByDefault || false;
        this.groups = state.groups || [];
        this.activeFields = params.activeFields;
        this.type = "group-list";
        this.isGrouped = true;
    }

    get groupByField() {
        return this.fields[this.groupBy[0]];
    }

    /**
     * @param {string} shortType
     * @returns {boolean}
     */
    groupedBy(shortType) {
        const { type } = this.groupByField;
        switch (shortType) {
            case "m2o":
            case "many2one": {
                return type === "many2one";
            }
            case "o2m":
            case "one2many": {
                return type === "one2many";
            }
            case "m2m":
            case "many2many": {
                return type === "many2many";
            }
            case "m2x":
            case "many2x": {
                return ["many2one", "many2many"].includes(type);
            }
            case "x2m":
            case "x2many": {
                return ["one2many", "many2many"].includes(type);
            }
        }
        return false;
    }

    exportState() {
        return {
            groups: this.groups,
        };
    }

    /**
     * List of loaded records inside groups.
     */
    get records() {
        let recs = [];
        for (const group of this.groups) {
            if (!group.isFolded) {
                recs = recs.concat(group.list.records);
            }
        }
        return recs;
    }

    async load() {
        this.groups = await this._loadGroups();
        await Promise.all(this.groups.map((group) => group.load()));
    }

    async resequence() {
        this.groups = await this._resequence(this.groups, ...arguments);
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    async _loadGroups() {
        const orderby = orderByToString(this.orderBy);
        const { groups, length } = await this.model.orm.webReadGroup(
            this.resModel,
            this.domain,
            this.fieldNames,
            this.groupBy,
            {
                orderby,
                limit: this.groupLimit,
                lazy: true,
            }
        );
        this.count = length;

        const commonGroupParams = {
            fields: this.fields,
            activeFields: this.activeFields,
            resModel: this.resModel,
            domain: this.domain,
            groupBy: this.groupBy.slice(1),
            context: this.context,
            orderBy: this.orderBy,
            groupByInfo: this.groupByInfo,
        };
        return Promise.all(
            groups.map(async (data) => {
                const groupParams = {
                    ...commonGroupParams,
                    aggregates: {},
                    isFolded: !this.openGroupsByDefault,
                    groupByFieldName: this.groupByField.name,
                };
                for (const key in data) {
                    const value = data[key];
                    switch (key) {
                        case this.groupByField.name: {
                            // FIXME: not sure about this
                            groupParams.value = Array.isArray(value) ? value[0] : value;
                            groupParams.displayName = Array.isArray(value) ? value[1] : value;
                            if (this.groupedBy("m2x")) {
                                if (!groupParams.value) {
                                    groupParams.displayName = this.model.env._t("Undefined");
                                }
                                if (this.groupByInfo[this.groupByField.name]) {
                                    groupParams.recordParam = {
                                        resModel: this.groupByField.relation,
                                        resId: groupParams.value,
                                        activeFields: this.groupByInfo[this.groupByField.name]
                                            .activeFields,
                                        fields: this.groupByInfo[this.groupByField.name].fields,
                                    };
                                }
                            }
                            break;
                        }
                        case `${this.groupByField.name}_count`: {
                            groupParams.count = value;
                            break;
                        }
                        case "__domain": {
                            groupParams.groupDomain = value;
                            break;
                        }
                        case "__fold": {
                            // optional
                            groupParams.isFolded = value;
                            break;
                        }
                        default: {
                            // other optional aggregated fields
                            if (key in this.fields) {
                                groupParams.aggregates[key] = value;
                            }
                        }
                    }
                }

                const previousGroup = this.groups.find((g) => g.value === groupParams.value);
                const state = previousGroup ? previousGroup.exportState() : {};
                return this.model.createDataPoint("group", groupParams, state);
            })
        );
    }
}

DynamicGroupList.DEFAULT_LIMIT = 10;

export class Group extends DataPoint {
    constructor(model, params, state) {
        super(...arguments);

        this.value = params.value;
        this.displayName = params.displayName;
        this.aggregates = params.aggregates;
        this.groupDomain = params.groupDomain;
        this.count = params.count;
        this.groupByFieldName = params.groupByFieldName;
        this.groupByInfo = params.groupByInfo;
        this.recordParam = params.recordParam;
        if ("isFolded" in state) {
            this.isFolded = state.isFolded;
        } else if ("isFolded" in params) {
            this.isFolded = params.isFolded;
        } else {
            this.isFolded = true;
        }

        const listParams = {
            domain: Domain.and([params.domain, this.groupDomain]).toList(),
            groupBy: params.groupBy,
            context: params.context,
            orderBy: params.orderBy,
            resModel: params.resModel,
            activeFields: params.activeFields,
            fields: params.fields,
            groupByInfo: params.groupByInfo,
        };
        this.list = this.model.createDataPoint("list", listParams, state.listState);
    }

    exportState() {
        return {
            isFolded: this.isFolded,
            listState: this.list.exportState(),
        };
    }

    async load() {
        if (!this.isFolded) {
            await this.list.load();
            if (this.recordParam) {
                this.record = this.model.createDataPoint("record", this.recordParam);
                await this.record.load();
            }
        }
    }

    async toggle() {
        this.isFolded = !this.isFolded;
        await this.load({});
        this.model.notify();
    }
}
export class StaticList extends DataPoint {
    constructor(model, params, state) {
        super(...arguments);

        this.resIds = params.resIds || [];
        this.records = [];
        this._cache = {};
        this.offset = 0;
        this.views = params.views || {};
        this.viewMode = params.viewMode;
        this.orderBy = params.orderBy || {}; // rename orderBy + get back from state
        this.limit = params.limit || state.limit || this.constructor.DEFAULT_LIMIT;
        this.offset = 0;
    }

    exportState() {
        return {
            limit: this.limit,
        };
    }

    get count() {
        return this.resIds.length;
    }

    async load() {
        if (!this.resIds.length) {
            return [];
        }
        const orderFieldName = this.orderBy.name;
        const hasSeveralPages = this.limit < this.resIds.length;
        if (hasSeveralPages && orderFieldName) {
            // there several pages in the x2many and it is ordered, so we must know the value
            // for the sorted field for all records and sort the resIds w.r.t. to those values
            // before fetching the activeFields for the resIds of the current page.
            // 1) populate values for already fetched records
            let recordValues = {};
            for (const resId in this._cache) {
                recordValues[resId] = this._cache[resId].data[orderFieldName];
            }
            // 2) fetch values for non loaded records
            const resIds = this.resIds.filter((resId) => !(resId in this._cache));
            if (resIds.length) {
                const records = await this.model.orm.read(this.resModel, resIds, [orderFieldName]);
                for (const record of records) {
                    recordValues[record.id] = record[orderFieldName];
                }
            }
            // 3) sort resIds
            this.resIds.sort((id1, id2) => {
                let v1 = recordValues[id1];
                let v2 = recordValues[id2];
                if (this.fields[orderFieldName].type === "many2one") {
                    v1 = v1[1];
                    v2 = v2[1];
                }
                if (v1 <= v2) {
                    return this.orderBy.asc ? -1 : 1;
                } else {
                    return this.orderBy.asc ? 1 : -1;
                }
            });
        }
        const resIdsInCurrentPage = this.resIds.slice(this.offset, this.offset + this.limit);
        this.records = await Promise.all(
            resIdsInCurrentPage.map(async (resId) => {
                let record = this._cache[resId];
                if (!record) {
                    record = this.model.createDataPoint("record", {
                        resModel: this.resModel,
                        resId,
                        fields: this.fields,
                        activeFields: this.activeFields,
                        viewMode: this.viewMode,
                        views: this.views,
                    });
                    this._cache[resId] = record;
                    await record.load();
                }
                return record;
            })
        );
        if (!hasSeveralPages && orderFieldName) {
            this.records.sort((r1, r2) => {
                let v1 = r1.data[orderFieldName];
                let v2 = r2.data[orderFieldName];
                if (this.fields[orderFieldName].type === "many2one") {
                    v1 = v1[1];
                    v2 = v2[1];
                }
                if (v1 <= v2) {
                    return this.orderBy.asc ? -1 : 1;
                } else {
                    return this.orderBy.asc ? 1 : -1;
                }
            });
        }
    }

    async sortBy(fieldName) {
        if (this.orderBy.name === fieldName) {
            this.orderBy.asc = !this.orderBy.asc;
        } else {
            this.orderBy = { name: fieldName, asc: true };
        }

        await this.load();
        this.model.notify();
    }
}

StaticList.DEFAULT_LIMIT = 80;

export class RelationalModel extends Model {
    setup(params, { rpc, user }) {
        this.rpc = rpc;
        this.orm = new RequestBatcherORM(rpc, user);
        this.keepLast = new KeepLast();

        this.rootType = params.rootType || "list";
        this.rootParams = {
            activeFields: params.activeFields || {},
            fields: params.fields || {},
            viewMode: params.viewMode || null,
            resModel: params.resModel,
            groupByInfo: params.groupByInfo,
        };
        if (this.rootType === "record") {
            this.rootParams.resId = params.resId;
        } else {
            this.rootParams.openGroupsByDefault = params.openGroupsByDefault || false;
            this.rootParams.limit = params.limit;
            this.rootParams.groupLimit = params.groupLimit;
        }

        // this.db = Object.create(null);
        this.root = null;

        // debug
        window.basicmodel = this;
        // console.group("Current model");
        // console.log(this);
        // console.groupEnd();
    }

    /**
     * @param {object} params
     * @param {Comparison | null} [params.comparison]
     * @param {Context} [params.context]
     * @param {DomainListRepr} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {string[]} [params.orderBy]
     * @param {number} [params.resId] should not be there
     * @returns {Promise<void>}
     */
    async load(params) {
        const rootParams = Object.assign({}, this.rootParams, params);
        const state = this.root ? this.root.exportState() : {};
        this.root = this.createDataPoint(this.rootType, rootParams, state);
        await this.keepLast.add(this.root.load());
        this.rootParams = rootParams;
        this.notify();
    }

    /**
     *
     * @param {"group" | "list" | "record"} type
     * @param {Record<any, any>} params
     * @param {Record<any, any>} [state={}]
     * @returns {DataPoint}
     */
    createDataPoint(type, params, state = {}) {
        let DpClass;
        switch (type) {
            case "group": {
                DpClass = this.constructor.Group;
                break;
            }
            case "list": {
                if (params.resIds) {
                    DpClass = this.constructor.StaticList;
                } else if ((params.groupBy || []).length) {
                    DpClass = this.constructor.DynamicGroupList;
                } else {
                    DpClass = this.constructor.DynamicRecordList;
                }
                break;
            }
            case "record": {
                DpClass = this.constructor.Record;
                break;
            }
        }
        return new DpClass(this, params, state);
    }

    // /**
    //  * @param  {...any} args
    //  * @returns {DataPoint | null}
    //  */
    // get(...args) {
    //     return this.getAll(...args)[0] || null;
    // }

    // /**
    //  * @param  {any} properties
    //  * @returns {DataPoint[]}
    //  */
    // getAll(properties) {
    //     return Object.values(this.db).filter((record) => {
    //         for (const prop in properties) {
    //             if (record[prop] !== properties[prop]) {
    //                 return false;
    //             }
    //         }
    //         return true;
    //     });
    // }
}

RelationalModel.services = ["rpc", "user"];
RelationalModel.Record = Record;
RelationalModel.Group = Group;
RelationalModel.DynamicRecordList = DynamicRecordList;
RelationalModel.DynamicGroupList = DynamicGroupList;
RelationalModel.StaticList = StaticList;

////////////////////////////////////////////////////////////////////////////////
// OLD IMPLEM
////////////////////////////////////////////////////////////////////////////////

// class DataPoint {
//     /**
//      * @param {RelationalModel} model
//      * @param {{ fields: any, activeFields: string[] }} params
//      */
//     constructor(model, resModel, params) {
//         this.model = model;
//         this.resModel = resModel;
//         this.id = DataPoint.nextId++;
//         this.data = null;

//         this.fields = params.fields;
//         this.activeFields = params.activeFields;
//         this.fieldNames = Object.keys(this.activeFields);
//         this.viewMode = params.viewMode || null;

//         this.model.db[this.id] = this;
//     }

//     /**
//      * @returns {boolean}
//      */
//     get hasData() {
//         return Boolean(this.data);
//     }

//     /**
//      * Transmits the current informations to a child datapoint
//      * @private
//      * @returns {any}
//      */
//     get dataPointContext() {
//         return {
//             activeFields: this.activeFields,
//             fields: this.fields,
//             viewMode: this.viewMode,
//         };
//     }

//     /**
//      * Returns the existing record with the samel resModel and resId if any, or
//      * creates and returns a new one.
//      * @param {string} resModel
//      * @param {number} resId
//      * @param {any} params
//      * @returns {Record}
//      */
//     createRecord(resModel, resId, params = {}) {
//         const existingRecord = this.model.get({ resModel, resId });
//         if (existingRecord) {
//             return existingRecord;
//         }
//         return new Record(this.model, resModel, resId, { ...this.dataPointContext, ...params });
//     }

//     /**
//      * Creates and returns a new data list with the given parameters.
//      * @param {string} resModel
//      * @param {any} params
//      * @returns {List}
//      */
//     createList(resModel, params = {}) {
//         return new List(this.model, resModel, { ...this.dataPointContext, ...params });
//     }
// }
// DataPoint.nextId = 1;

// class Record extends DataPoint {
//     /**
//      * @param {RelationalModel} model
//      * @param {string} resModel
//      * @param {number} resId
//      * @param {any} params
//      */
//     constructor(model, resModel, resId, params) {
//         super(model, resModel, params);
//         this.resId = resId;
//         this.data = {};
//         this._values = {};
//         this._changes = {};
//     }

//     /**
//      * @param {{ fields?: string[], data?: any }} [params={}]
//      * @returns {Promise<void>}
//      */
//     async load(params = {}) {
//         // Record data
//         const fields = params.fields || this.fieldNames;
//         if (!fields.length) {
//             return;
//         }
//         if ("resId" in params) {
//             this.resId = params.resId; // FIXME: don't update internal state directly
//         }
//         let { data } = params;
//         if (!data) {
//             if (this.resId) {
//                 // FIXME: if fieldNames contains only "id", we read anyway
//                 const result = await this.model.orm.read(
//                     this.resModel,
//                     [this.resId],
//                     this.fieldNames,
//                     { bin_size: true }
//                 );
//                 data = this._sanitizeValues(result[0]);
//             } else {
//                 data = await this._performOnchange();
//             }
//         }
//         this._values = data;
//         this._changes = {};
//         this.data = { ...data };

//         // Relational data
//         await Promise.all(this.fieldNames.map((fieldName) => this.loadRelationalField(fieldName)));
//     }

//     /**
//      * @param {string} fieldName
//      * @returns {Promise<void>}
//      */
//     async loadRelationalField(fieldName) {
//         const field = this.activeFields[fieldName];
//         if (!isX2Many(this.fields[fieldName])) {
//             return;
//         }
//         const { invisible, relatedFields = {}, relation, views = {}, viewMode } = field;

//         if (invisible) {
//             // FIXME: we'll maybe have to create a datapoint anyway, for instance when we'll
//             // implement the edition
//             return;
//         }

//         const resIds = this.data[fieldName];
//         const list = this.createList(relation, {
//             activeFields: relatedFields,
//             fields: relatedFields,
//             resIds,
//             views,
//             viewMode,
//         });
//         this.data[fieldName] = list;
//         return list.load();
//     }

//     async update(fieldName, value) {
//         this.data[fieldName] = value;
//         this._changes[fieldName] = value;
//         const onChangeValues = await this._performOnchange(fieldName);
//         Object.assign(this.data, onChangeValues);
//         Object.assign(this._changes, onChangeValues);
//         this.model.notify();
//     }

//     async save() {
//         const changes = this._getChanges();
//         if (this.resId) {
//             await this.model.orm.write(this.resModel, [this.resId], changes);
//         } else {
//             this.resId = await this.model.orm.create(this.resModel, changes);
//         }
//         await this.load();
//         this.model.notify();
//     }

//     discard() {
//         this.data = { ...this._values };
//         this._changes = {};
//         this.model.notify();
//     }

//     _getChanges(allFields = false) {
//         const changes = Object.assign({}, allFields ? this.data : this._changes);
//         for (const fieldName in changes) {
//             const fieldType = this.fields[fieldName].type;
//             if (fieldType === "one2many" || fieldType === "many2many") {
//                 // TODO: need to generate commands
//                 changes[fieldName] = [];
//             } else if (fieldType === "many2one") {
//                 changes[fieldName] = changes[fieldName] ? changes[fieldName][0] : false;
//             }
//         }
//         return changes;
//     }

//     async _performOnchange(fieldName) {
//         const result = await this.model.orm.call(this.resModel, "onchange", [
//             [],
//             this._getChanges(true),
//             fieldName ? [fieldName] : [],
//             this._getOnchangeSpec(),
//         ]);
//         return this._sanitizeValues(result.value);
//     }

//     _getOnchangeSpec() {
//         const onChangeSpec = {};
//         for (const fieldName of this.fieldNames) {
//             onChangeSpec[fieldName] = "1"; // FIXME: need to on_change info from arch
//         }
//         return onChangeSpec;
//     }

//     _sanitizeValues(values) {
//         const sanitizedValues = {};
//         for (const fieldName in values) {
//             switch (this.fields[fieldName].type) {
//                 case "char": {
//                     sanitizedValues[fieldName] = values[fieldName] || "";
//                     break;
//                 }
//                 case "date":
//                 case "datetime": {
//                     // TODO
//                     break;
//                 }
//                 default: {
//                     sanitizedValues[fieldName] = values[fieldName];
//                 }
//             }
//         }
//         return sanitizedValues;
//     }
// }

// class List extends DataPoint {
//     /**
//      * @param {RelationalModel} model
//      * @param {string} resModel
//      * @param {{
//      *  resIds?: number[],
//      *  groupData?: any,
//      *  views?: any,
//      * }} [params={}]
//      */
//     constructor(model, resModel, params = {}) {
//         super(model, resModel, params);

//         this.openGroupsByDefault = params.openGroupsByDefault;

//         this.resIds = params.resIds;

//         this.domains = {};
//         this.groupBy = params.groupBy || [];
//         this.groupByField = this.fields[this.groupBy[0]];
//         this.limit = params.limit;
//         this.groupLimit = params.groupLimit;
//         this.data = [];
//         this.views = {};
//         this.orderByColumn = {};

//         // Group parameters
//         this.updateGroupParams(params);

//         for (const type in params.views || {}) {
//             const [mode] = getX2MViewModes(type);
//             this.views[mode] = Object.freeze(params.views[type]);
//         }
//     }

//     /**
//      * @override
//      */
//     get dataPointContext() {
//         return {
//             limit: this.limit,
//             groupLimit: this.groupLimit,
//             ...super.dataPointContext,
//         };
//     }

//     /**
//      * @override
//      */
//     get hasData() {
//         return Boolean(super.hasData && this.data.length);
//     }

//     /**
//      * @returns {boolean}
//      */
//     get isGrouped() {
//         return Boolean(this.groupBy.length);
//     }

//     /**
//      * Returns the aggregate values of each (aggregatable) column for the given
//      * records.
//      *
//      * @param {Record[]} records list of records to aggregate (defaults to
//      *   all records if the list is empty)
//      * @param {Object}
//      */
//     getAggregates(records) {
//         if (this.isGrouped) {
//             console.warn("Aggregates on grouped list not supported yet");
//             return {};
//         }
//         records = records.length ? records : this.data;
//         const aggregates = {};
//         for (const fieldName in this.activeFields) {
//             const field = this.fields[fieldName];
//             const type = field.type;
//             if (type !== "integer" && type !== "float" && type !== "monetary") {
//                 continue;
//             }
//             // FIXME retrieve this from arch
//             // const func =
//             //     (attrs.sum && "sum") ||
//             //     (attrs.avg && "avg") ||
//             //     (attrs.max && "max") ||
//             //     (attrs.min && "min");
//             const func = field.group_operator;
//             if (func) {
//                 let count = 0;
//                 let aggregateValue = 0;
//                 if (func === "max") {
//                     aggregateValue = -Infinity;
//                 } else if (func === "min") {
//                     aggregateValue = Infinity;
//                 }
//                 for (const record of records) {
//                     count += 1;
//                     // FIXME: could be groups instead of records
//                     // const value = (d.type === 'record') ? d.data[attrs.name] : d.aggregateValues[attrs.name];
//                     const value = record.data[fieldName];
//                     if (func === "avg" || func === "sum") {
//                         aggregateValue += value;
//                     } else if (func === "max") {
//                         aggregateValue = Math.max(aggregateValue, value);
//                     } else if (func === "min") {
//                         aggregateValue = Math.min(aggregateValue, value);
//                     }
//                 }
//                 if (func === "avg") {
//                     aggregateValue = count > 0 ? aggregateValue / count : aggregateValue;
//                 }
//                 const formatter = formatterRegistry.get(type, false);
//                 aggregates[fieldName] = {
//                     // help: attrs[func], // FIXME: from arch
//                     value: formatter ? formatter(aggregateValue) : aggregateValue,
//                 };
//             }
//         }
//         return aggregates;
//     }

//     /**
//      * @param {{ domains?: any[], groupBy?: string[], defer?: boolean, orderByColumn?: { name: string, asc: boolean } }} [params={}]
//      * @returns {Promise<void> | () => Promise<void>}
//      */
//     async load(params = {}) {
//         this.offset = 0;

//         if (params.domain && !this.groupData) {
//             this.domains.main = params.domain; // FIXME: do not modify internal state directly
//         }
//         if (params.groupBy) {
//             this.groupBy = params.groupBy;
//             this.groupByField = this.fields[this.groupBy[0]];
//         }
//         if ("orderByColumn" in params) {
//             this.orderByColumn = params.orderByColumn; // FIXME: incorrect param name (could come from a favorite)
//         }

//         const previousData = this.data;

//         if (this.resIds !== undefined) {
//             this.data = await this.loadRecords();
//         } else if (this.isGrouped) {
//             this.data = await this.loadGroups(params.keepRecords);
//         } else {
//             this.data = await this.searchRecords();
//         }

//         if (params.keepArchivedLists) {
//             const archivedLists = previousData.filter((l) => l.archived);
//             this.data.push(...archivedLists);
//         }

//         this.offset = this.data.length;
//         this.isLoaded = true;
//     }

//     /**
//      * @private
//      * @returns {Promise<Record>}
//      */
//     async searchRecords() {
//         const order = this.orderByColumn.name
//             ? `${this.orderByColumn.name} ${this.orderByColumn.asc ? "ASC" : "DESC"}`
//             : "";
//         const recordsData = await this.model.orm.searchRead(
//             this.resModel,
//             this.getDomain(),
//             this.fieldNames,
//             {
//                 limit: this.limit,
//                 order,
//                 offset: this.offset,
//             },
//             { bin_size: true }
//         );

//         return Promise.all(
//             recordsData.map(async (data) => {
//                 const record = this.createRecord(this.resModel, data.id);
//                 await record.load({ data });
//                 return record;
//             })
//         );
//     }

//     /**
//      * @private
//      * @returns {Promise<Record>}
//      */
//     async loadRecords() {
//         if (!this.resIds.length) {
//             return [];
//         }
//         return Promise.all(
//             this.resIds.map(async (resId) => {
//                 const record = this.createRecord(this.resModel, resId);
//                 await record.load();
//                 return record;
//             })
//         );
//     }

//     async loadMore() {
//         const nextRecords = await this.searchRecords();
//         this.data.push(...nextRecords);
//         this.offset = this.data.length;
//         this.model.notify();
//     }

//     /**
//      * @private
//      * @param {boolean} [keepRecords=false] Whether to keep the previous data
//      * @returns {Promise<Record>}
//      */
//     async loadGroups(keepRecords = false) {
//         const { groups, length } = await this.model.orm.webReadGroup(
//             this.resModel,
//             this.getDomain(),
//             this.fieldNames,
//             this.groupBy,
//             {
//                 limit: this.groupLimit,
//                 lazy: true,
//             }
//         );
//         this.count = length;

//         const groupBy = this.groupBy.slice(1);
//         let loadedGroups = 0;
//         return Promise.all(
//             groups.map(async (groupData) => {
//                 const groupParams = {
//                     groupAggregates: Object.create(null),
//                     groupBy,
//                 };
//                 let shouldFold = false;
//                 for (const key in groupData) {
//                     const value = groupData[key];
//                     switch (key) {
//                         case this.groupByField.name: {
//                             const formatter = formatterRegistry.get(this.groupByField.type, false);
//                             let groupDisplay = formatter ? formatter(value) : value;
//                             let groupValue = value;
//                             if (isRelational(this.groupByField)) {
//                                 // many2many or many2one -> in both cases the group's value is a many2one value
//                                 groupValue = groupValue ? groupValue[0] : false;
//                                 groupDisplay = groupDisplay || _t("Undefined");
//                             }
//                             Object.assign(groupParams, { groupValue, groupDisplay });
//                             break;
//                         }
//                         case `${this.groupByField.name}_count`: {
//                             groupParams.groupCount = value;
//                             break;
//                         }
//                         case "__domain": {
//                             groupParams.groupDomain = value;
//                             break;
//                         }
//                         case "__fold": {
//                             shouldFold = value || false;
//                             break;
//                         }
//                         default: {
//                             if (key in this.fields) {
//                                 const formatter = formatterRegistry.get(
//                                     this.fields[key].type,
//                                     false
//                                 );
//                                 const formattedValue = formatter ? formatter(value) : value;
//                                 groupParams.groupAggregates[key] = formattedValue;
//                             }
//                         }
//                     }
//                 }
//                 // FIXME: only retrieve the former group if groupby same field
//                 let group = this.data.find((g) => g.value === groupParams.groupValue);
//                 if (group && group.isLoaded) {
//                     group.updateGroupParams(groupParams);
//                 } else {
//                     keepRecords = false;
//                     group = this.createList(this.resModel, groupParams);
//                 }
//                 if (
//                     !keepRecords &&
//                     !shouldFold &&
//                     loadedGroups < LOADED_GROUP_LIMIT &&
//                     (this.openGroupsByDefault || group.isLoaded)
//                 ) {
//                     loadedGroups++;
//                     const loadParams = { groupBy, orderByColumn: this.orderByColumn };
//                     if (groupParams.groupDomain) {
//                         loadParams.domain = groupParams.groupDomain;
//                     }
//                     await group.load(loadParams);
//                 }
//                 return group;
//             })
//         );
//     }

//     async toggle() {
//         if (this.isLoaded) {
//             this.data = [];
//             this.isLoaded = false;
//         } else {
//             await this.load();
//         }
//         this.model.notify();
//     }

//     async archive() {
//         const resIds = this.data.map((r) => r.resId);
//         await this.model.orm.call(this.resModel, "action_archive", [resIds]);
//         await this.model.load();
//     }

//     async unarchive() {
//         const resIds = this.data.map((r) => r.resId);
//         await this.model.orm.call(this.resModel, "action_unarchive", [resIds]);
//         await this.model.load();
//     }

//     async resequence(dataPointId, refId) {
//         if (dataPointId) {
//             this.data = this.data.filter((dp) => dp.id !== dataPointId);
//             const index = refId ? this.data.findIndex((dp) => dp.id === refId) + 1 : 0;
//             this.data.splice(index || 0, 0, this.model.db[dataPointId]);
//         }
//         const model = this.resModel;
//         const ids = this.data.map((r) => r.resId || r.value);
//         await this.model.rpc("/web/dataset/resequence", { model, ids });
//         this.model.notify();
//     }

//     async sortBy(fieldName) {
//         const { name, asc } = this.orderByColumn;
//         let orderByColumn = {
//             name: fieldName,
//             asc: fieldName === name ? !asc : true,
//         };
//         await this.model.keepLast.add(this.load({ orderByColumn }));
//         this.model.notify();
//     }

//     getDomain() {
//         return Domain.and(Object.values(this.domains)).toList();
//     }

//     updateGroupParams(params) {
//         if (params.groupDomain) {
//             this.domains.main = params.groupDomain;
//         }
//         this.count = params.groupCount;
//         this.displayName = params.groupDisplay;
//         this.value = params.groupValue;
//         this.aggregates = params.groupAggregates;
//     }
// }
