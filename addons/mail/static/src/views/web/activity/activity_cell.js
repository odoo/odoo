/* @odoo-module */

import { formatDate } from "@web/core/l10n/dates";
import { ActivityListPopover } from "@mail/core/web/activity_list_popover";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { Component, useRef } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";
const { DateTime } = luxon;

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
        const date = luxon.DateTime.fromISO(this.props.closestDate);
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

    get lastAttachmentDateFormatted() {
        return formatDate(DateTime.fromSQL(this.props.attachments.last.create_date, { zone: 'utc' }).toLocal());
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
