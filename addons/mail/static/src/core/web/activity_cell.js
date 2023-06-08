/* @odoo-module */

import { ActivityListPopover } from "@mail/core/web/activity_list_popover";

import { Component, useRef } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";

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
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
        this.contentRef = useRef("content");
    }

    get closestDeadlineFormatted() {
        const date = luxon.DateTime.fromISO(this.props.closestDeadline);
        // To remove year only if current year
        if (new luxon.DateTime.now().year === date.year) {
            return date.toLocaleString({
                day: "numeric",
                month: "short",
            });
        } else {
            return date.toLocaleDateString({
                day: "numeric",
                month: "short",
                year: "numeric",
            });
        }
    }

    onClick() {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.popover.open(this.contentRef.el, {
                activityIds: this.props.activityIds,
                defaultActivityTypeId: this.props.activityTypeId,
                onActivityChanged: () => {
                    this.props.reloadFunc();
                },
                resId: this.props.resId,
                resModel: this.props.resModel,
            });
        }
    }
}
