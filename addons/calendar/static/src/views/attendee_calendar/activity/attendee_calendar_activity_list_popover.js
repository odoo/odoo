import { AttendeeCalendarActivityListPopoverItem } from "@calendar/views/attendee_calendar/activity/attendee_calendar_activity_list_popover_item";
import { compareDatetime } from "@mail/utils/common/misc";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {number[]} activityIds
 * @property {Object} model
 * @property {function} close
 * @property {function} onActivityChanged
 * @extends {Component<Props, Env>}
 *
 * Highly inspired from the "ActivityListPopover" mail component.
 * Instead of managing the activities for a specific record (or specific selected records),
 * this component "activityIds" props refers to the user pending activities for a specific date.
 */
export class AttendeeCalendarActivityListPopover extends Component {
    static components = { Dialog, AttendeeCalendarActivityListPopoverItem };
    static props = ["activityIds", "model", "close", "onActivityChanged"];
    static template = "calendar.AttendeeCalendarActivityListPopover";

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.limit = this.env.isSmall ? false : 5;

        onWillStart(async () => {
            const data = await this.orm.silent.call("mail.activity", "activity_format", [
                this.props.activityIds,
            ]);
            this.store.insert(data);
        });
    }

    get activities() {
        return this.limit ? this.allActivities.splice(0, this.limit) : this.allActivities;
    }

    get allActivities() {
        /** @type {import("models").Activity[]} */
        const activities = Object.values(this.store["mail.activity"].records);
        return activities
            .filter((activity) => this.props.activityIds.includes(activity.id))
            .sort((a, b) => compareDatetime(a.date_deadline, b.date_deadline) || a.id - b.id);
    }

    get extraActivityCount() {
        const totalCount = this.allActivities.length;
        return this.limit && totalCount > this.limit ? totalCount - this.limit : 0;
    }

    /**
     * Open list view modal with all the popover activities.
     */
    async onClickViewAll() {
        const action = await this.action.loadAction(
            "calendar.action_mail_activity_view_tree_open_target"
        );
        this.props.close();
        this.action.doAction(
            {
                ...action,
                domain: [["id", "in", this.props.activityIds]],
            },
            {
                additionalContext: {
                    // Needed to keep track of the current list activities.
                    activity_ids: this.props.activityIds,
                },
                onClose: async (closeInfo) => {
                    // Prevent updating view on redirection
                    if (closeInfo?.noReload) {
                        return;
                    }
                    this.props.onActivityChanged();
                },
            }
        );
    }

    /**
     * Close activity list popover when there's no activity left.
     */
    onRemoveActivityItem() {
        if (!this.allActivities.length) {
            this.props.close();
        }
    }
}
