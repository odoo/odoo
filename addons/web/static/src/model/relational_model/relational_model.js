/* @odoo-module */
// @ts-check

import { EventBus, markRaw } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { registry } from "@web/core/registry";
import { shallowEqual, unique } from "@web/core/utils/arrays";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { orderByToString } from "@web/search/utils/order_by";
import { Model } from "../model";
import { DynamicGroupList } from "./dynamic_group_list";
import { DynamicRecordList } from "./dynamic_record_list";
import { Group } from "./group";
import { Record } from "./record";
import { StaticList } from "./static_list";
import {
    getFieldsSpec,
    createPropertyActiveField,
    getAggregatesFromGroupData,
    getDisplayNameFromGroupData,
    getValueFromGroupData,
    isRelational,
} from "./utils";

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
 */

/**
 * @typedef Config
 * @property {string} resModel
 * @property {Object} fields
 * @property {Object} activeFields
 * @property {object} context
 * @property {boolean} isMonoRecord
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
 * @property {boolean} [openGroupsByDefault]
 */

/**
 * @typedef Hooks
 * @property {Function} [onWillLoadRoot]
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
    onWillSaveRecord: () => {},
    onRecordSaved: () => {},
    onWillSaveMulti: () => {},
    onSavedMulti: () => {},
    onWillSetInvalidField: () => {},
    onRecordChanged: () => {},
};

export class FetchRecordError extends Error {
    constructor(resIds) {
        super(`Can't fetch record(s) ${resIds}. They might have been deleted.`);
    }
}

export function fetchRecordErrorHandler(env, error, originalError) {
    if (originalError instanceof FetchRecordError) {
        env.services.notification.add(originalError.message, { sticky: true, type: "danger" });
        return true;
    }
}
const errorHandlerRegistry = registry.category("error_handlers");
errorHandlerRegistry.add("fetchRecordErrorHandler", fetchRecordErrorHandler);

export class RelationalModel extends Model {
    static services = ["action", "company", "dialog", "notification", "orm", "rpc", "user"];
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
    setup(params, { action, company, dialog, notification, rpc, user }) {
        this.action = action;
        this.company = company;
        this.dialog = dialog;
        this.notification = notification;
        this.rpc = rpc;
        this.user = user;

        this.bus = new EventBus();

        this.keepLast = markRaw(new KeepLast());
        this.mutex = markRaw(new Mutex());

        /** @type {Config} */
        this.config = {
            isMonoRecord: false,
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

        this._urgentSave = false;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    exportState() {
        return {
            config: this.config,
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
        const data = await this.keepLast.add(this._loadData(config));
        this.root = this._createRoot(config, data);
        this.config = config;
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _applyProperties(records, config) {
        for (const record of records) {
            for (const fieldName in record) {
                const field = config.fields[fieldName];
                if (fieldName !== "id" && field.type === "properties" && record[fieldName]) {
                    const parent = record[field.definition_record];
                    const relatedPropertyField = {
                        fieldName,
                    };
                    if (parent) {
                        relatedPropertyField.id = parent.id;
                        relatedPropertyField.displayName = parent.display_name;
                    }
                    for (const property of record[fieldName]) {
                        const propertyFieldName = `${fieldName}.${property.name}`;
                        if (!config.fields[propertyFieldName]) {
                            config.fields[propertyFieldName] = {
                                ...property,
                                name: propertyFieldName,
                                relatedPropertyField,
                                propertyName: property.name,
                                relation: property.comodel,
                            };
                            config.activeFields[propertyFieldName] =
                                createPropertyActiveField(property);
                        }
                    }
                }
            }
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
        }
        if (!config.isMonoRecord && this.root) {
            // always reset the offset to 0 when reloading from above
            config.offset = 0;
        }

        return config;
    }

    /**
     *
     * @param {Config} config
     */
    async _loadData(config) {
        if (config.isRoot) {
            this.hooks.onWillLoadRoot();
        }
        if (config.isMonoRecord) {
            const evalContext = {
                ...config.context,
                active_id: config.resId,
                active_ids: [config.resId],
                active_model: config.resModel,
                current_company_id: this.company.currentCompany.id,
            };
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
        return this._loadUngroupedList({
            ...config,
            context: {
                ...config.context,
                current_company_id: this.company.currentCompany.id,
            },
        });
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
        const orderBy = config.orderBy.filter(
            (o) =>
                o.name === firstGroupByName ||
                (o.name in config.activeFields &&
                    config.fields[o.name].group_operator !== undefined)
        );
        const response = await this._webReadGroup(config, firstGroupByName, orderBy);
        const { groups, length } = response;
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
        for (const group of groups) {
            // When group_by_no_leaf key is present FIELD_ID_count doesn't exist
            // we have to get the count from `__count` instead
            // see _read_group_raw in models.py
            group.count = group.__count || group[`${firstGroupByName}_count`];
            group.length = group.count;
            group.range = group.__range ? group.__range[config.groupBy[0]] : null;
            delete group.__count;
            delete group[`${firstGroupByName}_count`];
            delete group.__range;
            group.value = getValueFromGroupData(group, groupByField, group[config.groupBy[0]]);
            group.displayName = getDisplayNameFromGroupData(groupByField, group[config.groupBy[0]]);
            group.aggregates = getAggregatesFromGroupData(group, config.fields);
            // delete group[config.groupBy[0]];
            if (!config.groups[group.value]) {
                config.groups[group.value] = {
                    ...commonConfig,
                    groupByFieldName: groupByField.name,
                    isFolded: "__fold" in group ? group.__fold : !config.openGroupsByDefault,
                    extraDomain: false,
                    value: group.value,
                    list: {
                        ...commonConfig,
                        groupBy,
                    },
                };
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
            groupConfig.initialDomain = group.__domain;
            if (groupConfig.extraDomain) {
                groupConfig.list.domain = Domain.and([
                    group.__domain,
                    groupConfig.extraDomain,
                ]).toList();
            } else {
                groupConfig.list.domain = group.__domain;
            }
            const context = {
                ...config.context,
                [`default_${firstGroupByName}`]: group.value,
            };
            groupConfig.list.context = context;
            groupConfig.context = context;
            if (groupBy.length) {
                group.groups = [];
            } else {
                group.records = [];
            }
            if (isRelational(config.fields[firstGroupByName]) && !group.value) {
                groupConfig.isFolded = true;
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
                    } else {
                        group.records = response ? response.records : [];
                    }
                });
                proms.push(prom);
            }
        }
        if (groupRecordConfig && Object.keys(groupRecordConfig.activeFields).length) {
            const prom = this._loadRecords({
                ...groupRecordConfig,
                resIds: groupRecordResIds,
            }).then((records) => {
                for (const group of groups) {
                    group.values = records.find((r) => group.value && r.id === group.value);
                }
            });
            proms.push(prom);
        }
        await Promise.all(proms);

        // if a group becomes empty at some point (e.g. we dragged its last record out of it), and the view is reloaded
        // with the same domain and groupbys, we want to keep the empty group in the UI
        if (
            config.currentGroups &&
            config.currentGroups.params ===
                JSON.stringify([config.domain, config.groupBy, config.offset, config.limit])
        ) {
            const currentGroups = config.currentGroups.groups;
            for (const group of currentGroups) {
                if (
                    config.groups[group.value] &&
                    !groups.some((g) => JSON.stringify(g.value) === JSON.stringify(group.value))
                ) {
                    groups.push(Object.assign({}, group, { count: 0, length: 0, records: [] }));
                }
            }
        }
        config.currentGroups = {
            params: JSON.stringify([config.domain, config.groupBy, config.offset, config.limit]),
            groups,
        };

        return { groups, length };
    }

    /**
     * @param {Config} config
     * @param {Object} [params={}]
     * @returns Promise<Object>
     */
    _loadNewRecord(config, params = {}) {
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

            this._applyProperties(records, config);
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
        const kwargs = {
            specification: getFieldsSpec(config.activeFields, config.fields, config.context),
            domain: config.domain,
            offset: config.offset,
            order: orderByToString(config.orderBy),
            limit: config.limit,
            context: { bin_size: true, ...config.context },
            count_limit:
                config.countLimit !== Number.MAX_SAFE_INTEGER ? config.countLimit + 1 : undefined,
        };
        const response = await this.orm.call(config.resModel, "unity_web_search_read", [], kwargs);

        this._applyProperties(response.records, config);
        return response;
    }

    /**
     * @param {Config} config
     * @param {Object} param
     * @param {Object} [param.changes={}]
     * @param {string[]} [param.fieldNames=[]]
     * @param {Object} [param.evalContext=config.context]
     * @returns Promise<Object>
     */
    async _onchange(config, { changes = {}, fieldNames = [], evalContext = config.context }) {
        const { fields, activeFields, resModel, resId } = config;
        let context = config.context;
        if (fieldNames.length === 1) {
            const fieldContext = config.activeFields[fieldNames[0]].context;
            context = makeContext([context, fieldContext], evalContext);
        }
        const spec = getFieldsSpec(activeFields, fields, evalContext, { withInvisible: true });
        const args = [resId ? [resId] : [], changes, fieldNames, spec];
        const response = await this.orm.call(resModel, "onchange2", args, { context });
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
     * @param {boolean} [options.noReload=false]
     * @param {Function} [options.commit] Function to call once the data has been loaded
     */
    async _updateConfig(config, patch, options = {}) {
        const tmpConfig = { ...config, ...patch };
        let data;
        if (!options.noReload) {
            data = await this._loadData(tmpConfig);
        }
        Object.assign(config, tmpConfig);
        if (data && options.commit) {
            options.commit(data);
        }
    }

    /**
     *
     * @param {Config} config
     * @returns {Promise<number>}
     */
    async _updateCount(config) {
        const count = await this.keepLast.add(this.orm.searchCount(config.resModel, config.domain));
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

    async _webReadGroup(config, firstGroupByName, orderBy) {
        return this.orm.webReadGroup(
            config.resModel,
            config.domain,
            unique([...Object.keys(config.activeFields), firstGroupByName]),
            [config.groupBy[0]],
            {
                orderby: orderByToString(orderBy),
                lazy: true, // maybe useless
                offset: config.offset,
                limit: config.limit,
                context: config.context,
            }
        );
    }
}
