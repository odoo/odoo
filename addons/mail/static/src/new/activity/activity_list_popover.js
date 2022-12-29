/* @odoo-module */

import { useMessaging, useStore } from "../core/messaging_hook";

import { ActivityListPopoverItem } from "@mail/new/activity/activity_list_popover_item";

import { Component, onWillUpdateProps } from "@odoo/owl";

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
    static components = { ActivityListPopoverItem };
    static props = [
        "activityIds",
        "close",
        "defaultActivityTypeId?",
        "onActivityChanged",
        "resId",
        "resModel",
    ];
    static template = "mail.ActivityListPopover";

    setup() {
        this.orm = useService("orm");
        this.messaging = useMessaging();
        this.user = useService("user");
        /** @type {import("@mail/new/activity/activity_service").ActivityService} */
        this.activity = useService("mail.activity");
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = useStore();
        this.updateFromProps(this.props);
        onWillUpdateProps((props) => this.updateFromProps(props));
    }

    get activities() {
        /** @type {import("./activity_model").Activity[]} */
        const allActivities = Object.values(this.store.activities);
        return allActivities
            .filter((activity) => this.props.activityIds.includes(activity.id))
            .sort(function (a, b) {
                if (a.date_deadline === b.date_deadline) {
                    return a.id - b.id;
                }
                return a.date_deadline < b.date_deadline ? -1 : 1;
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
        const activitiesData = await this.orm.silent.call(
            "mail.activity",
            "activity_format",
            [props.activityIds],
            {
                context: this.user.user_context,
            }
        );
        for (const activityData of activitiesData) {
            this.activity.insert(activityData);
        }
    }
}
