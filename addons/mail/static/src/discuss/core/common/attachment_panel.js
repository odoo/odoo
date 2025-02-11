/* @odoo-module */

import { DateSection } from "@mail/core/common/date_section";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { AttachmentList } from "@mail/core/common/attachment_list";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSequential, useVisible } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Props
 * @property {import("models").Thread} thread
 */
export class AttachmentPanel extends Component {
    static components = { ActionPanel, AttachmentList, DateSection };
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
    }

    /**
     * @return {Object<string, import("models").Attachment[]>}
     */
    get attachmentsByDate() {
        const attachmentsByDate = {};
        for (const attachment of this.props.thread.attachments) {
            const attachments = attachmentsByDate[attachment.monthYear] ?? [];
            attachments.push(attachment);
            attachmentsByDate[attachment.monthYear] = attachments;
        }
        return attachmentsByDate;
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
}
