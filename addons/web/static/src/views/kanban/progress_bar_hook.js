/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { extractInfoFromGroupData } from "@web/model/relational_model/utils";

const FALSE = Symbol("False");

/**
 *
 * @param {*} groups: returned by web_read_group
 * @param {*} groupByField
 * @param {*} value
 * @returns
 */

function _findGroup(groups, groupByField, value) {
    return groups.find((g) => g[groupByField.name] === value) || {};
}

function _createFilterDomain(fieldName, bars, value) {
    let filterDomain = undefined;
    if (value === FALSE) {
        const keys = bars.filter((x) => x.value !== FALSE).map((x) => x.value);
        filterDomain = ["!", [fieldName, "in", keys]];
    } else {
        filterDomain = [[fieldName, "=", value]];
    }
    return filterDomain;
}

function _groupsToAggregateValues(groups, groupBy, fields) {
    const groupByFieldName = groupBy[0].split(":")[0];
    return groups.map((g) => {
        const groupInfo = extractInfoFromGroupData(g, groupBy, fields);
        return Object.assign(groupInfo.aggregates, { [groupByFieldName]: groupInfo.serverValue });
    });
}

class ProgressBarState {
    constructor(progressAttributes, model, aggregateFields, activeBars = {}) {
        this.progressAttributes = progressAttributes;
        this.model = model;
        this._groupsInfo = {};
        this._aggregateFields = aggregateFields;
        this.activeBars = activeBars;
        this._aggregateValues = [];
        this._pbCounts = null;
    }

    getGroupInfo(group) {
        if (!this._groupsInfo[group.id]) {
            const aggValues = _findGroup(
                this._aggregateValues,
                group.groupByField,
                group.serverValue
            );
            const index = this._aggregateValues.indexOf(aggValues);
            if (index > -1) {
                this._aggregateValues.splice(index, 1);
            }
            this._aggregateValues.push({
                ...group.aggregates,
                [group.groupByField.name]: group.serverValue,
            });
            let groupValue = group.displayName || group.value;
            if (groupValue === true) {
                groupValue = "True";
            } else if (groupValue === false) {
                groupValue = "False";
            }
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
                count: group.count - bars.map((r) => r.count).reduce((a, b) => a + b, 0),
                value: FALSE,
                string: _t("Other"),
                color: "200",
            });

            // Update activeBars count and aggreagates
            if (this.activeBars[group.serverValue]) {
                this.activeBars[group.serverValue].count = bars.find(
                    (x) => x.value === this.activeBars[group.serverValue].value
                ).count;

                if (this.activeBars[group.serverValue].count === 0) {
                    group.applyFilter(undefined).then(() => {
                        delete this.activeBars[group.serverValue];
                        group.model.notify();
                    });
                }

                if (this._aggregateFields.length) {
                    //recompute the aggregates is not necessary
                    //the web_read_group was already done with the correct domain (containing the applied filter)
                    this.activeBars[group.serverValue].aggregates = _findGroup(
                        this._aggregateValues,
                        group.groupByField,
                        group.serverValue
                    );
                }
            }

            const self = this;
            const progressBar = {
                get activeBar() {
                    return self.activeBars[group.serverValue]?.value || null;
                },
                bars,
            };

            this._groupsInfo[group.id] = progressBar;
        }
        return this._groupsInfo[group.id];
    }

    getAggregateValue(group, aggregateField) {
        const title = aggregateField ? aggregateField.string : _t("Count");
        let value = 0;
        if (!this.activeBars[group.serverValue]) {
            value = group.count;
            if (aggregateField) {
                value =
                    _findGroup(this._aggregateValues, group.groupByField, group.serverValue)[
                        aggregateField.name
                    ] || 0;
            }
        } else {
            value = this.activeBars[group.serverValue].count;
            if (aggregateField) {
                value =
                    (this.activeBars[group.serverValue]?.aggregates &&
                        this.activeBars[group.serverValue]?.aggregates[aggregateField.name]) ||
                    0;
            }
        }
        return { title, value };
    }

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
            nextActiveBar.value
        );
        const proms = [];
        proms.push(
            group.applyFilter(filterDomain).then((res) => {
                const groupInfo = this.getGroupInfo(group);
                nextActiveBar.count = groupInfo.bars.find(
                    (x) => x.value === nextActiveBar.value
                ).count;
            })
        );
        if (this._aggregateFields.length) {
            proms.push(this._updateAggregateGroup(group, bars, nextActiveBar));
        }
        await Promise.all(proms);
        this.activeBars[group.serverValue] = nextActiveBar;
    }

    _updateAggregateGroup(group, bars, activeBar) {
        const filterDomain = _createFilterDomain(
            this.progressAttributes.fieldName,
            bars,
            activeBar.value
        );
        const { context, fields, groupBy, resModel } = this.model.root;
        const kwargs = { context };
        const fieldNames = [...this._aggregateFields.map((f) => f.name), group.groupByField.name];
        const domain = filterDomain
            ? Domain.and([group.groupDomain, filterDomain]).toList()
            : group.groupDomain;
        return this.model.orm
            .webReadGroup(resModel, domain, fieldNames, groupBy, kwargs)
            .then((res) => {
                if (res.length) {
                    const groupByField = group.groupByField;
                    const aggrValues = _groupsToAggregateValues(res.groups, groupBy, fields);
                    activeBar.aggregates = _findGroup(aggrValues, groupByField, group.serverValue);
                }
            });
    }

    updateCounts(group) {
        this._updateProgressBar();
        if (this._aggregateFields.length) {
            this._updateAggregates();
            this.updateAggreagteGroup(group);
        }

        // If the selected bar is empty, remove the selection
        for (const group of this.model.root.groups) {
            if (this.activeBars[group.serverValue] && group.list.count === 0) {
                this.selectBar(group.id, { value: null });
            }
        }
    }

    updateAggreagteGroup(group) {
        if (group && this.activeBars[group.serverValue]) {
            const { bars } = this.getGroupInfo(group);
            this._updateAggregateGroup(group, bars, this.activeBars[group.serverValue]);
        }
    }

    async _updateAggregates() {
        const { context, fields, groupBy, domain, resModel } = this.model.root;
        const fieldsName = this._aggregateFields.map((f) => f.name);
        const firstGroupByName = groupBy[0].split(":")[0];
        const kwargs = { context };
        const res = await this.model.orm.webReadGroup(
            resModel,
            domain,
            [...fieldsName, firstGroupByName],
            groupBy,
            kwargs
        );
        this._aggregateValues = _groupsToAggregateValues(res.groups, groupBy, fields);
    }

    async _updateProgressBar() {
        const groupBy = this.model.root.groupBy;
        const defaultGroupBy = this.model.root.defaultGroupBy;
        if (groupBy.length || defaultGroupBy) {
            const resModel = this.model.root.resModel;
            const domain = this.model.root.domain;
            const context = this.model.root.context;
            const { colors, fieldName: field, help } = this.progressAttributes;
            const groupsId = this.model.root.groups.map((g) => g.id).join();
            const res = await this.model.orm.call(resModel, "read_progress_bar", [], {
                domain,
                group_by: groupBy.length ? groupBy[0] : defaultGroupBy,
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
                    let groupValue = group.displayName || group.value;
                    if (groupValue === true) {
                        groupValue = "True";
                    } else if (groupValue === false) {
                        groupValue = "False";
                    }
                    const counts = res[groupValue];
                    for (const bar of groupInfo.bars) {
                        bar.count = (counts && counts[bar.value]) || 0;
                    }
                    groupInfo.bars.find((b) => b.value === FALSE).count = counts
                        ? group.count - Object.values(counts).reduce((a, b) => a + b, 0)
                        : group.count;

                    if (this.activeBars[group.serverValue]) {
                        this.activeBars[group.serverValue].count = groupInfo.bars.find(
                            (x) => x.value === this.activeBars[group.serverValue].value
                        ).count;
                    }
                }
            }
        }
    }

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

    getGroupCount(group) {
        const progressBarInfo = this.getGroupInfo(group);
        if (progressBarInfo.activeBar) {
            const progressBar = progressBarInfo.bars.find(
                (b) => b.value === progressBarInfo.activeBar
            );
            return progressBar.count;
        }
    }
}

export function useProgressBar(progressAttributes, model, aggregateFields, activeBars) {
    const progressBarState = reactive(
        new ProgressBarState(progressAttributes, model, aggregateFields, activeBars)
    );

    let prom;
    const onWillLoadRoot = model.hooks.onWillLoadRoot;
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
    model.hooks.onRootLoaded = async () => {
        await onRootLoaded();
        return prom;
    };

    return progressBarState;
}
