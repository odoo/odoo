/* @odoo-module */

import { ActivityListPopover } from "@mail/core/web/activity_list_popover";
import { serverDateToLocalDateShortFormat } from "@mail/utils/common/format";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { Component, useRef } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";

export class ActivityCell extends Component {
    static components = {
        Avatar,
    };
    static props = {
        activityIds: {
            type: Array,
            elements: Number,
        },
        attachments: {
            optional: true,
            type: Object,
        },
        activityTypeId: Number,
        closestDate: String,
        completedActivityIds: {
            type: Array,
            elements: Number,
        },
        countByState: Object,
        reloadFunc: Function,
        resId: Number,
        resModel: String,
        userIdsOrderedByDeadline: Array,
    };
    static template = "mail.ActivityCell";

    setup() {
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
        this.contentRef = useRef("content");
    }

    get closestDateFormatted() {
        return serverDateToLocalDateShortFormat(this.props.closestDate);
    }

    get lastAttachmentDateFormatted() {
        return serverDateToLocalDateShortFormat(this.props.closestDate);
    }

    get ongoingActivityCount() {
        return this.props.activityIds.length;
    }

    get totalActivityCount() {
        return this.props.activityIds.length + (this.props.completedActivityIds?.length ?? 0);
    }

    onClick() {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.popover.open(this.contentRef.el, {
                activityIds: this.props.activityIds,
                completedActivityIds: this.props.completedActivityIds,
                defaultActivityTypeId: this.props.activityTypeId,
                onActivityChanged: () => {
                    this.props.reloadFunc();
                    this.popover.close();
                },
                resId: this.props.resId,
                resModel: this.props.resModel,
            });
        }
    }
}
