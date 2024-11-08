import { Component, useState } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

class ImageActions extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["actions", "imagesHeight"];
    static template = "mail.ImageActions";

    setup() {
        super.setup();
        this.actionsMenuState = useDropdownState();
        this.isMobileOS = isMobileOS;
    }
}

/**
 * @typedef {Object} Props
 * @property {import("models").Attachment[]} attachments
 * @property {function} unlinkAttachment
 * @property {number} imagesHeight
 * @property {ReturnType<import('@mail/core/common/message_search_hook').useMessageSearch>} [messageSearch]
 * @extends {Component<Props, Env>}
 */
export class AttachmentList extends Component {
    static components = { ImageActions };
    static props = ["attachments", "unlinkAttachment", "imagesHeight", "messageSearch?"];
    static template = "mail.AttachmentList";

    setup() {
        super.setup();
        this.ui = useState(useService("ui"));
        // Arbitrary high value, this is effectively a max-width.
        this.imagesWidth = 1920;
        this.dialog = useService("dialog");
        this.fileViewer = useFileViewer();
        this.actionsMenuState = useDropdownState();
        this.isMobileOS = isMobileOS;
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
            width: this.imagesWidth * 2,
            height: this.props.imagesHeight * 2,
        });
    }

    get images() {
        return this.props.attachments.filter((a) => a.isImage);
    }

    get cards() {
        return this.props.attachments.filter((a) => !a.isImage);
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
            body: _t('Do you really want to delete "%s"?', attachment.name),
            cancel: () => {},
            confirm: () => this.onConfirmUnlink(attachment),
        });
    }

    onClickAttachment(attachment) {
        this.fileViewer.open(attachment, this.props.attachments);
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

    getActions(attachment) {
        const res = [];
        if (this.showDelete) {
            res.push({
                label: _t("Remove"),
                icon: "fa fa-trash",
                onSelect: () => this.onClickUnlink(attachment),
            });
        }
        if (this.canDownload(attachment)) {
            res.push({
                label: _t("Download"),
                icon: "fa fa-download",
                onSelect: () => this.onClickDownload(attachment),
            });
        }
        return res;
    }

    get showDelete() {
        // in the composer they should all be implicitly deletable
        if (this.env.inComposer) {
            return true;
        }
        if (!this.attachment.isDeletable) {
            return false;
        }
        // in messages users are expected to delete the message instead of just the attachment
        return (
            !this.env.message ||
            this.env.message.hasTextContent ||
            (this.env.message && this.props.attachments.length > 1)
        );
    }
}
