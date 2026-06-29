import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityAssignPopover } from "@mail/core/web/activity_assign_popover";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay, getMsToTomorrow } from "@mail/utils/common/dates";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, computed, onMounted, onWillUnmount, props, t } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import { render } from "@web/owl2/utils";
import { FileUploader } from "@web/views/fields/file_handler";

export class Activity extends Component {
    static components = { ActivityMailTemplate, FileUploader };
    static template = "mail.Activity";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.activity = propComputed("activity", t.instanceOf(this.store["mail.activity"].Class));
        this.onActivityChanged = props.static("onActivityChanged", t.function([]));
        this.reloadParentView = props.static("reloadParentView", t.function([]));
        this.assignPopover = usePopover(ActivityAssignPopover, { position: "bottom" });
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(AvatarCard);
        onMounted(() => {
            this.updateDelayAtNight();
        });
        onWillUnmount(() => browser.clearTimeout(this.updateDelayMidnightTimeout));
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

    updateDelayAtNight() {
        browser.clearTimeout(this.updateDelayMidnightTimeout);
        this.updateDelayMidnightTimeout = browser.setTimeout(
            () => render(this),
            getMsToTomorrow() + 100
        ); // Make sure there is no race condition
    }

    get delay() {
        return computeDelay(this.activity().date_deadline);
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
