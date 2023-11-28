/* @odoo-module */

import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { LinkPreview } from "@mail/core/common/link_preview";

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSequential, useVisible } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 */
export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection, LinkPreview };
    static props = ["thread"];
    static template = "mail.AttachmentPanel";

    setup() {
        this.sequential = useSequential();
        this.store = useService("mail.store");
        this.ormService = useService("orm");
        this.threadService = useService("mail.thread");
        this.attachmentUploadService = useService("mail.attachment_upload");
        onWillStart(() => {
            this.threadService.fetchMoreAttachments(this.props.thread);
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.notEq(this.props.thread)) {
                this.threadService.fetchMoreAttachments(nextProps.thread);
            }
        });
        const loadOlderState = useVisible("load-older", () => {
            if (loadOlderState.isVisible) {
                this.threadService.fetchMoreAttachments(this.props.thread);
            }
        });
        this.state = useState({
            current: "media",
        });
    }

    /**
     * @return {Object<string, import("models").Attachment[]>}
     */
    get mediaAttachmentsByDate() {
        const mediaAttachmentsByDate = {};
        const attachments = this.props.thread.attachments.filter(
            (attachment) => attachment.isMedia
        );
        for (const attachment of attachments) {
            const attachments = mediaAttachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            mediaAttachmentsByDate[attachment.monthYear] = attachments;
        }
        return mediaAttachmentsByDate;
    }

    /**
     * @return {Object<string, import("models").LinkPreview[]>}
     */
    get linkAttachmentsByDate() {
        const linkAttachmentsByDate = {};
        const linkPreviews = this.props.thread.messages
            .map((message) =>
                message.linkPreviews && message.linkPreviews.length > 0
                    ? message.linkPreviews[0]
                    : null
            )
            .filter((linkPreview) => linkPreview !== null);
        for (const attachment of linkPreviews) {
            const attachments = linkAttachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            linkAttachmentsByDate[attachment.monthYear] = attachments;
        }
        return linkAttachmentsByDate;
    }

    /**
     * @return {Object<string, import("models").Attachment[]>}
     */
    get filesAttachmentsByDate() {
        const fileAttachmentsByDate = {};
        const attachments = this.props.thread.attachments.filter(
            (attachment) => !attachment.isMedia
        );
        for (const attachment of attachments) {
            const attachments = fileAttachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            fileAttachmentsByDate[attachment.monthYear] = attachments;
        }
        return fileAttachmentsByDate;
    }

    get hasToggleAllowPublicUpload() {
        return (
            this.props.thread.model !== "mail.box" &&
            !["chatter", "chat"].includes(this.props.thread.type) &&
            this.store.self?.user?.isInternalUser
        );
    }

    toggleAllowPublicUpload() {
        this.sequential(() =>
            this.ormService.write("discuss.channel", [this.props.thread.id], {
                allow_public_upload: !this.props.thread.allow_public_upload,
            })
        );
    }
}
