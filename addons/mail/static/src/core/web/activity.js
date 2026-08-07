import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityAssignPopover } from "@mail/core/web/activity_assign_popover";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, computed, t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { FileUploader } from "@web/views/fields/file_handler";
import { callPhoneNumber, getPhoneHref } from "@web/core/phone/phone_call";

export class Activity extends Component {
    static components = { ActivityMailTemplate, FileUploader };
    static template = "mail.Activity";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propComputed("activity", t.instanceOf(this.store["mail.activity"]));
        this.onActivityChanged = useProps.static("onActivityChanged", t.function([]));
        this.reloadParentView = useProps.static("reloadParentView", t.function([]));
        this.assignPopover = usePopover(ActivityAssignPopover, { position: "bottom" });
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(AvatarCard);
        this.thread = computed(() =>
            this.store["mail.thread"].insert({
                model: this.activity().res_model,
                id: this.activity().res_id,
            })
        );
        this.attachmentUploader = useAttachmentUploader(this.thread);
    }

    get displayName() {
        return this.activity().summary || this.activity().display_name;
    }

    get hasMailButton() {
        const activity = this.activity();
        return (
            activity.state !== "done" &&
            activity.activity_type_id?.id === (this.store.emailActivityTypeId ?? false) && // type is the built-in email type
            activity.mail_template_ids.length == 0
        );
    }

    get tooltipInfo() {
        const activity = this.activity();
        return JSON.stringify({
            activity: {
                activity_type_id: pick(activity.activity_type_id || {}, "name"),
                dateCreateFormatted: activity.dateCreateFormatted,
                dateDeadlineFormatted: activity.dateDeadlineFormatted,
                create_uid_name: activity.create_uid?.name,
                user_id_name: activity.user_id?.name,
                role_id_name: activity.role_id?.name,
            },
        });
    }

    get delay() {
        return this.store.daysUntil(this.activity().date_deadline);
    }

    get phoneHref() {
        return getPhoneHref(this.activity().phone);
    }

    onClickPhoneNumber(ev) {
        const activity = this.activity();
        return callPhoneNumber(
            this.env,
            {
                activity,
                phoneNumber: activity.phone,
                resId: activity.res_id,
                resModel: activity.res_model,
            },
            ev
        );
    }

    onClickAssign(ev) {
        if (this.assignPopover.isOpen) {
            this.assignPopover.close();
            return;
        }
        this.assignPopover.open(ev.currentTarget, {
            activity: this.activity,
            onActivityChanged: this.onActivityChanged,
        });
    }

    /**
     * For activity of type email, open email composer and send message then mark activity as done.
     */
    async onClickMail() {
        const activity = this.activity();
        const thread = this.thread();
        const recipients = [
            ...thread.suggestedRecipients,
            ...thread.additionalRecipients
        ].filter((r) => r.partner_id);
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
                    default_partner_ids: recipients
                        .filter((r) => r.recipient_type !== "cc")
                        .map((r) => r.partner_id),
                    default_partner_cc_ids: recipients
                        .filter((r) => r.recipient_type === "cc")
                        .map((r) => r.partner_id),
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
                    await activity.markAsDone();
                    this.onActivityChanged(thread);
                },
            }
        );
    }

    onClickMarkAsDone(ev) {
        if (this.markDonePopover.isOpen) {
            this.markDonePopover.close();
            return;
        }
        this.markDonePopover.open(ev.currentTarget, {
            activity: this.activity,
            hasHeader: true,
            onActivityChanged: this.onActivityChanged,
        });
    }

    async onFileUploaded(data) {
        const activity = this.activity();
        const thread = this.thread();
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity,
        });
        await activity.markAsDone([attachmentId]);
        this.onActivityChanged(thread);
        await thread.fetchNewMessages();
    }

    onClickAvatar(ev) {
        if (!this.activity().user_id) {
            return;
        }
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.activity().user_id.id,
                model: "res.users",
            });
        }
    }

    async edit() {
        const thread = this.thread();
        await this.activity().edit();
        this.onActivityChanged(thread);
    }

    /**
     * @param {MouseEvent} ev
     */
    onClick(ev) {
        this.store.handleClickOnLink(ev, this.thread());
    }
}
