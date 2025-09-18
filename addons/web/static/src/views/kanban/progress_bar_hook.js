// @ts-check

/** @module @web/views/kanban/progress_bar_hook - Progress bar state computation, active bar filtering, and per-group aggregate tracking for kanban columns */

import { reactive } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import {
    extractInfoFromGroupData,
    getAggregateSpecifications,
} from "@web/model/relational_model/utils";

/** @import { Group } from "@web/model/relational_model/group" */
/** @*/

const FALSE = Symbol("False");

/**
 * Find a group entry matching a specific group-by field value.
 * @param {Object[]} groups - Aggregate group data from formatted_read_group.
 * @param {Object} groupByField - Field descriptor with a `name` property.
 * @param {*} value - The group value to match.
 * @returns {Object} The matching group entry, or an empty object.
 */
function _findGroup(groups, groupByField, value) {
    return groups.find((g) => g[groupByField.name] === value) || {};
}

/**
 * Build a domain filter for a selected progress bar segment.
 * @param {string} fieldName - The progress bar field name.
 * @param {Object[]} bars - All bar segments (including the "Other" sentinel).
 * @param {*} value - The selected bar value, or FALSE symbol for "Other".
 * @returns {Array} An Odoo domain expression.
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
 * Convert raw formatted_read_group results into aggregate value maps.
 * @param {Object[]} groups - Raw group data from formatted_read_group.
 * @param {string[]} groupBy - The group-by specification.
 * @param {Object} fields - Field definitions.
 * @param {Array} [domain] - Optional domain used for the read.
 * @returns {Object[]} Array of aggregate value objects keyed by field name.
 */
function _groupsToAggregateValues(groups, groupBy, fields, domain) {
    const groupByFieldName = groupBy[0].split(":")[0];
    return groups.map((g) => {
        const groupInfo = extractInfoFromGroupData(g, groupBy, fields, domain);
        return Object.assign(groupInfo.aggregates, {
            [groupByFieldName]: groupInfo.serverValue,
        });
    });
}

/**
 * Reactive state manager for kanban column progress bars.
 *
 * Tracks per-group bar segment counts, active bar selection (filtering),
 * and aggregate values. Coordinates with the model to load progress bar
 * data via `read_progress_bar` RPC and refresh counts after record changes.
 */
class ProgressBarState {
    /**
     * @param {Object} progressAttributes - Parsed `<progressbar>` arch config.
     * @param {Object} model - The kanban RelationalModel instance.
     * @param {Object[]} aggregateFields - Fields to compute aggregates for.
     * @param {Object} [activeBars={}] - Restored active bar selections keyed by group serverValue.
     */
    constructor(progressAttributes, model, aggregateFields, activeBars = {}) {
        this.progressAttributes = progressAttributes;
        this.model = model;
        this._groupsInfo = {};
        this._aggregateFields = aggregateFields;
        this.activeBars = activeBars;
        this._aggregateValues = [];
        this._pbCounts = null;
    }

    /**
     * Get or compute progress bar info for a group (bars, active selection, readiness).
     * @param {Group} group - The kanban group datapoint.
     * @returns {{ activeBar: string | null, bars: Object[], isReady: boolean }}
     */
    getGroupInfo(group) {
        if (this._pbCounts === null) {
            // progressbar isn't loaded yet
            return {
                activeBar: null,
                bars: [],
                isReady: false,
            };
        }
        if (!this._groupsInfo[group.id]) {
            const aggValues = _findGroup(
                this._aggregateValues,
                group.groupByField,
                group.serverValue,
            );
            const index = this._aggregateValues.indexOf(aggValues);
            if (index > -1) {
                this._aggregateValues.splice(index, 1);
            }
            this._aggregateValues.push({
                ...group.aggregates,
                [group.groupByField.name]: group.serverValue,
            });
            const groupValue = this._getGroupValue(group);
            const pbCount = this._pbCounts[groupValue];
            const { fieldName, colors } = this.progressAttributes;
            const { selection: fieldSelection } = this.model.root.fields[fieldName];
            const selection = fieldSelection && Object.fromEntries(fieldSelection);
            const bars = Object.entries(colors).map(([value, color]) => {
                let string;
                if (selection) {
                    string = selection[value];
                } else {
                    string = String(value);
                }
                return {
                    count: (pbCount && pbCount[value]) || 0,
                    value,
                    string,
                    color,
                };
            });
            bars.push({
                count:
                    group.count - bars.map((r) => r.count).reduce((a, b) => a + b, 0),
                value: /** @type {any} */ (FALSE),
                string: _t("Other"),
                color: "200",
            });

            // Update activeBars count and aggreagates
            if (this.activeBars[group.serverValue]) {
                this.activeBars[group.serverValue].count = bars.find(
                    (x) => x.value === this.activeBars[group.serverValue].value,
                ).count;

                if (this.activeBars[group.serverValue].count === 0) {
                    group.applyFilter(undefined).then(() => {
                        delete this.activeBars[group.serverValue];
                        group.model.notify();
                    });
                }

                if (this._aggregateFields.length) {
                    //recompute the aggregates is not necessary
                    //the formatted_read_group was already done with the correct domain (containing the applied filter)
                    this.activeBars[group.serverValue].aggregates = _findGroup(
                        this._aggregateValues,
                        group.groupByField,
                        group.serverValue,
                    );
                }
            }

            const self = this;
            const progressBar = {
                get activeBar() {
                    return self.activeBars[group.serverValue]?.value || null;
                },
                bars,
                isReady: true,
            };

            this._groupsInfo[group.id] = progressBar;
        }
        return this._groupsInfo[group.id];
    }

    /**
     * Compute the displayed aggregate value for a group's progress bar header.
     * @param {Group} group - The kanban group datapoint.
     * @param {Object} aggregateField - The sum field definition.
     * @returns {{ title: string, value: number, currencies?: Array }}
     */
    getAggregateValue(group, aggregateField) {
        const { groupByField, serverValue } = group;
        const title = aggregateField ? aggregateField.string : _t("Count");
        let value;
        if (!this.activeBars[serverValue]) {
            value = group.count;
            if (value && aggregateField) {
                value = _findGroup(this._aggregateValues, groupByField, serverValue)[
                    aggregateField.name
                ];
            }
        } else {
            value = this.activeBars[serverValue].count;
            if (value && aggregateField) {
                value =
                    this.activeBars[serverValue]?.aggregates &&
                    this.activeBars[serverValue]?.aggregates[aggregateField.name];
            }
        }
        value ||= 0;
        if (aggregateField.type === "monetary" && aggregateField.currency_field) {
            const aggValues = _findGroup(
                this._aggregateValues,
                groupByField,
                serverValue,
            );
            const currencies = aggValues?.[aggregateField.currency_field];
            if (currencies?.length > 1) {
                return {
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
     * Toggle a progress bar segment selection, filtering the group's records.
     * @param {string} groupId - The group datapoint ID.
     * @param {{ value: * }} bar - The bar segment that was clicked.
     */
    async selectBar(groupId, bar) {
        const group = this.model.root.groups.find((group) => group.id === groupId);
        const progressBar = this.getGroupInfo(group);
        const nextActiveBar = {};
        if (bar.value && this.activeBars[group.serverValue]?.value !== bar.value) {
            nextActiveBar.value = bar.value;
        } else {
            group.applyFilter(undefined).then(() => {
                delete this.activeBars[group.serverValue];
                group.model.notify();
            });
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
            group.applyFilter(filterDomain).then((res) => {
                const groupInfo = this.getGroupInfo(group);
                nextActiveBar.count = groupInfo.bars.find(
                    (x) => x.value === nextActiveBar.value,
                ).count;
            }),
        );
        if (this._aggregateFields.length) {
            proms.push(this._updateAggregateGroup(group, bars, nextActiveBar));
        }
        await Promise.all(proms);
        this.activeBars[group.serverValue] = nextActiveBar;
        this.updateCounts(group);
    }

    /**
     * Re-fetch aggregate values for a single group after bar selection changes.
     * @param {Group} group - The group to update.
     * @param {Object[]} bars - Current bar segments.
     * @param {Object} activeBar - The active bar selection with `value` and `aggregates`.
     * @returns {Promise<void>}
     */
    _updateAggregateGroup(group, bars, activeBar) {
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
        return this.model.orm
            .formattedReadGroup(resModel, domain, groupBy, aggregateSpecs, kwargs)
            .then((groups) => {
                if (groups.length) {
                    const groupByField = group.groupByField;
                    const aggrValues = _groupsToAggregateValues(
                        groups,
                        groupBy,
                        fields,
                        domain,
                    );
                    activeBar.aggregates = _findGroup(
                        aggrValues,
                        groupByField,
                        group.serverValue,
                    );
                }
            });
    }

    /**
     * Refresh all progress bar counts and aggregates after a record change.
     * @param {Group} group - The group where the change occurred.
     */
    updateCounts(group) {
        this._updateProgressBar();
        if (this._aggregateFields.length) {
            this._updateAggregates();
            this.updateAggregateGroup(group);
        }

        // If the selected bar is empty, remove the selection
        for (const group of this.model.root.groups) {
            if (this.activeBars[group.serverValue] && group.list.count === 0) {
                this.selectBar(group.id, { value: null });
            }
        }
    }

    /**
     * Re-fetch aggregates for a group if it has an active bar selection.
     * @param {Group} group - The group to update.
     */
    updateAggregateGroup(group) {
        if (group && this.activeBars[group.serverValue]) {
            const { bars } = this.getGroupInfo(group);
            this._updateAggregateGroup(group, bars, this.activeBars[group.serverValue]);
        }
    }

    /** Re-fetch aggregate values for all groups from the server. */
    async _updateAggregates() {
        const { context, fields, groupBy, domain, resModel } = this.model.root;
        const kwargs = { context };
        const groups = await this.model.orm.formattedReadGroup(
            resModel,
            domain,
            groupBy,
            getAggregateSpecifications(this._aggregateFields),
            kwargs,
        );
        this._aggregateValues = _groupsToAggregateValues(groups, groupBy, fields);
    }

    /** Re-fetch progress bar segment counts for all groups via `read_progress_bar`. */
    async _updateProgressBar() {
        const groupBy = this.model.root.groupBy;
        if (groupBy.length) {
            const resModel = this.model.root.resModel;
            const domain = this.model.root.domain;
            const context = this.model.root.context;
            const { colors, fieldName: field, help } = this.progressAttributes;
            const groupsId = this.model.root.groups.map((g) => g.id).join();
            const res = await this.model.orm.call(resModel, "read_progress_bar", [], {
                domain,
                group_by: groupBy[0],
                progress_bar: { colors, field, help },
                context,
            });
            if (groupsId !== this.model.root.groups.map((g) => g.id).join()) {
                return;
            }
            this._pbCounts = res;
            for (const group of this.model.root.groups) {
                if (!group.isFolded) {
                    const groupInfo = this.getGroupInfo(group);
                    const groupValue = this._getGroupValue(group);
                    const counts = res[groupValue];
                    for (const bar of groupInfo.bars) {
                        bar.count = (counts && counts[bar.value]) || 0;
                    }
                    groupInfo.bars.find((b) => b.value === FALSE).count = counts
                        ? group.count - Object.values(counts).reduce((a, b) => a + b, 0)
                        : group.count;

                    if (this.activeBars[group.serverValue]) {
                        this.activeBars[group.serverValue].count = groupInfo.bars.find(
                            (x) => x.value === this.activeBars[group.serverValue].value,
                        ).count;
                    }
                }
            }
        }
    }

    /**
     * Initial load of progress bar data. Called during model root loading.
     * @param {{ context: Object, domain: Array, groupBy: string[], resModel: string }} params
     */
    async loadProgressBar({ context, domain, groupBy, resModel }) {
        if (groupBy.length) {
            const { colors, fieldName: field, help } = this.progressAttributes;
            const res = await this.model.orm.call(resModel, "read_progress_bar", [], {
                domain,
                group_by: groupBy[0],
                progress_bar: { colors, field, help },
                context,
            });
            this._pbCounts = res;
        }
    }

    /**
     * Get the filtered record count for a group with an active bar.
     * @param {Group} group
     * @returns {number | undefined} Count if a bar is active, undefined otherwise.
     */
    getGroupCount(group) {
        const progressBarInfo = this.getGroupInfo(group);
        if (progressBarInfo.activeBar) {
            const progressBar = progressBarInfo.bars.find(
                (b) => b.value === progressBarInfo.activeBar,
            );
            return progressBar.count;
        }
    }

    /**
     * We must be able to match groups returned by the read_progress_bar call with groups previously
     * returned by formatted_read_group. When grouped on date(time) fields, the key of each group is the
     * displayName of the period (e.g. "W8 2024"). When grouped on boolean fields, it's "True" and
     * "False". For falsy values (e.g. unset many2one), it's "False". In all other cases, it's the
     * group's value (e.g. the id for a many2one).
     *
     * @param {Group} group
     * @return string
     */
    _getGroupValue(group) {
        if (group.value === true) {
            return "True";
        } else if (group.value === false) {
            return "False";
        }
        return group.serverValue;
    }
}

/**
 * OWL composition hook that creates and wires a reactive ProgressBarState.
 *
 * Intercepts the model's `onWillLoadRoot` and `onRootLoaded` hooks to
 * trigger parallel progress bar data loading alongside the main data fetch.
 * On first load, the progress bar loads asynchronously (non-blocking) so
 * the kanban view appears as fast as possible.
 *
 * @param {Object} progressAttributes - Parsed `<progressbar>` arch config.
 * @param {Object} model - The kanban RelationalModel instance.
 * @param {Object[]} aggregateFields - Fields to compute aggregates for.
 * @param {Object} [activeBars] - Restored active bar state from a previous session.
 * @returns {ProgressBarState} Reactive progress bar state.
 */
export function useProgressBar(progressAttributes, model, aggregateFields, activeBars) {
    const progressBarState = reactive(
        new ProgressBarState(progressAttributes, model, aggregateFields, activeBars),
    );

    const onWillLoadRoot = model.hooks.onWillLoadRoot;
    let prom;
    model.hooks.onWillLoadRoot = (config) => {
        onWillLoadRoot();
        prom = progressBarState.loadProgressBar({
            context: config.context,
            domain: config.domain,
            groupBy: config.groupBy,
            resModel: config.resModel,
        });
    };
    const onRootLoaded = model.hooks.onRootLoaded;
    model.hooks.onRootLoaded = async (root) => {
        await onRootLoaded(root);
        if (model.isReady) {
            // do not wait for the progressbar on first load, to show the kanban view asap
            return prom;
        }
    };

    return progressBarState;
}
