/* @odoo-module */

import { ActivityCell } from "@mail/views/web/activity/activity_cell";
import { ActivityRecord } from "@mail/views/web/activity/activity_record";

import { Component, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ColumnProgress } from "@web/views/view_components/column_progress";

export class ActivityRenderer extends Component {
    static components = {
        ActivityCell,
        ActivityRecord,
        ColumnProgress,
        Dropdown,
        DropdownItem,
        CheckBox,
    };
    static props = {
        activityTypes: { type: Array },
        activityResIds: { type: Array },
        fields: { type: Object },
        resModel: { type: String },
        records: { type: Array },
        archInfo: { type: Object },
        groupedActivities: { type: Object },
        scheduleActivity: { type: Function },
        onReloadData: { type: Function },
        onEmptyCell: { type: Function },
        onSendMailTemplate: { type: Function },
        openRecord: { type: Function },
    };
    static template = "mail.ActivityRenderer";

    setup() {
        this.activeFilter = useState({
            progressValue: {
                active: null,
            },
            activityTypeId: null,
            resIds: [],
        });

        this.storageKey = ["activity_columns", this.props.resModel, this.env.config.viewId];
        this.setupStorageActiveColumns();
    }

    /**
     * Gets all activity resIds in the view.
     *
     * @returns filtered resIds first then the rest.
     */
    get activityResIds() {
        return [...this.props.activityResIds].sort((a) =>
            this.activeFilter.resIds.includes(a) ? -1 : 0
        );
    }

    getGroupInfo(group) {
        const types = {
            done: {
                inProgressBar: false,
                value: 0,
            },
            planned: {
                color: "success",
                inProgressBar: true,
                value: 0,
            },
            today: {
                color: "warning",
                inProgressBar: true,
                value: 0,
            },
            overdue: {
                color: "danger",
                inProgressBar: true,
                value: 0,
            },
        };
        for (const [type, label] of this.props.fields.activity_state.selection) {
            types[type].label = label;
        }
        const typeId = group[0];
        const isColumnFiltered = this.activeFilter.activityTypeId === group[0];
        const progressValue = isColumnFiltered ? this.activeFilter.progressValue : { active: null };

        let totalCount = 0;
        for (const activities of Object.values(this.props.groupedActivities)) {
            if (typeId in activities) {
                types[activities[typeId].state].value += activities[typeId].count;
                totalCount++;
            }
        }

        const progressBar = {
            bars: [],
            activeBar: isColumnFiltered ? this.activeFilter.progressValue.active : null,
        };
        for (const [value, count] of Object.entries(types)) {
            if (count.inProgressBar) {
                progressBar.bars.push({
                    count: count.value,
                    value,
                    string: types[value].label,
                    color: count.color,
                });
            }
        }

        const plannedAndDoneCount = types.planned.value + types.done.value;
        const aggregatedOn = plannedAndDoneCount ? {
            title: `${types.planned.label} + ${types.done.label}`,
            value: types.planned.value + types.done.value,
        } : undefined;
        return {
            aggregate: {
                title: types.planned.label,
                value: isColumnFiltered ? types[progressValue.active].value : types.planned.value,
            },
            aggregateOn: aggregatedOn,
            data: {
                count: totalCount,
                filterProgressValue: (name) => this.onSetProgressBarState(typeId, name),
                progressBar,
                progressValue,
            },
        };
    }

    getRecord(resId) {
        return this.props.records.find((r) => r.resId === resId);
    }

    onSetProgressBarState(typeId, bar) {
        const name = bar.value;
        if (this.activeFilter.progressValue.active === name) {
            this.activeFilter.progressValue.active = null;
            this.activeFilter.activityTypeId = null;
            this.activeFilter.resIds = [];
        } else {
            this.activeFilter.progressValue.active = name;
            this.activeFilter.activityTypeId = typeId;
            this.activeFilter.resIds = Object.entries(this.props.groupedActivities)
                .filter(([, resIds]) => typeId in resIds && resIds[typeId].state === name)
                .map(([key]) => parseInt(key));
        }
    }

    get activeColumns() {
        return this.props.activityTypes.filter(
            (activity) => this.storageActiveColumns[activity[0]]
        );
    }

    setupStorageActiveColumns() {
        const storageActiveColumnsList = browser.localStorage.getItem(this.storageKey)?.split(",");

        this.storageActiveColumns = useState({});
        for (const activityType of this.props.activityTypes) {
            if (storageActiveColumnsList) {
                this.storageActiveColumns[activityType[0]] = storageActiveColumnsList.includes(
                    activityType[0].toString()
                );
            } else {
                this.storageActiveColumns[activityType[0]] = true;
            }
        }
    }

    toggleDisplayColumn(typeId) {
        this.storageActiveColumns[typeId] = !this.storageActiveColumns[typeId];
        browser.localStorage.setItem(
            this.storageKey.join(","),
            Object.keys(this.storageActiveColumns).filter(
                (activityType) => this.storageActiveColumns[activityType]
            )
        );
    }
}
