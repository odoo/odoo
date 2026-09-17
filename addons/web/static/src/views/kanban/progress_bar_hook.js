// @ts-check
/** @odoo-module native */

import { onWillDestroy, reactive } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { reportUncaught } from "@web/core/errors/error_utils";
import { _t } from "@web/core/translation";
import { KeepLast, KeepLastByKey, SupersededError } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import {
    extractAggregatesFromGroupData,
    getAggregateSpecifications,
} from "@web/model/relational_model";

/** @import { Group } from "@web/model/relational_model/group" */
const FALSE = Symbol("False");

const MOVE_RECONCILE_DELAY = 300;

/**
 * @template T
 * @param {() => Promise<T>} load
 * @returns {Promise<T | undefined>}
 */
async function latestOnly(load) {
    try {
        return await load();
    } catch (error) {
        if (error instanceof SupersededError) {
            return undefined;
        }
        throw error;
    }
}

/** @type {{ activeBar: string | null, bars: Object[], total: number, isReady: boolean }} */
const EMPTY_GROUP_INFO = Object.freeze({
    activeBar: null,
    bars: [],
    total: 0,
    isReady: false,
});

/**
 * @param {*} serverValue
 * @returns {string}
 */
function groupKey(serverValue) {
    return JSON.stringify(serverValue ?? false);
}

/**
 * @param {string} fieldName
 * @param {Object[]} bars
 * @param {*} value
 * @returns {Array}
 */
function _createFilterDomain(fieldName, bars, value) {
    let filterDomain;
    if (value === FALSE) {
        const keys = bars.filter((x) => x.value !== FALSE).map((x) => x.value);
        filterDomain = ["!", [fieldName, "in", keys]];
    } else {
        filterDomain = [[fieldName, "=", value]];
    }
    return filterDomain;
}

/**
 * @param {Object[]} groups
 * @param {string[]} groupBy
 * @param {Object} fields
 * @returns {Map<string, Object>}
 */
function _groupsToAggregatesByKey(groups, groupBy, fields) {
    return new Map(
        groups.map((g) => {
            const { aggregates, serverValue } = extractAggregatesFromGroupData(
                g,
                groupBy,
                fields,
            );
            return [groupKey(serverValue), aggregates];
        }),
    );
}

class ProgressBarState {
    /**
     * @param {Object} progressAttributes
     * @param {Object} model
     * @param {Object[]} aggregateFields
     * @param {Object} [activeBars={}]
     */
    constructor(progressAttributes, model, aggregateFields, activeBars = {}) {
        this.progressAttributes = progressAttributes;
        this.model = model;
        this._groupsInfo = {};
        this._aggregateFields = aggregateFields;
        /** @type {Record<string, Object>} */
        this.activeBars = activeBars;
        /** @type {Map<string, Object>} */
        this._aggregatesByKey = new Map();
        this._pbCounts = null;
        /** @type {KeepLast<any>} */
        this._pbLoads = new KeepLast({ rejectSuperseded: true });
        /** @type {KeepLast<any>} */
        this._aggLoads = new KeepLast({ rejectSuperseded: true });
        /** @type {KeepLastByKey<any>} */
        this._groupAggLoads = new KeepLastByKey({ rejectSuperseded: true });
        this._pendingBarDeselections = new Set();
        this._recordMoves = new Map();
        this._isDestroyed = false;
    }

    _destroy() {
        this._isDestroyed = true;
        this._pbLoads.cancel();
        this._aggLoads.cancel();
        this._groupAggLoads.cancel();
        this._moveReconcileDebounced?.cancel();
        this._membershipRetryDebounced?.cancel();
    }

    /**
     * @param {Group} group
     * @returns {{ activeBar: string | null, bars: Object[], total: number, isReady: boolean }}
     */
    getGroupInfo(group) {
        if (this._pbCounts === null) {
            return EMPTY_GROUP_INFO;
        }
        if (!this._groupsInfo[group.id]) {
            this._initGroupInfo(group);
        }
        return this._groupsInfo[group.id];
    }

    _initAllGroups() {
        if (this._pbCounts === null) {
            return;
        }
        for (const group of this.model.root.groups || []) {
            if (!this._groupsInfo[group.id]) {
                this._initGroupInfo(group);
            }
        }
    }

    /** @param {Group} group */
    _initGroupInfo(group) {
        const key = groupKey(group.serverValue);
        this._aggregatesByKey.set(key, { ...group.aggregates });
        const pbCount = this._pbCounts[this._pbCountKey(group)];
        const { fieldName, colors } = this.progressAttributes;
        const { selection: fieldSelection } = this.model.root.fields[fieldName];
        const selection = fieldSelection && Object.fromEntries(fieldSelection);
        const bars = Object.entries(colors).map(([value, color]) => ({
            count: (pbCount && pbCount[value]) || 0,
            value,
            string: selection ? selection[value] : String(value),
            color,
        }));
        bars.push({
            count: 0,
            value: /** @type {any} */ (FALSE),
            string: _t("Other"),
            color: "200",
        });

        const activeBar = this.activeBars[key];
        if (activeBar && this._aggregateFields.length) {
            activeBar.aggregates = this._aggregatesByKey.get(key);
        }

        this._groupsInfo[group.id] = {
            activeBar: this.activeBars[key]?.value || null,
            bars,
            total: 0,
            isReady: true,
        };
        this._recomputeTotals(group);
    }

    /** @param {Group} group */
    _recomputeTotals(group) {
        const groupInfo = this._groupsInfo[group.id];
        if (!groupInfo) {
            return;
        }
        const coloredCount = groupInfo.bars
            .filter((/** @type {any} */ bar) => bar.value !== FALSE)
            .reduce(
                (/** @type {any} */ sum, /** @type {any} */ bar) => sum + bar.count,
                0,
            );
        const otherBar = groupInfo.bars.find(
            (/** @type {any} */ bar) => bar.value === FALSE,
        );
        if (otherBar) {
            otherBar.count = Math.max(0, (group.count ?? 0) - coloredCount);
        }
        groupInfo.total = groupInfo.bars.reduce(
            (/** @type {any} */ sum, /** @type {any} */ bar) => sum + bar.count,
            0,
        );
        const activeBar = this.activeBars[groupKey(group.serverValue)];
        if (activeBar) {
            activeBar.count =
                groupInfo.bars.find(
                    (/** @type {any} */ bar) => bar.value === activeBar.value,
                )?.count ?? 0;
        }
        this._syncActiveBar(group);
    }

    /** @param {Group} group */
    _syncActiveBar(group) {
        const groupInfo = this._groupsInfo[group.id];
        if (!groupInfo) {
            return;
        }
        const value = this.activeBars[groupKey(group.serverValue)]?.value || null;
        if (groupInfo.activeBar !== value) {
            groupInfo.activeBar = value;
        }
    }

    /**
     * @param {Group} group
     * @param {Object} aggregateField
     * @returns {{ title: string, value: number, currencies?: Array }}
     */
    getAggregateValue(group, aggregateField) {
        const key = groupKey(group.serverValue);
        const activeBar = this.activeBars[key];
        const title = aggregateField ? aggregateField.string : _t("Count");
        let value;
        if (!activeBar) {
            value = group.count;
            if (value && aggregateField) {
                value = this._aggregatesByKey.get(key)?.[aggregateField.name];
            }
        } else {
            value = activeBar.count;
            if (value && aggregateField) {
                value = activeBar.aggregates?.[aggregateField.name];
            }
        }
        value ||= 0;
        if (
            aggregateField &&
            aggregateField.type === "monetary" &&
            aggregateField.currency_field
        ) {
            const currencies =
                this._aggregatesByKey.get(key)?.[aggregateField.currency_field];
            if (currencies?.length > 1) {
                return {
                    title,
                    value,
                    currencies,
                };
            }
            if (currencies?.[0]) {
                return {
                    title,
                    value,
                    currencies: [currencies[0]],
                };
            }
        }
        return { title, value };
    }

    /**
     * @param {string} groupId
     * @param {{ value: * }} bar
     */
    async selectBar(groupId, bar) {
        if (this._isDestroyed) {
            return;
        }
        const group = this.model.root.groups.find(
            (/** @type {any} */ group) => group.id === groupId,
        );
        const progressBar = this.getGroupInfo(group);
        const nextActiveBar = {};
        const key = groupKey(group.serverValue);
        if (bar.value && this.activeBars[key]?.value !== bar.value) {
            nextActiveBar.value = bar.value;
        } else {
            await group.applyFilter(undefined);
            if (this._isDestroyed) {
                return;
            }
            delete this.activeBars[key];
            this._syncActiveBar(group);
            group.model.notify();
            return;
        }
        const { bars } = progressBar;
        const filterDomain = _createFilterDomain(
            this.progressAttributes.fieldName,
            bars,
            nextActiveBar.value,
        );
        const proms = [];
        proms.push(
            group.applyFilter(filterDomain).then(() => {
                if (this._isDestroyed) {
                    return;
                }
                const groupInfo = this.getGroupInfo(group);
                nextActiveBar.count =
                    groupInfo.bars.find((x) => x.value === nextActiveBar.value)
                        ?.count ?? 0;
            }),
        );
        if (this._aggregateFields.length) {
            proms.push(this._updateAggregateGroup(group, bars, nextActiveBar));
        }
        await Promise.all(proms);
        if (this._isDestroyed) {
            return;
        }
        this.activeBars[key] = nextActiveBar;
        this._syncActiveBar(group);
        this.updateCounts(group);
    }

    /**
     * @param {Group} group
     * @param {Object[]} bars
     * @param {Object} activeBar
     * @returns {Promise<void>}
     */
    async _updateAggregateGroup(group, bars, activeBar) {
        const key = groupKey(group.serverValue);
        const filterDomain = _createFilterDomain(
            this.progressAttributes.fieldName,
            bars,
            activeBar.value,
        );
        const { context, fields, groupBy, resModel } = this.model.root;
        const kwargs = { context };
        const aggregateSpecs = getAggregateSpecifications(this._aggregateFields);
        const domain = filterDomain
            ? Domain.and([group.groupDomain, filterDomain]).toList()
            : group.groupDomain;
        const groups = await latestOnly(() =>
            this._groupAggLoads.add(
                key,
                this.model.orm.formattedReadGroup(
                    resModel,
                    domain,
                    groupBy,
                    aggregateSpecs,
                    kwargs,
                ),
            ),
        );
        if (!groups || this._isDestroyed) {
            return;
        }
        if (groups.length) {
            activeBar.aggregates =
                _groupsToAggregatesByKey(groups, groupBy, fields).get(key) || {};
        }
    }

    /**
     * @param {Group} group
     * @param {Object} [record]
     */
    updateCounts(group, record) {
        if (this._isDestroyed) {
            return;
        }
        const move = record && this._recordMoves.get(record.id);
        if (move) {
            this._recordMoves.delete(record.id);
        }
        if (!(move && this._reconcileMove(record, move))) {
            this._updateProgressBar().catch(reportUncaught);
            if (this._aggregateFields.length) {
                this._updateAggregates().catch(reportUncaught);
                this.updateAggregateGroup(group);
            }
        }

        this._deselectActiveBars((group) => group.list.count === 0);
    }

    /** @param {(group: Group, activeBar: Object) => boolean} shouldDeselect */
    _deselectActiveBars(shouldDeselect) {
        for (const group of this.model.root.groups || []) {
            const key = groupKey(group.serverValue);
            const activeBar = this.activeBars[key];
            if (
                !activeBar ||
                this._pendingBarDeselections.has(key) ||
                !shouldDeselect(group, activeBar)
            ) {
                continue;
            }
            this._pendingBarDeselections.add(key);
            this.selectBar(group.id, { value: null })
                .catch(reportUncaught)
                .finally(() => this._pendingBarDeselections.delete(key));
        }
    }

    /**
     * @param {string} recordId
     * @param {string} sourceGroupId
     * @param {string} targetGroupId
     */
    registerRecordMove(recordId, sourceGroupId, targetGroupId) {
        if (this._recordMoves.has(recordId)) {
            return;
        }
        const groups = this.model.root.groups || [];
        const sourceGroup = groups.find(
            (/** @type {any} */ g) => g.id === sourceGroupId,
        );
        const record = sourceGroup?.list.records.find(
            (/** @type {any} */ r) => r.id === recordId,
        );
        this._recordMoves.set(recordId, {
            sourceGroupId,
            targetGroupId,
            sourceValue: record?.data[this.progressAttributes.fieldName],
        });
    }

    /** @param {string} recordId */
    cancelRecordMove(recordId) {
        this._recordMoves.delete(recordId);
    }

    /**
     * @param {Object} record
     * @param {Object} move
     * @returns {boolean}
     */
    _reconcileMove(record, move) {
        const groups = this.model.root.groups || [];
        const sourceGroup = groups.find(
            (/** @type {any} */ g) => g.id === move.sourceGroupId,
        );
        const targetGroup = groups.find(
            (/** @type {any} */ g) => g.id === move.targetGroupId,
        );
        const { fieldName } = this.progressAttributes;
        if (
            this._pbCounts === null ||
            !sourceGroup ||
            !targetGroup ||
            !(fieldName in record.data) ||
            fieldName === this.model.root.groupByField.name
        ) {
            return false;
        }
        this._pbLoads.cancel();
        this._applyMoveDelta(sourceGroup, move.sourceValue, -1);
        this._applyMoveDelta(targetGroup, record.data[fieldName], +1);
        if (this._aggregateFields.length) {
            this._updateAggregatesForGroups([sourceGroup, targetGroup]).catch(
                reportUncaught,
            );
            this.updateAggregateGroup(sourceGroup);
            this.updateAggregateGroup(targetGroup);
        }
        this._scheduleMoveReconcile();
        return true;
    }

    /**
     * @param {Group} group
     * @param {*} value
     * @param {number} delta
     */
    _applyMoveDelta(group, value, delta) {
        const { colors } = this.progressAttributes;
        const bucket = Object.keys(colors).find((key) => key === String(value));
        if (bucket) {
            const counts = (this._pbCounts[this._pbCountKey(group)] ||= {});
            counts[bucket] = Math.max(0, (counts[bucket] || 0) + delta);
        }
        const groupInfo = this._groupsInfo[group.id];
        if (!groupInfo) {
            return;
        }
        if (bucket) {
            const bar = groupInfo.bars.find(
                (/** @type {any} */ b) => b.value === bucket,
            );
            if (bar) {
                bar.count = Math.max(0, bar.count + delta);
            }
        }
        this._recomputeTotals(group);
    }

    /**
     * @param {Group[]} groupsToUpdate
     * @returns {Promise<void>}
     */
    async _updateAggregatesForGroups(groupsToUpdate) {
        const { context, fields, groupBy, resModel } = this.model.root;
        const domain = Domain.or(groupsToUpdate.map((g) => g.groupDomain)).toList();
        const groups = await latestOnly(() =>
            this._aggLoads.add(
                this.model.orm.formattedReadGroup(
                    resModel,
                    domain,
                    groupBy,
                    getAggregateSpecifications(this._aggregateFields),
                    { context },
                ),
            ),
        );
        if (!groups || this._isDestroyed) {
            return;
        }
        const aggregatesByKey = _groupsToAggregatesByKey(groups, groupBy, fields);
        for (const group of groupsToUpdate) {
            const key = groupKey(group.serverValue);
            this._aggregatesByKey.set(key, aggregatesByKey.get(key) || {});
        }
    }

    _scheduleMoveReconcile() {
        if (!this._moveReconcileDebounced) {
            this._moveReconcileDebounced = debounce(() => {
                this._updateProgressBar().catch(reportUncaught);
                if (this._aggregateFields.length) {
                    this._updateAggregates().catch(reportUncaught);
                    for (const group of this.model.root.groups || []) {
                        this.updateAggregateGroup(group);
                    }
                }
            }, MOVE_RECONCILE_DELAY);
        }
        this._moveReconcileDebounced();
    }

    _scheduleMembershipRetry() {
        if (!this._membershipRetryDebounced) {
            this._membershipRetryDebounced = debounce(() => {
                this._updateProgressBar().catch(reportUncaught);
            }, MOVE_RECONCILE_DELAY);
        }
        this._membershipRetryDebounced();
    }

    /** @param {Group} group */
    updateAggregateGroup(group) {
        const activeBar = group && this.activeBars[groupKey(group.serverValue)];
        if (activeBar) {
            const { bars } = this.getGroupInfo(group);
            this._updateAggregateGroup(group, bars, activeBar).catch(reportUncaught);
        }
    }

    async _updateAggregates() {
        const { context, fields, groupBy, domain, resModel } = this.model.root;
        const kwargs = { context };
        const groups = await latestOnly(() =>
            this._aggLoads.add(
                this.model.orm.formattedReadGroup(
                    resModel,
                    domain,
                    groupBy,
                    getAggregateSpecifications(this._aggregateFields),
                    kwargs,
                ),
            ),
        );
        if (!groups || this._isDestroyed) {
            return;
        }
        this._aggregatesByKey = _groupsToAggregatesByKey(groups, groupBy, fields);
    }

    /**
     * @param {{ context: Object, domain: Array, groupBy: string[], resModel: string }} params
     * @returns {Promise<Object>}
     */
    _fetchProgressBarCounts({ context, domain, groupBy, resModel }) {
        const { colors, fieldName: field, help } = this.progressAttributes;
        return this.model.orm.call(resModel, "read_progress_bar", [], {
            domain,
            group_by: groupBy[0],
            progress_bar: { colors, field, help },
            context,
        });
    }

    async _updateProgressBar() {
        const { context, domain, groupBy, resModel } = this.model.root;
        if (groupBy.length) {
            const groupIds = new Set(
                this.model.root.groups.map((/** @type {any} */ g) => g.id),
            );
            const res = await latestOnly(() =>
                this._pbLoads.add(
                    this._fetchProgressBarCounts({
                        context,
                        domain,
                        groupBy,
                        resModel,
                    }),
                ),
            );
            if (!res || this._isDestroyed) {
                return;
            }
            const currentIds = this.model.root.groups.map(
                (/** @type {any} */ g) => g.id,
            );
            if (
                currentIds.length !== groupIds.size ||
                currentIds.some((/** @type {any} */ id) => !groupIds.has(id))
            ) {
                this._scheduleMembershipRetry();
                return;
            }
            this._pbCounts = res;
            this._refreshBars();
        }
    }

    _refreshBars() {
        if (this._pbCounts === null) {
            return;
        }
        for (const group of this.model.root.groups || []) {
            if (group.isFolded) {
                continue;
            }
            const groupInfo = this.getGroupInfo(group);
            const counts = this._pbCounts[this._pbCountKey(group)];
            for (const bar of groupInfo.bars) {
                if (bar.value !== FALSE) {
                    bar.count = (counts && counts[bar.value]) || 0;
                }
            }
            this._recomputeTotals(group);
        }
        this._deselectEmptyActiveBars();
    }

    _deselectEmptyActiveBars() {
        if (this._pbCounts === null) {
            return;
        }
        this._deselectActiveBars(
            (group, activeBar) =>
                !group.isFolded &&
                (this.getGroupInfo(group).bars.find((x) => x.value === activeBar.value)
                    ?.count || 0) === 0,
        );
    }

    /** @param {{ context: Object, domain: Array, groupBy: string[], resModel: string }} params */
    async loadProgressBar({ context, domain, groupBy, resModel }) {
        if (groupBy.length) {
            const res = await latestOnly(() =>
                this._pbLoads.add(
                    this._fetchProgressBarCounts({
                        context,
                        domain,
                        groupBy,
                        resModel,
                    }),
                ),
            );
            if (!res || this._isDestroyed) {
                return;
            }
            this._pbCounts = res;
        } else {
            // The root is about to become ungrouped: it will have no `groups` at
            // all, so counts harvested for the previous group-by must not survive.
            this._pbCounts = null;
        }
    }

    /**
     * @param {Group} group
     * @returns {number | undefined}
     */
    getGroupCount(group) {
        const progressBarInfo = this.getGroupInfo(group);
        if (progressBarInfo.activeBar) {
            return progressBarInfo.bars.find(
                (b) => b.value === progressBarInfo.activeBar,
            )?.count;
        }
    }

    _removeStaleGroupsInfo() {
        const groupIds = new Set(
            (this.model.root.groups || []).map((/** @type {any} */ group) => group.id),
        );
        for (const id of Object.keys(this._groupsInfo)) {
            if (!groupIds.has(id)) {
                delete this._groupsInfo[id];
            }
        }
    }

    /** @param {Group} group */
    _pbCountKey(group) {
        if (group.value === true) {
            return "True";
        } else if (group.value === false) {
            return "False";
        }
        return group.serverValue;
    }
}

/**
 * @param {Object} progressAttributes
 * @param {Object} model
 * @param {Object[]} aggregateFields
 * @param {Object} [activeBars]
 * @returns {ProgressBarState}
 */
export function useProgressBar(progressAttributes, model, aggregateFields, activeBars) {
    const progressBarState = reactive(
        new ProgressBarState(progressAttributes, model, aggregateFields, activeBars),
    );

    let prom;
    const unsubscribe = [
        model.subscribeLifecycle("onWillLoadRoot", (/** @type {any} */ config) => {
            prom = progressBarState.loadProgressBar({
                context: config.context,
                domain: config.domain,
                groupBy: config.groupBy,
                resModel: config.resModel,
            });
        }),
        model.subscribeLifecycle("onRootLoaded", async () => {
            progressBarState._removeStaleGroupsInfo();
            try {
                await prom;
            } catch (error) {
                if (!progressBarState._isDestroyed) {
                    reportUncaught(error);
                }
                return;
            }
            if (progressBarState._isDestroyed) {
                return;
            }
            progressBarState._initAllGroups();
            if (model.isReady) {
                progressBarState._refreshBars();
            } else {
                progressBarState._deselectEmptyActiveBars();
            }
        }),
    ];
    onWillDestroy(() => {
        progressBarState._destroy();
        unsubscribe.forEach((stop) => stop());
    });

    return progressBarState;
}
