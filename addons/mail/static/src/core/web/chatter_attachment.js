/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { LinkPreviewList } from "@mail/core/common/link_preview_list";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ChatterAttachment extends Component {
    static components = { AttachmentList, LinkPreviewList };
    static template = "mail.ChatterAttachment";
    static props = [ "thread"];

    setup() {
        this.state = useState({
            current: "media",
            media: this.props.thread.attachments.filter(attachment => attachment.isMedia).length,
            linkPreviews: this.props.thread.messages.reduce((count, message) => count + (message.linkPreviews && message.linkPreviews.length > 0 ? 1 : 0), 0),
            files: this.props.thread.attachments.filter(attachment => !attachment.isMedia).length,
        })
        this.attachmentUploadService = useService("mail.attachment_upload");
    }
    
    get mediaAttachments() {
        const attachments =  this.props.thread.attachments.filter(attachment => attachment.isMedia);
        this.state.media = attachments.length;
        return attachments ?? [];
    }

    get fileAttachments() {
        const attachments =  this.props.thread.attachments.filter(attachment => !attachment.isMedia);
        this.state.media = attachments.length;
        return attachments ?? [];
    }

    get linkAttachements() {
        const messages = this.props.thread.messages.map((message) => message.linkPreviews && message.linkPreviews.length > 0 ? message.linkPreviews[0] : null).filter(linkPreview => linkPreview !== null);
        this.state.linkPreviews = messages.length
        return messages;
    }

    handleTabSelection = (ev) => {
        if (ev.target.dataset.tab !== this.state.current) {
            this.state.current = ev.target.dataset.tab;
        }
        ev.target.classList.toggle("active", true);
    };

}
