import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { ActivityAssignPopover } from "@mail/core/web/activity_assign_popover";
import { computeDelay } from "@mail/utils/common/dates";
import { propComputed } from "@mail/utils/common/hooks";
import { toggleFn } from "@mail/utils/common/signal";

import { Component, computed, props, signal, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { FileUploader } from "@web/views/fields/file_handler";

export class ActivityListPopoverItem extends Component {
    static components = { ActivityMailTemplate, ActivityMarkAsDone, FileUploader };
    static template = "mail.ActivityListPopoverItem";

    setup() {
        super.setup();
        this.action = useService("action");
        this.store = useService("mail.store");
        this.activity = propComputed("activity", t.instanceOf(this.store["mail.activity"].Class));
        this.onActivityChanged = props.static("onActivityChanged", t.function([]).optional());
        this.onClickDoneAndScheduleNext = props.static(
            "onClickDoneAndScheduleNext",
            t.function([]).optional()
        );
        this.onClickEditActivityButtonProp = props.static(
            "onClickEditActivityButton",
            t.function([]).optional()
        );
        this.hasMarkDoneView = signal(false);
        this.toggleFn = toggleFn;
        this.assignPopover = usePopover(ActivityAssignPopover, { position: "right" });
        // bound once so `close` can be passed as a stable (props.static) handler
        this.closeMarkDoneView = () => this.hasMarkDoneView.set(false);
        if (this.activity().activity_category === "upload_file") {
            this.attachmentUploader = useAttachmentUploader(
                computed(() =>
                    this.store["mail.thread"].insert({
                        model: this.activity().res_model,
                        id: this.activity().res_id,
                    })
                )
            );
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
        } else if (diff < 7) {
            return _t("Due in %s days", Math.round(Math.abs(diff)));
        } else if (diff == 7) {
            return _t("Due in 1 week");
        } else {
            return _t("Due %s", this.props.activity.date_deadline.toLocaleString({
                weekday: "long",
                day: "numeric",
                month: "long",
            }));
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

    get hasMailButton() {
        const activity = this.props.activity;
        return activity.state !== "done" && activity.activity_category === "default" && activity.mail_template_ids.length == 0;
    }

    get hasMarkDoneButton() {
        return this.activity().state !== "done" && !this.hasFileUploader;
    }

    onClickEditActivityButton() {
        this.onClickEditActivityButtonProp?.();
        this.activity()
            .edit()
            .then(() => this.onActivityChanged?.());
    }

    onClickAssignButton(ev) {
        if (this.assignPopover.isOpen) {
            this.assignPopover.close();
            return;
        }
        this.assignPopover.open(ev.currentTarget, {
            activity: this.activity,
            hasHeader: true,
            onActivityChanged: (thread) => this.onActivityChanged?.(thread),
        });
    }

    /**
     * For activity of type email, open email composer and send message on activity linked record chatter
     * (visible by followers + all recipients specified in the form) then mark activity as done.
     */
    onClickMailButton() {
        const activity = this.props.activity;
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Compose Email"),
                view_mode: "form",
                res_model: "mail.compose.message",
                views: [[false, "form"]],
                target: "new",
                view_id: false,
                context: {
                    default_composition_mode: "comment",
                    default_model: activity.res_model,
                    default_res_ids: [activity.res_id],
                    force_email: true,
                },
            },
            {
                onClose: async (args) => {
                    if (args?.dismiss || args?.special) {
                        // Close or Discard
                        return;
                    }
                    // Mark done
                    await this.props.activity.markAsDone();
                    this.props.onActivityChanged?.();
                },
            }
        );
    }

    async onFileUploaded(data) {
        const activity = this.activity();
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity,
        });
        await activity.markAsDone([attachmentId]);
        this.onActivityChanged?.();
    }
}
