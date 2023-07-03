/* @odoo-module */

import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { CompletedActivity } from "@mail/core/web/completed_activity";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {number[]} activityIds
 * @property {function} close
 * @property {number} [defaultActivityTypeId]
 * @property {function} onActivityChanged
 * @property {number} resId
 * @property {string} resModel
 * @extends {Component<Props, Env>}
 */
export class ActivityListPopover extends Component {
    static components = {
        ActivityListPopoverItem,
        CompletedActivity,
    };
    static props = [
        "activityIds",
        "close",
        "completedActivityIds?",
        "defaultActivityTypeId?",
        "onActivityChanged",
        "resId",
        "resModel",
    ];
    static template = "mail.ActivityListPopover";

    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        /** @type {import("@mail/core/web/activity_service").ActivityService} */
        this.activityService = useService("mail.activity");
        this.store = useState(useService("mail.store"));
        this.updateFromProps(this.props);
        onWillUpdateProps((props) => this.updateFromProps(props));
    }

    get activities() {
        /** @type {import("models").Activity[]} */
        const allActivities = Object.values(this.store.Activity.records);
        return allActivities
            .filter((activity) => this.props.activityIds.includes(activity.id))
            .sort(function (a, b) {
                if (a.date_deadline === b.date_deadline) {
                    return a.id - b.id;
                }
                return a.date_deadline < b.date_deadline ? -1 : 1;
            });
    }

    get completedActivities() {
        if (!this.props.completedActivityIds) {
            return [];
        }
        const allCompletedActivities = Object.values(this.store.CompletedActivity.records);
        return allCompletedActivities
            .filter((activity) => this.props.completedActivityIds.includes(activity.id))
            .sort(function (a, b) {
                if (a.date_done === b.date_done) {
                    return b.id - a.id;
                }
                return b.date_done < a.date_done ? -1 : 1;
            });
    }

    onClickAddActivityButton() {
        this.env.services["mail.activity"]
            .schedule(
                this.props.resModel,
                this.props.resId,
                undefined,
                this.props.defaultActivityTypeId
            )
            .then(() => this.props.onActivityChanged());
        this.props.close();
    }

    get overdueActivities() {
        return this.activities.filter((activity) => activity.state === "overdue");
    }

    get plannedActivities() {
        return this.activities.filter((activity) => activity.state === "planned");
    }

    get todayActivities() {
        return this.activities.filter((activity) => activity.state === "today");
    }

    async updateFromProps(props) {
        this.activityService.fetchData(props.activityIds, props.completedActivityIds);
    }
}
