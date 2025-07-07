// @ts-check

import { EventBus, markRaw, toRaw } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { rpcBus } from "@web/core/network/rpc";
import { shallowEqual } from "@web/core/utils/arrays";
import { pick } from "@web/core/utils/objects";
import { Deferred, KeepLast, Mutex } from "@web/core/utils/concurrency";
import { orderByToString } from "@web/search/utils/order_by";
import { Model } from "../model";
import { DynamicGroupList } from "./dynamic_group_list";
import { DynamicRecordList } from "./dynamic_record_list";
import { Group } from "./group";
import { Record as RelationalRecord } from "./record";
import { StaticList } from "./static_list";
import {
    extractInfoFromGroupData,
    getAggregateSpecifications,
    getBasicEvalContext,
    getFieldsSpec,
    getGroupServerValue,
    getId,
    makeActiveField,
} from "./utils";
import { FetchRecordError } from "./errors";

/**
 * @typedef {import("@web/core/context").Context} Context
 * @typedef {import("./datapoint").DataPoint} DataPoint
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 * @typedef {import("@web/search/search_model").Field} Field
 * @typedef {import("@web/search/search_model").FieldInfo} FieldInfo
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 * @typedef {import("services").ServiceFactories} Services
 *
 * @typedef {{
 *  changes?: Record<string, unknown>;
 *  fieldNames?: string[];
 *  evalContext?: Context;
 *  onError?: (error: unknown) => unknown;
 *  cached?: Object;
 * }} OnChangeParams
 *
 * @typedef {SearchParams & {
 *  fields: Record<string, Field>;
 *  activeFields: Record<string, FieldInfo>;
 *  isMonoRecord: boolean;
 *  isRoot: boolean;
 *  resIds?: number[];
 *  mode?: "edit" | "readonly";
 *  loadId?: string;
 *  limit?: number;
 *  offset?: number;
 *  countLimit?: number;
 *  groupsLimit?: number;
 *  groups?: Record<string, unknown>;
 *  currentGroups?: Record<string, unknown>; // FIXME: could be cleaned: Object
 *  openGroupsByDefault?: boolean;
 * }} RelationalModelConfig
 *
 * @typedef {{
 *  config: RelationalModelConfig;
 *  state?: RelationalModelState;
 *  hooks?: Partial<typeof DEFAULT_HOOKS>;
 *  limit?: number;
 *  countLimit?: number;
 *  groupsLimit?: number;
 *  defaultOrderBy?: string[];
 *  maxGroupByDepth?: number;
 *  multiEdit?: boolean;
 *  groupByInfo?: Record<string, unknown>;
 *  activeIdsLimit?: number;
 *  useSendBeaconToSaveUrgently?: boolean;
 * }} RelationalModelParams
 *
 * @typedef {{
 *  config: RelationalModelConfig;
 *  specialDataCaches: Record<string, unknown>;
 * }} RelationalModelState
 */

const DEFAULT_HOOKS = {
    /** @type {(config: RelationalModelConfig) => any} */
    onWillLoadRoot: () => {},
    /** @type {(root: DataPoint) => any} */
    onRootLoaded: () => {},
    /** @type {(record: RelationalRecord) => any} */
    onWillSaveRecord: () => {},
    /** @type {(record: RelationalRecord) => any} */
    onRecordSaved: () => {},
    /** @type {(record: RelationalRecord) => any} */
    onWillSaveMulti: () => {},
    /** @type {(records: RelationalRecord[]) => any} */
    onSavedMulti: () => {},
    /** @type {(record: RelationalRecord, fieldName: string) => any} */
    onWillSetInvalidField: () => {},
    /** @type {(record: RelationalRecord) => any} */
    onRecordChanged: () => {},
};

rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
    if (ev.detail.data.params?.method === "unlink") {
        rpcBus.trigger("CLEAR-CACHES", ["web_read", "web_search_read"]);
    }
});

export class RelationalModel extends Model {
    static services = ["action", "dialog", "notification", "orm"];
    static Record = RelationalRecord;
    static Group = Group;
    static DynamicRecordList = DynamicRecordList;
    static DynamicGroupList = DynamicGroupList;
    static StaticList = StaticList;
    static DEFAULT_LIMIT = 80;
    static DEFAULT_COUNT_LIMIT = 10000;
    static DEFAULT_GROUP_LIMIT = 80;
    static DEFAULT_OPEN_GROUP_LIMIT = 10; // TODO: remove ?
    static withCache = true;

    /**
     * @param {RelationalModelParams} params
     * @param {Services} services
     */
    setup(params, { action, dialog, notification }) {
        this.action = action;
        this.dialog = dialog;
        this.notification = notification;

        this.bus = new EventBus();

        this.keepLast = markRaw(new KeepLast());
        this.mutex = markRaw(new Mutex());

        /** @type {RelationalModelConfig} */
        this.config = {
            isMonoRecord: false,
            context: {},
            ...params.config,
            isRoot: true,
        };

        this.hooks = Object.assign({}, DEFAULT_HOOKS, params.hooks);

        this.initialLimit = params.limit || this.constructor.DEFAULT_LIMIT;
        this.initialGroupsLimit = params.groupsLimit;
        this.initialCountLimit = params.countLimit || this.constructor.DEFAULT_COUNT_LIMIT;
        this.defaultOrderBy = params.defaultOrderBy;
        this.maxGroupByDepth = params.maxGroupByDepth;
        this.groupByInfo = params.groupByInfo || {};
        this.multiEdit = params.multiEdit;
        this.activeIdsLimit = params.activeIdsLimit || Number.MAX_SAFE_INTEGER;
        this.specialDataCaches = markRaw(params.state?.specialDataCaches || {});
        this.useSendBeaconToSaveUrgently = params.useSendBeaconToSaveUrgently || false;
        this.withCache = this.constructor.withCache && this.env.config?.cache;

        this._urgentSave = false;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    exportState() {
        const config = { ...toRaw(this.config) };
        delete config.currentGroups;
        return {
            config,
            specialDataCaches: this.specialDataCaches,
        };
    }

    /**
     * @override
     * @type {Model["hasData"]}
     */
    hasData() {
        return this.root.hasData;
    }

    /**
     * @override
     * @type {Model["load"]}
     */
    async load(params = {}) {
        const config = this._getNextConfig(this.config, params);
        if (!this.isReady) {
            // We want the control panel to be displayed directly, without waiting for data to be
            // loaded, for instance to be able to interact with the search view. For that reason, we
            // create an empty root, without data, s.t. controllers can make the assumption that the
            // root is set when they are rendered. The root is replaced later on by the real root,
            // when data are loaded.
            this.root = this._createEmptyRoot(config);
            this.config = config;
        }
        this.hooks.onWillLoadRoot(config);
        const rootLoadDef = new Deferred();
        const cached = this._getCacheParams(config, rootLoadDef);
        const data = await this.keepLast.add(this._loadData(config, cached));
        this.root = this._createRoot(config, data);
        rootLoadDef.resolve({ root: this.root, loadId: config.loadId });
        this.config = config;
        await this.hooks.onRootLoaded(this.root);
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    /**
     * If we group by default based on a property, the property might not be loaded in `fields`.
     *
     * @param {RelationalModelConfig} config
     * @param {string} propertyFullName
     */
    async _getPropertyDefinition(config, propertyFullName) {
        // dynamically load the property and add the definition in the fields attribute
        const result = await this.orm.call(
            config.resModel,
            "get_property_definition",
            [propertyFullName],
            { context: config.context }
        );
        if (!result) {
            // the property might have been removed
            config.groupBy = null;
        } else {
            result.propertyName = result.name;
            result.name = propertyFullName; // "xxxxx" -> "property.xxxxx"
            // needed for _applyChanges
            result.relatedPropertyField = { fieldName: propertyFullName.split(".")[0] };
            result.relation = result.comodel; // match name on field
            config.fields[propertyFullName] = result;
        }
    }

    async _askChanges() {
        const proms = [];
        this.bus.trigger("NEED_LOCAL_CHANGES", { proms });
        await Promise.all([...proms, this.mutex.getUnlockedDef()]);
    }

    /**
     * Creates a root datapoint without data. Supported root types are DynamicRecordList and
     * DynamicGroupList.
     *
     * @param {RelationalModelConfig} config
     * @returns {DataPoint | undefined}
     */
    _createEmptyRoot(config) {
        if (!config.isMonoRecord) {
            if (config.groupBy.length) {
                return this._createRoot(config, { groups: [], length: 0 });
            }
            return this._createRoot(config, { records: [], length: 0 });
        }
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Record<string, unknown>} data
     * @returns {DataPoint}
     */
    _createRoot(config, data) {
        if (config.isMonoRecord) {
            return new this.constructor.Record(this, config, data);
        }
        if (config.groupBy.length) {
            return new this.constructor.DynamicGroupList(this, config, data);
        }
        return new this.constructor.DynamicRecordList(this, config, data);
    }

    _getCacheParams(config, rootLoadDef) {
        if (!this.withCache) {
            return;
        }
        if (
            !this.isReady || // first load of the model
            // monorecord, loading a different id, or creating a new record (onchange)
            (config.isMonoRecord && (this.root.config.resId !== config.resId || !config.resId))
        ) {
            return {
                onFinish: async (hasChanged, result) => {
                    if (!hasChanged) {
                        return;
                    }
                    const { root, loadId } = await rootLoadDef;
                    if (root.id !== this.root.id) {
                        // The root that we want to update is not the current one. It may happen
                        // we displayed sample data from the cache, but the rpc returned records. In
                        // that case, we want to display those records. In all other usecases, we
                        // simply ignore the update.
                        if (this.useSampleModel && result.length > 0) {
                            this.useSampleModel = false;
                            this.root._setData(result);
                        }
                        return;
                    }
                    if (loadId !== this.root.config.loadId) {
                        // Avoid updating if another load was already done.
                        // For instance a sort in a list.
                        return;
                    }
                    if (root.config.isMonoRecord) {
                        if (!root.config.resId) {
                            // result is the response of the onchange rpc
                            return root._setData(result.value);
                        }
                        // result is the response of a web_read rpc
                        if (!result.length) {
                            // we read a record that no longer exists
                            throw new FetchRecordError([root.config.resId]);
                        }
                        return root._setData(result[0]);
                    }

                    // result is the response of a web_search_read rpc
                    root._setData(result);
                },
            };
        }
    }

    /**
     * @param {RelationalModelConfig} currentConfig
     * @param {Partial<SearchParams>} params
     * @returns {RelationalModelConfig}
     */
    _getNextConfig(currentConfig, params) {
        const currentGroupBy = currentConfig.groupBy;
        const config = Object.assign({}, currentConfig);

        config.context = "context" in params ? params.context : config.context;
        config.context = { ...config.context };
        if (currentConfig.isMonoRecord) {
            config.resId = "resId" in params ? params.resId : config.resId;
            config.resIds = "resIds" in params ? params.resIds : config.resIds;
            if (!config.resIds) {
                config.resIds = config.resId ? [config.resId] : [];
            }
            if (!config.resId && config.mode !== "edit") {
                config.mode = "edit";
            }
        } else {
            config.domain = "domain" in params ? params.domain : config.domain;

            // groupBy
            config.groupBy = "groupBy" in params ? params.groupBy : config.groupBy;
            // restrict the number of groupbys if requested
            if (this.maxGroupByDepth) {
                config.groupBy = config.groupBy.slice(0, this.maxGroupByDepth);
            }
            // apply month granularity if none explicitly given
            // TODO: accept only explicit granularity
            config.groupBy = config.groupBy.map((g) => {
                if (g in config.fields && ["date", "datetime"].includes(config.fields[g].type)) {
                    return `${g}:month`;
                }
                return g;
            });

            // orderBy
            config.orderBy = "orderBy" in params ? params.orderBy : config.orderBy;
            // re-apply previous orderBy if not given (or no order)
            if (!config.orderBy.length) {
                config.orderBy = currentConfig.orderBy || [];
            }
            // apply default order if no order
            if (this.defaultOrderBy && !config.orderBy.length) {
                config.orderBy = this.defaultOrderBy;
            }

            // keep current root config if any, if the groupBy parameter is the same
            if (!shallowEqual(config.groupBy || [], currentGroupBy || [])) {
                delete config.groups;
            }
            if (!config.groupBy.length) {
                config.orderBy = config.orderBy.filter((order) => order.name !== "__count");
            }
        }
        if (!config.isMonoRecord && this.root && params.domain) {
            // always reset the offset to 0 when reloading from above with a domain
            const resetOffset = (config) => {
                config.offset = 0;
                for (const group of Object.values(config.groups || {})) {
                    resetOffset(group.list);
                }
            };
            resetOffset(config);
            if (!!config.groupBy.length !== !!currentGroupBy.length) {
                // from grouped to ungrouped or the other way around -> force the limit to be reset
                delete config.limit;
            }
        }

        return config;
    }

    /**
     *
     * @param {RelationalModelConfig} config
     * @param {Object} [cached]
     */
    async _loadData(config, cached) {
        config.loadId = getId("load");
        if (config.isMonoRecord) {
            const evalContext = getBasicEvalContext(config);
            if (!config.resId) {
                return this._loadNewRecord(config, { evalContext, cached });
            }
            const records = await this._loadRecords(config, evalContext, cached);
            return records[0];
        }
        if (config.resIds) {
            // static list
            const resIds = config.resIds.slice(config.offset, config.offset + config.limit);
            return this._loadRecords({ ...config, resIds });
        }
        if (config.groupBy.length) {
            return this._loadGroupedList(config);
        }
        Object.assign(config, {
            limit: config.limit || this.initialLimit,
            countLimit: "countLimit" in config ? config.countLimit : this.initialCountLimit,
            offset: config.offset || 0,
        });
        if (config.countLimit !== Number.MAX_SAFE_INTEGER) {
            config.countLimit = Math.max(config.countLimit, config.offset + config.limit);
        }
        const { records, length } = await this._loadUngroupedList(config, cached);
        if (config.offset && !records.length) {
            config.offset = 0;
            return this._loadData(config, cached);
        }
        return { records, length };
    }

    /**
     * @param {RelationalModelConfig} config
     */
    async _loadGroupedList(config) {
        config.offset = config.offset || 0;
        config.limit = config.limit || this.initialGroupsLimit;
        if (!config.limit) {
            config.limit = config.openGroupsByDefault
                ? this.constructor.DEFAULT_OPEN_GROUP_LIMIT
                : this.constructor.DEFAULT_GROUP_LIMIT;
        }
        config.groups = config.groups || {};

        const commonConfig = {
            resModel: config.resModel,
            fields: config.fields,
            activeFields: config.activeFields,
            offset: 0,
        };

        const extractGroups = async (currentConfig, groupsData) => {
            const groupByFieldName = currentConfig.groupBy[0].split(":")[0];
            if (groupByFieldName.includes(".")) {
                if (!config.fields[groupByFieldName]) {
                    await this._getPropertyDefinition(config, groupByFieldName);
                }
                const propertiesFieldName = groupByFieldName.split(".")[0];
                if (!config.activeFields[propertiesFieldName]) {
                    // add the properties field so we load its data when reading the records
                    // so when we drag and drop we don't need to fetch the value of the record
                    config.activeFields[propertiesFieldName] = makeActiveField();
                }
            }
            const nextLevelGroupBy = currentConfig.groupBy.slice(1);
            const groups = [];

            let groupRecordConfig;
            if (this.groupByInfo[groupByFieldName]) {
                groupRecordConfig = {
                    ...this.groupByInfo[groupByFieldName],
                    resModel: currentConfig.fields[groupByFieldName].relation,
                    context: {},
                };
            }

            for (const groupData of groupsData) {
                const group = extractInfoFromGroupData(
                    groupData,
                    currentConfig.groupBy,
                    currentConfig.fields,
                    currentConfig.domain
                );
                if (!currentConfig.groups[group.value]) {
                    const isFolded =
                        !Object.hasOwn(groupData, "__records") &&
                        !Object.hasOwn(groupData, "__groups");
                    currentConfig.groups[group.value] = {
                        ...commonConfig,
                        groupByFieldName,
                        isFolded: isFolded,
                        extraDomain: false,
                        value: group.value,
                        list: {
                            ...commonConfig,
                            groupBy: nextLevelGroupBy,
                            groups: {},
                            limit:
                                nextLevelGroupBy.length === 0
                                    ? this.initialLimit
                                    : this.initialGroupsLimit ||
                                      this.constructor.DEFAULT_GROUP_LIMIT,
                        },
                    };
                }

                const groupConfig = currentConfig.groups[group.value];
                groupConfig.list.orderBy = currentConfig.orderBy;
                groupConfig.initialDomain = group.domain;
                if (groupConfig.extraDomain) {
                    groupConfig.list.domain = Domain.and([
                        group.domain,
                        groupConfig.extraDomain,
                    ]).toList();
                } else {
                    groupConfig.list.domain = group.domain;
                }
                const context = {
                    ...currentConfig.context,
                    [`default_${groupByFieldName}`]: group.serverValue,
                };
                groupConfig.list.context = context;
                groupConfig.context = context;
                if (nextLevelGroupBy.length) {
                    if (!groupConfig.isFolded) {
                        const { groups, length } = groupData.__groups;
                        group.groups = await extractGroups(groupConfig.list, groups);
                        group.length = length;
                    } else {
                        group.groups = [];
                    }
                } else {
                    if (!groupConfig.isFolded) {
                        group.records = groupData.__records;
                        group.length = groupData.__count;
                    } else {
                        group.records = [];
                    }
                }
                if (Object.hasOwn(groupData, "__offset")) {
                    groupConfig.list.offset = group.__offset;
                }
                if (groupRecordConfig) {
                    groupConfig.record = {
                        ...groupRecordConfig,
                        resId: group.value ?? false,
                    };
                }
                groups.push(group);
            }

            return groups;
        };

        const response = await this._webReadGroup(config);
        const groups = await extractGroups(config, response.groups);

        const params = JSON.stringify([
            config.domain,
            config.groupBy,
            config.offset,
            config.limit,
            config.orderBy,
        ]);
        if (config.currentGroups && config.currentGroups.params === params) {
            const currentGroups = config.currentGroups.groups;
            currentGroups.forEach((group, index) => {
                if (
                    config.groups[group.value] &&
                    !groups.some((g) => JSON.stringify(g.value) === JSON.stringify(group.value))
                ) {
                    const aggregates = Object.assign({}, group.aggregates);
                    for (const key in aggregates) {
                        aggregates[key] = 0;
                    }
                    groups.splice(
                        index,
                        0,
                        Object.assign({}, group, { count: 0, length: 0, records: [], aggregates })
                    );
                }
            });
        }
        config.currentGroups = { params, groups };

        return { groups, length: response.length };
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Partial<RelationalModelParams>} [params={}]
     * @returns {Promise<Record<string, unknown>>}
     */
    async _loadNewRecord(config, params = {}) {
        return this._onchange(config, params);
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Context} evalContext
     * @param {Object} [cached]
     */
    async _loadRecords(config, evalContext = config.context, cached) {
        const { resModel, activeFields, fields, context } = config;
        const resIds = config.resId ? [config.resId] : config.resIds;
        if (!resIds.length) {
            return [];
        }
        const fieldSpec = getFieldsSpec(activeFields, fields, evalContext);
        if (Object.keys(fieldSpec).length > 0) {
            const kwargs = {
                context: { bin_size: true, ...context },
                specification: fieldSpec,
            };
            const orm = cached ? this.orm.cached(cached) : this.orm;
            const records = await orm.webRead(resModel, resIds, kwargs);
            if (!records.length) {
                throw new FetchRecordError(resIds);
            }

            return records;
        } else {
            return resIds.map((resId) => ({ id: resId }));
        }
    }

    /**
     * Load records from the server for an ungrouped list. Return the result
     * of unity read RPC.
     *
     * @param {RelationalModelConfig} config
     * @param {Object} [cached]
     */
    async _loadUngroupedList(config, cached) {
        const orderBy = config.orderBy.filter((o) => o.name !== "__count");
        const kwargs = {
            specification: getFieldsSpec(config.activeFields, config.fields, config.context),
            offset: config.offset,
            order: orderByToString(orderBy),
            limit: config.limit,
            context: { bin_size: true, ...config.context },
            count_limit:
                config.countLimit !== Number.MAX_SAFE_INTEGER ? config.countLimit + 1 : undefined,
        };
        const orm = cached ? this.orm.cached(cached) : this.orm;
        return orm.webSearchRead(config.resModel, config.domain, kwargs);
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {OnChangeParams} params
     * @returns {Promise<Record<string, unknown>>}
     */
    async _onchange(
        config,
        { changes = {}, fieldNames = [], evalContext = config.context, onError, cached }
    ) {
        const { fields, activeFields, resModel, resId } = config;
        let context = config.context;
        if (fieldNames.length === 1) {
            const fieldContext = config.activeFields[fieldNames[0]].context;
            context = makeContext([context, fieldContext], evalContext);
        }
        const spec = getFieldsSpec(activeFields, fields, evalContext, { withInvisible: true });
        const args = [resId ? [resId] : [], changes, fieldNames, spec];
        let response;
        try {
            const orm = cached ? this.orm.cached(cached) : this.orm;
            response = await orm.call(resModel, "onchange", args, { context });
        } catch (e) {
            if (onError) {
                return void onError(e);
            }
            throw e;
        }
        if (response.warning) {
            const { type, title, message, className, sticky } = response.warning;
            if (type === "dialog") {
                this.dialog.add(WarningDialog, { title, message });
            } else {
                this.notification.add(message, {
                    className,
                    sticky,
                    title,
                    type: "warning",
                });
            }
        }
        return response.value;
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Partial<RelationalModelConfig>} patch
     * @param {{
     *  commit?: (data: Record<string, unknown>) => unknown;
     *  reload?: boolean;
     * }} [options]
     */
    async _updateConfig(config, patch, { reload = true, commit } = {}) {
        const tmpConfig = { ...config, ...patch };
        markRaw(tmpConfig.activeFields);
        markRaw(tmpConfig.fields);

        let data;
        if (reload) {
            if (tmpConfig.isRoot) {
                this.hooks.onWillLoadRoot(tmpConfig);
            }
            data = await this._loadData(tmpConfig);
        }
        Object.assign(config, tmpConfig);
        if (data && commit) {
            commit(data);
        }
        if (reload && config.isRoot) {
            await this.hooks.onRootLoaded(this.root);
        }
    }

    /**
     *
     * @param {RelationalModelConfig} config
     * @returns {Promise<number>}
     */
    async _updateCount(config) {
        const count = await this.keepLast.add(
            this.orm.searchCount(config.resModel, config.domain, { context: config.context })
        );
        config.countLimit = Number.MAX_SAFE_INTEGER;
        return count;
    }

    /**
     * When grouped by a many2many field, the same record may be displayed in
     * several groups. When one of these records is edited, we want all other
     * occurrences to be updated. The purpose of this function is to find and
     * update all occurrences of a record that has been reloaded, in a grouped
     * list view.
     *
     * @param {RelationalRecord} reloadedRecord
     * @param {Record<string, unknown>} serverValues
     */
    _updateSimilarRecords(reloadedRecord, serverValues) {
        if (this.config.isMonoRecord || !this.config.groupBy.length) {
            return;
        }
        for (const record of this.root.records) {
            if (record === reloadedRecord) {
                continue;
            }
            if (record.resId === reloadedRecord.resId) {
                record._applyValues(serverValues);
            }
        }
    }

    async _webReadGroup(config) {
        function getGroupInfo(groups) {
            return Object.values(groups).map((group) => {
                const field = group.fields[group.groupByFieldName];
                const value =
                    field.type !== "many2many"
                        ? getGroupServerValue(field, group.value)
                        : group.value;
                if (group.isFolded) {
                    return { value, folded: group.isFolded };
                } else {
                    return {
                        value,
                        folded: group.isFolded,
                        limit: group.list.limit,
                        offset: group.list.offset,
                        progressbar_domain: group.extraDomain,
                        groups: group.list.groups && getGroupInfo(group.list.groups),
                    };
                }
            });
        }

        const aggregates = getAggregateSpecifications(
            pick(config.fields, ...Object.keys(config.activeFields))
        );
        const currentGroupInfos = getGroupInfo(config.groups);
        const { activeFields, fields } = config;
        const evalContext = getBasicEvalContext(config);
        const unfoldReadSpecification = getFieldsSpec(activeFields, fields, evalContext);

        const groupByReadSpecification = {};
        for (const groupBy of config.groupBy) {
            const groupInfo = this.groupByInfo[groupBy];
            if (groupInfo) {
                const { activeFields, fields } = this.groupByInfo[groupBy];
                groupByReadSpecification[groupBy] = getFieldsSpec(
                    activeFields,
                    fields,
                    evalContext
                );
            }
        }

        return this.orm.webReadGroup(config.resModel, config.domain, config.groupBy, aggregates, {
            limit: config.limit !== Number.MAX_SAFE_INTEGER ? config.limit : undefined,
            offset: config.offset,
            order: orderByToString(config.orderBy),
            auto_unfold: config.openGroupsByDefault,
            opening_info: currentGroupInfos,
            unfold_read_specification: unfoldReadSpecification,
            unfold_read_default_limit: this.initialLimit,
            groupby_read_specification: groupByReadSpecification,
            context: { read_group_expand: true, ...config.context },
        });
    }
}
