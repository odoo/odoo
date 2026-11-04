import { MailColumnProgress } from "@mail/core/web/mail_column_progress";
import { ActivityCell } from "@mail/views/web/activity/activity_cell";
import { ActivityRecord } from "@mail/views/web/activity/activity_record";

import { Component, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

export class ActivityRenderer extends Component {
    static components = {
        ActivityCell,
        ActivityRecord,
        ColumnProgress: MailColumnProgress,
        Dropdown,
        DropdownItem,
        CheckBox,
    };
    static props = {
        activityTypes: { type: Object },
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
            resIds: new Set(Object.keys(this.props.groupedActivities)),
        });

        this.storageKey = ["activity_columns", this.props.resModel, this.env.config.viewId];
        this.setupStorageActiveColumns();
    }

    getGroupInfo(activityType) {
        const types = {
            done: {
                color: "secondary",
                inProgressBar: false,
                label: _t("done"), // activity_mixin.activity_state has no done state, so we add it manually here
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
        const typeId = activityType.id;
        const isColumnFiltered = this.activeFilter.activityTypeId === activityType.id;
        const progressValue = isColumnFiltered ? this.activeFilter.progressValue : { active: null };

        let totalCountWithoutDone = 0;
        for (const activities of Object.values(this.props.groupedActivities)) {
            if (typeId in activities) {
                for (const [state, stateCount] of Object.entries(
                    activities[typeId].count_by_state
                )) {
                    types[state].value += stateCount;
                    if (state !== "done") {
                        totalCountWithoutDone += stateCount;
                    }
                }
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

        const ongoingActivityCount = types.overdue.value + types.today.value + types.planned.value;
        const ongoingAndDoneCount = ongoingActivityCount + types.done.value;
        const labelAggregate = `${types.overdue.label} + ${types.today.label} + ${types.planned.label}`;
        const aggregateOn =
            ongoingAndDoneCount && this.isTypeDisplayDone(typeId)
                ? {
                      title: `${types.done.label} + ${labelAggregate}`,
                      value: ongoingAndDoneCount,
                  }
                : undefined;
        return {
            aggregate: {
                title: labelAggregate,
                value: isColumnFiltered ? types[progressValue.active].value : ongoingActivityCount,
            },
            aggregateOn: aggregateOn,
            data: {
                count: totalCountWithoutDone,
                filterProgressValue: (name) => this.onSetProgressBarState(typeId, name),
                progressBar,
                progressValue,
            },
        };
    }

    getRecord(resId) {
        return this.props.records.find((r) => r.resId === resId);
    }

    isTypeDisplayDone(typeId) {
        return this.props.activityTypes.find((a) => a.id === typeId).keep_done;
    }

    onSetProgressBarState(typeId, bar) {
        const name = bar.value;
        if (this.activeFilter.progressValue.active === name) {
            this.activeFilter.progressValue.active = null;
            this.activeFilter.activityTypeId = null;
            this.activeFilter.resIds = new Set(Object.keys(this.props.groupedActivities));
        } else {
            this.activeFilter.progressValue.active = name;
            this.activeFilter.activityTypeId = typeId;
            this.activeFilter.resIds = new Set(
                Object.entries(this.props.groupedActivities)
                    .filter(
                        ([, resIds]) => typeId in resIds && name in resIds[typeId].count_by_state
                    )
                    .map(([key]) => parseInt(key))
            );
        }
    }

    get activeColumns() {
        return this.props.activityTypes.filter(
            (activityType) => this.storageActiveColumns[activityType.id]
        );
    }

    setupStorageActiveColumns() {
        const storageActiveColumnsList = browser.localStorage.getItem(this.storageKey)?.split(",");

        this.storageActiveColumns = useState({});
        for (const activityType of this.props.activityTypes) {
            if (storageActiveColumnsList) {
                this.storageActiveColumns[activityType.id] = storageActiveColumnsList.includes(
                    activityType.id.toString()
                );
            } else {
                this.storageActiveColumns[activityType.id] = true;
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
