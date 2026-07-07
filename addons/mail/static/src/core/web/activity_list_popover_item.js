import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { onActivityChangedType } from "@mail/core/web/activity_types";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { ActivityAssignPopover } from "@mail/core/web/activity_assign_popover";
import { computeDelay } from "@mail/utils/common/dates";
import { propComputed } from "@mail/utils/common/hooks";
import { toggleFn } from "@mail/utils/common/signal";

import { Component, computed, signal, t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { FileUploader } from "@web/views/fields/file_handler";

export class ActivityListPopoverItem extends Component {
    static components = { ActivityMailTemplate, ActivityMarkAsDone, FileUploader };
    static template = "mail.ActivityListPopoverItem";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propComputed("activity", t.instanceOf(this.store["mail.activity"]));
        this.thread = computed(() => this.activity().thread);
        this.onActivityChanged = useProps.static(
            "onActivityChanged",
            onActivityChangedType(this.store).optional()
        );
        this.onClickDoneAndScheduleNext = useProps.static(
            "onClickDoneAndScheduleNext",
            t.function([]).optional()
        );
        this.onClickEditActivityButtonProp = useProps.static(
            "onClickEditActivityButton",
            t.function([]).optional()
        );
        this.hasMarkDoneView = signal(false);
        this.toggleFn = toggleFn;
        this.assignPopover = usePopover(ActivityAssignPopover, { position: "right" });
        // bound once so `close` can be passed as a stable (useProps.static) handler
        this.closeMarkDoneView = () => this.hasMarkDoneView.set(false);
        if (this.activity().activity_category === "upload_file") {
            this.attachmentUploader = useAttachmentUploader(this.thread);
        }
    }

    get delayLabel() {
        const diff = computeDelay(this.activity().date_deadline);
        if (diff === 0) {
            return _t("Today");
        } else if (diff === -1) {
            return _t("Yesterday");
        } else if (diff < 0) {
            return _t("%s days overdue", Math.round(Math.abs(diff)));
        } else if (diff === 1) {
            return _t("Tomorrow");
        } else {
            return _t("Due in %s days", Math.round(Math.abs(diff)));
        }
    }

    get hasEditButton() {
        const activity = this.activity();
        return activity.state !== "done" && activity.can_write;
    }

    get hasAssignButton() {
        const activity = this.activity();
        return activity.state !== "done" && activity.can_write && !activity.user_id;
    }

    get hasFileUploader() {
        const activity = this.activity();
        return activity.state !== "done" && activity.activity_category === "upload_file";
    }

    get hasMarkDoneButton() {
        return this.activity().state !== "done" && !this.hasFileUploader;
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ activityAtRender: import("models").Activity }} param1
     */
    onClickEditActivityButton(ev, { activityAtRender }) {
        const thread = activityAtRender.thread;
        this.onClickEditActivityButtonProp?.();
        activityAtRender.edit().then(() => this.onActivityChanged?.({ thread }));
    }

    onClickAssignButton(ev) {
        if (this.assignPopover.isOpen) {
            this.assignPopover.close();
            return;
        }
        this.assignPopover.open(ev.currentTarget, {
            activity: this.activity,
            hasHeader: true,
            /** @type {ReturnType<typeof import("@mail/core/web/activity_types").onActivityChangedType>["type"]} */
            onActivityChanged: ({ thread }) => this.onActivityChanged?.({ thread }),
        });
    }

    /**
     * @param {Object} data
     * @param {{ activityAtRender: import("models").Activity }} param1
     */
    async onFileUploaded(data, { activityAtRender }) {
        const thread = activityAtRender.thread;
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: activityAtRender,
        });
        await activityAtRender.markAsDone([attachmentId]);
        this.onActivityChanged?.({ thread });
    }
}
