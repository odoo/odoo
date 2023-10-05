/* @odoo-module */

import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { LinkAttachment } from "./link_attachment";

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSequential, useVisible } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 */
export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection, LinkAttachment };
    static props = ["thread"];
    static template = "mail.AttachmentPanel";

    setup() {
        this.sequential = useSequential();
        this.store = useService("mail.store");
        this.ormService = useService("orm");
        this.threadService = useService("mail.thread");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.state = useState({
            current: "media",
            media: this.props.thread.attachments.filter(attachment => attachment.isMedia).length,
            linkPreviews: this.props.thread.messages.reduce((count, message) => count + (message.linkPreviews && message.linkPreviews.length > 0 ? 1 : 0), 0),
            files: this.props.thread.attachments.filter(attachment => !attachment.isMedia).length,
        });
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
    }

    categorizeAttachmentsByMonthYear(attachments, filterAttachments) {
        const attachmentsArray = Array.from(attachments);
        const attachmentByMonthYear = {};
        for (const attachment of attachmentsArray) {
            if (filterAttachments(attachment)) {
                const { monthYear } = attachment;
                if(!attachmentByMonthYear[monthYear]){
                    attachmentByMonthYear[monthYear] = [];
                }
                attachmentByMonthYear[monthYear].push(attachment);
            }
        }
        return attachmentByMonthYear;
    }

    get hasToggleAllowPublicUpload() {
        return (
            this.props.thread.model !== "mail.box" &&
            this.props.thread.type !== "chat" &&
            this.store.user?.user?.isInternalUser
        );
    }

    toggleAllowPublicUpload() {
        this.sequential(() =>
            this.ormService.write("discuss.channel", [this.props.thread.id], {
                allow_public_upload: !this.props.thread.allow_public_upload,
            })
        );
    }

    categorizedAttachments(type) {
        const { attachments, messages } = this.props.thread;
        const linkAttachments = messages.map((message) => message.linkPreviews && message.linkPreviews.length > 0 ? message.linkPreviews[0] : null).filter(linkPreview => linkPreview !== null);
        switch (type) {
            case "media":
                this.state.media =  this.props.thread.attachments.filter(attachment => attachment.isMedia).length;
                return this.categorizeAttachmentsByMonthYear(
                    attachments,
                    (attachment) => attachment.isMedia
                );
            case "link":
                this.state.linkPreviews = this.props.thread.messages.reduce((count, message) => count + (message.linkPreviews && message.linkPreviews.length > 0 ? 1 : 0), 0);
                return this.categorizeAttachmentsByMonthYear(linkAttachments,() => true);
            case "file":
                this.state.files = this.props.thread.attachments.filter(attachment => !attachment.isMedia).length;
                return this.categorizeAttachmentsByMonthYear(
                    attachments,
                    (attachment) => !attachment.isMedia
                );
            default:
                return {};
        }
    }

    handleTabSelection = (ev) => {
        if (ev.target.dataset.tab !== this.state.current) {
            this.state.current = ev.target.dataset.tab;
        }
        ev.target.classList.toggle("active", true);
    };
}
