/** @odoo-module **/

import { onWillStart, onWillUpdateProps, reactive, useComponent } from "@odoo/owl";
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
                return s[groupByField.name][0] === value;
            } else {
                return s[groupByField.name] === value;
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
                !Object.keys(_findGroup(this._aggregateValues, group.groupByField, group.value))
                    .length
            ) {
                this._aggregateValues.push({
                    ...group.aggregates,
                    [group.groupByField.name]: group.value,
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

            if (
                this.activeBars[group.value] &&
                bars.find((b) => b.value === this.activeBars[group.value].value).count === 0
            ) {
                group.applyFilter(undefined).then(() => {
                    delete this.activeBars[group.value];
                    group.model.notify();
                });
            }

            const self = this;
            const progressBar = {
                get activeBar() {
                    return self.activeBars[group.value]?.value || null;
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
        if (!this.activeBars[group.value]) {
            value = group.count;
            if (aggregateField) {
                value =
                    _findGroup(this._aggregateValues, group.groupByField, group.value)[
                        aggregateField.name
                    ] || 0;
            }
        } else {
            value = this.activeBars[group.value].count;
            if (aggregateField) {
                value =
                    (this.activeBars[group.value]?.aggregates &&
                        this.activeBars[group.value]?.aggregates[aggregateField.name]) ||
                    0;
            }
        }
        return { title, value };
    }

    async selectBar(groupId, bar) {
        const group = this.model.root.groups.find((group) => group.id === groupId);
        const progressBar = this._groupsInfo[groupId];
        const nextActiveBar = {};
        if (bar.value && this.activeBars[group.value]?.value !== bar.value) {
            nextActiveBar.value = bar.value;
        } else {
            group.applyFilter(undefined).then(() => {
                delete this.activeBars[group.value];
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
                const groupInfo = this._groupsInfo[group.id];
                nextActiveBar.count = groupInfo.bars.find(
                    (x) => x.value === nextActiveBar.value
                ).count;
            })
        );
        if (this._aggregateFields.length) {
            proms.push(this._updateAggregateGroup(group, nextActiveBar));
        }
        await Promise.all(proms);
        this.activeBars[group.value] = nextActiveBar;
    }

    _updateAggregateGroup(group, activeBar) {
        const groupInfo = this._groupsInfo[group.id];
        const filterDomain = _createFilterDomain(
            this.progressAttributes.fieldName,
            groupInfo.bars,
            activeBar.value
        );
        const { context, groupBy, resModel } = this.model.root;
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
                    const resGroup = _findGroup(res.groups, group.groupByField, group.value);
                    activeBar.aggregates = {
                        ...resGroup,
                        [group.groupByField.name]: group.value,
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
            if (this.activeBars[group.value] && group.list.count === 0) {
                this.selectBar(group.id, { value: null });
            }
        }
    }

    updateAggreagteGroup(group) {
        if (group && this.activeBars[group.value]) {
            this._updateAggregateGroup(group, this.activeBars[group.value]);
        }
    }

    async updateCountsArchive(group) {
        const groupInfo = this._groupsInfo[group.id];
        for (const bar of groupInfo.bars) {
            bar.count = 0;
        }
        if (this._aggregateFields.length) {
            const key = Object.keys(this._aggregateValues).find(
                (key) => this._aggregateValues[key][group.groupByField.name] === group.value
            );
            for (const sumField of this._aggregateFields) {
                this._aggregateValues[key][sumField.name] = 0;
            }
        }
        if (this.activeBars[group.value] && group.list.count === 0) {
            // If the selected bar is empty, remove the selection
            this.selectBar(group.id, { value: null });
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
        this._aggregateValues = res.groups;
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
                    const groupInfo = this._groupsInfo[group.id];
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

                    if (this.activeBars[group.value]) {
                        this.activeBars[group.value].count = groupInfo.bars.find(
                            (x) => x.value === this.activeBars[group.value].value
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
            this._pbCounts = res;
        }
    }

    getGroupCount(group) {
        const progressBarInfo = this._groupsInfo[group.id];
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
        return progressBarState.loadProgressBar(nextProps);
    });

    return reactive(progressBarState);
}
