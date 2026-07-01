import { Gif } from "@mail/core/common/gif";
import { MessageSearchState } from "@mail/core/common/message_search_hook";

import { Component, props, signal, t } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { download } from "@web/core/network/download";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

import { attClassObjectToString } from "@mail/utils/common/format";

class Actions extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "mail.Actions";
    props = props({
        actions: t.array(
            t.object({
                label: t.string(),
                icon: t.string(),
                onSelect: t.function([t.instanceOf(Event)]),
            })
        ),
    });

    setup() {
        super.setup();
        this.actionsMenuState = useDropdownState();
    }
}

export class AttachmentList extends Component {
    static components = { Actions, Gif };
    static template = "mail.AttachmentList";

    // make this available for class evaluation in the template
    attClassObjectToString = attClassObjectToString;
    rootRef = signal(null);

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            attachments: t.array(t.instanceOf(this.store["ir.attachment"].Class)),
            messageSearch: t.instanceOf(MessageSearchState).optional(),
            unlinkAttachment: t.function([t.instanceOf(this.store["ir.attachment"].Class)]),
        });
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.fileViewer = useFileViewer();
        this.actionsMenuState = useDropdownState();
        this.isMobileOS = isMobileOS();
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
        download({
            data: {},
            url: attachment.downloadUrl,
        });
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    onClickUnlink(attachment) {
        if (this.env.inComposer) {
            return this.props.unlinkAttachment(attachment);
        }
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Delete Attachment"),
                body: _t(
                    'Are you sure you want to delete "%s"?\nThis action cannot be undone.',
                    attachment.name
                ),
                confirmLabel: _t("Delete Attachment"),
                cancel: () => resolve(false),
                confirm: () => {
                    this.onConfirmUnlink(attachment);
                    resolve(true);
                },
            });
        });
    }

    onClickAttachment(attachment) {
        this.fileViewer.open(attachment, this.props.attachments, {
            onUnlink: this.onClickUnlink.bind(this),
            canUnlink: (file) => this.showDelete(file),
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

    getActions(attachment) {
        const res = [];
        if (this.showDelete(attachment)) {
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

    showDelete(attachment) {
        // in the composer they should all be implicitly deletable
        if (this.env.inComposer) {
            return true;
        }
        if (!attachment.isDeletable) {
            return false;
        }
        // in messages users are expected to delete the message instead of just the attachment
        return (
            !this.env.message ||
            this.env.message.hasTextContent ||
            (this.env.message && this.props.attachments.length > 1)
        );
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    showUploaded(attachment) {
        return !attachment.isImage && !attachment.uploading && this.env.inComposer;
    }
}
