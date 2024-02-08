/* @odoo-module */

import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay, getMsToTomorrow } from "@mail/utils/common/dates";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";

/**
 * @typedef {Object} Props
 * @property {import("models").Activity} activity
 * @property {function} onActivityChanged
 * @property {function} reloadParentView
 * @extends {Component<Props, Env>}
 */
export class Activity extends Component {
    static components = { ActivityMailTemplate, FileUploader };
    static props = ["activity", "onActivityChanged", "reloadParentView"];
    static template = "mail.Activity";

    setup() {
        this.activityService = useService("mail.activity");
        this.threadService = useService("mail.thread");
        this.state = useState({ showDetails: false });
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(AvatarCardPopover);
        onMounted(() => {
            this.updateDelayAtNight();
        });
        onWillUnmount(() => browser.clearTimeout(this.updateDelayMidnightTimeout));
        this.attachmentUploader = useAttachmentUploader(this.thread);
    }

    get displayName() {
        if (this.props.activity.summary) {
            return _t("“%s”", this.props.activity.summary);
        }
        return this.props.activity.display_name;
    }

    get displayCreateDate() {
        return deserializeDateTime(this.props.activity.create_date).toLocaleString(
            luxon.DateTime.DATETIME_SHORT_WITH_SECONDS
        );
    }

    updateDelayAtNight() {
        browser.clearTimeout(this.updateDelayMidnightTimeout);
        this.updateDelayMidnightTimeout = browser.setTimeout(
            () => this.render(),
            getMsToTomorrow() + 100
        ); // Make sure there is no race condition
    }

    get delay() {
        return computeDelay(this.props.activity.date_deadline);
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
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
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data);
        await this.activityService.markAsDone(this.props.activity, [attachmentId]);
        this.props.onActivityChanged(thread);
        await this.threadService.fetchNewMessages(thread);
    }

    onClickAvatar(ev) {
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.props.activity.persona.userId,
            });
        }
    }

    async edit() {
        const thread = this.thread;
        const id = this.props.activity.id;
        await this.env.services["mail.activity"].edit(id);
        this.props.onActivityChanged(thread);
    }

    async unlink() {
        const thread = this.thread;
        this.activityService.delete(this.props.activity);
        await this.env.services.orm.unlink("mail.activity", [this.props.activity.id]);
        this.props.onActivityChanged(thread);
    }

    get thread() {
        return this.threadService.getThread(
            this.props.activity.res_model,
            this.props.activity.res_id
        );
    }
}
