/* @odoo-module */

import { ActivityListPopover } from "@mail/new/activity/activity_list_popover";

import { usePopover } from "@web/core/popover/popover_hook";

import { Component, useRef } from "@odoo/owl";

export class ActivityCell extends Component {
    static props = {
        activityIds: {
            type: Array,
            elements: Number,
        },
        activityTypeId: Number,
        closestDeadline: String,
        reloadFunc: Function,
        resId: Number,
        resModel: String,
    };
    static template = "mail.ActivityCell";

    setup() {
        this.popover = usePopover();
        this.contentRef = useRef("content");
    }

    get closestDeadlineFormatted() {
        const date = moment(this.props.closestDeadline).toDate();
        // To remove year only if current year
        if (moment().year() === moment(date).year()) {
            return date.toLocaleDateString(moment().locale(), {
                day: "numeric",
                month: "short",
            });
        } else {
            return moment(date).format("ll");
        }
    }

    onClick() {
        if (this.closePopover) {
            this.closePopover();
            this.closePopover = undefined;
        } else {
            this.closePopover = this.popover.add(
                this.contentRef.el,
                ActivityListPopover,
                {
                    activityIds: this.props.activityIds,
                    defaultActivityTypeId: this.props.activityTypeId,
                    onActivityChanged: () => {
                        this.props.reloadFunc();
                    },
                    resId: this.props.resId,
                    resModel: this.props.resModel,
                },
                {
                    onClose: () => (this.closePopover = undefined),
                    position: "bottom", // should be "bottom-start" but not supported for some reason
                }
            );
        }
    }
}
