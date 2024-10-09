import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {function} unlinkAttachment
 * @extends {Component<Props, Env>}
 */
export class AttachmentUtils extends Component {
    static template = "";
    static props = ["unlinkAttachment"];

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    canDownload(attachment) {
        return !attachment.uploading && !this.env.inComposer;
    }

    getActions(attachment) {
        const res = [];
        if (this.showDelete ?? this.props.showDelete) {
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
}
