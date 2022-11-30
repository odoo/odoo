/** @odoo-module **/

import { ActivityListPopover } from "@mail/new/chatter/components/activity_list_popover";

import { usePopover } from "@web/core/popover/popover_hook";
import { useWowlService } from "@web/legacy/utils";

import { Component, useRef, useSubEnv } from "@odoo/owl";

export class ActivityCell extends Component {
    setup() {
        const messaging = useWowlService("mail.messaging");
        /**
         * Ensure this component uses the same env as the messaging service. Indeed ActivityRenderer
         * (the parent component of this one) still uses the legacy env, but ActivityCell (the
         * current component) needs the new env.
         */
        useSubEnv(messaging.env);
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

Object.assign(ActivityCell, {
    props: {
        activityIds: {
            type: Array,
            elements: Number,
        },
        activityTypeId: Number,
        closestDeadline: String,
        reloadFunc: Function,
        resId: Number,
        resModel: String,
    },
    template: "mail.ActivityCell",
});
