// @ts-check
/** @odoo-module native */

import { markRaw, toRaw } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { makeLogger } from "@web/core/debug/debug_logger";
import { reportUncaught } from "@web/core/errors/error_utils";
import { ModelEvent } from "@web/core/events";
import { modelLog } from "@web/core/utils/asset_log";
import { deepCopy } from "@web/core/utils/collections/objects";
import {
    Deferred,
    KeepLast,
    Mutex,
    SupersededError,
} from "@web/core/utils/concurrency";
import { orderByToString } from "@web/core/utils/order_by";
import { Model } from "@web/model/model";
import { addPropertyFieldDef } from "@web/model/property_fields";

import { cloneGroupTree, computeNextConfig } from "./config_transitions.js";
import { DynamicGroupList } from "./dynamic_group_list.js";
import { DynamicRecordList } from "./dynamic_record_list.js";
import { FetchRecordError } from "./errors.js";
import { getId, getSpecEvalContext } from "./field_context.js";
import { getFieldsSpec } from "./field_spec.js";
import { Group } from "./group.js";
import { postprocessReadGroup } from "./group_postprocessor.js";
import { getWebReadGroupParams } from "./read_group_builder.js";
import { RelationalRecord } from "./record.js";
import { SpecialDataCache } from "./special_data_cache.js";
import { StaticList } from "./static_list.js";
import { UrgentSaveCoordinator } from "./urgent_save_coordinator.js";

/** @import { Context } from "@web/core/context" */

/** @import { DomainListRepr } from "@web/core/domain" */

/** @import { Field, FieldInfo, SearchParams } from "@web/model/types" */

/** @import { ServiceFactories as Services } from "services" */

/** @import { DataPoint } from "./datapoint.js" */

/**
 * @typedef {{
 * changes?: Record<string, any>;
 * fieldNames?: string[];
 * evalContext?: any;
 * onError?: (error: unknown) => unknown;
 * cache?: Object;
 * [key: string]: any;
 * }} OnChangeParams
 * @typedef {Pick<Partial<RelationalModelConfig>, "resModel" | "fields" | "activeFields" | "fieldsToAggregate" | "context" | "isFolded"> & {
 * list: Partial<RelationalModelConfig>;
 * record?: Partial<RelationalModelConfig>;
 * value?: unknown;
 * groupByFieldName?: string;
 * initialDomain?: import("@web/core/domain").DomainListRepr;
 * extraDomain?: import("@web/core/domain").DomainListRepr | false;
 * }} RelationalGroupConfig
 * @typedef {SearchParams & {
 * fields: Record<string, Field>;
 * activeFields: Record<string, FieldInfo>;
 * fieldsToAggregate: string[];
 * isMonoRecord: boolean;
 * isRoot: boolean;
 * resIds?: number[];
 * mode?: "edit" | "readonly";
 * loadId?: string;
 * limit?: number;
 * offset?: number;
 * countLimit?: number;
 * groupsLimit?: number;
 * groups?: Record<string, RelationalGroupConfig>;
 * currentGroups?: { params: string; groups: Record<string, unknown>[] };
 * openGroupsByDefault?: boolean;
 * extraDomain?: import("@web/core/domain").DomainListRepr;
 * isFolded?: boolean;
 * isGroupList?: boolean;
 * rawContext?: Record<string, unknown>;
 * [key: string]: any;
 * }} RelationalModelConfig
 * @typedef {{
 * config: RelationalModelConfig;
 * state?: RelationalModelState;
 * hooks?: { lifecycle?: Partial<LifecycleHooks>; ui?: Partial<UIHooks> };
 * limit?: number;
 * countLimit?: number;
 * groupsLimit?: number;
 * defaultOrderBy?: import("@web/core/utils/order_by").OrderTerm[];
 * maxGroupByDepth?: number;
 * multiEdit?: boolean;
 * groupByInfo?: Record<string, { activeFields: Record<string, FieldInfo>; fields: Record<string, Field> }>;
 * activeIdsLimit?: number;
 * useSendBeaconToSaveUrgently?: boolean;
 * canUseSampleModel?: boolean;
 * isAlive?: () => boolean;
 * }} RelationalModelParams
 * @typedef {{
 * config: RelationalModelConfig;
 * specialDataCaches: import("./special_data_cache.js").SpecialDataCache;
 * }} RelationalModelState
 */

/**
 * @typedef {{
 * onWillLoadRoot: (config: RelationalModelConfig) => any;
 * onRootLoaded: (root: DataPoint) => any;
 * onWillSaveRecord: (record: RelationalRecord, changes: Record<string, unknown>) => any;
 * onRecordSaved: (record: RelationalRecord, changes: Record<string, unknown>) => any;
 * onWillSaveMulti: (record: RelationalRecord, changes: Object) => any;
 * onSavedMulti: (records: RelationalRecord[]) => any;
 * onWillSetInvalidField: (record: RelationalRecord, fieldName: string) => any;
 * onRecordChanged: (record: RelationalRecord, changes: Record<string, unknown>) => any;
 * onWillDisplayOnchangeWarning: (warning: Object) => any;
 * onAskMultiSaveConfirmation: (changes: Object, validRecords: RelationalRecord[]) => any;
 * }} LifecycleHooks
 */
const DEFAULT_LIFECYCLE_HOOKS = /** @type {LifecycleHooks} */ ({
    onWillLoadRoot: () => {},
    onRootLoaded: () => {},
    onWillSaveRecord: () => {},
    onRecordSaved: () => {},
    onWillSaveMulti: () => {},
    onSavedMulti: () => {},
    onWillSetInvalidField: () => {},
    onRecordChanged: () => {},
    onWillDisplayOnchangeWarning: () => {},
    onAskMultiSaveConfirmation: () => true,
});

/**
 * @typedef {{
 * onDisplayOnchangeWarning: (warning: {type: string, title: string, message: string, className?: string, sticky?: boolean}) => void;
 * onDisplayInvalidFields: () => (() => void);
 * onDisplayUrgentSave: (message: string) => (() => void);
 * onDisplayPropertyWarning: (message: string) => void;
 * onDisplayArchiveAction: (action: Object, reload: () => Promise<any>) => any;
 * onConfirmArchive: (archiveFn: Function, dialogProps?: Object) => void;
 * onConfirmDuplicate: (resIds: number[], copyFn: Function) => void;
 * onDisplayLimitNotification: (msg: string) => void;
 * }} UIHooks
 */
const DEFAULT_UI_HOOKS = /** @type {UIHooks} */ ({
    onDisplayOnchangeWarning: () => {},
    onDisplayInvalidFields: () => () => {},
    onDisplayUrgentSave: () => () => {},
    onDisplayPropertyWarning: () => {},
    onDisplayArchiveAction: (_action, reload) => reload(),
    onConfirmArchive: (archiveFn) => archiveFn(),
    onConfirmDuplicate: (resIds, copyFn) => copyFn(resIds),
    onDisplayLimitNotification: () => {},
});

const ASK_CHANGES_MAX_ROUNDS = 100;

const log = makeLogger("web.model");

export class RelationalModel extends Model {
    static services = ["orm"];
    static Record = RelationalRecord;
    static Group = Group;
    static DynamicRecordList = DynamicRecordList;
    static DynamicGroupList = DynamicGroupList;
    static StaticList = StaticList;
    static DEFAULT_LIMIT = 80;
    static DEFAULT_COUNT_LIMIT = 10000;
    static DEFAULT_GROUP_LIMIT = 80;
    static DEFAULT_OPEN_GROUP_LIMIT = 10;
    static withCache = true;

    /** @returns {typeof RelationalModel} */
    get Class() {
        return /** @type {typeof RelationalModel} */ (this.constructor);
    }

    /**
     * @param {RelationalModelParams} params
     * @param {Object} _services
     */
    setup(params, _services) {
        this.keepLast = markRaw(new KeepLast({ rejectSuperseded: true }));
        this.countKeepLast = markRaw(new KeepLast({ rejectSuperseded: true }));
        this.mutex = markRaw(new Mutex());

        /** @type {RelationalModelConfig} */
        this.config = {
            isMonoRecord: false,
            context: {},
            fieldsToAggregate: Object.keys(params.config.activeFields),
            .../** @type {Partial<RelationalModelConfig>} */ (params.config),
            isRoot: true,
        };

        this.hooks = {
            lifecycle: { ...DEFAULT_LIFECYCLE_HOOKS, ...params.hooks?.lifecycle },
            ui: { ...DEFAULT_UI_HOOKS, ...params.hooks?.ui },
        };
        /** @type {Map<string, Set<Function>>} */
        this._lifecycleListeners = new Map();

        /** @type {number} */
        this.initialLimit = params.limit || this.Class.DEFAULT_LIMIT;
        this.initialGroupsLimit = params.groupsLimit;
        this.initialCountLimit = params.countLimit || this.Class.DEFAULT_COUNT_LIMIT;
        this.defaultOrderBy = params.defaultOrderBy;
        this.maxGroupByDepth = params.maxGroupByDepth;
        this.groupByInfo = params.groupByInfo || {};
        this.multiEdit = params.multiEdit;
        this.activeIdsLimit = params.activeIdsLimit || Number.MAX_SAFE_INTEGER;
        this.specialDataCaches = markRaw(
            params.state?.specialDataCaches || new SpecialDataCache(),
        );
        this.useSendBeaconToSaveUrgently = params.useSendBeaconToSaveUrgently || false;
        this.withCache = this.Class.withCache && this.env.config?.cache;
        this.initialSampleGroups = undefined;
        this.canUseSampleModel = Boolean(params.canUseSampleModel);

        /** @type {UrgentSaveCoordinator} */
        this.urgentSave = new UrgentSaveCoordinator(this.bus);
        /** @type {(() => void) | null} */
        this._closeUrgentSaveNotification = null;
        /** @type {Deferred | null} */
        this._rootLoadDef = null;

        /** @type {Set<Promise<unknown>>} */
        this._compoundUpdates = new Set();
    }

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

    /** @returns {LifecycleHooks} */
    get lifecycleHooks() {
        return /** @type {{ lifecycle: LifecycleHooks, ui: UIHooks }} */ (this.hooks)
            .lifecycle;
    }

    /** @returns {UIHooks} */
    get uiHooks() {
        return /** @type {{ lifecycle: LifecycleHooks, ui: UIHooks }} */ (this.hooks)
            .ui;
    }

    /**
     * @param {ReturnType<typeof import("@web/core/translation")._t>} message
     * @returns {void}
     */
    displayUrgentSaveNotification(message) {
        this._closeUrgentSaveNotification = this.uiHooks.onDisplayUrgentSave(message);
    }

    /** @returns {void} */
    closeUrgentSaveNotification() {
        if (this._closeUrgentSaveNotification) {
            this._closeUrgentSaveNotification();
        }
    }

    /**
     * @param {import("./record").RelationalRecord} record
     * @param {Object} changes
     * @returns {Promise<any>}
     */
    multiEditDispatch(record, changes) {
        return this.root.multiSaveLocked(record, changes);
    }

    /**
     * @override
     * @type {Model["load"]}
     */
    async load(params = {}) {
        modelLog("load", this.config.resModel, params);
        log.pipeline("load", () => ({
            resModel: this.config.resModel,
            params,
            isReady: this.isReady,
        }));
        const endLoad = log.perf(`load ${this.config.resModel}`);
        if (this.orm.isSample && this.initialSampleGroups?.length) {
            this.orm.setGroups(this.initialSampleGroups);
        }
        const config = this._getNextConfig(this.config, params);
        if (!this.isReady) {
            this.root = this._createEmptyRoot(config);
            this.config = config;
        }
        this.notifyLifecycleSync("onWillLoadRoot", config);
        const rootLoadDef = new Deferred();
        this._retireRootLoadDef();
        this._rootLoadDef = rootLoadDef;
        const cache = this._getCacheParams(config, rootLoadDef);
        const profiling = Boolean(odoo.debug);
        if (profiling) {
            performance.mark("model:loadData:start");
        }
        /** @type {any} */
        let data;
        const loadAbort = new AbortController();
        try {
            data = await this.keepLast.add(
                this._loadData(config, cache, loadAbort.signal),
                { abort: () => loadAbort.abort() },
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                endLoad({ superseded: true });
                return;
            }
            this._retireRootLoadDef();
            endLoad({ failed: true });
            throw error;
        }
        if (profiling) {
            performance.measure("model:loadData", "model:loadData:start");
        }
        this.root = this._createRoot(config, data, { previousRoot: this.root });
        endLoad({
            loadId: config.loadId,
            records: data?.records?.length ?? data?.groups?.length ?? (data ? 1 : 0),
            grouped: Boolean(config.groupBy?.length),
        });
        rootLoadDef.resolve({ root: this.root, loadId: config.loadId });
        if (this._rootLoadDef === rootLoadDef) {
            this._rootLoadDef = null;
        }
        this.config = config;
        if (!this.isReady) {
            this.isReady = true;
        }
        await this.notifyLifecycle("onRootLoaded", this.root);
    }

    /**
     * @param {keyof LifecycleHooks} name
     * @param {Function} listener
     * @returns {() => void}
     */
    subscribeLifecycle(name, listener) {
        if (!(name in DEFAULT_LIFECYCLE_HOOKS)) {
            throw new Error(
                `RelationalModel.subscribeLifecycle: unknown lifecycle "${name}". ` +
                    `Known: ${Object.keys(DEFAULT_LIFECYCLE_HOOKS).join(", ")}.`,
            );
        }
        let listeners = this._lifecycleListeners.get(name);
        if (!listeners) {
            listeners = new Set();
            this._lifecycleListeners.set(name, listeners);
        }
        listeners.add(listener);
        return () => {
            listeners.delete(listener);
            if (!listeners.size) {
                this._lifecycleListeners.delete(name);
            }
        };
    }

    /**
     * @param {keyof LifecycleHooks} name
     * @param {...any} args
     * @returns {Promise<any>}
     */
    async notifyLifecycle(name, ...args) {
        const hook = /** @type {(...a: any[]) => any} */ (this.lifecycleHooks[name]);
        const result = await hook(...args);
        const listeners = this._lifecycleListeners.get(name);
        if (listeners?.size) {
            await this._runLifecycleListeners([...listeners], args);
        }
        return result;
    }

    /**
     * @param {keyof LifecycleHooks} name
     * @param {...any} args
     * @returns {any}
     */
    notifyLifecycleSync(name, ...args) {
        const hook = /** @type {(...a: any[]) => any} */ (this.lifecycleHooks[name]);
        const result = hook(...args);
        const listeners = this._lifecycleListeners.get(name);
        if (listeners?.size) {
            this._runLifecycleListeners([...listeners], args).catch(reportUncaught);
        }
        return result;
    }

    /** @returns {boolean} */
    get hasOnRecordChangedHook() {
        return (
            this.lifecycleHooks.onRecordChanged !==
                DEFAULT_LIFECYCLE_HOOKS.onRecordChanged ||
            Boolean(this._lifecycleListeners.get("onRecordChanged")?.size)
        );
    }

    /**
     * @param {Function[]} listeners
     * @param {any[]} args
     * @returns {Promise<void>}
     */
    async _runLifecycleListeners(listeners, args) {
        for (const listener of listeners) {
            await listener(...args);
        }
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {string} propertyFullName
     */
    async _getPropertyDefinition(config, propertyFullName) {
        await addPropertyFieldDef(
            this.orm,
            config.resModel,
            config.context,
            config.fields,
            propertyFullName,
        );
    }

    /**
     * @template T
     * @param {() => Promise<T>} fn
     * @returns {Promise<T>}
     */
    trackCompoundUpdate(fn) {
        const prom = Promise.resolve().then(fn);
        this._compoundUpdates.add(prom);
        const forget = () => this._compoundUpdates.delete(prom);
        prom.then(forget, forget);
        return prom;
    }

    /**
     * @override
     * @returns {Promise<void> | void}
     */
    settleBeforeReload() {
        if (this.mutex.locked || this._compoundUpdates.size) {
            return this.askChanges();
        }
    }

    async askChanges() {
        for (let round = 0; round < ASK_CHANGES_MAX_ROUNDS; round++) {
            const proms = [];
            this.bus.trigger(ModelEvent.NEED_LOCAL_CHANGES, { proms });
            const compound = [...(this._compoundUpdates ?? [])].map((p) =>
                p.catch(() => {}),
            );
            await Promise.all([...proms, ...compound, this.mutex.getUnlockedDef()]);
            if (!this._compoundUpdates.size) {
                return;
            }
        }
        console.warn(
            `RelationalModel.askChanges: local changes did not settle after ` +
                `${ASK_CHANGES_MAX_ROUNDS} rounds (resModel: ${this.config.resModel}); ` +
                `${this._compoundUpdates.size} compound update(s) still in flight. ` +
                `A field widget is very likely re-opening one from a render side ` +
                `effect — see trackCompoundUpdate(). Proceeding unsettled.`,
        );
    }

    /**
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
     * @param {{ previousRoot?: any }} [options]
     * @returns {any}
     */
    _createRoot(config, data, { previousRoot } = {}) {
        if (config.isMonoRecord) {
            return new this.Class.Record(this, config, data);
        }
        // sample rows carry made-up ids that a real load's ids collide with,
        // so a root built on either side of the sample ORM donates nothing
        const isSample = Boolean(this.orm.isSample);
        const donor =
            isSample || previousRoot?._loadedFromSample ? undefined : previousRoot;
        const root = config.groupBy.length
            ? new this.Class.DynamicGroupList(this, config, data, {
                  previousRoot: donor,
              })
            : new this.Class.DynamicRecordList(this, config, data, {
                  previousRoot: donor,
              });
        root._loadedFromSample = isSample;
        return root;
    }

    _retireRootLoadDef() {
        if (this._rootLoadDef) {
            this._rootLoadDef.resolve(null);
            this._rootLoadDef = null;
        }
    }

    /**
     * @param {Object} [cache]
     * @param {AbortSignal} [signal]
     * @returns {import("@web/core/network/orm_service").ORM}
     */
    _scopedOrm(cache, signal) {
        let orm = this.orm;
        if (cache) {
            orm = orm.cache(cache);
        }
        if (signal) {
            orm = orm.withSignal(signal);
        }
        return orm;
    }

    _getCacheParams(config, rootLoadDef) {
        if (!this.withCache) {
            return;
        }
        const currentResId = config.resId;
        if (
            !this.isReady ||
            (config.isMonoRecord &&
                (this.root.config.resId !== config.resId || !config.resId))
        ) {
            return {
                type: "disk",
                update: "always",
                callback: (result, hasChanged) =>
                    this._applyBackgroundRefresh(result, hasChanged, {
                        rootLoadDef,
                        currentResId,
                    }),
            };
        }
    }

    /**
     * @param {any} result
     * @param {boolean} hasChanged
     * @param {{ rootLoadDef: Promise<any>, currentResId: any }} ctx
     */
    async _applyBackgroundRefresh(result, hasChanged, { rootLoadDef, currentResId }) {
        if (!hasChanged) {
            return;
        }
        const loaded = await rootLoadDef;
        if (!loaded) {
            return;
        }
        const { root, loadId } = loaded;
        if (root.config.isMonoRecord && currentResId !== root.config.resId) {
            return;
        }
        if (root.id !== this.root.id) {
            if (this.useSampleModel) {
                this.useSampleModel = false;
                if (this.root.config.groupBy.length) {
                    delete this.root.config.currentGroups;
                    result = await this._postprocessReadGroup(this.root.config, result);
                }
                this.root.setData(result);
            }
            return;
        }
        if (loadId !== this.root.config.loadId) {
            return;
        }
        if (root.config.isMonoRecord) {
            if (!root.config.resId) {
                return root.setData(result.value, { keepChanges: true });
            }
            if (!result.length) {
                throw new FetchRecordError([root.config.resId]);
            }
            return root.setData(result[0], { keepChanges: true });
        }
        if (
            root.records.some((r) => r.isInEdition || r.hasPendingChanges || r.selected)
        ) {
            return;
        }
        if (root.config.groupBy.length) {
            delete root.config.currentGroups;
            result = await this._postprocessReadGroup(root.config, result);
        }
        root.setData(result);
    }

    /**
     * @param {RelationalModelConfig} currentConfig
     * @param {Partial<SearchParams>} params
     * @returns {RelationalModelConfig}
     */
    _getNextConfig(currentConfig, params) {
        return computeNextConfig(currentConfig, params, {
            maxGroupByDepth: this.maxGroupByDepth,
            defaultOrderBy: this.defaultOrderBy,
            hasRoot: Boolean(this.root),
        });
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Object} [cache]
     * @param {AbortSignal} [signal]
     */
    async _loadData(config, cache, signal) {
        config.loadId = getId("load");
        log.pipeline("_loadData", () => ({
            loadId: config.loadId,
            resModel: config.resModel,
            resId: config.resId,
            resIds: config.resIds?.length,
            groupBy: config.groupBy,
            offset: config.offset,
            limit: config.limit,
            domain: config.domain,
        }));
        if (config.isMonoRecord) {
            const evalContext = getSpecEvalContext(config);
            if (!config.resId) {
                return this.loadNewRecord(config, { evalContext, cache, signal });
            }
            const records = await this.loadRecords(config, evalContext, cache, signal);
            return records[0];
        }
        if (config.resIds) {
            Object.assign(config, {
                limit: config.limit || this.initialLimit,
                offset: config.offset || 0,
            });
            const resIds = config.resIds.slice(
                config.offset,
                config.offset + config.limit,
            );
            const records = await this.loadRecords(
                { ...config, resIds },
                getSpecEvalContext(config),
                cache,
                signal,
            );
            return { records, length: config.resIds.length };
        }
        if (config.groupBy.length) {
            return this.loadGroupedList(config, cache, signal);
        }
        Object.assign(config, {
            limit: config.limit || this.initialLimit,
            countLimit:
                "countLimit" in config ? config.countLimit : this.initialCountLimit,
            offset: config.offset || 0,
        });
        if (config.countLimit !== Number.MAX_SAFE_INTEGER) {
            config.countLimit = Math.max(
                config.countLimit,
                config.offset + config.limit,
            );
        }
        const { records, length } = await this._loadUngroupedList(
            config,
            cache,
            signal,
        );
        if (config.offset && !records.length) {
            config.offset = 0;
            return this._loadData(config, cache, signal);
        }
        return { records, length };
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Object} [cache]
     * @param {AbortSignal} [signal]
     */
    async loadGroupedList(config, cache, signal) {
        config.offset = config.offset || 0;
        config.limit = config.limit || this.initialGroupsLimit;
        if (!config.limit) {
            config.limit = config.openGroupsByDefault
                ? this.Class.DEFAULT_OPEN_GROUP_LIMIT
                : this.Class.DEFAULT_GROUP_LIMIT;
        }
        config.groups = config.groups || {};

        const response = await this.webReadGroup(config, cache, signal);
        return this._postprocessReadGroup(config, response);
    }

    async _postprocessReadGroup(config, response) {
        return postprocessReadGroup(config, response, {
            getPropertyDefinition: (cfg, propertyFullName) =>
                this._getPropertyDefinition(cfg, propertyFullName),
            groupByInfo: this.groupByInfo,
            initialLimit: this.initialLimit,
            initialGroupsLimit: this.initialGroupsLimit,
            defaultGroupLimit: this.Class.DEFAULT_GROUP_LIMIT,
        });
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {OnChangeParams} [params={}]
     * @returns {Promise<Record<string, any>>}
     */
    async loadNewRecord(config, params = {}) {
        return this.onchange(config, params);
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Context} [evalContext]
     * @param {Object} [cache]
     * @param {AbortSignal} [signal]
     */
    async loadRecords(config, evalContext = getSpecEvalContext(config), cache, signal) {
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
            const orm = this._scopedOrm(cache, signal);
            const endRead = log.perf(`webRead ${resModel}`);
            const records = await orm.webRead(resModel, resIds, kwargs);
            endRead({
                ids: resIds.length,
                fields: Object.keys(fieldSpec).length,
                records: records.length,
            });
            if (!records.length) {
                throw new FetchRecordError(resIds);
            }

            return records;
        } else {
            return resIds.map((resId) => ({ id: resId }));
        }
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Object} [cache]
     * @param {AbortSignal} [signal]
     * @returns {Promise<{ records: any[]; length: number }>}
     */
    async _loadUngroupedList(config, cache, signal) {
        const orderBy = config.orderBy.filter((o) => o.name !== "__count");
        let order = orderByToString(orderBy);
        if (config.isGroupList && order && !orderBy.some((o) => o.name === "id")) {
            order += ", id ASC";
        }
        const kwargs = {
            specification: getFieldsSpec(
                config.activeFields,
                config.fields,
                getSpecEvalContext(config),
            ),
            offset: config.offset,
            order,
            limit: config.limit,
            context: { bin_size: true, ...config.context },
            count_limit:
                config.countLimit !== Number.MAX_SAFE_INTEGER
                    ? config.countLimit + 1
                    : undefined,
        };
        const orm = this._scopedOrm(cache, signal);
        return orm.webSearchRead(config.resModel, config.domain, kwargs);
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {OnChangeParams} params
     * @returns {Promise<Record<string, unknown>>}
     */
    async onchange(
        config,
        {
            changes = {},
            fieldNames = [],
            evalContext = getSpecEvalContext(config),
            onError,
            cache,
            signal,
        },
    ) {
        if (!this.isAlive()) {
            return {};
        }
        const { fields, activeFields, resModel, resId } = config;
        let context = config.context;
        if (fieldNames.length === 1) {
            const fieldContext = config.activeFields[fieldNames[0]].context;
            context = makeContext([context, fieldContext], evalContext);
        }
        const spec = getFieldsSpec(activeFields, fields, evalContext, {
            withInvisible: true,
        });
        const args = [resId ? [resId] : [], changes, fieldNames, spec];
        let response;
        const endOnchange = log.perf(`onchange ${resModel}`);
        try {
            const orm = this._scopedOrm(cache, signal);
            response = await orm.call(resModel, "onchange", args, { context });
            endOnchange({
                fieldNames,
                resId,
                changed: Object.keys(response.value || {}).length,
                warning: Boolean(response.warning),
            });
        } catch (e) {
            endOnchange({ failed: true });
            if (onError) {
                return void onError(e);
            }
            throw e;
        }
        if (response.warning) {
            Promise.resolve(
                this.notifyLifecycle("onWillDisplayOnchangeWarning", response.warning),
            )
                .then(() => {
                    this.uiHooks.onDisplayOnchangeWarning(response.warning);
                })
                .catch((error) => console.error(error));
        }
        return response.value;
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Partial<RelationalModelConfig>} patch
     */
    patchConfig(config, patch) {
        const tmpConfig = { ...config, ...patch };
        markRaw(tmpConfig.activeFields);
        markRaw(tmpConfig.fields);
        Object.assign(config, tmpConfig);
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Partial<RelationalModelConfig>} patch
     * @param {{
     * commit?: (data: Record<string, unknown>) => unknown;
     * }} [options]
     */
    async reloadWithConfig(config, patch, { commit } = {}) {
        log.pipeline("reloadWithConfig", () => ({
            resModel: config.resModel,
            isRoot: config.isRoot,
            patch: Object.keys(patch),
        }));
        const tmpConfig = { ...config, ...patch };
        if (tmpConfig.groups) {
            tmpConfig.groups = cloneGroupTree(tmpConfig.groups);
        }
        markRaw(tmpConfig.activeFields);
        markRaw(tmpConfig.fields);
        if (tmpConfig.isRoot) {
            this.notifyLifecycleSync("onWillLoadRoot", tmpConfig);
        }
        const data = await this._loadData(tmpConfig);
        this.patchConfig(config, tmpConfig);
        if (data && commit) {
            commit(data);
        }
        if (config.isRoot) {
            await this.notifyLifecycle("onRootLoaded", this.root);
        }
    }

    /**
     * @param {RelationalModelConfig} config
     * @returns {Promise<number>}
     */
    async fetchExactCount(config) {
        const count = await this.countKeepLast.add(
            this.orm.searchCount(config.resModel, config.domain, {
                context: config.context,
            }),
        );
        config.countLimit = Number.MAX_SAFE_INTEGER;
        return count;
    }

    /**
     * @returns {RelationalRecord[]} the records a reloaded one may be a second
     * copy of: only a grouped root shows one record in several groups
     */
    similarRecordCandidates() {
        if (this.config.isMonoRecord || !this.config.groupBy.length) {
            return [];
        }
        return this.root.records;
    }

    /**
     * @param {RelationalRecord} reloadedRecord
     * @param {Record<string, unknown>} serverValues
     * @param {RelationalRecord[]} [siblings]
     */
    updateSimilarRecords(
        reloadedRecord,
        serverValues,
        siblings = this.similarRecordCandidates(),
    ) {
        for (const record of siblings) {
            if (record === reloadedRecord) {
                continue;
            }
            if (record.resId === reloadedRecord.resId) {
                record.applyValues(serverValues);
            }
        }
    }

    /**
     * @param {RelationalModelConfig} config
     * @param {Object} cache
     * @param {AbortSignal} [signal]
     * @returns {Promise<{ groups: any[]; length: number }>}
     */
    async webReadGroup(config, cache, signal) {
        const { aggregates, params } = getWebReadGroupParams(config, {
            groupByInfo: this.groupByInfo,
            initialLimit: this.initialLimit,
        });
        const orm = this._scopedOrm(cache, signal);
        const endGroup = log.perf(`webReadGroup ${config.resModel}`);
        const result = await orm.webReadGroup(
            config.resModel,
            config.domain,
            config.groupBy,
            aggregates,
            params,
        );
        endGroup({
            groupBy: config.groupBy,
            groups: result.groups.length,
            length: result.length,
        });
        if (this.canUseSampleModel && !this.initialSampleGroups) {
            this.initialSampleGroups = deepCopy(
                result.groups.map((group) =>
                    "__records" in group ? { ...group, __records: [] } : group,
                ),
            );
        }
        return result;
    }
}
