/** @odoo-module **/

import { onWillStart, onWillUpdateProps, reactive, toRaw, useComponent } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
const FALSE = Symbol("False");

/**
 *
 * @param {*} groups: returned by web_read_group
 * @param {*} groupByField
 * @param {*} value
 * @returns
 */

function _findGroup(groups, groupByField, value) {
    return (
        groups.find((s) => {
            if (Array.isArray(s[groupByField.name])) {
                return s[groupByField.name][0] === value[0];
            } else {
                return toRaw(s[groupByField.name]) === value;
            }
        }) || {}
    );
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

function _groupsToAggregateValues(groups, groupBy) {
    const groupByFieldName = groupBy.split(":")[0];
    return groups.map((r) => {
        return { ...r, [groupByFieldName]: r[groupBy] };
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
            if (
                !Object.keys(
                    _findGroup(this._aggregateValues, group.groupByField, group.__rawValue)
                ).length
            ) {
                this._aggregateValues.push({
                    ...group.aggregates,
                    [group.groupByField.name]: group.__rawValue,
                });
            }
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
            if (this.activeBars[group.__rawValue]) {
                this.activeBars[group.__rawValue].count = bars.find(
                    (x) => x.value === this.activeBars[group.__rawValue].value
                ).count;

                if (this.activeBars[group.__rawValue].count === 0) {
                    group.applyFilter(undefined).then(() => {
                        delete this.activeBars[group.__rawValue];
                        group.model.notify();
                    });
                }

                if (this._aggregateFields.length) {
                    //recompute the aggregates is not necessary
                    //the web_read_group was already done with the correct domain (containing the applied filter)
                    this.activeBars[group.__rawValue].aggregates = _findGroup(
                        this._aggregateValues,
                        group.groupByField,
                        group.__rawValue
                    );
                }
            }

            const self = this;
            const progressBar = {
                get activeBar() {
                    return self.activeBars[group.__rawValue]?.value || null;
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
        if (!this.activeBars[group.__rawValue]) {
            value = group.count;
            if (aggregateField) {
                value =
                    _findGroup(this._aggregateValues, group.groupByField, group.__rawValue)[
                        aggregateField.name
                    ] || 0;
            }
        } else {
            value = this.activeBars[group.__rawValue].count;
            if (aggregateField) {
                value =
                    (this.activeBars[group.__rawValue]?.aggregates &&
                        this.activeBars[group.__rawValue]?.aggregates[aggregateField.name]) ||
                    0;
            }
        }
        return { title, value };
    }

    async selectBar(groupId, bar) {
        const group = this.model.root.groups.find((group) => group.id === groupId);
        const progressBar = this.getGroupInfo(group);
        const nextActiveBar = {};
        if (bar.value && this.activeBars[group.__rawValue]?.value !== bar.value) {
            nextActiveBar.value = bar.value;
        } else {
            group.applyFilter(undefined).then(() => {
                delete this.activeBars[group.__rawValue];
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
        this.activeBars[group.__rawValue] = nextActiveBar;
    }

    _updateAggregateGroup(group, bars, activeBar) {
        const filterDomain = _createFilterDomain(
            this.progressAttributes.fieldName,
            bars,
            activeBar.value
        );
        const { context, groupBy, resModel, firstGroupBy } = this.model.root;
        const kwargs = { context };
        const fieldNames = this._aggregateFields.map((f) => f.name);
        const fields = [...fieldNames, group.groupByField.name];
        const domain = filterDomain
            ? Domain.and([group.groupDomain, filterDomain]).toList()
            : group.groupDomain;
        return this.model.orm
            .webReadGroup(resModel, domain, fields, groupBy, kwargs)
            .then((res) => {
                if (res.length) {
                    const groupByField = group.groupByField;
                    const aggregateValues = _groupsToAggregateValues(res.groups, firstGroupBy);
                    const resGroup = _findGroup(aggregateValues, groupByField, group.__rawValue);
                    activeBar.aggregates = {
                        ...resGroup,
                        [groupByField.name]: group.__rawValue,
                    };
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
            if (this.activeBars[group.__rawValue] && group.list.count === 0) {
                this.selectBar(group.id, { value: null });
            }
        }
    }

    updateAggreagteGroup(group) {
        if (group && this.activeBars[group.__rawValue]) {
            const { bars } = this.getGroupInfo(group);
            this._updateAggregateGroup(group, bars, this.activeBars[group.__rawValue]);
        }
    }

    async _updateAggregates() {
        const { context, groupBy, domain, resModel, firstGroupBy } = this.model.root;
        const fieldsName = this._aggregateFields.map((f) => f.name);
        const firstGroupByName = firstGroupBy.split(":")[0];
        const kwargs = { context };
        const res = await this.model.orm.webReadGroup(
            resModel,
            domain,
            [...fieldsName, firstGroupByName],
            groupBy,
            kwargs
        );
        this._aggregateValues = _groupsToAggregateValues(res.groups, firstGroupBy);
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

                    if (this.activeBars[group.__rawValue]) {
                        this.activeBars[group.__rawValue].count = groupInfo.bars.find(
                            (x) => x.value === this.activeBars[group.__rawValue].value
                        ).count;
                    }
                }
            }
        }
    }

    async loadProgressBar(props = {}) {
        const groupBy = props.groupBy || this.model.root.groupBy;
        const defaultGroupBy =
            props.defaultGroupBy || (this.model.root && this.model.root.defaultGroupBy);
        if (groupBy.length || defaultGroupBy) {
            const resModel = props.resModel || this.model.root.resModel;
            const domain = props.domain || this.model.root.domain;
            const context = props.context || this.model.root.context;
            const { colors, fieldName: field, help } = this.progressAttributes;
            const res = await this.model.orm.call(resModel, "read_progress_bar", [], {
                domain,
                group_by: groupBy.length ? groupBy[0] : defaultGroupBy,
                progress_bar: { colors, field, help },
                context,
            });
            this._groupsInfo = {};
            this._aggregateValues = [];
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
    const component = useComponent();

    const progressBarState = new ProgressBarState(
        progressAttributes,
        model,
        aggregateFields,
        activeBars
    );

    // FIXME: maybe this can be do directly on the readGroup
    onWillStart(() => {
        return progressBarState.loadProgressBar(component.props);
    });
    onWillUpdateProps((nextProps) => {
        progressBarState.loadProgressBar(nextProps);
    });

    return reactive(progressBarState);
}
