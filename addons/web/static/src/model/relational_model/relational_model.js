// @ts-check

import { EventBus, markRaw, toRaw } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { shallowEqual } from "@web/core/utils/arrays";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { orderByToString } from "@web/search/utils/order_by";
import { Model } from "../model";
import { DynamicGroupList } from "./dynamic_group_list";
import { DynamicRecordList } from "./dynamic_record_list";
import { Group } from "./group";
import { Record } from "./record";
import { StaticList } from "./static_list";
import {
    extractInfoFromGroupData,
    getBasicEvalContext,
    getFieldsSpec,
    isRelational,
    makeActiveField,
} from "./utils";
import { FetchRecordError } from "./errors";

/**
 * @typedef Params
 * @property {Config} config
 * @property {State} [state]
 * @property {Hooks} [hooks]
 * @property {number} [limit]
 * @property {number} [countLimit]
 * @property {number} [groupsLimit]
 * @property {string[]} [defaultOrderBy]
 * @property {string[]} [defaultGroupBy]
 * @property {number} [maxGroupByDepth]
 * @property {boolean} [multiEdit]
 * @property {Object} [groupByInfo]
 * @property {number} [activeIdsLimit]
 * @property {boolean} [useSendBeaconToSaveUrgently]
 */

/**
 * @typedef Config
 * @property {string} resModel
 * @property {Object} fields
 * @property {Object} activeFields
 * @property {object} context
 * @property {boolean} isMonoRecord
 * @property {number} currentCompanyId
 * @property {boolean} isRoot
 * @property {Array} [domain]
 * @property {Array} [groupBy]
 * @property {Array} [orderBy]
 * @property {number} [resId]
 * @property {number[]} [resIds]
 * @property {string} [mode]
 * @property {number} [limit]
 * @property {number} [offset]
 * @property {number} [countLimit]
 * @property {number} [groupsLimit]
 * @property {Object} [groups]
 * @property {Object} [currentGroups] // FIXME: could be cleaned
 * @property {boolean} [openGroupsByDefault]
 */

/**
 * @typedef Hooks
 * @property {(nextConfiguration: Config) => void} [onWillLoadRoot]
 * @property {() => Promise} [onRootLoaded]
 * @property {Function} [onWillSaveRecord]
 * @property {Function} [onRecordSaved]
 * @property {Function} [onWillSaveMulti]
 * @property {Function} [onSavedMulti]
 * @property {Function} [onWillSetInvalidField]
 * @property {Function} [onRecordChanged]
 */

/**
 * @typedef State
 * @property {Config} config
 * @property {Object} specialDataCaches
 */

const DEFAULT_HOOKS = {
    onWillLoadRoot: () => {},
    onRootLoaded: () => {},
    onWillSaveRecord: () => {},
    onRecordSaved: () => {},
    onWillSaveMulti: () => {},
    onSavedMulti: () => {},
    onWillSetInvalidField: () => {},
    onRecordChanged: () => {},
};

export class RelationalModel extends Model {
    static services = ["action", "company", "dialog", "notification", "orm"];
    static Record = Record;
    static Group = Group;
    static DynamicRecordList = DynamicRecordList;
    static DynamicGroupList = DynamicGroupList;
    static StaticList = StaticList;
    static DEFAULT_LIMIT = 80;
    static DEFAULT_COUNT_LIMIT = 10000;
    static DEFAULT_GROUP_LIMIT = 80;
    static DEFAULT_OPEN_GROUP_LIMIT = 10;
    static MAX_NUMBER_OPENED_GROUPS = 10;

    /**
     * @param {Params} params
     */
    setup(params, { action, company, dialog, notification }) {
        this.action = action;
        this.dialog = dialog;
        this.notification = notification;

        this.bus = new EventBus();

        this.keepLast = markRaw(new KeepLast());
        this.mutex = markRaw(new Mutex());

        /** @type {Config} */
        this.config = {
            isMonoRecord: false,
            currentCompanyId: company.currentCompany.id,
            context: {},
            ...params.config,
            isRoot: true,
        };

        /** @type {Hooks} */
        this.hooks = Object.assign({}, DEFAULT_HOOKS, params.hooks);

        this.initialLimit = params.limit || this.constructor.DEFAULT_LIMIT;
        this.initialGroupsLimit = params.groupsLimit;
        this.initialCountLimit = params.countLimit || this.constructor.DEFAULT_COUNT_LIMIT;
        this.defaultOrderBy = params.defaultOrderBy;
        this.defaultGroupBy = params.defaultGroupBy;
        this.maxGroupByDepth = params.maxGroupByDepth;
        this.groupByInfo = params.groupByInfo || {};
        this.multiEdit = params.multiEdit;
        this.activeIdsLimit = params.activeIdsLimit || Number.MAX_SAFE_INTEGER;
        this.specialDataCaches = markRaw(params.state?.specialDataCaches || {});
        this.useSendBeaconToSaveUrgently = params.useSendBeaconToSaveUrgently || false;

        this._urgentSave = false;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    exportState() {
        return {
            config: toRaw(this.config),
            specialDataCaches: this.specialDataCaches,
        };
    }

    hasData() {
        return this.root.hasData;
    }

    /**
     * @param {Object} [params={}]
     * @param {Comparison | null} [params.comparison]
     * @param {Context} [params.context]
     * @param {DomainListRepr} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {Object[]} [params.orderBy]
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        const config = this._getNextConfig(this.config, params);
        this.hooks.onWillLoadRoot(config);
        const data = await this.keepLast.add(this._loadData(config));
        this.root = this._createRoot(config, data);
        this.config = config;
        return this.hooks.onRootLoaded();
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    /**
     * If we group by default based on a property, the property might not be loaded in `fields`.
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

    _askChanges() {
        const proms = [];
        this.bus.trigger("NEED_LOCAL_CHANGES", { proms });
        return Promise.all([...proms, this.mutex.getUnlockedDef()]);
    }

    /**
     *
     * @param {Config} config
     * @param {*} data
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

    /**
     * @param {*} params
     * @returns {Config}
     */
    _getNextConfig(currentConfig, params) {
        const currentGroupBy = currentConfig.groupBy;
        const config = Object.assign({}, currentConfig);

        config.context = "context" in params ? params.context : config.context;
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
            config.comparison = "comparison" in params ? params.comparison : config.comparison;

            // groupBy
            config.groupBy = "groupBy" in params ? params.groupBy : config.groupBy;
            // apply default groupBy if any
            if (this.defaultGroupBy && !config.groupBy.length) {
                config.groupBy = [this.defaultGroupBy];
            }
            // restrict the number of groupbys if requested
            if (this.maxGroupByDepth) {
                config.groupBy = config.groupBy.slice(0, this.maxGroupByDepth);
            }

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
     * @param {Config} config
     */
    async _loadData(config) {
        if (config.isMonoRecord) {
            const evalContext = getBasicEvalContext(config);
            if (!config.resId) {
                return this._loadNewRecord(config, { evalContext });
            }
            const records = await this._loadRecords(
                {
                    ...config,
                    resIds: [config.resId],
                },
                evalContext
            );
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
        const { records, length } = await this._loadUngroupedList({
            ...config,
            context: {
                ...config.context,
                current_company_id: config.currentCompanyId,
            },
        });
        if (config.offset && !records.length) {
            config.offset = 0;
            return this._loadData(config);
        }
        return { records, length };
    }

    /**
     * @param {Config} config
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
        const firstGroupByName = config.groupBy[0].split(":")[0];
        if (firstGroupByName.includes(".")) {
            if (!config.fields[firstGroupByName]) {
                await this._getPropertyDefinition(config, firstGroupByName);
            }
            const propertiesFieldName = firstGroupByName.split(".")[0];
            if (!config.activeFields[propertiesFieldName]) {
                // add the properties field so we load its data when reading the records
                // so when we drag and drop we don't need to fetch the value of the record
                config.activeFields[propertiesFieldName] = makeActiveField();
            }
        }
        const orderBy = config.orderBy.filter(
            (o) =>
                o.name === firstGroupByName ||
                o.name === "__count" ||
                (o.name in config.activeFields && config.fields[o.name].aggregator !== undefined)
        );
        const response = await this._webReadGroup(config, orderBy);
        const { groups: groupsData, length } = response;
        const groupBy = config.groupBy.slice(1);
        const groupByField = config.fields[config.groupBy[0].split(":")[0]];
        const commonConfig = {
            resModel: config.resModel,
            fields: config.fields,
            activeFields: config.activeFields,
        };
        let groupRecordConfig;
        const groupRecordResIds = [];
        if (this.groupByInfo[firstGroupByName]) {
            groupRecordConfig = {
                ...this.groupByInfo[firstGroupByName],
                resModel: config.fields[firstGroupByName].relation,
                context: {},
            };
        }
        const proms = [];
        let nbOpenGroups = 0;

        const groups = [];
        for (const groupData of groupsData) {
            const group = extractInfoFromGroupData(groupData, config.groupBy, config.fields);
            if (!config.groups[group.value]) {
                config.groups[group.value] = {
                    ...commonConfig,
                    groupByFieldName: groupByField.name,
                    isFolded:
                        "__fold" in groupData ? groupData.__fold : !config.openGroupsByDefault,
                    extraDomain: false,
                    value: group.value,
                    list: {
                        ...commonConfig,
                        groupBy,
                    },
                };
                if (isRelational(config.fields[firstGroupByName]) && !group.value) {
                    // fold the "unset" group by default when grouped by many2one
                    config.groups[group.value].isFolded = true;
                }
                if (groupRecordConfig) {
                    config.groups[group.value].record = {
                        ...groupRecordConfig,
                        resId: group.value ?? false,
                    };
                }
            }
            if (groupRecordConfig) {
                const resId = config.groups[group.value].record.resId;
                if (resId) {
                    groupRecordResIds.push(resId);
                }
            }
            const groupConfig = config.groups[group.value];
            groupConfig.list.orderBy = config.orderBy;
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
                ...config.context,
                [`default_${firstGroupByName}`]: group.serverValue,
            };
            groupConfig.list.context = context;
            groupConfig.context = context;
            if (groupBy.length) {
                group.groups = [];
            } else {
                group.records = [];
            }
            if (!groupConfig.isFolded) {
                nbOpenGroups++;
                if (nbOpenGroups > this.constructor.MAX_NUMBER_OPENED_GROUPS) {
                    groupConfig.isFolded = true;
                }
            }
            if (!groupConfig.isFolded && group.count > 0) {
                const prom = this._loadData(groupConfig.list).then((response) => {
                    if (groupBy.length) {
                        group.groups = response ? response.groups : [];
                        group.length = response ? response.length : 0;
                    } else {
                        group.records = response ? response.records : [];
                    }
                });
                proms.push(prom);
            }
            groups.push(group);
        }
        if (groupRecordConfig && Object.keys(groupRecordConfig.activeFields).length) {
            const prom = this._loadRecords({
                ...groupRecordConfig,
                resIds: groupRecordResIds,
            }).then((records) => {
                for (const group of groups) {
                    if (!group.value) {
                        group.values = { id: false };
                        continue;
                    }
                    group.values = records.find((r) => group.value && r.id === group.value);
                }
            });
            proms.push(prom);
        }
        await Promise.all(proms);

        // if a group becomes empty at some point (e.g. we dragged its last record out of it), and the view is reloaded
        // with the same domain and groupbys, we want to keep the empty group in the UI
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

        return { groups, length };
    }

    /**
     * @param {Config} config
     * @param {Object} [params={}]
     * @returns Promise<Object>
     */
    async _loadNewRecord(config, params = {}) {
        return this._onchange(config, params);
    }

    /**
     *
     * @param {Config} config
     * @param {object} evalContext
     * @returns
     */
    async _loadRecords(config, evalContext = config.context) {
        const { resModel, resIds, activeFields, fields, context } = config;
        if (!resIds.length) {
            return [];
        }
        const fieldSpec = getFieldsSpec(activeFields, fields, evalContext);
        if (Object.keys(fieldSpec).length > 0) {
            const kwargs = {
                context: { bin_size: true, ...context },
                specification: fieldSpec,
            };
            const records = await this.orm.webRead(resModel, resIds, kwargs);
            if (!records.length) {
                throw new FetchRecordError(resIds);
            }

            return records;
        } else {
            return resIds.map((resId) => {
                return { id: resId };
            });
        }
    }

    /**
     * Load records from the server for an ungrouped list. Return the result
     * of unity read RPC.
     *
     * @param {Config} config
     * @returns
     */
    async _loadUngroupedList(config) {
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
        return this.orm.webSearchRead(config.resModel, config.domain, kwargs);
    }

    /**
     * @param {Config} config
     * @param {Object} param
     * @param {Object} [param.changes={}]
     * @param {string[]} [param.fieldNames=[]]
     * @param {Object} [param.evalContext=config.context]
     * @returns Promise<Object>
     */
    async _onchange(
        config,
        { changes = {}, fieldNames = [], evalContext = config.context, onError }
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
            response = await this.orm.call(resModel, "onchange", args, { context });
        } catch (e) {
            if (onError) {
                return onError(e);
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
     *
     * @param {Config} config
     * @param {Partial<Config>} patch
     * @param {Object} [options]
     * @param {boolean} [options.reload=true]
     * @param {Function} [options.commit] Function to call once the data has been loaded
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
            return this.hooks.onRootLoaded();
        }
    }

    /**
     *
     * @param {Config} config
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

    async _webReadGroup(config, orderBy) {
        const aggregates = Object.values(config.fields)
            .filter(
                (field) =>
                    field.aggregator &&
                    field.name in config.activeFields &&
                    field.name !== config.groupBy[0]
            )
            .map((field) => `${field.name}:${field.aggregator}`);
        return this.orm.webReadGroup(
            config.resModel,
            config.domain,
            aggregates,
            [config.groupBy[0]],
            {
                orderby: orderByToString(orderBy),
                lazy: true,
                offset: config.offset,
                limit: config.limit, // TODO: remove limit when == MAX_integer
                context: config.context,
            }
        );
    }
}
