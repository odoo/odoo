/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

/**
 * @typedef {Object} Props
 * @property {import("models").Attachment[]} attachments
 * @property {function} unlinkAttachment
 * @property {number} imagesHeight
 * @property {ReturnType<import('@mail/core/common/message_search_hook').useMessageSearch>} [messageSearch]
 * @extends {Component<Props, Env>}
 */
export class AttachmentList extends Component {
    static props = ["attachments", "unlinkAttachment", "imagesHeight", "messageSearch?"];
    static template = "mail.AttachmentList";

    setup() {
        this.ui = useState(useService("ui"));
        // Arbitrary high value, this is effectively a max-width.
        this.imagesWidth = 1920;
        this.dialog = useService("dialog");
        this.fileViewer = useFileViewer();
    }

    /**
     * @return {import("models").Attachment[]}
     */
    get nonImagesAttachments() {
        return this.props.attachments.filter((attachment) => !attachment.isImage);
    }

    /**
     * @return {import("models").Attachment[]}
     */
    get imagesAttachments() {
        return this.props.attachments.filter((attachment) => attachment.isImage);
    }

    /**
     * @param {import("models").Attachment} attachment
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
     * @param {import("models").Attachment} attachment
     */
    canDownload(attachment) {
        return !attachment.uploading && !this.env.inComposer;
    }

    /**
     * @param {import("models").Attachment} attachment
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
     * @param {import("models").Attachment} attachment
     */
    onClickUnlink(attachment) {
        if (this.env.inComposer) {
            return this.props.unlinkAttachment(attachment);
        }
        this.dialog.add(ConfirmationDialog, {
            body: _t('Do you really want to delete "%s"?', attachment.filename),
            cancel: () => {},
            confirm: () => this.onConfirmUnlink(attachment),
        });
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    onConfirmUnlink(attachment) {
        this.props.unlinkAttachment(attachment);
    }

    onImageLoaded() {
        this.env.onImageLoaded?.();
    }

    get isInChatWindowAndIsAlignedRight() {
        return this.env.inChatWindow && this.env.alignedRight;
    }

    get isInChatWindowAndIsAlignedLeft() {
        return this.env.inChatWindow && !this.env.alignedRight;
    }

    get showDelete() {
        return (
            (this.attachment.isDeletable &&
                (!this.env.message || this.env.message?.hasTextContent)) ||
            this.env.inComposer ||
            this.props.attachments.length > 1
        );
    }
}
