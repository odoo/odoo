/* @odoo-module */

import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";
import { LinkPreviewList } from "@mail/core/common/link_preview_list";

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSequential, useVisible } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 */
export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection, LinkPreviewList };
    static props = ["thread"];
    static template = "mail.AttachmentPanel";

    setup() {
        this.state = useState({
            current: "media",
        });
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
    }

    /**
     * @return {Object<string, import("models").Attachment[]|import("models").LinkPreview[]>}
     */
    get attachmentsByDate() {
        const attachmentsByDate = {};
        let attachments = [];
        switch (this.state.current) {
            case "media":
            case "file":
                attachments = this.props.thread.attachments.filter((attachment) => {
                    return this.state.current === "media"
                        ? attachment.isMedia
                        : !attachment.isMedia;
                });
                break;

            case "link":
                this.props.thread.messages.forEach((message) => {
                    attachments.push(...(message.linkPreviews || []));
                });
                break;
        }
        for (const attachment of attachments) {
            (attachmentsByDate[attachment.monthYear] ??= []).push(attachment);
        }
        return attachmentsByDate;
    }

    get attachmentCategories() {
        return [
            ["media", "Media"],
            ["link", "Links"],
            ["file", "Files"],
        ];
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
