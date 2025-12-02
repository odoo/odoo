import { reactive } from "@odoo/owl";
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
                isReady: true,
            };

            this._groupsInfo[group.id] = progressBar;
        }
        return this._groupsInfo[group.id];
    }

    getAggregateValue(group, aggregateField) {
        const { groupByField, serverValue } = group;
        const title = aggregateField ? aggregateField.string : _t("Count");
        let value = 0;
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
            const aggValues = _findGroup(this._aggregateValues, groupByField, serverValue);
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
        this.updateCounts(group);
    }

    _updateAggregateGroup(group, bars, activeBar) {
        const filterDomain = _createFilterDomain(
            this.progressAttributes.fieldName,
            bars,
            activeBar.value
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
                    const aggrValues = _groupsToAggregateValues(groups, groupBy, fields, domain);
                    activeBar.aggregates = _findGroup(aggrValues, groupByField, group.serverValue);
                }
            });
    }

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

    updateAggregateGroup(group) {
        if (group && this.activeBars[group.serverValue]) {
            const { bars } = this.getGroupInfo(group);
            this._updateAggregateGroup(group, bars, this.activeBars[group.serverValue]);
        }
    }

    async _updateAggregates() {
        const { context, fields, groupBy, domain, resModel } = this.model.root;
        const kwargs = { context };
        const groups = await this.model.orm.formattedReadGroup(
            resModel,
            domain,
            groupBy,
            getAggregateSpecifications(this._aggregateFields),
            kwargs
        );
        this._aggregateValues = _groupsToAggregateValues(groups, groupBy, fields);
    }

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
