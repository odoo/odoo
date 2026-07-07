import { ActivityListPopover } from "@mail/core/web/activity_list_popover";
import { propComputed } from "@mail/utils/common/hooks";
import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { Component, signal, t, useProps } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";

import { formatDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { formatList } from "@web/core/l10n/utils";

export class ActivityCell extends Component {
    static components = {
        Avatar,
    };
    static template = "mail.ActivityCell";

    contentRef = signal.ref();

    setup() {
        this.activityIds = propComputed("activityIds", t.array(t.number()));
        this.activityTypeId = propComputed("activityTypeId", t.number());
        this.attachmentsInfo = propComputed(
            "attachmentsInfo",
            t
                .object({
                    count: t.number(),
                    most_recent_id: t.number(),
                    most_recent_name: t.string(),
                })
                .optional()
        );
        this.countByState = propComputed("countByState", t.record(t.number()));
        this.reloadFunc = useProps.static("reloadFunc", t.function([]));
        this.reportingDate = propComputed("reportingDate", t.string());
        this.resId = propComputed("resId", t.number());
        this.resModel = propComputed("resModel", t.string());
        this.roleToAssignIds = propComputed("roleToAssignIds", t.array(t.number()).optional());
        this.summaries = propComputed("summaries", t.array());
        this.userAssignedIds = propComputed("userAssignedIds", t.array(t.number()));
        this.popover = usePopover(ActivityListPopover, { position: "bottom-start" });
    }

    get reportingDateFormatted() {
        return formatDate(luxon.DateTime.fromISO(this.reportingDate()));
    }
    get displayedSummaries() {
        const summariesWithContent = this.summaries().filter((textContent) => !!textContent);
        const extras = this.summaries().length - summariesWithContent.length;
        if (summariesWithContent.length > 0 && extras > 0) {
            summariesWithContent.push(_t("%(extraCount)s more", { extraCount: extras }));
        }
        return formatList(summariesWithContent);
    }

    get ongoingActivityCount() {
        return (
            (this.countByState()?.planned ?? 0) +
            (this.countByState()?.today ?? 0) +
            (this.countByState()?.overdue ?? 0)
        );
    }

    get totalActivityCount() {
        return this.ongoingActivityCount + (this.countByState()?.done ?? 0);
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ resIdAtRender: number, resModelAtRender: string }} param1
     */
    onClick(ev, { resIdAtRender, resModelAtRender }) {
        if (this.popover.isOpen) {
            this.popover.close();
        } else {
            this.popover.open(this.contentRef(), {
                activityIds: this.activityIds(),
                defaultActivityTypeId: this.activityTypeId(),
                /** @type {ReturnType<typeof import("@mail/core/web/activity_types").onActivityChangedType>["type"]} */
                onActivityChanged: ({ thread }) => {
                    this.reloadFunc();
                    this.popover.close();
                },
                resId: resIdAtRender,
                resModel: resModelAtRender,
            });
        }
    }
}
