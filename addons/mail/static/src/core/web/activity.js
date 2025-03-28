import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay, getMsToTomorrow } from "@mail/utils/common/dates";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { createDocumentFragmentFromContent } from "@web/core/utils/html";

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
        super.setup();
        this.storeService = useService("mail.store");
        this.state = useState({ showDetails: false , fileModel: {}});
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(AvatarCardPopover);
        this.fileViewer = useFileViewer();
        onMounted(() => {
            this.updateDelayAtNight();
            this.processActivityImage();
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
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: this.props.activity,
        });
        await this.props.activity.markAsDone([attachmentId]);
        this.props.onActivityChanged(thread);
        await thread.fetchNewMessages();
    }

    onClickAvatar(ev) {
        if (!this.props.activity.persona) {
            return;
        }
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(target, {
                id: this.props.activity.persona.main_user_id?.id,
            });
        }
    }

    async edit() {
        const thread = this.thread;
        await this.props.activity.edit();
        this.props.onActivityChanged(thread);
    }

    async unlink() {
        const thread = this.thread;
        this.props.activity.remove();
        await this.env.services.orm.unlink("mail.activity", [this.props.activity.id]);
        this.props.onActivityChanged(thread);
    }

    processActivityImage() {
        const img = createDocumentFragmentFromContent(this.props.activity.note).querySelector("img");
        let fileModel = {} ;
        if (img) {
            const imgName = img.src ? decodeURIComponent(img.src.split('/').pop().split('?')[0]) : '';
            fileModel = {
                isImage: true,
                isViewable: true,
                name: imgName,
                defaultSource: img.src,
                downloadUrl: img.src,
            };
            this.state.fileModel = fileModel;
        }
        return fileModel;
    }

    get thread() {
        return this.env.services["mail.store"].Thread.insert({
            model: this.props.activity.res_model,
            id: this.props.activity.res_id,
        });
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClick(ev) {
        this.storeService.handleClickOnLink(ev, this.thread);
    }
}
