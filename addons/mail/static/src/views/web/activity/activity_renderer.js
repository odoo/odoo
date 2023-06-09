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
            planned: {
                color: "success",
                value: 0,
            },
            today: {
                color: "warning",
                value: 0,
            },
            overdue: {
                value: 0,
                color: "danger",
            },
        };
        const typeId = group[0];
        const isColumnFiltered = this.activeFilter.activityTypeId === group[0];
        const progressValue = isColumnFiltered ? this.activeFilter.progressValue : { active: null };

        let totalCount = 0;
        for (const activities of Object.values(this.props.groupedActivities)) {
            if (typeId in activities) {
                types[activities[typeId].state].value += 1;
                totalCount++;
            }
        }

        const progressBar = {
            bars: [],
        };
        for (const [value, count] of Object.entries(types)) {
            progressBar.bars.push({
                count: count.value,
                value,
                string: this.props.fields.activity_state.selection.find((e) => e[0] === value)[1],
                color: count.color,
            });
        }

        return {
            aggregate: {
                title: group[1],
                value: isColumnFiltered ? types[progressValue.active].value : totalCount,
            },
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
