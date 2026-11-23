/* @odoo-module */

import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay, getMsToTomorrow } from "@mail/utils/common/dates";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";

/**
 * @typedef {Object} Props
 * @property {import("models").Activity} data
 * @property {function} [onUpdate]
 * @property {function} reloadParentView
 * @extends {Component<Props, Env>}
 */
export class Activity extends Component {
    static components = { ActivityMailTemplate, FileUploader };
    static props = ["data", "onUpdate?", "reloadParentView"];
    static defaultProps = { onUpdate: () => {} };
    static template = "mail.Activity";

    /** @type {function} */
    closePopover;

    setup() {
        this.activityService = useService("mail.activity");
        this.threadService = useService("mail.thread");
        this.storeService = useService("mail.store");
        this.state = useState({ showDetails: false });
        this.popover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(AvatarCardPopover);
        onMounted(() => {
            this.updateDelayAtNight();
        });
        onWillUnmount(() => browser.clearTimeout(this.updateDelayMidnightTimeout));
        this.attachmentUploader = useAttachmentUploader(this.thread);
    }

    get displayName() {
        if (this.props.data.summary) {
            return _t("“%s”", this.props.data.summary);
        }
        return this.props.data.display_name;
    }

    get displayCreateDate() {
        return formatDateTime(deserializeDateTime(this.props.data.create_date));
    }

    get displayDeadlineDate() {
        return formatDate(deserializeDate(this.props.data.date_deadline));
    }

    updateDelayAtNight() {
        browser.clearTimeout(this.updateDelayMidnightTimeout);
        this.updateDelayMidnightTimeout = browser.setTimeout(
            () => this.render(),
            getMsToTomorrow() + 100
        ); // Make sure there is no race condition
    }

    get delay() {
        return computeDelay(this.props.data.date_deadline);
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }

    async onClickMarkAsDone(ev) {
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        this.popover.open(ev.currentTarget, {
            activity: this.props.data,
            hasHeader: true,
            reload: this.props.onUpdate,
        });
    }

    async onFileUploaded(data) {
        const thread = this.thread;
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: this.props.data,
        });
        await this.activityService.markAsDone(this.props.data, [attachmentId]);
        this.props.onUpdate(thread);
        await this.threadService.fetchNewMessages(thread);
    }

    onClickAvatar(ev) {
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.props.data.user_id[0],
            });
        }
    }

    async edit() {
        const thread = this.thread;
        const id = this.props.data.id;
        await this.env.services["mail.activity"].edit(id);
        this.props.onUpdate(thread);
    }

    async unlink() {
        const thread = this.thread;
        this.activityService.delete(this.props.data);
        await this.env.services.orm.unlink("mail.activity", [this.props.data.id]);
        this.props.onUpdate(thread);
    }

    get thread() {
        return this.threadService.getThread(this.props.data.res_model, this.props.data.res_id);
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClick(ev) {
        this.storeService.handleClickOnLink(ev, this.thread);
    }
}
