import { useRef } from "@web/owl2/utils";
import { ActivityListPopover } from "@mail/core/web/activity_list_popover";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { Component, props, types } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";

import { formatDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { formatList } from "@web/core/l10n/utils";

export class ActivityCell extends Component {
    static components = {
        Avatar,
    };
    static template = "mail.ActivityCell";

    setup() {
        this.props = props({
            activityIds: types.array(types.number()),
            activityTypeId: types.number(),
            attachmentsInfo: types
                .object({
                    count: types.number(),
                    most_recent_id: types.number(),
                    most_recent_name: types.string(),
                })
                .optional(),
            countByState: types.record(types.number()),
            reloadFunc: types.function([]),
            reportingDate: types.string(),
            resId: types.number(),
            resModel: types.string(),
            summaries: types.array(),
            userAssignedIds: types.array(types.number()),
        });
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
        this.contentRef = useRef("content");
    }

    get reportingDateFormatted() {
        return formatDate(luxon.DateTime.fromISO(this.props.reportingDate));
    }
    get displayedSummaries() {
        const summariesWithContent = this.props.summaries.filter((textContent) => !!textContent);
        const extras = this.props.summaries.length - summariesWithContent.length;
        if (summariesWithContent.length > 0 && extras > 0) {
            summariesWithContent.push(_t("%(extraCount)s more", { extraCount: extras }));
        }
        return formatList(summariesWithContent);
    }

    get ongoingActivityCount() {
        return (
            (this.props.countByState?.planned ?? 0) +
            (this.props.countByState?.today ?? 0) +
            (this.props.countByState?.overdue ?? 0)
        );
    }

    get totalActivityCount() {
        return this.ongoingActivityCount + (this.props.countByState?.done ?? 0);
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
                    this.popover.close();
                },
                resId: this.props.resId,
                resModel: this.props.resModel,
            });
        }
    }
}
