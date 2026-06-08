import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityAssignPopover } from "@mail/core/web/activity_assign_popover";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay, getMsToTomorrow } from "@mail/utils/common/dates";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";

import { Component, onMounted, onWillUnmount, props, types } from "@odoo/owl";

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
        this.props = props({
            activity: types.instanceOf(this.store["mail.activity"].Class),
            onActivityChanged: types.function([]),
            reloadParentView: types.function([]),
        });
        this.assignPopover = usePopover(ActivityAssignPopover, { position: "bottom" });
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(AvatarCard);
        onMounted(() => {
            this.updateDelayAtNight();
        });
        onWillUnmount(() => browser.clearTimeout(this.updateDelayMidnightTimeout));
        this.attachmentUploader = useAttachmentUploader(this.thread);
    }

    get displayName() {
        return this.props.activity.summary || this.props.activity.display_name;
    }

    get tooltipInfo() {
        const activity = this.props.activity;
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
        return computeDelay(this.props.activity.date_deadline);
    }

    async onClickAssign(ev) {
        if (this.assignPopover.isOpen) {
            this.assignPopover.close();
            return;
        }
        this.assignPopover.open(ev.currentTarget, {
            activity: this.props.activity,
            onActivityChanged: this.props.onActivityChanged,
        });
    }

    async onClickMarkAsDone(ev) {
        if (this.markDonePopover.isOpen) {
            this.markDonePopover.close();
            return;
        }
        this.markDonePopover.open(ev.currentTarget, {
            activity: this.props.activity,
            hasHeader: true,
            onActivityChanged: this.props.onActivityChanged,
        });
    }

    async onFileUploaded(data) {
        const thread = this.thread;
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: this.props.activity,
        });
        await this.props.activity.markAsDone([attachmentId]);
        this.props.onActivityChanged(thread);
        await thread.fetchNewMessages();
    }

    onClickAvatar(ev) {
        if (!this.props.activity.user_id) {
            return;
        }
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.props.activity.user_id.id,
                model: "res.users",
            });
        }
    }

    async edit() {
        const thread = this.thread;
        await this.props.activity.edit();
        this.props.onActivityChanged(thread);
    }

    get thread() {
        return this.env.services["mail.store"]["mail.thread"].insert({
            model: this.props.activity.res_model,
            id: this.props.activity.res_id,
        });
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClick(ev) {
        this.store.handleClickOnLink(ev, this.thread);
    }
}
