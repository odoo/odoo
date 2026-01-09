import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component, useExternalListener, useState } from "@odoo/owl";

export class AttendeeCalendarActivityPopover extends Component {
    static template = "calendar.AttendeeCalendarActivityPopover";
    static subTemplates = {
        popover: "calendar.AttendeeCalendarActivityPopover.popover",
        body: "calendar.AttendeeCalendarActivityPopover.body",
        footer: "calendar.AttendeeCalendarActivityPopover.footer",
    };
    static components = {
        Dialog,
    };
    static props = {
        close: Function,
        model: Object,
        record: Object,
        markDoneActivityRecord: Function,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.limit = this.env.isSmall ? 10 : 5;
        this.state = useState({ activities: this.props.record.activities });

        useExternalListener(window, "pointerdown", (e) => e.preventDefault(), { capture: true });
    }

    /**
     * Get the activities to display.
     * Activities are grouped per res record and their count doesn't exceed the limit.
     */
    get activitiesPerResRecord() {
        return Array.from(
            this.state.activities
                .slice(0, this.limit)
                .sort((a, b) => {
                    // No res_model comes first
                    if ((!a.res_model && b.res_model) || (a.res_model && !b.res_model)) {
                        return !a.res_model && b.res_model ? -1 : 1;
                    }
                    // Sort by res_model alphabetically
                    if (a.res_model !== b.res_model) {
                        return (a.res_model ?? "").localeCompare(b.res_model ?? "");
                    }
                    // Sort by res_id ascending then by activity id ascending
                    return a.res_id !== b.res_id ? a.res_id - b.res_id : a.id - b.id;
                })
                .reduce((map, activity) => {
                    const key = `${activity.res_model ?? ""}-${activity.res_id ?? ""}`;
                    (map.get(key) ?? map.set(key, []).get(key)).push(activity);
                    return map;
                }, new Map())
                .values()
        );
    }

    get hasFooter() {
        return false;
    }

    get moreActivitiesCount() {
        return this.state.activities.length > this.limit
            ? this.state.activities.length - this.limit
            : 0;
    }

    get title() {
        return this.props.record.isMultiActivity
            ? _t("%s pending activities", this.state.activities.length)
            : _t("Pending Activity");
    }

    async cancelActivityRecord(activityId) {
        await this.orm.call("mail.activity", "action_cancel", [[activityId]]);
        this.props.model.load();
        this.removeActivity(activityId);
    }

    async editActivityRecord(activityId) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "mail.activity",
                res_id: activityId,
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: () => {
                    this.props.model.load();
                },
            }
        );
        this.props.close();
    }

    markDoneActivityRecord(activityId) {
        this.props.markDoneActivityRecord(activityId, false);
        this.removeActivity(activityId);
    }

    async openActivitiesListView() {
        const action = await this.action.loadAction("mail.mail_activity_action_my");
        this.action.doAction(
            {
                ...action,
                domain: [["id", "in", this.state.activities.map((a) => a.id)]],
                context: {}, // Prevent default search filters
            },
            {
                onClose: () => {
                    this.props.model.load();
                },
            }
        );
        this.props.close();
    }

    async openResRecord(activityId) {
        this.action.doAction(
            await this.orm.call("mail.activity", "action_open_document", [activityId])
        );
    }

    removeActivity(activityId) {
        this.state.activities = this.state.activities.filter((a) => a.id !== activityId);
        if (this.state.activities.length === 0) {
            this.props.close();
        }
    }
}
