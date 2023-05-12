/* @odoo-module */

import { Component } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { useAttachmentViewer } from "./attachment_viewer_hook";

import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/attachment_model").Attachment[]} attachments
 * @property {function} unlinkAttachment
 * @property {number} imagesHeight
 * @extends {Component<Props, Env>}
 */
export class AttachmentList extends Component {
    static props = ["attachments", "unlinkAttachment", "imagesHeight"];
    static template = "mail.AttachmentList";

    setup() {
        // Arbitrary high value, this is effectively a max-width.
        this.imagesWidth = 1920;
        this.dialog = useService("dialog");
        this.attachmentViewer = useAttachmentViewer();
    }

    /**
     * @return {import("@mail/attachments/attachment_model").Attachment[]}
     */
    get nonImagesAttachments() {
        return this.props.attachments.filter((attachment) => !attachment.isImage);
    }

    /**
     * @return {import("@mail/attachments/attachment_model").Attachment[]}
     */
    get imagesAttachments() {
        return this.props.attachments.filter((attachment) => attachment.isImage);
    }

    /**
     * @param {import("@mail/attachments/attachment_model").Attachment} attachment
     */
    getImageUrl(attachment) {
        if (attachment.uploading && attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        return url(attachment.urlRoute, {
            ...attachment.urlQueryParams,
            width: this.imagesWidth,
            height: this.props.imagesHeight,
        });
    }

    /**
     * @param {import("@mail/attachments/attachment_model").Attachment} attachment
     */
    canDownload(attachment) {
        return !attachment.uploading && !this.env.inComposer;
    }

    /**
     * @param {import("@mail/attachments/attachment_model").Attachment} attachment
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
     * @param {import("@mail/attachments/attachment_model").Attachment} attachment
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
     * @param {import("@mail/attachments/attachment_model").Attachment} attachment
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
