/* @odoo-module */

import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";

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
    static components = { ActivityListPopoverItem };
    static props = [
        "activityIds",
        "close",
        "defaultActivityTypeId?",
        "onActivityChanged",
        "resId",
        /** Ids of record selection used to schedule activities in batch; it must include resId. */
        "resIds?",
        "resModel",
    ];
    static template = "mail.ActivityListPopover";

    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
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

    onClickAddActivityButton() {
        this.env.services["mail.activity"]
            .schedule(
                this.props.resModel,
                this.props.resIds ? this.props.resIds : [this.props.resId],
                this.props.defaultActivityTypeId
            )
            .then(() => this.props.onActivityChanged());
        this.props.close();
    }

    get doneActivities() {
        return this.activities.filter((activity) => activity.state === "done");
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
        this.store.Activity.insert(activitiesData, { html: true });
    }
}
