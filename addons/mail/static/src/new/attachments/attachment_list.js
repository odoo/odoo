/* @odoo-module */

import { Component } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { useAttachmentViewer } from "./attachment_viewer_hook";

import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/core/attachment_model").Attachment[]} attachments
 * @property {function} unlinkAttachment
 * @property {number} imagesHeight
 * @extends {Component<Props, Env>}
 */
export class AttachmentList extends Component {
    static props = ["attachments", "unlinkAttachment", "imagesHeight"];
    static template = "mail.attachment_list";

    setup() {
        // Arbitrary high value, this is effectively a max-width.
        this.imagesWidth = 1920;
        this.dialog = useService("dialog");
        this.attachmentViewer = useAttachmentViewer();
    }

    /**
     * @return {import('@mail/new/attachments/attachment_model').Attachment[]}
     */
    get nonImagesAttachments() {
        return this.props.attachments.filter((attachment) => !attachment.isImage);
    }

    /**
     * @return {import('@mail/new/attachments/attachment_model').Attachment[]}
     */
    get imagesAttachments() {
        return this.props.attachments.filter((attachment) => attachment.isImage);
    }

    /**
     * @param {import('@mail/new/attachments/attachment_model').Attachment} attachment
     */
    getImageUrl(attachment) {
        const { imagesHeight } = this.props;
        if (attachment.uploading && attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        if (
            !this.env.inComposer &&
            !this.env.inChatter &&
            !attachment.accessToken &&
            attachment.originThread?.model === "mail.channel"
        ) {
            return `/mail/channel/${attachment.originThread?.id}/image/${attachment.id}/${this.imagesWidth}x${imagesHeight}`;
        }
        const accessToken = attachment.accessToken ? `?access_token=${attachment.accessToken}` : "";
        return `/web/image/${attachment.id}/${this.imagesWidth}x${imagesHeight}${accessToken}`;
    }

    /**
     * @param {import('@mail/new/attachments/attachment_model').Attachment} attachment
     */
    canDownload(attachment) {
        return !attachment.uploading && !this.env.inComposer;
    }

    /**
     * @param {import('@mail/new/attachments/attachment_model').Attachment} attachment
     */
    onClickDownload(attachment) {
        const downloadLink = document.createElement("a");
        downloadLink.setAttribute("href", attachment.downloadUrl);
        // Adding 'download' attribute into a link prevents open a new
        // tab or change the current location of the window. This avoids
        // interrupting the activity in the page such as rtc call.
        downloadLink.setAttribute("download", "");
        downloadLink.click();
    }

    /**
     * @param {import('@mail/new/attachments/attachment_model').Attachment} attachment
     */
    onClickUnlink(attachment) {
        if (this.env.inComposer) {
            return this.props.unlinkAttachment(attachment);
        }
        this.dialog.add(ConfirmationDialog, {
            body: sprintf(_t('Do you really want to delete "%s"?'), attachment.filename),
            cancel: () => {},
            confirm: () => this.onConfirmUnlink(attachment),
        });
    }

    /**
     * @param {import('@mail/new/attachments/attachment_model').Attachment} attachment
     */
    onConfirmUnlink(attachment) {
        this.props.unlinkAttachment(attachment);
    }

    get isInChatWindowAndIsAlignedRight() {
        return this.env.inChatWindow && this.env.alignedRight;
    }

    get isInChatWindowAndIsAlignedLeft() {
        return this.env.inChatWindow && !this.env.alignedRight;
    }
}
