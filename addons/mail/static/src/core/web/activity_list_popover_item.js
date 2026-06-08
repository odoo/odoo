import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { ActivityAssignPopover } from "@mail/core/web/activity_assign_popover";
import { computeDelay } from "@mail/utils/common/dates";
import { toggleFn } from "@mail/utils/common/signal";

import { Component, props, signal, t } from "@odoo/owl";

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
        this.props = props({
            activity: t.instanceOf(this.store["mail.activity"].Class),
            onActivityChanged: t.function([]).optional(),
            onClickDoneAndScheduleNext: t.function([]).optional(),
            onClickEditActivityButton: t.function([]).optional(),
        });
        this.hasMarkDoneView = signal(false);
        this.toggleFn = toggleFn;
        this.assignPopover = usePopover(ActivityAssignPopover, { position: "right" });
        if (this.props.activity.activity_category === "upload_file") {
            this.attachmentUploader = useAttachmentUploader(
                this.store["mail.thread"].insert({
                    model: this.props.activity.res_model,
                    id: this.props.activity.res_id,
                })
            );
        }
    }

    get delayLabel() {
        const diff = computeDelay(this.props.activity.date_deadline);
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
        const activity = this.props.activity;
        return activity.state !== "done" && activity.can_write;
    }

    get hasAssignButton() {
        const activity = this.props.activity;
        return activity.state !== "done" && activity.can_write && !activity.user_id;
    }

    get hasFileUploader() {
        const activity = this.props.activity;
        return activity.state !== "done" && activity.activity_category === "upload_file";
    }

    get hasMarkDoneButton() {
        return this.props.activity.state !== "done" && !this.hasFileUploader;
    }

    onClickEditActivityButton() {
        this.props.onClickEditActivityButton();
        this.props.activity.edit().then(() => this.props.onActivityChanged?.());
    }

    onClickAssignButton(ev) {
        if (this.assignPopover.isOpen) {
            this.assignPopover.close();
            return;
        }
        this.assignPopover.open(ev.currentTarget, {
            activity: this.props.activity,
            hasHeader: true,
            onActivityChanged: (thread) => this.props.onActivityChanged?.(thread),
        });
    }

    async onFileUploaded(data) {
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: this.props.activity,
        });
        await this.props.activity.markAsDone([attachmentId]);
        this.props.onActivityChanged?.();
    }
}
