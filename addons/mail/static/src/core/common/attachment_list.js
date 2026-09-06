import { AttachmentDeleteDialog } from "@mail/core/common/attachment_delete_dialog";
import { Gif } from "@mail/core/common/gif";
import { MessageSearchState } from "@mail/core/common/message_search_hook";

import { Component, signal, t, useProps } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { download } from "@web/core/network/download";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

import { attClassObjectToString } from "@mail/utils/common/format";

class Actions extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "mail.Actions";
    props = useProps({
        actions: t.array(
            t.object({
                label: t.string(),
                icon: t.string(),
                iconClass: t.string().optional(),
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
    static components = { Actions, Dropdown, Gif };
    static template = "mail.AttachmentList";

    rootRef = signal.ref();

    setup() {
        super.setup();
        Object.assign(this, { attClassObjectToString, formatDate, formatDateTime });
        this.store = useService("mail.store");
        this.props = useProps({
            attachmentGroups: t.array(
                t.object({
                    attachment: t.instanceOf(this.store["ir.attachment"]),
                    duplicates: t.array(t.instanceOf(this.store["ir.attachment"])),
                })
            ),
            isSelecting: t.boolean().optional(false),
            messageSearch: t.instanceOf(MessageSearchState).optional(),
            onToggleSelected: t.function([t.instanceOf(this.store["ir.attachment"])]).optional(),
            selectedAttachments: t.array(t.instanceOf(this.store["ir.attachment"])).optional(),
            unlinkAttachments: t.function(
                [t.array(t.instanceOf(this.store["ir.attachment"]))],
                t.or([t.promise(), t.literal(undefined)])
            ),
        });
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.fileViewer = useFileViewer(this.rootRef);
        this.actionsMenuState = useDropdownState();
        this.isMobileOS = isMobileOS();
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    isSelected(attachment) {
        return Boolean(this.props.selectedAttachments?.some((selected) => selected.eq(attachment)));
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
     * @returns {Object.<string, boolean>}
     */
    getPreviewAttClass(attachment) {
        return { o_image: true };
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

    hasUnlinkConfirmation(attachment) {
        return true;
    }

    /**
     * @param {import("models").Attachment} attachment
     * @param {import("models").Attachment[]} [duplicates] every attachment the
     *  clicked one stands for, itself alone most of the time
     */
    onClickUnlink(attachment, duplicates = [attachment]) {
        if (this.env.inComposer) {
            this.props.unlinkAttachments(duplicates);
            return true;
        }
        if (duplicates.every((duplicate) => !this.hasUnlinkConfirmation(duplicate))) {
            this.onConfirmUnlink(duplicates);
            return true;
        }
        if (duplicates.length > 1) {
            return new Promise((resolve) => {
                this.dialog.add(
                    AttachmentDeleteDialog,
                    {
                        groups: [{ attachment, duplicates }],
                        onDelete: (attachments) => {
                            this.onConfirmUnlink(attachments);
                            resolve(true);
                        },
                    },
                    { onClose: () => resolve(false) }
                );
            });
        }
        return new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Delete Attachment"),
                body: _t(
                    'Are you sure you want to delete "%(name)s"?\nThis action cannot be undone.',
                    {
                        name: attachment.name,
                    }
                ),
                confirmLabel: _t("Delete Attachment"),
                cancel: () => resolve(false),
                confirm: () => {
                    this.onConfirmUnlink(duplicates);
                    resolve(true);
                },
            });
        });
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    onClickAttachment(attachment) {
        if (this.props.isSelecting) {
            this.props.onToggleSelected?.(attachment);
            return;
        }
        const attachments = this.props.attachmentGroups.map((group) => group.attachment);
        this.fileViewer.open(attachment, attachments, {
            onUnlink: (file) => this.onClickUnlink(file),
            canUnlink: (file) => this.showDelete(file),
        });
    }

    /**
     * @param {import("models").Attachment[]} attachments
     */
    async onConfirmUnlink(attachments) {
        await this.props.unlinkAttachments(attachments);
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

    /**
     * Compute the action items for the given attachment.
     *
     * @param {import("models").Attachment} attachment - The representative attachment for the actions.
     * @param {import("models").Attachment[]} [duplicates] - Array of duplicate attachments the action may operate on.
     * @returns {{label: string, icon: string, icon_class?: string, onSelect: function}[]} Array of action descriptors.
     */
    getActions(attachment, duplicates = [attachment]) {
        const res = [];
        if (this.showDelete(attachment)) {
            res.push({
                label: _t("Remove"),
                icon: "delete",
                iconClass: "oi-filled",
                onSelect: () => this.onClickUnlink(attachment, duplicates),
            });
        }
        if (!attachment.isImage && attachment.type === "url") {
            res.push({
                label: _t("Open Link"),
                icon: "open_in_new",
                onSelect: () => browser.open(attachment.url, "_blank"),
            });
        } else if (this.canDownload(attachment)) {
            res.push({
                label: _t("Download"),
                icon: "download",
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
            (this.env.message && this.props.attachmentGroups.length > 1)
        );
    }

    /**
     * @param {import("models").Attachment} attachment
     */
    showUploaded(attachment) {
        return !attachment.isImage && !attachment.uploading && this.env.inComposer;
    }
}
