import { reactive } from "@odoo/owl";
import { getCurrency } from "@web/core/currency";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import {
    extractInfoFromGroupData,
    getAggregateSpecifications,
} from "@web/model/relational_model/utils";

const FALSE = Symbol("False");

/**
 *
 * @param {*} groups: returned by formatted_read_group
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

function _groupsToAggregateValues(groups, groupBy, fields, domain) {
    const groupByFieldName = groupBy[0].split(":")[0];
    return groups.map((g) => {
        const groupInfo = extractInfoFromGroupData(g, groupBy, fields, domain);
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
                    //the formatted_read_group was already done with the correct domain (containing the applied filter)
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
            if (value && aggregateField) {
                value = _findGroup(this._aggregateValues, group.groupByField, group.serverValue)[
                    aggregateField.name
                ];
            }
        } else {
            value = this.activeBars[group.serverValue].count;
            if (value && aggregateField) {
                value =
                    this.activeBars[group.serverValue]?.aggregates &&
                    this.activeBars[group.serverValue]?.aggregates[aggregateField.name];
            }
        }
        value ??= false;
        if (value && aggregateField.type === "monetary" && aggregateField.currency_field) {
            const currencyId = group.aggregates[aggregateField.currency_field][0];
            if (currencyId) {
                return {
                    title,
                    value,
                    currency: getCurrency(currencyId),
                };
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
            proms.push(this._updateAggregatesBars([group], [bars], [nextActiveBar]));
        }
        await Promise.all(proms);
        this.activeBars[group.serverValue] = nextActiveBar;
    }

    _updateAggregatesBars(groups, groupsBars, activeBars) {
        const domain = Domain.or(
            groups.map((group, i) => {
                const bars = groupsBars[i];
                const activeBar = activeBars[i];
                const filterDomain = _createFilterDomain(
                    this.progressAttributes.fieldName,
                    bars,
                    activeBar.value
                );
                return filterDomain
                    ? Domain.and([group.groupDomain, filterDomain]).toList()
                    : group.groupDomain;
            })
        ).toList();

        const { context, fields, groupBy, resModel } = this.model.root;
        const kwargs = { context };
        const aggregateSpecs = getAggregateSpecifications(fields);
        return this.model.orm
            .formattedReadGroup(resModel, domain, groupBy, aggregateSpecs, kwargs)
            .then((resGroups) => {
                const aggrValues = _groupsToAggregateValues(resGroups, groupBy, fields, domain);
                for (const resGroup of resGroups) {
                    const rawValue = Array.isArray(resGroup[groupBy])
                        ? resGroup[groupBy][0]
                        : resGroup[groupBy];
                    const i = groups.findIndex((g) => g.serverValue === rawValue);
                    activeBars[i].aggregates = _findGroup(
                        aggrValues,
                        groups[i].groupByField,
                        groups[i].serverValue
                    );
                }
            });
    }

    updateCounts(groupsToReload) {
        this._updateProgressBars(groupsToReload);
        if (this._aggregateFields.length) {
            // Update aggregates without taking in account the bar selection
            this._updateAggregates(groupsToReload);

            const updateAggregatesGroups = [];
            const updateAggregatesGroupsBars = [];
            const updateAggregatesActiveBars = [];
            for (const group in groupsToReload) {
                if (this.activeBars[group.serverValue]) {
                    updateAggregatesGroups.push(group);
                    updateAggregatesGroupsBars.push(this.getGroupInfo(group).bars);
                    updateAggregatesActiveBars.push(this.activeBars[group.serverValue]);
                }
            }
            if (updateAggregatesGroups.length > 0) {
                this._updateAggregatesBars(
                    updateAggregatesGroups,
                    updateAggregatesGroupsBars,
                    updateAggregatesActiveBars
                );
            }
        }

        // If the selected bar is empty, remove the selection
        for (const group of this.model.root.groups) {
            if (this.activeBars[group.serverValue] && group.list.count === 0) {
                this.selectBar(group.id, { value: null });
            }
        }
    }

    async _updateAggregates(groupsToReload) {
        const { context, fields, groupBy, resModel } = this.model.root;
        const kwargs = { context };
        const groupsDomain = Domain.or(groupsToReload.map((g) => g.groupDomain)).toList();
        const groups = await this.model.orm.formattedReadGroup(
            resModel,
            groupsDomain,
            groupBy,
            getAggregateSpecifications(this._aggregateFields),
            kwargs
        );
        const updatedAggregateValues = _groupsToAggregateValues(groups, groupBy, fields);
        const groupByFieldName = groupBy[0].split(":")[0];
        for (const updatedAggregateValue of updatedAggregateValues) {
            const index = this._aggregateValues.findIndex(
                (aggregateValue) =>
                    aggregateValue[groupByFieldName] === updatedAggregateValue[groupByFieldName]
            );
            if (index !== -1) {
                this._aggregateValues[index] = updatedAggregateValue;
            } else {
                this._aggregateValues.push(updatedAggregateValue);
            }
        }
    }

    async _updateProgressBars(groupsToReload) {
        const resModel = this.model.root.resModel;
        const domain = Domain.or(groupsToReload.map((g) => g.groupDomain)).toList();
        const context = this.model.root.context;
        const { colors, fieldName: field, help } = this.progressAttributes;
        const groupsId = this.model.root.groups.map((g) => g.id).join();
        const res = await this.model.orm.call(resModel, "read_progress_bar", [], {
            domain,
            group_by: this.model.root.groupBy[0],
            progress_bar: { colors, field, help },
            context,
        });
        if (groupsId !== this.model.root.groups.map((g) => g.id).join()) {
            return;
        }
        this._pbCounts = Object.assign(this._pbCounts || {}, res);

        const idsReloaded = groupsToReload.map((g) => g.id);
        for (const group of this.model.root.groups) {
            if (group.isFolded || !idsReloaded.includes(group.id)) {
                continue;
            }
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
                    (x) => x.value === this.activeBars[group.serverValue].value
                ).count;
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
    model.hooks.onRootLoaded = async (root) => {
        await onRootLoaded(root);
        return prom;
    };

    return progressBarState;
}
